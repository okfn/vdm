'''Demo of vdm for SQLAlchemy.

This module sets up a small domain model with some versioned objects. Code
that then uses these objects can be found in demo_test.py.
'''
from datetime import datetime
import logging
logger = logging.getLogger('vdm')
import uuid
def uuidstr(): return str(uuid.uuid4())

from sqlalchemy import *
from sqlalchemy import __version__ as sqla_version
from sqlalchemy.ext.associationproxy import association_proxy
# from sqlalchemy import create_engine

import vdm.sqlalchemy
from vdm.sqlalchemy import Changeset, ChangeObject, VersionedListener

TEST_ENGINE = "postgres"  # or "sqlite"

if TEST_ENGINE == "postgres":
    engine = create_engine('postgres://tester:pass@localhost/vdmtest',
                           pool_threadlocal=True)
else:
    # setting the isolation_level is a hack required for sqlite support
    # until http://code.google.com/p/pysqlite/issues/detail?id=24 is
    # fixed.
    engine = create_engine('sqlite:///:memory:',
                           connect_args={'isolation_level': None})

metadata = MetaData(bind=engine)

## Demo tables

license_table = Table('license', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(100)),
        Column('open', Boolean),
        )

package_table = Table('package', metadata,
        # Column('id', Integer, primary_key=True),
        Column('id', String(36), default=uuidstr, primary_key=True),
        Column('name', String(100), unique=True),
        Column('title', String(100)),
        Column('license_id', Integer, ForeignKey('license.id')),
        Column('notes', UnicodeText),
)

tag_table = Table('tag', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(100)),
)

package_tag_table = Table('package_tag', metadata,
        Column('id', Integer, primary_key=True),
        # Column('package_id', Integer, ForeignKey('package.id')),
        Column('package_id', String(36), ForeignKey('package.id')),
        Column('tag_id', Integer, ForeignKey('tag.id')),
        )


## -------------------
## Mapped classes

        
class License(vdm.sqlalchemy.SQLAlchemyMixin):
    __history_mapper__ = True

class Package(vdm.sqlalchemy.SQLAlchemyMixin):
    __history_mapper__ = True

    # TODO: reinstate m2m tests ...
    # tags = association_proxy('package_tags', 'tag')


class Tag(vdm.sqlalchemy.SQLAlchemyMixin):
    def __init__(self, name):
        self.name = name


class PackageTag(vdm.sqlalchemy.SQLAlchemyMixin):
    def __init__(self, tag=None, **kwargs):
        logger.debug('PackageTag.__init__: %s' % (tag))
        self.tag = tag
        for k,v in kwargs.items():
            setattr(self, k, v)


## --------------------------------------------------------
## Mapper Stuff

from sqlalchemy.orm import scoped_session, sessionmaker, create_session
from sqlalchemy.orm import relation, backref
# both options now work
# Session = scoped_session(sessionmaker(autoflush=False, transactional=True))
# this is the more testing one ...
Session = scoped_session(
            sessionmaker(autoflush=True,
            expire_on_commit=False,
            autocommit=False,
            # Where we introduced the revisioning/versioning
            extension=VersionedListener()
            ))

# mapper = Session.mapper
from sqlalchemy.orm import mapper

# Sets up tables and maps ChangeObject and Changeset
vdm.sqlalchemy.setup_changeset(metadata, mapper)


mapper(License, license_table, properties={
    })

mapper(Package, package_table, properties={
    'license':relation(License),
    # delete-orphan on cascade does NOT work!
    # Why? Answer: because of way SQLAlchemy/our code works there are points
    # where PackageTag object is created *and* flushed but does not yet have
    # the package_id set (this cause us other problems ...). Some time later a
    # second commit happens in which the package_id is correctly set.
    # However after first commit PackageTag does not have Package and
    # delete-orphan kicks in to remove it!
    # 
    # do we want lazy=False here? used in:
    # <http://www.sqlalchemy.org/trac/browser/sqlalchemy/trunk/examples/association/proxied_association.py>
    'package_tags':relation(PackageTag, backref='package', cascade='all'), #, delete-orphan'),
    })

mapper(Tag, tag_table)

mapper(PackageTag, package_tag_table, properties={
    'tag':relation(Tag),
    })

## ------------------------
## Repository helper object

from vdm.sqlalchemy import Repository
repo = Repository(metadata, Session,
        versioned_objects = [ Package, License,  PackageTag ]
        )

