# many of the tests are in demo_test as that sets up nice fixtures
from tools import *

dburi = 'postgres://tester:pass@localhost/vdmtest'
from demo import *
class TestRepository:
    repo = Repository(metadata, Session, dburi)

    def test_transactional(self):
        assert self.repo.have_scoped_session
        assert self.repo.transactional

    def test_init_vdm(self):
        self.repo.session.remove()
        self.repo.rebuild_db()
        assert len(State.query.all()) == 0
        self.repo.init_vdm()
        assert len(State.query.all()) == 2

    def test_new_revision(self):
        self.repo.session.remove()
        rev = self.repo.new_revision()
        assert rev is not None

