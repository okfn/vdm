'''
A versioning plugin for Elixir.

Supports changes to multiple objects and relationships in a single
revision/version.
'''
from datetime              import datetime
import inspect

from sqlalchemy            import Table, Column, and_, desc
from sqlalchemy.orm        import mapper, MapperExtension, EXT_PASS, \
                                  object_session

import elixir
from elixir                import Integer, DateTime
from elixir.statements     import Statement


#
# utility functions
#

def get_entity_where(instance):
    clauses = []
    for column in instance.table.primary_key.columns:
        instance_value = getattr(instance, column.name)
        clauses.append(column==instance_value)
    return and_(*clauses)


def get_history_where(instance):
    clauses = []
    for column in instance.table.primary_key.columns:
        instance_value = getattr(instance, column.name)
        history_column = getattr(instance.__history_table__.primary_key.columns, column.name)
        clauses.append(history_column==instance_value)
    return and_(*clauses)

class RevisionState(object):

    PENDING = 0
    ACTIVE = 1

class Revision(elixir.Entity):

    # should default to pending category
    # elixir.belongs_to('state', of_kind='State', default=3)
    elixir.has_field('state', elixir.Integer, default=RevisionState.PENDING)
    elixir.has_field('author', elixir.Unicode)
    elixir.has_field('log_message', elixir.Unicode)
    # for a transaction this time it started
    # for a revision time it was completed
    elixir.has_field('timestamp', elixir.DateTime, default=datetime.now)

    def __init__(self):
        super(Revision, self).__init__()
        # elixir has only one ScopedSession in the thread ... 
        # could just use this:
        # self.session = elixir.session
        self.session = object_session(self)
        # TODO: check if session already has a revision
        # if so raise an error
        self.session.revision = self

    def commit(self):
        self.state = RevisionState.ACTIVE
        self.timestamp = datetime.now()
        # flush commits everything into the db
        elixir.objectstore.flush()
        # self.session.revision = None
        # self.session = None


#
# a mapper extension to track versions on insert, update, and delete
#

class VersionedMapperExtension(MapperExtension):

    def _set_revision(self, instance):
        # elixir >= 0.4 has ScopedSession session always around
        # could just use that
        # session = elixir.session
        session = object_session(instance)
        if session.revision is None:
            msg = 'Versioning impossible as no revision has been set for this session'
            raise Exception(msg)
        # does NOT work
        # instance.revision = session.revision
        # appears we have to set revision_id rather than revision ...
        instance.revision_id = session.revision.id

    def before_insert(self, mapper, connection, instance):
        self._set_revision(instance)
        instance.timestamp = datetime.now()
        return EXT_PASS

    def after_insert(self, mapper, connection, instance):
        colvalues = dict([(key, getattr(instance, key)) 
                          for key in instance.c.keys()])
        instance.__class__.__history_table__.insert().execute(colvalues)
        return EXT_PASS
    
    def before_update(self, mapper, connection, instance):
        self._set_revision(instance)
        instance.timestamp = datetime.now()
        colvalues = dict([(key, getattr(instance, key)) 
                          for key in instance.c.keys()])
        history = instance.__class__.__history_table__
        
        values = history.select(get_history_where(instance), 
                                order_by=[desc(history.c.timestamp)],
                                limit=1).execute().fetchone()
        # In case the data was dumped into the db, the initial version might 
        # be missing so we put this version in as the original.
        if not values:
            # instance.version = colvalues['version'] = 1
            instance.timestamp = colvalues['timestamp'] = datetime.now()
            history.insert().execute(colvalues)
            return EXT_PASS
        
        # SA might've flagged this for an update even though it didn't change.
        # This occurs when a relation is updated, thus marking this instance
        # for a save/update operation. We check here against the last version
        # to ensure we really should save this version and update the version
        # data.
        ignored = instance.__class__.__ignored_fields__
        for key in instance.c.keys():
            if key in ignored:
                continue
            if getattr(instance, key) != values[key]:
                # the instance was really updated, so we create a new version
                # instance.version = colvalues['version'] = instance.version + 1
                instance.timestamp = colvalues['timestamp'] = datetime.now()
                history.insert().execute(colvalues)
                break

        return EXT_PASS
    
    def before_delete(self, mapper, connection, instance):
        instance.__history_table__.delete(
            get_history_where(instance)
        ).execute()
        return EXT_PASS


versioned_mapper_extension = VersionedMapperExtension()


#
# the acts_as_versioned statement
#

class ActsAsVersioned(object):
        
    # use ignore=None rather than ignore=[] to avoid problems with defaults
    # shared across objects
    def __init__(self, entity, ignore=[]):
        entity._descriptor.add_mapper_extension(versioned_mapper_extension)
        self.entity = entity
        if not ignore:
            ignore = []
        entity.__ignored_fields__ = ignore
        entity.__ignored_fields__.extend(['version', 'timestamp'])
        # will auto attach to the entity in question
        # revisionField = elixir.relationships.ManyToOne(entity=entity,
        #        name='revision', of_kind='vdm.elixir.complex.Revision')
        # based on lines in
        # http://elixir.ematia.de/trac/browser/elixir/trunk/elixir/properties.py
        # class Property: def attach
        newproperty = elixir.relationships.ManyToOne('Revision')
        newproperty.attach(entity=entity, name='revision')

    def create_non_pk_cols(self):
        # add a version column to the entity, along with a timestamp
        version_col = Column('version', Integer)
        timestamp_col = Column('timestamp', DateTime)
        self.entity._descriptor.add_column(version_col)
        self.entity._descriptor.add_column(timestamp_col)
    
    def after_table(self):
        entity = self.entity

        # look for events
#        after_revert_events = []
#        for name, func in inspect.getmembers(entity, inspect.ismethod):
#            if getattr(func, '_elixir_after_revert', False):
#                after_revert_events.append(func)
        
        # create a history table for the entity
        columns = [ column.copy() for column in entity.table.c ]
        for col in columns:
            if col.name == 'revision_id':
                col.primary_key = True
        # columns.append(Column('revision_id', Integer,
        #    ForeignKey('revision.id')
        #    ))
        table = Table(entity.table.name + '_history', entity.table.metadata, 
            *columns
        )
        entity.__history_table__ = table
        
        # create an object that represents a version of this entity
        class Version(object):
            pass
            
        # map the version class to the history table for this entity
        Version.__name__ = entity.__name__ + 'Version'
        Version.__versioned_entity__ = entity
        mapper(Version, entity.__history_table__)
        entity.__history_class__ = Version
                        
        # attach utility methods and properties to the entity
        def get_versions(self):
            return object_session(self).query(Version) \
                                       .filter(get_history_where(self)) \
                                       .all()
        
        def get_as_of(self, dt):
            # if the passed in timestamp is older than our current version's
            # time stamp, then the most recent version is our current version
            if self.timestamp < dt:
                return self
            
            # otherwise, we need to look to the history table to get our
            # older version
            query = object_session(self).query(Version)
            query = query.filter(and_(get_history_where(self), 
                                      Version.c.timestamp <= dt))
            query = query.order_by(desc(Version.c.timestamp)).limit(1)
            return query.first()
        
        
# remove for time being
#        def revert_to(self, to_version):
        
# ditto
#        def revert(self):
            
        def compare_with(self, version):
            differences = {}
            for column in self.c:
                if column.name == 'version':
                    continue
                this = getattr(self, column.name)
                that = getattr(version, column.name)
                if this != that:
                    differences[column.name] = (this, that)
            return differences
        
        entity.versions      = property(get_versions)
        entity.get_as_of     = get_as_of
        # entity.revert_to     = revert_to
        # entity.revert        = revert
        entity.compare_with  = compare_with
        Version.compare_with = compare_with


acts_as_versioned = Statement(ActsAsVersioned)


#
# decorator for watching for revert events
#

def after_revert(func):
    func._elixir_after_revert = True
    return func


__all__ = ['acts_as_versioned', 'after_revert']
