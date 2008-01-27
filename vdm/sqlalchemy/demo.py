'''Versioned Domain Model Support for SQLAlchemy.

TODO
====

1. How do we commit revisions (do we need to).
    * At very least do we not need to update timestamps?
    * Could have rule that flush ends revision.

'''
from datetime import datetime

from sqlalchemy import *
# from sqlalchemy import create_engine

from vdm.sqlalchemy.base import Revisioner, set_revision, get_revision, RevisionedObjectMixin

engine = create_engine('sqlite:///:memory:',
        # echo=True
        )
metadata = MetaData(bind=engine)


state_table = Table('state', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(8))
        )

state_col = Column('state_id', Integer, ForeignKey('state.id'))

revision_table = Table('revision', metadata,
        Column('id', Integer, primary_key=True),
        Column('timestamp', DateTime, default=datetime.now),
        Column('author', String(200)),
        )

## Demo tables

license_table = Table('license', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(100)),
        Column('open', Boolean),
        state_col.copy()
        )

package_table = Table('package', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(100)),
        Column('title', String(100)),
        Column('license_id', Integer, ForeignKey('license.id')),
        state_col.copy(),
)

tag_table = Table('tag', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(100)),
        state_col.copy()
)

package_tag_table = Table('package_tag', metadata,
        Column('package_id', Integer, ForeignKey('package.id'),
            primary_key=True),
        Column('tag_id', Integer, ForeignKey('tag.id'), primary_key=True),
        )

def make_rev_table(base_table):
    base_table.append_column(
            Column('revision_id', Integer, ForeignKey('revision.id'))
            )
    columns = [ col.copy() for col in base_table.c ]
    for col in columns:
        if col.name == 'revision_id':
            col.primary_key = True
    newtable = Table(base_table.name + '_revision', base_table.metadata,
            *columns)
    return newtable

license_revision_table = make_rev_table(license_table)
package_revision_table = make_rev_table(package_table)

metadata.create_all(engine) 


## -------------------
## Mapped classes

        

class State(object):
    pass

class Revision(object):
    # TODO:? set timestamp in ctor ... (maybe not as good to have undefined
    # until actual save ...)

    def __repr__(self):
        return '<Revision %s>' % self.id 

class License(object):
    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)

class Package(RevisionedObjectMixin):
    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self):
        return '<Package %s>' % self.name

class Tag(object):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<Tag %s>' % self.name




from sqlalchemy.orm import scoped_session, sessionmaker, create_session
from sqlalchemy.orm import relation, backref#, secondary
# SessionObject = scoped_session(sessionmaker(autoflush=True, transactional=True))
# SessionObject = scoped_session(sessionmaker())
SessionObject = scoped_session(create_session)
# WARNING: you must instantiate a session for object_session to work correctly
# that is for: object_session(some_instance) == session
# this is essential for our technique of passing around the current revision as
# an attribute on the session
session = SessionObject()
mapper = SessionObject.mapper

mapper(State, state_table)
mapper(Revision, revision_table)


## -----------------------------
## Helpers

def create_object_version(base_object, rev_table):
    class MyClass(object):
        pass
    name = base_object.__name__ + 'Revision'
    MyClass.__name__ = name
    base_object.__revision_object__ = MyClass
    # TODO: properties (copy?)
    mapper(MyClass, rev_table) 
    return MyClass

## -----------------------------
## Concrete

mapper(License, license_table, properties={
    'revision':relation(Revision),
    },
    extension=Revisioner(license_revision_table)
    )

mapper(Package, package_table, properties={
    'revision':relation(Revision),
    'license':relation(License),
    'tags':relation(Tag, secondary=package_tag_table),
    },
    extension = Revisioner(package_revision_table)
    )

mapper(Tag, tag_table)

PackageRevision = create_object_version(Package,
        package_revision_table)

LicenseRevision = create_object_version(License,
        license_revision_table)

