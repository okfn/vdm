from sqlalchemy.orm import object_session, class_mapper

import vdm.sqlalchemy
from demo import *

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('vdm')


class TestVersioning:

    @classmethod
    def setup_class(self):
        rebuild_db()
        # does not work if just done in rebuild_db (WHY!!!???)
        make_states()

        logger.debug('===== STARTING REV 1')
        session = Session()
        rev1 = Revision() 
        vdm.sqlalchemy.set_revision(session, rev1)

        self.name1 = 'anna'
        self.name2 = 'warandpeace'
        self.title1 = 'XYZ'
        self.title2 = 'ABC'
        lic1 = License(name='blah', open=True)
        p1 = Package(name=self.name1, title=self.title1, license=lic1)
        p2 = Package(name=self.name2, title=self.title1, license=lic1)
        # t1 = Tag(name='geo')
        # p1.tags = [t1]

        logger.debug('***** Committing/Flushing Rev 1')
        session.commit()
        # can only get it after the flush
        self.rev1_id = rev1.id
        Session.clear()
        Session.remove()

        logger.debug('===== STARTING REV 2')
        session = Session()
        session.begin()
        rev2 = Revision()
        vdm.sqlalchemy.set_revision(session, rev2)
        outlic1 = License.query.filter_by(name='blah').first()
        outlic1.open = False
        outp1 = Package.query.filter_by(name=self.name1).one()
        outp2 = Package.query.filter_by(name=self.name2).one()
        outp1.title = self.title2
        # outp1.tags = []
        t1 = Tag(name='geo')
        outp1.tags = [t1]
        outp2.delete()
        # session.flush()
        session.commit()
        # must do this after flush as timestamp not set until then
        self.ts2 = rev2.timestamp
        Session.clear()

    def teardown_class(self):
        Session.remove()
        
    def test_revisions_exist(self):
        revs = Revision.query.all()
        assert len(revs) == 2
        # also check order (youngest first)
        assert revs[0].id > revs[1].id

    def test_revision_youngest(self):
        rev = Revision.youngest()
        assert rev.timestamp == self.ts2

    def test_basic(self):
        assert len(License.query.all()) == 1
        assert len(Package.query.all()) == 2
        assert 'revision_id' in LicenseRevision.c
        assert len(LicenseRevision.query.all()) == 2
        assert len(PackageRevision.query.all()) == 4

    def test_all_revisions(self):
        p1 = Package.query.filter_by(name=self.name1).one()
        assert len(p1.all_revisions) == 2

    def test_basic_2(self):
        # should be at HEAD (i.e. rev2) by default 
        p1 = Package.query.filter_by(name=self.name1).one()
        assert p1.license.open == False
        assert p1.revision.timestamp == self.ts2
        # assert p1.tags == []
        assert len(p1.tags) == 1

    def test_basic_continuity(self):
        p1 = Package.query.filter_by(name=self.name1).one()
        pr1 = PackageRevision.query.filter_by(name=self.name1).first()
        table = class_mapper(PackageRevision).mapped_table
        print table.c.keys()
        print pr1.continuity_id
        assert pr1.continuity == p1

    def test_basic_state(self):
        p1 = Package.query.filter_by(name=self.name1).one()
        p2 = Package.query.filter_by(name=self.name2).one()
        assert p1.state
        assert p1.state.name == ACTIVE
        assert p2.state.name == DELETED

    def test_versioning_0(self):
        p1 = Package.query.filter_by(name=self.name1).one()
        rev1 = Revision.query.get(self.rev1_id)
        p1r1 = p1.get_as_of(rev1)
        assert p1r1.continuity == p1

    def test_versioning_1(self):
        p1 = Package.query.filter_by(name=self.name1).one()
        rev1 = Revision.query.get(self.rev1_id)
        p1r1 = p1.get_as_of(rev1)
        assert p1r1.name == self.name1
        assert p1r1.title == self.title1

    def test_traversal_normal_fks_and_state_at_same_time(self):
        p2 = Package.query.filter_by(name=self.name2).one()
        rev1 = Revision.query.get(self.rev1_id)
        p2r1 = p2.get_as_of(rev1)
        assert p2r1.state.name == ACTIVE

    def test_versioning_traversal_fks(self):
        p1 = Package.query.filter_by(name=self.name1).one()
        rev1 = Revision.query.get(self.rev1_id)
        p1r1 = p1.get_as_of(rev1)
        assert p1r1.license.open == True

    def test_versioning_m2m_1(self):
        p1 = Package.query.filter_by(name=self.name1).one()
        rev1 = Revision.query.get(self.rev1_id)
        ptag = p1.package_tags[0]
        # does not exist
        assert ptag.get_as_of(rev1) == None

    def test_versioning_m2m(self):
        p1 = Package.query.filter_by(name=self.name1).one()
        rev1 = Revision.query.get(self.rev1_id)
        p1r1 = p1.get_as_of(rev1)
        assert len(p1.tags_active) == 0
        assert len(p1.tags_deleted) == 1
        assert len(p1.tags) == 0
        assert len(p1r1.tags) == 0
       
class TestVersioning2:

    @classmethod
    def setup_class(self):
        rebuild_db()
        logger.debug('====== TestVersioning2: start')

        rev1 = Revision() 
        vdm.sqlalchemy.set_revision(Session, rev1)
        
        self.name1 = 'anna'
        p1 = Package(name=self.name1)
        t1 = Tag(name='geo')
        t2 = Tag(name='geo2')
        p1.tags.append(t1)
        p1.tags.append(t2)
        Session.commit()
    
        # can only get it after the flush
        self.rev1_id = rev1.id
        Session.remove()

        # rev2 = Revision() 
        # vdm.sqlalchemy.set_revision(Session, rev2)

    def test_1(self):
        # rev1 = Revision.query.get(self.rev1_id)
        p1 = Package.query.filter_by(name=self.name1).one()
        print p1.tags
        assert len(p1.tags) == 2

    def test_revision_has_state(self):
        rev1 = Revision.query.get(self.rev1_id)
        assert rev1.state.name == ACTIVE

