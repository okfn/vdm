import pprint

from sqlalchemy.orm import object_session

from demo import *

def test_column_create():
    col = Column('abc', Integer, ForeignKey('xyz.id'))
    # FK does *not* work
    assert len(col.foreign_keys) == 0
    tab = Table('tab', metadata,
        Column('abc', Integer, ForeignKey('xyz.id')),
        )
    col0 = tab.c['abc']
    fk0 = col0.foreign_keys[0]
    assert len(col0.foreign_keys) == 1
    assert fk0.parent

    tab2 = Table('tab', metadata)
    tab2.append_column(
        Column('abc', Integer, ForeignKey('xyz.id'))
        )
    assert len(tab2.c['abc'].foreign_keys) == 1
    assert tab2.c['abc'].foreign_keys[0].parent

    tab3 = Table('tab', metadata)
    col3 = col0.copy()
    col3.foreign_keys.add(tab.c['abc'].foreign_keys[0].copy())
    tab3.append_column(col3)
    assert len(tab3.c['abc'].foreign_keys) == 1
    # fails
    # assert tab3.c['abc'].foreign_keys[0].parent

    tab3 = Table('tab', metadata)
    col3 = col0.copy()
    tab3.append_column(col3)
    col3.foreign_keys.add(ForeignKey(col0.key)) 
    assert len(tab3.c['abc'].foreign_keys) == 1
    # fails
    # assert tab3.c['abc'].foreign_keys[0].parent


    tab4 = Table('tab', metadata)
    tab4.append_column(
        col0.copy()
        )
    tab4.c[col0.key].append_foreign_key(fk0.copy())
    assert len(tab4.c['abc'].foreign_keys) == 1
    assert tab4.c['abc'].foreign_keys[0].parent

def test_copy_column():
    t1 = package_table
    newtable = Table('mytable', metadata)
    copy_column('id', t1, newtable)
    outcol = newtable.c['id']
    assert outcol.name == 'id'
    assert outcol.primary_key == True
    # pick one with a fk
    name = 'license_id'
    copy_column(name, t1, newtable)
    incol = t1.c[name]
    outcol = newtable.c[name]
    assert outcol != incol
    assert outcol.key == incol.key
    assert len(incol.foreign_keys) == 1
    assert len(outcol.foreign_keys) == 1
    infk = incol.foreign_keys[0]
    outfk = outcol.foreign_keys[0]
    assert infk.parent
    assert outfk.parent

def test_table_copy():
    t1 = package_table
    newtable = Table('newtable', metadata)
    copy_table(t1, newtable)
    assert len(newtable.c) == len(t1.c)
    # pick one with a fk
    incol = t1.c['license_id']
    outcol = None
    for col in newtable.c:
        if col.name == 'license_id':
            outcol = col
    assert outcol != incol
    assert outcol.key == incol.key
    assert len(incol.foreign_keys) == 1
    assert len(outcol.foreign_keys) == 1
    infk = incol.foreign_keys[0]
    outfk = outcol.foreign_keys[0]
    assert infk.parent
    assert outfk.parent

def test_package_tag_table():
    col = package_tag_table.c['tag_id']
    assert len(col.foreign_keys) == 1

def test_make_stateful():
    assert 'state_id' in package_table.c

def test_make_revision_table():
    assert package_revision_table.name == 'package_revision'
    assert 'revision_id' in package_table.c
    assert 'state_id' in package_revision_table.c
    assert 'revision_id' in package_revision_table.c
    # very crude ...
    assert len(package_revision_table.c) == len(package_table.c) + 1
    # these tests may seem odd but they would incorporated following a bug
    # where this was *not* the case
    base = package_table
    rev = package_revision_table
    # base = license_table
    # rev = license_revision_table
    colname = 'state_id'
    # crude (could be more specific about the fk)
    assert len(base.c['state_id'].foreign_keys) == 1
    assert len(rev.c['state_id'].foreign_keys) == 1
    assert len(rev.c['revision_id'].foreign_keys) == 1
    assert rev.c['revision_id'].primary_key
    assert rev.c['id'].primary_key
    print rev.primary_key.columns
    assert len(rev.primary_key.columns) == 2

def test_accessing_columns_on_object():
    print Package.c.keys()
    assert len(Package.c.keys()) > 0
    print Package.c.keys()
    assert 'revision_id' in Package.c.keys()


class TestMain:

    def teardown_class(self):
        SessionObject.close()
        SessionObject.remove()
    
    def setup_class(self):
        self.name1 = 'anna'
        self.name2 = 'warandpeace'
        self.title1 = 'XYZ'
        self.title2 = 'ABC'
        lic1 = License(name='blah', open=True)
        p1 = Package(name=self.name1, title=self.title1, license=lic1)
        p2 = Package(name=self.name2, title=self.title1, license=lic1)
        t1 = Tag(name='geo')
        # t2 = Tag(name='novel')
        p1.tags.append(t1)

        rev1 = Revision() 
        set_revision(session, rev1)

        # experiment with object_session
        # note that this fails: assert object_session(p1) == SessionObject
        assert object_session(p1) == session
        session.flush()
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
        outp1 = Package.query.filter_by(name=self.name1).one()
        outp2 = Package.query.filter_by(name=self.name2).one()
        outp1.title = self.title2
        outp1.tags = []
        outp2.delete()
        session.flush()
        # must do this after flush as timestamp not set until then
        self.ts2 = rev2.timestamp
        session.clear()
        
    def test_revisions_exist(self):
        revs = Revision.query.all()
        assert len(revs) == 2

    def test_basic(self):
        assert len(License.query.all()) == 1
        assert len(Package.query.all()) == 2
        assert 'revision_id' in LicenseRevision.c
        print LicenseRevision.c['revision_id'].table
        pprint.pprint(LicenseRevision.c['revision_id'].__dict__)
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

