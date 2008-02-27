from sqlalchemy import *
from sqlalchemy.orm import *

from stateful import *

engine = create_engine('sqlite:///:memory:')

metadata = MetaData(bind=engine)

license_table = Table('license', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(100)),
        )

package_table = Table('package', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(100)),
)

package_license_table = Table('package_license', metadata,
        Column('id', Integer, primary_key=True),
        Column('package_id', Integer, ForeignKey('package.id')),
        Column('license_id', Integer, ForeignKey('license.id')),
        Column('state', String, default='active'),
        )

metadata.create_all(engine)


from sqlalchemy.orm import scoped_session, sessionmaker, create_session
from sqlalchemy.orm import relation, backref
SessionObject = scoped_session(create_session)
session = SessionObject()
mapper = SessionObject.mapper

from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm.collections import attribute_mapped_collection

class BaseObject(object):

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.id)

def delete(st):
    st.state = 'deleted'

def undelete(st):
    st.state = 'active'

def is_active(st):
    return st.state == 'active'

class StatefulListProxy(object):
    def __init__(self, target):
        self.target = target

    def __get__(self, obj, class_):
        return Stateful

def _create_pl_by_license(license):
    return PackageLicense(license=license)

class Package(BaseObject):

    def __init__(self, name=''):
        self.name = name

    active_licenses = StatefulListProperty('package_licenses', is_active,
            delete, undelete)
    deleted_licenses = StatefulListProperty('package_licenses', lambda x: not is_active(x),
            undelete, delete)
    licenses = OurAssociationProxy('active_licenses', 'license',
        creator=_create_pl_by_license)
    licenses2 = association_proxy('package_licenses', 'license',
            creator=_create_pl_by_license)

class License(BaseObject):
    def __init__(self, name):
        self.name = name

class PackageLicense(object):
    def __init__(self, package=None, license=None, state='active'):
        self.package = package
        self.license = license
        self.state = state
    
    def __repr__(self):
        return '<PackageLicense %s %s %s %s>' % (self.id, self.package,
                self.license, self.state)

mapper(Package, package_table, properties={
    'package_licenses':relation(PackageLicense),
    })
mapper(License, license_table)
mapper(PackageLicense, package_license_table, properties={
        'package':relation(Package),
        'license':relation(License),
        })


class TestStatefulCollections(object):

    def setup_class(self):
        pkg1 = Package()
        lic1 = License('a')
        lic2 = License('b')
        lic3 = License('c')
        lic4 = License('d')
        # for lic in [lic1, lic2, lic3]:
        #    pkg1.licenses.append(lic)
        # pkg1.licenses = [lic1, lic2, lic3]
        for li in [lic1, lic2, lic3, lic4]:
            pkg1.active_licenses.append(PackageLicense(pkg1, li))
        del pkg1.active_licenses[3]
        session.flush()
        session.clear()

    def test_0(self):
        pkg1 = Package.query.get(1)
        assert len(pkg1.package_licenses) == 4
        assert pkg1.package_licenses[-1].state == 'deleted'

    def test_1(self):
        p1 = Package.query.get(1)
        assert len(p1.licenses) == 3

    def test_2(self):
        p1 = Package.query.get(1)
        assert len(p1.active_licenses) == 3
        assert len(p1.deleted_licenses) == 1
        p1.deleted_licenses.append(PackageLicense(license=License('e')))
        assert len(p1.active_licenses) == 3
        assert len(p1.deleted_licenses) == 2
        session.flush()
        session.clear()
        p1 = Package.query.get(1)
        assert len(p1.package_licenses) == 5
        assert len(p1.active_licenses) == 3
        assert len(p1.deleted_licenses) == 2

    def test_3(self):
        p1 = Package.query.get(1)
        p1.licenses = []
        assert len(p1.licenses) == 0 
        assert len(p1.active_licenses) == 0
        assert len(p1.deleted_licenses) == 5
        session.flush()
        session.clear()

        p1 = Package.query.get(1)
        assert len(p1.licenses) == 0 
        assert len(p1.package_licenses) == 5
        assert len(p1.deleted_licenses) == 5


class TestSimple:
    def test_1(self):
        pkg1 = Package()
        lic1 = License('a')
        lic2 = License('b')
        lic3 = License('c')
        lic4 = License('d')
        pkg1.licenses2 = [lic1, lic2, lic3]
        assert len(pkg1.package_licenses) == 3
        assert pkg1.licenses2[0].name == 'a'
        pkg1.licenses2.append(lic4)
        pkg1.package_licenses[-1].state = 'deleted'
        session.flush()
        # must clear or other things won't behave
        session.clear()

    def test_2(self):
        p1 = Package.query.get(1)
        assert p1.package_licenses[0].package == p1

