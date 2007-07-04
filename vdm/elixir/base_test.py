from datetime import datetime

from elixir import *
uri = 'sqlite:///:memory:'
metadata.connect(uri)

from vdm.elixir import *


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
