"""
A versioned domain model demonstration.
"""
import sqlobject
uri = 'sqlite:/:memory:'
__connection__ = sqlobject.connectionForURI(uri)

import base
from base import State


class License(sqlobject.SQLObject):

    name = sqlobject.StringCol(alternateID=True)


class PackageSQLObject(sqlobject.SQLObject):

    name = sqlobject.UnicodeCol(alternateID=True)


class PackageRevision(base.ObjectRevisionSQLObject):

    base_object_name = 'Package'
    # TODO: probably should not have this on the revision as immutable
    name = sqlobject.UnicodeCol(default=None)
    notes = sqlobject.UnicodeCol(default=None)
    license = sqlobject.ForeignKey('License', default=None)


class Package(base.VersionedDomainObject):

    sqlobj_class = PackageSQLObject
    sqlobj_version_class = PackageRevision


class DomainModel(object):

    def __init__(self, revision, transaction=None):
        self.revision = revision
        self.packages = base.VersionedDomainObjectRegister(Package, 'name', revision, transaction)

# -----------------------------------------------------------------
# Versioned Material Follows

class Revision(sqlobject.SQLObject):
    """A Revision to the domain model.

    A revision in the is valid only if {number} is not null (there may be some
    non-valid revisions in the database which correspond to failed or pending transactions).
    """

    # would like number to have alternateID=True but then cannot have
    # default=None
    number = sqlobject.IntCol(default=None, unique=True)
    author = sqlobject.UnicodeCol(default=None)
    log = sqlobject.UnicodeCol(default=None)
    # TODO: date time col (need to set in transaction)
    # date = sqlobject.DateTimeCol(default=None)

    # sqlobject takees over __init__ ...
    def _init(self, *args, **kw):
        sqlobject.SQLObject._init(self, *args, **kw)
        if 'transaction' in kw.keys():
            self.model = DomainModel(self, transaction)
        else:
            self.model = DomainModel(self)


class Transaction(object):
    """A transaction encapsulates an atomic change to the domain model.

    Should it just inherit from revision?
    ANS: no a Transaction generates a revision (if successful) but is not a
    revision
    """

    def __init__(self, base_revision):
        # TODO: start db transaction ....
        self.base_revision = base_revision
        self.model = DomainModel(self.base_revision, transaction=self)
        # the new revision that will be 'created' if this Transaction succeeds
        self.revision = Revision()
        self.author = None
        self.log = u''

    def commit(self):
        # TODO: generate the revision number in some better way
        self.revision.number = self.revision.id
        self.revision.log = self.log
        self.revision.author = self.author


class Repository(object):

    # should be in order needed for creation
    classes = [
            State,
            Revision,
            License,
            PackageSQLObject,
            PackageRevision,
            ]

    def create_tables(self):
        for cls in self.classes:
            cls.createTable(ifNotExists=True)

    def drop_tables(self):
        # cannot just use reversed as this operates in place
        size = len(self.classes)
        indices = range(size)
        indices.reverse()
        reversed = [ self.classes[xx] for xx in indices ]
        for cls in reversed:
            cls.dropTable(ifExists=True)
    
    def rebuild(self):
        "Rebuild the domain model."
        self.drop_tables()
        self.create_tables()
        self.init()

    def init(self):
        "Initialise the domain model with default data."
        State(name='active')
        State(name='deleted')

    def youngest_revision(self):
        revisions = Revision.select(orderBy=Revision.q.number).reversed()
        for rev in revisions:
            return rev
        # no revisions
        return None
    
    def get_revision(self, id):
        revs = list(Revision.select(Revision.q.number == id))
        if len(revs) == 0:
            raise Exception('Error: no revisions with id: %s' % id)
        elif len(revs) > 1:
            raise Exception('Error: more than one revision with id: %s' % id)
        else:
            return revs[0]
    
    def begin_transaction(self, revision_number=None):
        if revision_number == None:
            revision_number = self.youngest_revision()
        txn = Transaction(revision_number)
        return txn

    def history(self):
        """Get the history of the repository.

        @return: a list of ordered revisions with youngest first.
        """
        revisions = list(
                Revision.select(orderBy=Revision.q.number).reversed()
                )
        return revisions
