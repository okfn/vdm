from datetime import datetime
import sqlobject
uri = 'sqlite:/:memory:'
connection = sqlobject.connectionForURI(uri)
sqlobject.sqlhub.processConnection = connection

from vdm.sqlobject.base import *

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

    def test_history(self):
        revs = list(self.repo.history())
        assert revs is not None
        assert len(revs) == 4
        assert revs[-1].number == 1

    def test_youngest_revision(self):
        rev1 = self.repo.youngest_revision()
        assert rev1.number == 5


class TestGetAttributeNames:

    def test_1(self):
        class X:
            class sqlmeta:
                columns = { 
                        'id' : None,
                        'name' : None,
                        'licenseID' : None,
                        'revisionID' : None,
                        'base' : None,
                        }
        out = get_attribute_names(X) 
        exp = [ 'id', 'name', 'license' ]
        assert set(out) == set(exp)

import sqlobject
class StubSQLObject(sqlobject.SQLObject):
    name = sqlobject.StringCol(alternateID=True)

class TestRegister:
    
    def setup_class(self):
        StubSQLObject.dropTable(ifExists=True)
        StubSQLObject.createTable()
        self.reg = Register(StubSQLObject, 'name')
        self.name1 = 'a'
        self.name2 = 'b'
        self.reg.create(name=self.name1)
        self.reg.create(name=self.name2)

    def test_get(self):
        # tests create too obviously
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
        assert len(self.reg) == 1

    def test_purge(self):
        self.reg.purge(self.name2)
        assert len(self.reg) == 0
