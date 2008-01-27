from sqlalchemy.orm import object_session

from demo import *

def test_0():
    assert package_revision_table.name == 'package_revision'
    print package_revision_table.c
    assert 'state_id' in package_revision_table.c

def test_1():
    print Package.c.keys()
    assert len(Package.c.keys()) > 0
    print Package.c.keys()
    assert 'revision_id' in Package.c.keys()

class TestMain:

    def teardown_class(self):
        SessionObject.close()
        SessionObject.remove()
    
    def setup_class(self):
        # also acts as general setup
        self.name1 = 'anna'
        self.title1 = 'XYZ'
        self.title2 = 'ABC'
        lic1 = License(name='blah', open=True)
        p1 = Package(name=self.name1, title=self.title1, license=lic1)
        t1 = Tag(name='geo')
        # t2 = Tag(name='novel')
        p1.tags.append(t1)
        rev1 = Revision() 
        set_revision(session, rev1)
        assert object_session(p1) == session
        assert object_session(lic1) == session
        session.flush()
        print 'after flush'
        assert rev1.id
        assert p1.revision == rev1
        # will fail because would need to refresh object to get fk ids
        # assert p1.revision_id == rev1.id
        # can only get it after the flush
        self.rev1_id = rev1.id
        session.clear()

        rev2 = Revision()
        set_revision(session, rev2)
        outlic1 = License.query.filter_by(name='blah').first()
        outlic1.open = False
        outp1 = Package.query.filter_by(name=self.name1).first()
        outp1.title = self.title2
        outp1.tags = []
        session.flush()
        # must do this after flush as timestamp not set until then
        self.ts2 = rev2.timestamp
        session.clear()
        
    def test_revisions_exist(self):
        revs = Revision.query.all()
        assert len(revs) == 2

    def test_basic(self):
        assert len(License.query.all()) == 1
        assert len(Package.query.all()) == 1
        assert len(PackageRevision.query.all()) == 2
        assert len(LicenseRevision.query.all()) == 2

    def test_basic_2(self):
        # should be at HEAD (i.e. rev2) by default 
        p1 = Package.query.filter_by(name=self.name1).one()
        assert p1.license.open == False
        assert p1.revision.timestamp == self.ts2
        assert p1.tags == []

    def test_versioning_1(self):
        p1 = Package.query.filter_by(name=self.name1).one()
        rev1 = Revision.query.get(self.rev1_id)
        p1r1 = p1.get_as_of(rev1)
        assert p1r1.name == self.name1
        assert p1r1.title == self.title1

    def test_versioning_2(self):
        p1 = Package.query.filter_by(name=self.name1).one()
        rev1 = Revision.query.get(self.rev1_id)
        p1r1 = p1.get_as_of(rev1)
        # assert p1r1.license.open == True
        # assert len(p1r1.tags) == 0

