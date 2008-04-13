from sqlalchemy.orm import object_session

from demo import *


class TestVersioning:

    def teardown_class(self):
        Session.close()
        Session.remove()
    
    def setup_class(self):
        rev1 = Revision() 
        session = Session()
        set_revision(session, rev1)

        self.name1 = 'anna'
        self.name2 = 'warandpeace'
        self.title1 = 'XYZ'
        self.title2 = 'ABC'
        lic1 = License(name='blah', open=True)
        p1 = Package(name=self.name1, title=self.title1, license=lic1)
        p2 = Package(name=self.name2, title=self.title1, license=lic1)
        t1 = Tag(name='geo')
        # p1.tags.append(t1)

        session.flush()
        # assert rev1.id
        # assert p1.revision == rev1
        # can only get it after the flush
        self.rev1_id = rev1.id
        Session.clear()

        session = Session()
        rev2 = Revision()
        set_revision(session, rev2)
        outlic1 = License.query.filter_by(name='blah').first()
        outlic1.open = False
        outp1 = Package.query.filter_by(name=self.name1).one()
        outp2 = Package.query.filter_by(name=self.name2).one()
        outp1.title = self.title2
        outp1.tags = []
        outp2.delete()
        session.flush()
        # must do this after flush as timestamp not set until then
        self.ts2 = rev2.timestamp
        Session.clear()
        
    def test_revisions_exist(self):
        revs = Revision.query.all()
        assert len(revs) == 2

    def test_basic(self):
        assert len(License.query.all()) == 1
        assert len(Package.query.all()) == 2
        assert 'revision_id' in LicenseRevision.c
        assert len(LicenseRevision.query.all()) == 2
        assert len(PackageRevision.query.all()) == 4

    def test_basic_2(self):
        # should be at HEAD (i.e. rev2) by default 
        p1 = Package.query.filter_by(name=self.name1).one()
        assert p1.license.open == False
        assert p1.revision.timestamp == self.ts2
        assert p1.tags == []

    def test_basic_continuity(self):
        p1 = Package.query.filter_by(name=self.name1).one()
        pr1 = PackageRevision.query.filter_by(name=self.name1).first()
        print pr1.c.keys()
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

    def test_versioning_m2m(self):
        p1 = Package.query.filter_by(name=self.name1).one()
        rev1 = Revision.query.get(self.rev1_id)
        p1r1 = p1.get_as_of(rev1)
        assert len(p1r1.tags) == 0
        # TODO: more testing of the m2m relation ...

