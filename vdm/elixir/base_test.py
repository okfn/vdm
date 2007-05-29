from datetime import datetime

from elixir import *
uri = 'sqlite:///:memory:'
metadata.connect(uri)


from vdm.elixir.base import *

class TestStateAndRevision:

    def setup_class(self):
        elixir.create_all()
        self.active = State(name='active')
        self.deleted = State(name='deleted')
        self.pending = State(name='pending')
        self.msg = 'blah'
        self.rev1 = Revision(log_message=self.msg)
        elixir.objectstore.flush()
    
    def teardown_class(self):
        elixir.objectstore.clear()
        elixir.drop_all()

    def test_1(self):
        count = 0
        for mm in State.select():
            count += 1
        assert count == 3 

    def test_revision(self):
        rev = Revision.get(self.rev1.id)
        assert rev.log_message == self.msg
        assert rev.timestamp is not None

    def test_is_transaction(self):
        assert self.rev1.is_transaction()

    def test_commit(self):
        self.rev1.commit()
        rev = Revision.get(self.rev1.id)
        assert rev.state == self.active 
        assert rev.number == self.rev1.id


class StubModel(DomainModelBase):
    classes = []
    name = 'StubbedModel'

    def __init__(self, revision, transaction=None):
        super(StubModel, self).__init__(revision, transaction)


class TestRepositoryBasics:

    def setup_class(self):
        self.model_name = StubModel.name
        self.repo = Repository(StubModel)
        self.repo.rebuild()

    def test_states(self):
        states = list(State.select()) 
        assert len(states) == 3

    def test_history(self):
        revs = self.repo.history()
        assert revs is not None
        assert len(list(revs)) == 1

    def test_init(self):
        revs = list(Revision.select())
        assert len(revs) == 1
        rev1 = None
        for rev in revs:
            rev1 = rev
        assert rev1.author == 'system'
        assert rev1.state.name == 'active'
        assert rev.log_message == 'Initialising the Repository'
        now = datetime.now()
        assert rev.timestamp <= now

    def test_youngest_revision(self):
        rev1 = self.repo.youngest_revision()
        assert rev1.number == 1
        assert rev1.author == 'system'
        assert rev1.state.name == 'active'
        assert not rev1.is_transaction()

    def test_begin_transaction(self):
        txn = self.repo.begin_transaction()
        starttime = txn.timestamp
        assert txn.model.name == self.model_name
        assert txn.is_transaction()
        txn.commit()
        assert not txn.is_transaction()
        endtime = txn.timestamp
        print starttime, endtime
        assert endtime > starttime

    def test_get_revision(self):
        id = 1
        rev = self.repo.get_revision(id)
        assert rev.author == 'system'
        assert rev.model.revision.id == id
        assert rev.model.name == self.model_name


class TestRepository2:

    def setup_class(self):
        self.model_name = StubModel.name
        self.repo = Repository(StubModel)
        self.repo.rebuild()
        # create a couple of transactions
        txn1 = self.repo.begin_transaction()
        txn1.commit()
        txn2 = self.repo.begin_transaction()
        txn2.commit()
        # leave this one uncommitted so it just does nothing
        txn3 = self.repo.begin_transaction()
        txn4 = self.repo.begin_transaction()
        txn4.commit()
        assert txn4.number is not None

    def test_history(self):
        revs = list(self.repo.history())
        assert revs is not None
        for rev in revs:
            print rev.id, rev.number, rev.state.name
        assert len(revs) == 4
        assert revs[-1].number == 1
        assert revs[0].number == 5

    def test_youngest_revision(self):
        rev1 = self.repo.youngest_revision()
        print rev1.id
        assert rev1.number == 5


#class TestGetAttributeNames:
#
#    def test_1(self):
#        class X:
#            class sqlmeta:
#                columns = { 
#                        'id' : None,
#                        'name' : None,
#                        'licenseID' : None,
#                        'revisionID' : None,
#                        'base' : None,
#                        }
#        out = get_attribute_names(X) 
#        exp = [ 'id', 'name', 'license' ]
#        assert set(out) == set(exp)
#

class StubEntity(elixir.Entity):
    elixir.has_field('name', Unicode)

class TestRegister:
    
    def setup_class(self):
        elixir.objectstore.clear()
        elixir.drop_all()
        elixir.create_all()
        self.reg = Register(StubEntity, 'name')
        self.name1 = 'a'
        self.name2 = 'b'
        self.reg.create(name=self.name1)
        self.reg.create(name=self.name2)
        elixir.objectstore.flush()

    def test_get(self):
        # tests create too -- obviously
        obj = self.reg.get(self.name1)
        assert obj.name == self.name1
    
    def test_list(self):
        out = self.reg.list()
        assert len(out) == 2

    def test__iter__(self):
        count = 0
        names = [ self.name1, self.name2 ]
        for obj in self.reg:
            assert obj.name in names
            count += 1
        assert count == 2

    def test_len(self):
        assert len(self.reg) == 2

    def test_delete(self):
        self.reg.delete(self.name1)
        elixir.objectstore.flush()
        assert len(self.reg) == 1

    def test_purge(self):
        self.reg.purge(self.name2)
        elixir.objectstore.flush()
        assert len(self.reg) == 0
