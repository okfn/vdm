'''Various useful tools for working with Versioned Domain Models.

Primarily organized within a `Repository` object.
'''
import logging
logger = logging.getLogger('vdm')

# fix up table dropping on postgres
# http://blog.pythonisito.com/2008/01/cascading-drop-table-with-sqlalchemy.html
from sqlalchemy.databases import postgres
class PGCascadeSchemaDropper(postgres.PGSchemaDropper):
     def visit_table(self, table):
        for column in table.columns:
            if column.default is not None:
                self.traverse_single(column.default)
        self.append("\nDROP TABLE " +
                    self.preparer.format_table(table) +
                    " CASCADE")
        self.execute()

postgres.dialect.schemadropper = PGCascadeSchemaDropper

from sqlalchemy import create_engine
from sqlalchemy.orm import ScopedSession
from base import set_revision, State, Revision
class Repository(object):
    def __init__(self, our_metadata, our_session, dburi=None):
        '''
        TODO: deal with scoped versus non-scoped sessions ... 
            e.g. in init_vdm

        @param dburi: sqlalchemy dburi. If supplied will create engine and bind
        it to metadata and session.
        '''
        self.metadata = our_metadata
        self.session = our_session
        self.dburi = dburi
        self.have_scoped_session = isinstance(self.session, ScopedSession)
        self.transactional = False 
        if self.have_scoped_session:
            self.transactional = self.session().transactional
        else:
            self.transactional = self.session.transactional
        if self.dburi:
            engine = create_engine(dburi)
            self.metadata.bind = engine 
            self.session.bind = engine

    def rebuild_db(self):
        logger.info('Rebuilding DB')
        self.metadata.drop_all(bind=self.metadata.bind)
        self.metadata.create_all(bind=self.metadata.bind)

    def make_states(self, session):
        ACTIVE = State(id=1, name='active').name
        DELETED = State(id=2, name='deleted').name
        self.commit()
        return ACTIVE, DELETED

    def init_vdm(self):
        states = State.query.all()
        if len(states) == 0:
            self.make_states(self.session())
        self.session.remove()

    def commit(self, remove=True):
        if self.transactional:
            self.session.commit()
        else:
            self.session.flush()
        if remove:
            self.session.remove()
    
    def new_revision(self):
        rev = Revision()
        set_revision(self.session, rev)
        return rev


from sqlalchemy.orm import class_mapper
class PurgeRevision(object):
    '''Purge all changes associated with a revision.

    @param leave_record: if True leave revision in existence but change message
        to "PURGED: {date-time-of-purge}". If false delete revision object as
        well.

    Summary of the Algorithm
    ------------------------

    # list everything affected by this transaction
    # check continuity objects and cascade on everything else ?
    # crudely get all object revisions associated with this
    # then check whether this is the only revision and delete the
    # continuity object

    # alternatively delete all associated object revisions\
    # then do a select on continutity to check which have zero associated
    # revisions (should only be these ...)
    '''

    def __init__(self, revision, leave_record=True):
        super(PurgeRevision, self).__init__()
        self.revision = revision
        self.leave_record = leave_record
        self.versioned_objects = versioned_objects
        self.revision_objects = [ obj.__revision_class__ for obj in
                self.versioned_objects ]

    def execute(self):
        logger.debug('Purging revision: %s' % self.revision.id)
        to_purge = []
        for revobj in self.revision_objects:
            items = revobj.query.filter_by(revision=self.revision)
            for item in items:
                continuity = item.continuity
                if continuity.revision == self.revision:
                    trevobjs = revobj.query.filter_by(
                            continuity=continuity
                            ).order_by(revobj.c.revision_id.desc()).limit(2).all()
                    if len(trevobjs) == 0:
                        raise Exception('Should have at least one revision.')
                    if len(trevobjs) == 1:
                        to_purge.append(continuity)
                    else:
                        new_correct_revobj = trevobjs[1] # older one
                        # revert continuity object back to original version
                        table = class_mapper(continuity.__class__).mapped_table
                        # TODO: ? this will only set columns and not mapped attribs
                        # TODO: need to do this directly on table or disable
                        # revisioning behaviour ...
                        for key in table.c.keys():
                            value = getattr(new_correct_revobj, key)
                            print key, value
                            print 'old:', getattr(continuity, key)
                            setattr(continuity, key, value)
                model.Session.delete(item)
        for item in to_purge:
            item.purge()
        if self.leave_record:
            self.revision.message = 'PURGED'
        else:
            model.Session.delete(self.revision)

        # now commit changes
        try:
            model.Session.commit()
        except:
            model.Session.rollback()
            model.Session.remove()
            raise

