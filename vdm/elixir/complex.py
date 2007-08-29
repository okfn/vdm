'''
A versioning plugin for Elixir.

Supports changes to multiple objects and relationships in a single
revision/version.
'''
import elixir
import sqlalchemy
from elixir                import Integer, DateTime
from elixir.statements     import Statement
from elixir.fields         import Field
from sqlalchemy            import Table, Column, and_, desc
from sqlalchemy.orm        import mapper, MapperExtension, EXT_PASS
from datetime              import datetime

import inspect


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
        import sqlalchemy
        self.session = sqlalchemy.object_session(self)
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
        session = sqlalchemy.object_session(instance)
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
    
    def before_update(self, mapper, connection, instance):        
        self._set_revision(instance)
        instance.timestamp = datetime.now()
        # copy old value into history
        values = instance.table.select(get_entity_where(instance)).execute().fetchone()
        colvalues = dict(values.items())
        instance.__class__.__history_table__.insert().execute(colvalues)
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
        
    def __init__(self, entity):
        entity._descriptor.add_mapper_extension(versioned_mapper_extension)
        
        timestampField = Field(DateTime, colname='timestamp')
        entity._descriptor.add_field(timestampField)
        # will auto attach to the entity in question
        revisionField = elixir.relationships.BelongsTo(entity=entity,
                name='revision', of_kind='vdm.elixir.complex.Revision')
        self.entity = entity
    
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
            return entity._descriptor.objectstore.query(Version).select(get_history_where(self))
        
        def get_as_of(self, dt):
            # if the passed in timestamp is older than our current version's
            # time stamp, then the most recent version is our current version
            if self.timestamp < dt: return self
            
            # otherwise, we need to look to the history table to get our
            # older version
            items = entity._descriptor.objectstore.query(Version).select(
                and_(get_history_where(self), Version.c.timestamp <= dt),
                order_by=desc(Version.c.timestamp),
                limit=1
            )
            if items: return items[0]
            else: return None
        
#        def revert_to(self, to_version):
#            hist = entity.__history_table__
#            old_version = hist.select(and_(
#                get_history_where(self), 
#                hist.c.version==to_version
#            )).execute().fetchone()
#            
#            entity.table.update(get_entity_where(self)).execute(
#                dict(old_version.items())
#            )
#            
#            hist.delete(and_(get_history_where(self), hist.c.version>=to_version)).execute()
#            for event in after_revert_events: event(self)
        
#        def revert(self):
#            assert self.version > 1
#            self.revert_to(self.version - 1)
            
        def compare_with(self, version):
            differences = {}
            for column in self.c:
                if column.name == 'version': continue
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
