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

from vdm.sqlalchemy.base import *

engine = create_engine('sqlite:///:memory:',
        # echo=True
        )
metadata = MetaData(bind=engine)


state_table = Table('state', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(8))
        )

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
        )

package_table = Table('package', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(100)),
        Column('title', String(100)),
        Column('license_id', Integer, ForeignKey('license.id')),
)

tag_table = Table('tag', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(100)),
)

package_tag_table = Table('package_tag', metadata,
        Column('package_id', Integer, ForeignKey('package.id'),
            primary_key=True),
        Column('tag_id', Integer, ForeignKey('tag.id'), primary_key=True),
        )


make_stateful(license_table)
make_stateful(package_table)
make_stateful(tag_table)
make_stateful(package_tag_table)
license_revision_table = make_revision_table(license_table)
package_revision_table = make_revision_table(package_table)
tag_revision_table = make_revision_table(tag_table)
# TODO: this has a composite primary key ...
# package_tag_revision_table = make_revision_table(package_tag_table)


metadata.create_all(engine) 


## -------------------
## Mapped classes

        

class State(object):

    def __repr__(self):
        return '<State %s>' % self.name
    

class Revision(object):
    # TODO:? set timestamp in ctor ... (maybe not as good to have undefined
    # until actual save ...)

    def __repr__(self):
        return '<Revision %s>' % self.id 

class License(RevisionedObjectMixin):
    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)

class Package(RevisionedObjectMixin, StatefulObjectMixin):
    # TODO: complete hack this has got to be set up in some nicer fashion
    State = State
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


## --------------------------------------------------------
## Mapper Stuff

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

mapper(License, license_table, properties={
    },
    extension=Revisioner(license_revision_table)
    )

mapper(Package, package_table, properties={
    'license':relation(License),
    'tags':relation(Tag, secondary=package_tag_table),
    },
    extension = Revisioner(package_revision_table)
    )

mapper(Tag, tag_table)

modify_base_object_mapper(Package, Revision, State)
modify_base_object_mapper(License, Revision, State)
PackageRevision = create_object_version(mapper, Package,
        package_revision_table)

LicenseRevision = create_object_version(mapper, License,
        license_revision_table)

ACTIVE = State(id=1, name='active').name
DELETED = State(id=2, name='deleted').name

