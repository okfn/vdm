import logging
# logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('vdm')

from sqlalchemy.orm import object_session, class_mapper

import vdm.sqlalchemy
from vdm.sqlalchemy import Changeset, ChangeObject
from vdm.sqlalchemy.model import get_object_id
from demo import *

_clear = Session.expunge_all

def all_revisions(obj):
    objid = get_object_id(obj)
    alldata = Session.query(ChangeObject).all()
    out = Session.query(ChangeObject).filter_by(object_id=objid
            ).join('changeset'
                ).order_by(Changeset.timestamp.desc())
    return list(out)
    
class Test_01_SQLAlchemySession:
    @classmethod
    def setup_class(self):
        repo.rebuild_db()
    @classmethod
    def teardown_class(self):
        Session.remove()

    def test_1(self):
        assert not hasattr(Session, 'revision')
        assert vdm.sqlalchemy.SQLAlchemySession.at_HEAD(Session)
        rev = Changeset()
        vdm.sqlalchemy.SQLAlchemySession.set_revision(Session, rev)
        assert vdm.sqlalchemy.SQLAlchemySession.at_HEAD(Session)
        assert Session.revision is not None
        out = vdm.sqlalchemy.SQLAlchemySession.get_revision(Session)
        assert out == rev
        out = vdm.sqlalchemy.SQLAlchemySession.get_revision(Session())
        assert out == rev
        assert vdm.sqlalchemy.SQLAlchemySession.at_HEAD(Session)
        assert vdm.sqlalchemy.SQLAlchemySession.at_HEAD(Session())
        Session.remove()


class Test_02_Versioning:
    @classmethod
    def setup_class(self):
        repo.rebuild_db()

        logger.debug('===== STARTING REV 1')
        session = Session()
        rev1 = Changeset()
        session.add(rev1)
        vdm.sqlalchemy.SQLAlchemySession.set_revision(session, rev1)

        self.name1 = 'anna'
        self.name2 = 'warandpeace'
        self.title1 = 'XYZ'
        self.title2 = 'ABC'
        self.notes1 = u'Here\nare some\nnotes'
        self.notes2 = u'Here\nare no\nnotes'
        lic1 = License(name='blah', open=True)
        lic2 = License(name='foo', open=True)
        p1 = Package(name=self.name1, title=self.title1, license=lic1, notes=self.notes1)
        p2 = Package(name=self.name2, title=self.title1, license=lic1)
        session.add_all([lic1,lic2,p1,p2])

        logger.debug('***** Committing/Flushing Rev 1')
        session.commit()
        # can only get it after the flush
        self.rev1_id = rev1.id
        self.p2_objid = get_object_id(p2)
        _clear()
        Session.remove()

        logger.debug('===== STARTING REV 2')
        session = Session()
        rev2 = Changeset()
        session.add(rev2)
        vdm.sqlalchemy.SQLAlchemySession.set_revision(session, rev2)
        outlic1 = Session.query(License).filter_by(name='blah').first()
        outlic2 = Session.query(License).filter_by(name='foo').first()
        outlic2.open = False
        outp1 = Session.query(Package).filter_by(name=self.name1).one()
        outp2 = Session.query(Package).filter_by(name=self.name2).one()
        outp1.title = self.title2
        outp1.notes = self.notes2
        outp1.license = outlic2
        t1 = Tag(name='geo')
        session.add_all([outp1,outp2,t1])
        outp1.tags = [t1]
        Session.delete(outp2)
        # session.flush()
        session.commit()
        # must do this after flush as timestamp not set until then
        self.ts2 = rev2.timestamp
        self.rev2_id = rev2.id
        Session.remove()

    @classmethod
    def teardown_class(self):
        repo.rebuild_db()
        Session.remove()

    def test_01_revisions_exist(self):
        revs = Session.query(Changeset).all()
        assert len(revs) == 2
        # also check order (youngest first)
        print [ rev.timestamp for rev in revs ]
        assert revs[0].timestamp > revs[1].timestamp

    def test_02_revision_youngest(self):
        rev = Changeset.youngest(Session)
        assert rev.timestamp == self.ts2

    def test_03_basic(self):
        assert Session.query(License).count() == 2, Session.query(License).count()
        assert Session.query(Package).count() == 1, Session.query(Package).count()

    def test_04_all_revisions(self):
        p1 = Session.query(Package).filter_by(name=self.name1).one()
        assert len(all_revisions(p1)) == 2
        # problem here is that it might pass even if broken because ordering of
        # uuid ids is 'right' 
        revs = [ pr.changeset for pr in all_revisions(p1) ]
        assert revs[0].timestamp > revs[1].timestamp, revs

    def test_05_basic_2(self):
        # should be at HEAD (i.e. rev2) by default 
        p1 = Session.query(Package).filter_by(name=self.name1).one()
        assert p1.license.open == False
        # TODO: reinstate tags tests ...
        # assert len(p1.tags) == 1

    def test_07_operation_type(self):
        p1 = Session.query(Package).filter_by(name=self.name1).one()
        changeobjects = all_revisions(p1)

        _create = ChangeObject.OperationType.CREATE
        optype = changeobjects[-1].operation_type 
        assert optype == _create, optype

        optype = changeobjects[0].operation_type 
        assert optype == ChangeObject.OperationType.UPDATE

        p2_changeobjects = Session.query(ChangeObject).filter_by(object_id=self.p2_objid).all()
        p2_changeobjects = sorted(
                p2_changeobjects,
                lambda x,y: cmp(x.changeset.timestamp, y.changeset.timestamp)
                )
        optype = p2_changeobjects[-1].operation_type
        print p2_changeobjects
        assert optype == ChangeObject.OperationType.DELETE, optype

    def test_09_versioning(self):
        p1 = Session.query(Package).filter_by(name=self.name1).one()
        changeobjects = all_revisions(p1)
        co = changeobjects[-1]
        assert co.data['name'] == self.name1
        assert co.data['title'] == self.title1

#    def test_10_traversal_normal_fks_and_state_at_same_time(self):
#        p2 = Session.query(Package).filter_by(name=self.name2).one()
#        rev1 = Session.query(Revision).get(self.rev1_id)
#        p2r1 = p2.get_as_of(rev1)
#        assert p2r1.state == State.ACTIVE
#
#    def test_11_versioning_traversal_fks(self):
#        p1 = Session.query(Package).filter_by(name=self.name1).one()
#        rev1 = Session.query(Revision).get(self.rev1_id)
#        p1r1 = p1.get_as_of(rev1)
#        assert p1r1.license.open == True
#
#    def test_12_versioning_m2m_1(self):
#        p1 = Session.query(Package).filter_by(name=self.name1).one()
#        rev1 = Session.query(Revision).get(self.rev1_id)
#        ptag = p1.package_tags[0]
#        # does not exist
#        assert ptag.get_as_of(rev1) == None
#
#    def test_13_versioning_m2m(self):
#        p1 = Session.query(Package).filter_by(name=self.name1).one()
#        rev1 = Session.query(Revision).get(self.rev1_id)
#        p1r1 = p1.get_as_of(rev1)
#        assert len(p1.tags_active) == 0
#        # NB: deleted includes tags that were non-existent
#        assert len(p1.tags_deleted) == 1
#        assert len(p1.tags) == 0
#        assert len(p1r1.tags) == 0
#    
#    def test_14_revision_has_state(self):
#        rev1 = Session.query(Revision).get(self.rev1_id)
#        assert rev1.state == State.ACTIVE
#
#    def test_15_diff(self):
#        p1 = Session.query(Package).filter_by(name=self.name1).one()
#        pr2, pr1 = all_revisions(p1)
#        # pr1, pr2 = prs[::-1]
#        
#        diff = p1.diff_revisioned_fields(pr2, pr1, Package)
#        assert diff['title'] == '- XYZ\n+ ABC', diff['title']
#        assert diff['notes'] == '  Here\n- are some\n+ are no\n  notes', diff['notes']
#        assert diff['license_id'] == '- 1\n+ 2', diff['license_id']
#
#        diff1 = p1.diff(pr2.changeset, pr1.changeset)
#        assert diff1 == diff, (diff1, diff)
#
#        diff2 = p1.diff()
#        assert diff2 == diff, (diff2, diff)
#
#    def test_16_diff_2(self):
#        '''Test diffing at a revision where just created.'''
#        p1 = Session.query(Package).filter_by(name=self.name1).one()
#        pr2, pr1 = all_revisions(p1)
#
#        diff1 = p1.diff(to_revision=pr1.changeset)
#        assert diff1['title'] == u'- None\n+ XYZ', diff1


class _Test_03_StatefulVersioned:
    @classmethod
    def setup_class(self):
        repo.rebuild_db()
        logger.info('====== TestVersioning2: start')

        # create a package with some tags
        rev1 = repo.new_revision()
        self.name1 = 'anna'
        p1 = Package(name=self.name1)
        t1 = Tag(name='geo')
        t2 = Tag(name='geo2')
        p1.tags.append(t1)
        p1.tags.append(t2)
        Session.add_all([p1,t1,t2])
        Session.commit()
        self.rev1_id = rev1.id
        Session.remove()
        
        # now remove those tags
        logger.debug('====== start Changeset 2')
        rev2 = repo.new_revision()
        newp1 = Session.query(Package).filter_by(name=self.name1).one()
        # either one works
        newp1.tags = []
        # newp1.tags_active.clear()
        assert len(newp1.tags_active) == 0
        Session.commit()
        self.rev2_id = rev2.id
        Session.remove()

        # now add one of them back
        logger.debug('====== start Changeset 3')
        rev3 = repo.new_revision()
        newp1 = Session.query(Package).filter_by(name=self.name1).one()
        self.tagname1 = 'geo'
        t1 = Session.query(Tag).filter_by(name=self.tagname1).one()
        assert t1
        newp1.tags.append(t1)
        repo.commit_and_remove()

    @classmethod
    def teardown_class(self):
        Session.remove()

    def test_0_remove_and_readd_m2m(self):
        p1 = Session.query(Package).filter_by(name=self.name1).one()
        assert len(p1.package_tags) == 2, p1.package_tags
        assert len(p1.tags_active) == 1, p1.tags_active
        assert len(p1.tags) == 1
        Session.remove()

    def test_1_underlying_is_right(self):
        rev1 = Session.query(Changeset).get(self.rev1_id)
        ptrevs = Session.query(PackageTagChangeset).filter_by(revision_id=rev1.id).all()
        assert len(ptrevs) == 2
        for pt in ptrevs:
            assert pt.state == State.ACTIVE

        rev2 = Session.query(Changeset).get(self.rev2_id)
        ptrevs = Session.query(PackageTagChangeset).filter_by(revision_id=rev2.id).all()
        assert len(ptrevs) == 2
        for pt in ptrevs:
            assert pt.state == State.DELETED
    
    # test should be higher up but need at least 3 revisions for problem to
    # show up
    def test_2_get_as_of(self):
        p1 = Session.query(Package).filter_by(name=self.name1).one()
        rev2 = Session.query(Changeset).get(self.rev2_id)
        # should be 2 deleted and 1 as None
        ptrevs = [ pt.get_as_of(rev2) for pt in p1.package_tags ]
        print ptrevs
        print Session.query(PackageTagChangeset).all()
        assert ptrevs[0].changeset_id == rev2.id

    def test_3_remove_and_readd_m2m_2(self):
        num_package_tags = 2
        rev1 = Session.query(Changeset).get(self.rev1_id)
        p1 = Session.query(Package).filter_by(name=self.name1).one()
        p1rev = p1.get_as_of(rev1)
        # NB: relations on revision object proxy to continuity
        # (though with get_as_of revision set)
        assert len(p1rev.package_tags) == num_package_tags
        assert len(p1rev.tags) == 2
        Session.remove()

        rev2 = Session.query(Changeset).get(self.rev2_id)
        p1 = Session.query(Package).filter_by(name=self.name1).one()
        p2rev = p1.get_as_of(rev2)
        assert p2rev.__class__ == PackageChangeset
        assert len(p2rev.package_tags) == num_package_tags
        print rev2.id
        print p2rev.tags_active
        assert len(p2rev.tags) == 0


class _Test_04_StatefulVersioned2:
    '''Similar to previous but setting m2m list using existing objects'''

    def setup(self):
        Session.remove()
        repo.rebuild_db()
        logger.info('====== TestStatefulVersioned2: start')

        # create a package with some tags
        rev1 = repo.new_revision()
        self.name1 = 'anna'
        p1 = Package(name=self.name1)
        t1 = Tag(name='geo')
        p1.tags.append(t1)
        Session.add_all([p1,t1])
        Session.commit()
        self.rev1_id = rev1.id
        Session.remove()

    def setup_method(self, name=''):
        self.setup()
        
    @classmethod
    def teardown_class(self):
        Session.remove()

    def _test_package_tags(self, check_all_pkg_tags=True):
        p1 = Session.query(Package).filter_by(name=self.name1).one()
        assert len(p1.package_tags) == 2, p1.package_tags
        all_pkg_tags = Session.query(PackageTag).all()
        if check_all_pkg_tags:
            assert len(all_pkg_tags) == 2

    def _test_tags(self):
        p1 = Session.query(Package).filter_by(name=self.name1).one()
        assert len(p1.tags) == 2, p1.tags

    def test_1(self):
        rev2 = repo.new_revision()
        newp1 = Session.query(Package).filter_by(name=self.name1).one()
        t1 = Session.query(Tag).filter_by(name='geo').one()
        t2 = Tag(name='geo2')
        newp1.tags = [ t1, t2 ]
        repo.commit_and_remove()

        self._test_package_tags()
        self._test_tags()
    
    def test_2(self):
        rev2 = repo.new_revision()
        newp1 = Session.query(Package).filter_by(name=self.name1).one()
        t1 = Session.query(Tag).filter_by(name='geo').one()
        t2 = Tag(name='geo2')
        print '**** setting tags'
        newp1.tags[:] = [ t1, t2 ]
        repo.commit_and_remove()

        # TODO: (?) check on No of PackageTags fails
        # the story is that an extra PackageTag for first tag gets constructed
        # even though existing in deleted state (as expected)
        # HOWEVER (unlike in 3 other cases in this class) this PackageTag is
        # *already committed* when it arrives at _check_for_existing_on_add and
        # therefore expunge has no effect on it (we'd need to delete and that
        # may start getting 'hairy' ...)
        self._test_package_tags(check_all_pkg_tags=False)
        self._test_tags()

    def test_3(self):
        rev2 = repo.new_revision()
        newp1 = Session.query(Package).filter_by(name=self.name1).one()
        t1 = Session.query(Tag).filter_by(name='geo').one()
        t2 = Tag(name='geo2')
        newp1.tags[0] = t1
        newp1.tags.append(t2)
        repo.commit_and_remove()

        self._test_package_tags()
        self._test_tags()

    def test_4(self):
        rev2 = repo.new_revision()
        newp1 = Session.query(Package).filter_by(name=self.name1).one()
        t1 = Session.query(Tag).filter_by(name='geo').one()
        t2 = Tag(name='geo2')
        newp1.tags = [ t1, t2 ]
        newp1.tags[0] = t1
        del newp1.tags[1]
        newp1.tags.append(t2)
        # NB: doing this the other way round will result in 3 PackageTags
        # newp1.tags.append(t2)
        # del newp1.tags[1]
        # this is because our system can't work out that we've just added and
        # deleted the same tag
        repo.commit_and_remove()

        self._test_package_tags()
        self._test_tags()


class _Test_05_RevertAndPurge:

    @classmethod
    def setup_class(self):
        Session.remove()
        repo.rebuild_db()

        rev1 = Changeset()
        Session.add(rev1)
        vdm.sqlalchemy.SQLAlchemySession.set_revision(Session, rev1)
        
        self.name1 = 'anna'
        p1 = Package(name=self.name1)
        p2 = Package(name='blahblah')
        Session.add_all([p1,p2])
        repo.commit_and_remove()

        self.name2 = 'warandpeace'
        self.lname = 'testlicense'
        rev2 = repo.new_revision()
        p1 = Session.query(Package).filter_by(name=self.name1).one()
        p1.name = self.name2
        l1 = License(name=self.lname)
        Session.add_all([p1,l1])
        repo.commit()
        self.rev2id = rev2.id
        Session.remove()

    @classmethod
    def teardown_class(self):
        Session.remove()
        repo.rebuild_db()

    def test_basics(self):
        revs = Session.query(Changeset).all()
        assert len(revs) == 2
        p1 = Session.query(Package).filter_by(name=self.name2).one()
        assert p1.name == self.name2
        assert len(Session.query(Package).all()) == 2

    def test_list_changes(self):
        rev2 = Session.query(Changeset).get(self.rev2id)
        out = repo.list_changes(rev2)
        assert len(out) == 3
        assert len(out[Package]) == 1, out
        assert len(out[License]) == 1, out

    def test_purge_revision(self):
        logger.debug('BEGINNING PURGE REVISION')
        Session.remove()
        rev2 = Session.query(Changeset).get(self.rev2id)
        repo.purge_revision(rev2)
        revs = Session.query(Changeset).all()
        assert len(revs) == 1
        p1 = Session.query(Package).filter_by(name=self.name1).first()
        assert p1 is not None
        assert len(Session.query(License).all()) == 0
        pkgs = Session.query(Package).all()
        assert len(pkgs) == 2, pkgrevs
        pkgrevs = Session.query(PackageChangeset).all()
        assert len(pkgrevs) == 2, pkgrevs

