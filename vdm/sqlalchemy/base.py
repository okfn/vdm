# make explicit to avoid errors from typos (no attribute defns in python!)
def set_revision(session, revision):
    session.revision = revision

def get_revision(session):
    # NB: will return None if not set
    return session.revision

## --------------------------------------------------------
## Table Helpers

from sqlalchemy import *

def make_revision_table(base_table):
    base_table.append_column(
            Column('revision_id', Integer, ForeignKey('revision.id'))
            )
    columns = [ col.copy() for col in base_table.c ]

    # TODO: (complex) support for complex primary keys on continuity. 
    fk_name = base_table.name + '.id'
    columns.append(
            Column('continuity_id', Integer, ForeignKey(fk_name))
            )

    for col in columns:
        if col.name == 'revision_id':
            col.primary_key = True
    newtable = Table(base_table.name + '_revision', base_table.metadata,
            *columns)
    return newtable

## --------------------------------------------------------
## Object Helpers

class RevisionedObjectMixin(object):

    def _get_revision(self):
        sess = object_session(self)
        rev = get_revision(sess)
        return rev

    def _set_revision(self, revision):
        # rev = self._get_revision()
        # if not rev or rev != revision:
        #     msg = 'The revision on the session does not match the one you' + \
        #     'requesting.'
        #     raise Exception(msg)
        sess = object_session(self)
        set_revision(sess, revision)

    def get_as_of(self, revision=None):
        # TODO: work out what happens if we start calling this when a
        # 'transactional' revision is active (i.e. we doing new stuff)

        if revision:
            # set revision on the session so dom traversal works
            self._set_revision(revision)
        else:
            revision = self._get_revision()
            assert revision
        revision_object = self.__revision_object__
        # exploit orderings of ids
        out = revision_object.query.filter(
                revision_object.revision_id <= revision.id
                )
        if out.count() == 0:
            return None
        else:
            return out.first()


## --------------------------------------------------------
## Mapper Helpers

import sqlalchemy.orm.properties
from sqlalchemy.orm import class_mapper
from sqlalchemy.orm import relation, backref
def create_object_version(mapper_fn, base_object, rev_table):
    class MyClass(object):
        pass
    name = base_object.__name__ + 'Revision'
    MyClass.__name__ = name
    MyClass.__base_class__ = base_object
    # TODO: add revision relation here (rather than explicitly below)
    base_object.__revision_object__ = MyClass

    # this better get called after mapping has happened ...
    base_mapper = class_mapper(base_object)
    for prop in base_mapper.iterate_properties:
        # only want relation stuff ...
        if prop.__class__ == sqlalchemy.orm.properties.PropertyLoader:
            name = prop.key
            add_fake_relation(MyClass, name)
    mapper_fn(MyClass, rev_table, properties={
        'continuity':relation(base_object),
        })
    return MyClass

def add_fake_relation(revision_class, name): 
    def _pget(self):
        related_object = getattr(self.continuity, name)
        # will use whatever the current session.revision is
        return related_object.get_as_of()
    x = property(_pget)
    setattr(revision_class, name, x)


from sqlalchemy.orm import MapperExtension
from sqlalchemy.orm import object_session
from sqlalchemy.orm import EXT_CONTINUE

class Revisioner(MapperExtension):
    # TODO: support ignored fields and check we really have changed ..

    def __init__(self, revision_table):
        self.revision_table = revision_table

    def set_revision(self, instance):
        sess = object_session(instance)
        current_rev = sess.revision
        # was using revision_id but this led to weird intermittent erros
        # (1/3: fail on first item, 1/3 on second, 1/3 ok).
        # assert current_rev.id
        # instance.revision_id = current_rev.id
        # LATER: this resulted (I think) from setting revision_id but not
        # setting revision on the object

        # In fact must do *both* Why?
        # SQLAlchemy mapper extension methods can only make changes to columns.
        # Any changes make to relations will not be picked up (from docs):
        # "Column-based attributes can be modified within this method which will
        # result in their being updated. However no changes to the overall
        # flush plan can be made; this means any collection modification or
        # save() operations which occur within this method will not take effect
        # until the next flush call."
        #
        # Thus: set revision_id to ensure that value is saved
        # set revision to ensure object behaves how it should (e.g. we use
        # instance.revision in after_update)
        assert current_rev
        assert current_rev.id
        instance.revision_id = current_rev.id
        instance.revision = current_rev
        # also set this so that we flush

    def make_revision(self, instance):
        # NO GOOD working with the object as that only gets committed at next
        # flush. Need to work with the table directly (could this be dangerous)
        colvalues = {}
        for key in instance.c.keys():
            val = getattr(instance, key)
            colvalues[key] = val
        # because it is unlikely instance has been refreshed at this point the
        # fk revision_id is not yet set on this object so get it directly
        assert instance.revision.id
        colvalues['revision_id'] = instance.revision.id
        colvalues['continuity_id'] = instance.id
        self.revision_table.insert().execute(colvalues)
        # set to None to avoid accidental reuse
        # ERROR: cannot do this as after_* is called per object and may be run
        # before_update on other objects ...
        # probably need a SessionExtension to deal with this properly
        # object_session(instance).revision = None

    def before_update(self, mapper, connection, instance):
        self.set_revision(instance)
        return EXT_CONTINUE

    def before_insert(self, mapper, connection, instance):
        self.set_revision(instance)
        return EXT_CONTINUE

    def after_update(self, mapper, connection, instance):
        self.make_revision(instance)
        return EXT_CONTINUE

    def after_insert(self, mapper, connection, instance):
        self.make_revision(instance)
        return EXT_CONTINUE


# TODO: __all__ = [ ... ]
