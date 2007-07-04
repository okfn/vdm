from datetime import datetime

from elixir import *
import elixir
import sqlalchemy

class State(elixir.Entity):

    elixir.has_field('name', elixir.Unicode) 

class Revision(elixir.Entity):

    # should default to pending category
    # elixir.belongs_to('state', of_kind='State', default=3)
    elixir.belongs_to('state', of_kind='State')
    elixir.has_field('number', elixir.Integer)
    elixir.has_field('author', elixir.Unicode)
    elixir.has_field('log_message', elixir.Unicode)
    # for a transaction this time it started
    # for a revision time it was completed
    elixir.has_field('timestamp', elixir.DateTime, default=datetime.now)
    elixir.belongs_to('base_revision', of_kind='Revision')

    def __init__(self, *arg, **kwargs):
        super(Revision, self).__init__(*arg, **kwargs)
        self._state_pending = State.get_by(name='pending')
        if self.state is None: # only on creation ...
            self.state = self._state_pending
        # TODO: sort this out
        # seemingly default value is not working if we do not flush (not in the
        # session???)
        self.timestamp = datetime.now()
        self.model = None
        # automatically flush so that this now exists in the db
        elixir.objectstore.flush()

    def is_transaction(self):
        is_txn = self.state == self._state_pending
        return is_txn

    def set_model(self, model):
        self.model = model

    def commit(self):
        print "Committing: ", self.id
        if not self.is_transaction():
            raise Exception('This is not a transaction')
        # TODO: generate the revision number in some better way
        self.number = self.id
        self.state = State.get_by(name='active')
        self.timestamp = datetime.now()
        # flush commits everything into the db
        elixir.objectstore.flush()


class DomainModelBase(object):

    def __init__(self, revision, transaction):
        super(DomainModelBase, self).__init__()
        self.revision = revision
        self.transaction = transaction

    @classmethod
    def initialise_repository(self):
        """Stub method used to initialise default data in the repository.

        Only run once when repository is first created.
        """
        pass


class Repository(object):

    def __init__(self, model_class):
        self.model_class = model_class

    def create_tables(self):
        elixir.create_all()

    def drop_tables(self):
        elixir.objectstore.clear()
        elixir.drop_all()
    
    def rebuild(self):
        "Rebuild the domain model."
        self.drop_tables()
        self.create_tables()
        self.init()

    def init(self):
        "Initialise the domain model with default data."
        State(name='active')
        State(name='deleted')
        State(name='pending')
        elixir.objectstore.flush()
        # do not use a transaction but insert directly to avoid the bootstrap
        # problem
        base_rev = Revision(
                number=1,
                log_message='Initialising the Repository',
                author='system',
                state = State.get_by(name='active'),
                )
        self.model_class.initialise_repository()
        elixir.objectstore.flush()

    def youngest_revision(self):
        # TODO: write a test to check that we only get 'active' revisions not
        # those which are inactive or aborted ...
        revs = self.history()
        print len(revs)
        for rev in revs:
            model = self.model_class(rev)
            rev.set_model(model)
            return rev
        # no revisions
        return None
    
    def get_revision(self, id):
        revs = Revision.select_by(number=id)
        if len(revs) == 0:
            raise Exception('Error: no revisions with id: %s' % id)
        elif len(revs) > 1:
            raise Exception('Error: more than one revision with id: %s' % id)
        else:
            rev = revs[0]
            model = self.model_class(rev)
            rev.set_model(model)
            return rev
    
    def begin_transaction(self, revision=None):
        if revision is None:
            revision = self.youngest_revision()
        txn = Revision(base_revision=revision)
        model = self.model_class(revision, txn)
        txn.set_model(model)
        return txn
    
    def history(self):
        """Get the history of the repository.

        Revisions will not allow you to be at the model as that will not
        work correctly (see comments at top of module).

        @return: a list of ordered revisions with youngest first.
        """
        active = State.get_by(name='active') 
        revisions = Revision.query()
        revisions = revisions.filter_by(state=active)
        revisions = revisions.order_by(sqlalchemy.desc('number'))
        revisions = revisions.select()
        return revisions


