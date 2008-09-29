from datetime import datetime

import logging
logger = logging.getLogger('vdm')

# make explicit to avoid errors from typos (no attribute defns in python!)
def set_revision(session, revision):
    session.revision = revision
    # check if we are being given the Session class (threadlocal case)
    # if so set on both class and instance
    if isinstance(session, sqlalchemy.orm.scoping.ScopedSession):
        sess = session()
        sess.revision = revision

def get_revision(session):
    '''Get revision on current Session/session.
    
    NB: will return None if not set
    '''
    return getattr(session, 'revision', None)

## --------------------------------------------------------
## VDM-Specific Domain Objects and Tables

class STATE:
    active = 'active'
    deleted = 'deleted'

def make_state_table(metadata):
    state_table = Table('state', metadata,
            Column('id', Integer, primary_key=True),
            Column('name', String(8))
            )
    return state_table

def make_revision_table(metadata):
    revision_table = Table('revision', metadata,
            Column('id', Integer, primary_key=True),
            Column('timestamp', DateTime, default=datetime.now),
            Column('author', String(200)),
            Column('message', Text),
            )
    return revision_table

class State(object):

    def __repr__(self):
        return '<State %s>' % self.name

def make_State(mapper, state_table):
    mapper(State, state_table,
            order_by=state_table.c.id)
    return State

def make_states(session):
    ACTIVE = State(id=1, name='active').name
    DELETED = State(id=2, name='deleted').name
    # use flush as may not be transactional
    if session.transactional:
        session.commit()
    else:
        session.flush()
    return ACTIVE, DELETED

class Revision(object):
    '''A Revision to the Database/Domain Model.

    All versioned objects have an associated Revision which can be accessed via
    the revision attribute.
    '''
    # TODO:? set timestamp in ctor ... (maybe not as good to have undefined
    # until actual save ...)

    @classmethod
    def youngest(self, session=None):
        '''Get the youngest (most recent) revision.

        If session is not provided assume there is a contextual session.
        '''
        if session:
            q = session.query(self.__class__)
        else: # this depends upon having a contextual session
            q = self.query
        q = q.order_by(self.c.id.desc())
        return q.first()

    def __repr__(self):
        return '<Revision %s>' % self.id 

def make_Revision(mapper, revision_table):
    mapper(Revision, revision_table,
            order_by=revision_table.c.id)
    return Revision

## --------------------------------------------------------
## Table Helpers

from sqlalchemy import *

def make_table_stateful(base_table):
    '''Make a table 'stateful' by adding appropriate state column.'''
    base_table.append_column(
            # TODO: should probably not use default but should set on object
            # using StatefulObjectMixin 
            Column('state_id', Integer, ForeignKey('state.id'), default=1)
            )

def copy_column(name, src_table, dest_table):
    '''
    Note you cannot just copy columns standalone e.g.

        col = table.c['xyz']
        col.copy()

    This will only copy basic info while more complex properties (such as fks,
    constraints) to work must be set when the Column has a parent table.

    TODO: stuff other than fks (e.g. constraints such as uniqueness)
    '''
    col = src_table.c[name]
    dest_table.append_column(col.copy())
    # only get it once we have a parent table
    newcol = dest_table.c[name]
    if len(col.foreign_keys) > 0:
        for fk in col.foreign_keys: 
            newcol.append_foreign_key(fk.copy())

def copy_table_columns(table):
    # still does not work on fks because parent cannot be set
    columns = []
    for col in table.c:
        newcol = col.copy() 
        if len(col.foreign_keys) > 0:
            for fk in col.foreign_keys: 
                newcol.foreign_keys.add(fk.copy())
        columns.append(newcol)
    return columns

def copy_table(table, newtable):
    for key in table.c.keys():
        copy_column(key, table, newtable)

def make_table_revisioned(base_table):
    '''Modify base_table and create correponding revision table.

    @ruturn revision table.
    '''
    base_table.append_column(
            Column('revision_id', Integer, ForeignKey('revision.id'))
            )
    newtable = Table(base_table.name + '_revision', base_table.metadata,
            )
    copy_table(base_table, newtable)
    # TODO: (complex) support for complex primary keys on continuity. 
    # setting fks here will not work
    fk_name = base_table.name + '.id'
    newtable.append_column(
            Column('continuity_id', Integer, ForeignKey(fk_name))
            )

    for col in newtable.c:
        if col.name == 'revision_id':
            col.primary_key = True
            newtable.primary_key.add(col)
    return newtable


## --------------------------------------------------------
## Object Helpers

class StatefulObjectMixin(object):

    __stateful__ = True
    # TODO: complete hack this has got to be set up in some nicer fashion
    state_obj = State

    def delete(self):
        # HACK: how do we get the real value without having State object
        # available ...
        logger.debug('RUNNING delete on %s' % self)
        deleted = self.state_obj.query.filter_by(name='deleted').one()
        self.state = deleted
    
    def undelete(self):
        active = self.state_obj.query.get(1)
        self.state = active

    def is_active(self):
        # also support None in case this object is not yet refreshed ...
        active = self.state_obj.query.get(1)
        return self.state is None or self.state == active


class RevisionedObjectMixin(object):

    __revisioned__ = True

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
        '''Get this domain object at the specified revision.
        
        If no revision is specified revision will be looked up on the global
        session object. If that not found return head.

        get_as_of does most of the crucial work in supporting the
        versioning.
        '''
        if revision:
            # set revision on the session so dom traversal works
            # TODO: should we assert revision.id?
            self._set_revision(revision)
        else:
            revision = self._get_revision()
        # if revision is None or does not have an id (implies in transaction)
        # then we should use head (i.e. continuity object since this caches
        # head)
        at_head = (revision is None or revision.id is None)
        if at_head:
            return self
        else:
            revision_class = self.__revision_class__
            # exploit orderings of ids
            out = revision_class.query.filter(
                    revision_class.revision_id <= revision.id
                    ).filter(
                        revision_class.id == self.id
                        )
            if out.count() == 0: # object does not exist yet
                return None
            else:
                return out.first()


## --------------------------------------------------------
## Mapper Helpers

import sqlalchemy.orm.properties
from sqlalchemy.orm import class_mapper
from sqlalchemy.orm import relation, backref

def modify_base_object_mapper(base_object, revision_obj, state_obj):
    base_mapper = class_mapper(base_object)
    base_mapper.add_property('revision', relation(revision_obj))
    base_mapper.add_property('state', relation(state_obj))

def create_object_version(mapper_fn, base_object, rev_table):
    '''Create the Version Domain Object corresponding to base_object.

    E.g. if Package is our original object we should do::
    
        # name of Version Domain Object class 
        PackageVersion = create_object_version(..., Package, ...)
    
    NB: This must obviously be called after mapping has happened to
    base_object.
    '''
    # TODO: can we always assume all versioned objects are stateful?
    # If not need to do an explicit check
    class MyClass(StatefulObjectMixin):
        pass
    name = base_object.__name__ + 'Revision'
    MyClass.__name__ = name
    MyClass.__continuity_class__ = base_object

    # Must add this so base object can retrieve revisions ...
    base_object.__revision_class__ = MyClass

    ourmapper = mapper_fn(MyClass, rev_table, properties={
        # NB: call it all_revisions rather than just revisions because it will
        # yield all revisions not just those less than the current revision
        'continuity':relation(base_object, backref=backref('all_revisions',
            cascade='all, delete, delete-orphan')),
        # 'continuity':relation(base_object),
        })
    base_mapper = class_mapper(base_object)
    # add in 'relationship' stuff from continuity onto revisioned obj
    # If related object is revisioned then ok
    # If not can support simple relation but nothing else
    for prop in base_mapper.iterate_properties:
        is_relation = prop.__class__ == sqlalchemy.orm.properties.PropertyLoader
        if is_relation:
            # in sqlachemy 0.4.2
            # prop_remote_obj = prop.select_mapper.class_
            # in 0.4.5
            prop_remote_obj = prop.argument
            remote_obj_is_revisioned = getattr(prop_remote_obj, '__revisioned__', False)
            # this is crude, probably need something better
            is_m2m = (prop.secondary != None or prop.uselist)
            if remote_obj_is_revisioned:
                propname = prop.key
                add_fake_relation(MyClass, propname)
            elif not is_m2m:
                # import pprint
                # if prop.key == 'tags':
                #    pprint.pprint(prop.__dict__)
                ourmapper.add_property(prop.key, relation(prop_remote_obj))
            else:
                # TODO: ? raise a warning of some kind ...
                pass

    return MyClass

def add_fake_relation(revision_class, name, m2m=False): 
    def _pget(self):
        related_object = getattr(self.continuity, name)
        # will use whatever the current session.revision is
        if m2m:
            # with m2m get_as_of already implemented inside the m2m relation
            return related_object
        else:
            return related_object.get_as_of()
    x = property(_pget)
    setattr(revision_class, name, x)

from stateful import add_stateful_m2m
def add_stateful_versioned_m2m(*args, **kwargs):
    '''Add a Stateful versioned m2m attributes to a domain object.
    
    For args and kwargs see add_stateful_m2m.
    '''
    def get_as_of(obj):
        return obj.get_as_of()

    newkwargs = dict(kwargs)
    newkwargs['base_modifier'] = get_as_of
    add_stateful_m2m(*args, **newkwargs)

def add_stateful_versioned_m2m_on_version(revision_class, m2m_property_name):
    active_name = m2m_property_name + '_active'
    deleted_name = m2m_property_name + '_deleted'
    for propname in [active_name, deleted_name, m2m_property_name]:
        add_fake_relation(revision_class, propname,
                m2m=True)


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

    def check_real_change(self, instance, mapper):
        logger.debug('check_real_change: %s' % instance)
        table = mapper.tables[0]
        colname = 'id'
        ctycol = table.c[colname]
        ctyval = getattr(instance, colname)
        values = table.select(ctycol==ctyval).execute().fetchone() 
        if values is None: # object not yet created
            logging.debug('check_real_change: True')
            return True
        ignored = [ 'revision_id' ]

        # (Based on Elixir's solution to this problem)
        # SA might've flagged this for an update even though it didn't change.
        # This occurs when a relation is updated, thus marking this instance
        # for a save/update operation. We check here against the last version
        # to ensure we really should save this version and update the version
        # data.
        for key in table.c.keys():
            if key in ignored:
                continue
            # logger.debug('%s, %s, %s' % (key, getattr(instance, key), values[key]))
            if getattr(instance, key) != values[key]:
                # the instance was really updated, so we create a new version
                logging.debug('check_real_change: True')
                return True
        logging.debug('check_real_change: False')
        return False

    def make_revision(self, instance, mapper):
        # NO GOOD working with the object as that only gets committed at next
        # flush. Need to work with the table directly (could this be dangerous)
        colvalues = {}
        table = mapper.tables[0]
        for key in table.c.keys():
            val = getattr(instance, key)
            colvalues[key] = val
        # because it is unlikely instance has been refreshed at this point the
        # fk revision_id is not yet set on this object so get it directly
        assert instance.revision.id
        colvalues['revision_id'] = instance.revision.id
        colvalues['continuity_id'] = instance.id

        # Allow for multiple SQLAlchemy flushes/commits per VDM revision
        revision_already_query = self.revision_table.count()
        existing_revision_clause = and_(
                self.revision_table.c.continuity_id == instance.id,
                self.revision_table.c.revision_id == instance.revision.id)
        revision_already_query = revision_already_query.where(
                existing_revision_clause
                )
        num_revisions = revision_already_query.execute().scalar()
        revision_already = num_revisions > 0

        if revision_already:
            logging.debug('Updating version of %s: %s' % (instance, colvalues))
            # print self.revision_table.c.keys()
            # print self.revision_table.select().execute().fetchall()
            self.revision_table.update(existing_revision_clause).execute(colvalues)
        else:
            logging.debug('Creating version of %s: %s' % (instance, colvalues))
            self.revision_table.insert().execute(colvalues)

        # set to None to avoid accidental reuse
        # ERROR: cannot do this as after_* is called per object and may be run
        # before_update on other objects ...
        # probably need a SessionExtension to deal with this properly
        # object_session(instance).revision = None

    def before_update(self, mapper, connection, instance):
        logger.debug('before_update: %s' % instance)
        self.set_revision(instance)
        self._is_changed = self.check_real_change(instance, mapper)
        return EXT_CONTINUE

    def before_insert(self, mapper, connection, instance):
        logger.debug('before_insert: %s' % instance)
        # TODO: explain why we cannot do everything here
        # i.e. why do we need to run stuff in after_update
        self.set_revision(instance)
        self._is_changed = self.check_real_change(instance, mapper)
        return EXT_CONTINUE

    def after_update(self, mapper, connection, instance):
        logger.debug('after_update: %s' % instance)
        if self._is_changed:
            self.make_revision(instance, mapper)
        return EXT_CONTINUE

    def after_insert(self, mapper, connection, instance):
        logger.debug('after_insert: %s' % instance)
        if self._is_changed:
            self.make_revision(instance, mapper)
        return EXT_CONTINUE

    def append_result(self, mapper, selectcontext, row, instance, result,
             **flags):
        logger.debug('append_result: %s' % instance)
        return EXT_CONTINUE



