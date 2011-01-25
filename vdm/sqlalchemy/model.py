"""Versioning (revisioning) for sqlalchemy model objects.

Based partially on:

http://www.sqlalchemy.org/trac/browser/examples/versioning/history_meta.py
"""
import logging
logger = logging.getLogger('vdm')

from sqlalchemy.orm import mapper, class_mapper, attributes, object_mapper
from sqlalchemy.orm.exc import UnmappedClassError, UnmappedColumnError
from sqlalchemy import Table, Column, ForeignKeyConstraint, Integer
from sqlalchemy.orm.interfaces import SessionExtension
from sqlalchemy.orm.properties import RelationshipProperty
from sqlalchemy.ext.declarative import DeclarativeMeta

from vdm import json
from .changeset import ChangeObject

def versioned_objects(iter):
    for obj in iter:
        if hasattr(obj, '__history_mapper__'):
            yield obj

class VersionedMeta(DeclarativeMeta):
    def __init__(cls, classname, bases, dict_):
        DeclarativeMeta.__init__(cls, classname, bases, dict_)
        try:
            mapper = class_mapper(cls)
            cls.__history_mapper__ = True
            set_revisioned_attributes(mapper)
        except UnmappedClassError:
            pass

def set_revisioned_attributes(local_mapper):
    cls = local_mapper.class_
    # Do the simplest thing possible
    # TODO: inherited attributes etc
    # TODO: work out primary key etc
    # TODO: allow for exclude attributes
    cols = []
    for column in local_mapper.local_table.c:
        col = column.copy()
        col.unique = False
        cols.append(col)
    cls.__revisioned_attributes__ = [ col.key for col in cols ]
    return cols

def get_object_id(obj):
    obj_mapper = object_mapper(obj)
    object_id = [obj.__class__.__name__]
    for om in obj_mapper.iterate_to_root():
        for col in om.local_table.c:
            if col.primary_key:
                prop = obj_mapper.get_property_by_column(col)
                val = getattr(obj, prop.key)
                object_id.append(val)
    object_id = tuple(object_id)
    return object_id

# Questions: when does this create the first version

def create_version(obj, session,
        operation_type=ChangeObject.OperationType.UPDATE
        ):
    obj_mapper = object_mapper(obj)
    ## TODO: very inefficient to do this each time (would like to do this when
    ## setting up object)
    if not hasattr(obj, '__revisioned_attributes__'):
        set_revisioned_attributes(obj_mapper)

    obj_state = attributes.instance_state(obj)

    attr = {}

    obj_changed = False

    for om in obj_mapper.iterate_to_root():
        for col_key in obj.__revisioned_attributes__:

            obj_col = om.local_table.c[col_key]

            # get the value of the
            # attribute based on the MapperProperty related to the
            # mapped column.  this will allow usage of MapperProperties
            # that have a different keyname than that of the mapped column.
            try:
                prop = obj_mapper.get_property_by_column(obj_col)
            except UnmappedColumnError:
                # in the case of single table inheritance, there may be 
                # columns on the mapped table intended for the subclass only.
                # the "unmapped" status of the subclass column on the 
                # base class is a feature of the declarative module as of sqla 0.5.2.
                continue

            # expired object attributes and also deferred cols might not be in the
            # dict.  force it to load no matter what by using getattr().
            if prop.key not in obj_state.dict:
                getattr(obj, prop.key)

            a, u, d = attributes.get_history(obj, prop.key)

            if d:
                attr[col_key] = d[0]
                obj_changed = True
            elif u:
                attr[col_key] = u[0]
            else:
                # if the attribute had no value.
                attr[col_key] = a[0]
                obj_changed = True

    if not obj_changed:
        # not changed, but we have relationships.  OK
        # check those too
        for prop in obj_mapper.iterate_properties:
            if isinstance(prop, RelationshipProperty) and \
                attributes.get_history(obj, prop.key).has_changes():
                obj_changed = True
                break

    if not obj_changed and operation_type == ChangeObject.OperationType.UPDATE:
        return

    co = ChangeObject()
    session.add(co)

    ## TODO: address worry that iterator over columns may mean we get pkids in
    ## different order ...
    co.object_id = get_object_id(obj)
    co.operation_type = operation_type
    co.data = attr
    session.revision.manifest.append(co)
    return attr


class VersionedListener(SessionExtension):
    '''

    Notes
    =====

    Use after_flush rather than before_flush (as in sqlalchemy example)
    because:

    In before_flush pks will not be set on objects which have values autoset
    (e.g. int autoincrement). This in turn will mean that ChangeObject
    object_id will not be unique.
    Original sqlalchemy versioning code avoids this by *only* copying objects
    that are updated or deleted and hence object pks are set (i.e. it does not
    do anything for creation)

    TODO: is there a danger here that things will not work if we are not using
    commit (and only flush).
    '''

    # def before_commit(self, session):
    # def before_flush(self, session, flush_context, instances):
    def after_flush(self, session, flush_context):
        for obj in versioned_objects(session.dirty):
            create_version(obj, session)
        for obj in versioned_objects(session.deleted):
            create_version(obj, session,
                operation_type=ChangeObject.OperationType.DELETE
                )
        for obj in versioned_objects(session.new):
            create_version(obj, session,
                operation_type=ChangeObject.OperationType.CREATE
                )

