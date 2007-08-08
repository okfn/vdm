from datetime import datetime

import elixir
from elixir import *
uri = 'sqlite:///:memory:'
metadata.connect(uri)

from vdm.elixir import *


class DemoEntityRevision(elixir.Entity):

    is_version()
    elixir.has_field('name', elixir.Unicode()) 
    elixir.belongs_to('base', of_kind='DemoEntity')


class DemoEntity(elixir.Entity):

    is_versioned('DemoEntityRevision')
    has_versioned_field('name')
    # elixir barfs if the object has no defined fields ...
    elixir.has_field('blah', elixir.Integer)


class TestStuff:

    def setup_class(self):
        elixir.create_all()
        self.xx = DemoEntity()
        elixir.objectstore.flush()

    def teardown_class(self):
        elixir.objectstore.clear()
        elixir.drop_all()

    def test_basic_attributes(self):
        assert hasattr(self.xx, '_ensure_version_operations_ok')
        self.xx._ensure_version_operations_ok()
        assert len(self.xx.history) == 0

    def test_history(self):
        self.xx._ensure_working_copy()
        assert len(self.xx.history) == 1
        out = self.xx._current()
        assert out is not None
        assert hasattr(out, 'name')

    def test_set_attribute(self):
        en1 = DemoEntity()
        en1.name = 'jones'
        elixir.objectstore.flush()
        elixir.objectstore.clear()
        out1 = DemoEntity.get(en1.id)
        assert out1.name == 'jones'

