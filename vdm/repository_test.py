from repository import Repository
# has to be a singleton ...
repo = Repository()

class TestRepositoryBasics:

    repo = repo
    reg = repo.registry 

    def test_states(self):
        states = self.reg.states
        assert len(states) == 3

    def test_revisions(self):
        revs = self.reg.revisions
        assert revs is not None
        assert len(revs) == 1

    def test__is_new_repository(self):
        assert not self.repo._is_new_repository()

    def test_init(self):
        assert len(self.repo.revisions) == 1
        rev1 = None
        for rev in self.repo.revisions:
            rev1 = rev
        assert rev1.author == 'system'
        assert rev1.state.name == 'active'

    def test_youngest_revision(self):
        rev1 = self.repo.youngest_revision()
        assert rev1.number == 1
        assert rev1.author == 'system'
        assert rev1.state.name == 'active'

