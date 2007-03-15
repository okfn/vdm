import dm.application
import dm.dom.builder
from vdm.app import *

class RepositoryModelBuilder(SimpleModelBuilder):

    def construct(self):
        self.load_state()
        self.load_vdm()

    def load_state(self):
        from dm.dom.state import State
        self.registry.registerDomainClass(State)
        self.registry.states = State.createRegister()

    def load_vdm(self):
        import vdm.revision
        self.registry.registerDomainClass(vdm.revision.Revision)
        self.registry.revisions = vdm.revision.Revision.createRegister()

class RepositoryBuilder(SimpleBuilder):

    def findModelBuilder(self):
        return RepositoryModelBuilder()

class Repository(dm.application.Application):
    builderClass = RepositoryBuilder

    def __init__(self):
        super(Repository, self).__init__()
        # TODO: check this has not been done already
        self.initialise()
        self.revisions = self.registry.revisions
        if self._is_new_repository():
            self.init()

    def initialise(self):
        self.registry.states.create('active')
        self.registry.states.create('deleted')
        self.registry.states.create('pending')

    def _is_new_repository(self):
        # Need to be more careful -- could have a non-valid revision in there
        # from a failed transaction but would be very unusual as it would mean
        # init() had failed
        no_revisions = len(self.registry.revisions) == 0
        return no_revisions

    def init(self):
        # do not use a transaction but insert directly to avoid the bootstrap
        # problem
        base_rev = self.registry.revisions.create(
                number=1,
                log_message='Initialising the Repository',
                author='system',
                state = self.registry.states['active'],
                )

    def youngest_revision(self):
        # sort by hand for the time being
        # investigate search in future ...
        holding = {}
        for rev in self.registry.revisions:
            if rev.number is not None:
                holding[rev.number] = rev
        numbers = holding.keys()
        if len(numbers) == 0:
            return None # no revisions
        numbers.sort()
        last_rev_number = numbers[-1]
        return holding[last_rev_number]
    
    def get_revision(self, id):
        raise Exception('Not Implemented')
        revs = list(Revision.select(Revision.q.number == id))
        if len(revs) == 0:
            raise Exception('Error: no revisions with id: %s' % id)
        elif len(revs) > 1:
            raise Exception('Error: more than one revision with id: %s' % id)
        else:
            return revs[0]
    
    def begin_transaction(self, revision=None):
        if revision == None:
            revision = self.youngest_revision()
        txn = self.registry.revisions.create()
        txn.base_revision = revision
        txn.save()
        return txn

    def history(self):
        """Get the history of the repository.

        @return: a list of ordered revisions with youngest first.
        """
        raise Exception('Not Implemented')
        revisions = list(
                Revision.select(orderBy=Revision.q.number).reversed()
                )
        return revisions

