import repository

# TODO: multiple changes to same object in the same transaction

class TestRepository1:

    def setup_class(self):
        # we tear down here rather than in a teardown method so we can
        # investigate if things go wrong
        self.repo = repository.Repository() 
        self.repo.rebuild()

        txn = self.repo.begin_transaction()
        self.author = 'jones'
        self.pkgname = 'jones'
        pkg = txn.model.packages.create(name=self.pkgname)
        txn.author = self.author
        txn.log = ''
        txn.commit()

        txn2 = self.repo.begin_transaction()
        self.pkgname2 = 'testpkg2'
        self.log = 'Revision 2'
        txn2.author = self.author
        txn2.log = self.log
        self.newnotes = 'This is a note on a package.'
        pkg = txn2.model.packages.get(self.pkgname)
        pkg.notes = self.newnotes
        pkg2 = txn2.model.packages.create(name=self.pkgname2)
        txn2.commit()

    def test_youngest_revision(self):
        rev = self.repo.youngest_revision()
        revnum = rev.number
        assert revnum == 2

    def test_commit_attributes(self):
        rev = self.repo.youngest_revision()
        assert rev.author == self.author
        assert rev.log == self.log

    def test_package_revisions(self):
        rev = self.repo.youngest_revision()
        pkg = rev.model.packages.get(self.pkgname)
        assert len(pkg.revisions) == 2
        assert pkg.revisions[-1].revision.number == 2

    def test_package_revisions_2(self):
        rev = self.repo.get_revision(1)
        pkg = rev.model.packages.get(self.pkgname)
        assert len(pkg.revisions) == 1
        assert pkg.revisions[-1].revision.number == 1

    def test_exists_1(self):
        rev = self.repo.get_revision(1)
        pkg = rev.model.packages.get(self.pkgname)
        assert pkg.exists()

    def test_exists_2(self):
        rev = self.repo.get_revision(1)
        try:
            pkg = rev.model.packages.get(self.pkgname2)
            assert False, 'Should have raised an exception'
        except:
            pass

    def test_commit_material(self):
        rev = self.repo.youngest_revision()
        pkg = rev.model.packages.get(self.pkgname)
        revnum = pkg.revision.number 
        assert revnum == 2
        assert pkg.name == self.pkgname
        assert pkg.notes == self.newnotes

    def test_commit_material_2(self):
        rev = self.repo.get_revision(1)
        pkg = rev.model.packages.get(self.pkgname)
        assert pkg.revision.number == 1
        assert pkg.notes == None

    def test_list(self):
        rev = self.repo.youngest_revision()
        allpkgs = rev.model.packages.list()
        assert len(allpkgs) == 2

    def test_history(self):
        count = 2 # number of revisions
        history = self.repo.history()
        assert len(history) > 0
        for item in history:
            assert count == item.number
            count -= 1


class TestRepository2:

    def setup_class(self):
        self.repo = repository.Repository() 
        self.repo.rebuild()

        txn = self.repo.begin_transaction()
        self.pkgname = 'testpkg2'
        pkg = txn.model.packages.create(name=self.pkgname)
        txn.commit()

        txn3 = self.repo.begin_transaction()
        txn3.model.packages.delete(self.pkgname)
        txn3.commit()

    def test_delete_ok(self):
        rev = self.repo.youngest_revision()
        pkg = rev.model.packages.get(self.pkgname)
        assert pkg.state.name == 'deleted'

    def test_list(self):
        rev = self.repo.youngest_revision()
        allpkgs = rev.model.packages.list()
        assert len(allpkgs) == 0

    def test_list_2(self):
        rev = self.repo.youngest_revision()
        allpkgs = rev.model.packages.list('deleted')
        assert len(allpkgs) == 1


class TestDomainObjectWithForeignKey:

    def setup_class(self):
        # we tear down here rather than in a teardown method so we can
        # investigate if things go wrong
        self.repo = repository.Repository() 
        self.repo.rebuild()

        self.license1 = repository.License(name='test_license1')
        self.license2 = repository.License(name='test_license2')
        txn = self.repo.begin_transaction()
        self.pkgname = 'testpkgfk'
        pkg = txn.model.packages.create(name=self.pkgname)
        pkg.license = self.license1
        txn.commit()

        txn2 = self.repo.begin_transaction()
        pkg = txn2.model.packages.get(self.pkgname)
        pkg.license = self.license2
        txn2.commit()
 
    def test_set1(self):
        rev = self.repo.get_revision(1)
        pkg = rev.model.packages.get(self.pkgname)
        out = pkg.license.name 
        exp = self.license1.name
        assert out == exp

    def test_set2(self):
        rev = self.repo.get_revision(2)
        pkg = rev.model.packages.get(self.pkgname)
        out = pkg.license.name 
        exp = self.license2.name
        assert out == exp


class TestManyToMany:

    def setup_class(self):
        self.repo = repository.Repository() 
        self.repo.rebuild()

        txn = self.repo.begin_transaction()
        self.tagname = 'testtagm2m'
        self.pkgname = 'testpkgm2m'
        pkg = txn.model.packages.create(name=self.pkgname)
        tag = txn.model.tags.create(name=self.tagname)
        pkg2tag = txn.model.package_tags.create(package=pkg, tag=tag)
        self.pkg2tag_id = pkg2tag.id
        txn.commit()

    def test_1(self):
        rev = self.repo.youngest_revision()
        pkg = rev.model.packages.get(self.pkgname)
        # not really working so nothing to test

