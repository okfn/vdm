import sqlobject
uri = 'sqlite:/:memory:'
connection = sqlobject.connectionForURI(uri)
sqlobject.sqlhub.processConnection = connection

import vdm.sqlobject.base
import vdm.sqlobject.demo


# TODO: multiple changes to same object in the same transaction

class TestRepository1:

    def setup_class(self):
        # we tear down here rather than in a teardown method so we can
        # investigate if things go wrong
        self.repo = vdm.sqlobject.base.Repository(vdm.sqlobject.demo.DomainModel) 
        self.repo.rebuild()

        txn = self.repo.begin_transaction()
        self.author = 'jones'
        self.pkgname = 'jones'
        pkg = txn.model.packages.create(name=self.pkgname)
        txn.commit()

        txn2 = self.repo.begin_transaction()
        self.pkgname2 = 'testpkg2'
        self.log_message = 'Revision 2'
        txn2.author = self.author
        txn2.log_message = self.log_message
        self.newnotes = 'This is a note on a package.'
        pkg = txn2.model.packages.get(self.pkgname)
        pkg.notes = self.newnotes
        pkg2 = txn2.model.packages.create(name=self.pkgname2)
        txn2.commit()

    def test_youngest_revision(self):
        rev = self.repo.youngest_revision()
        revnum = rev.number
        assert revnum == 3

    def test_commit_attributes(self):
        rev = self.repo.youngest_revision()
        assert rev.author == self.author
        assert rev.log_message == self.log_message

    def test_package_history(self):
        rev = self.repo.youngest_revision()
        pkg = rev.model.packages.get(self.pkgname)
        assert len(pkg.history) == 2
        assert pkg.history[-1].revision.number == 3

    def test_package_history_2(self):
        rev = self.repo.get_revision(2)
        pkg = rev.model.packages.get(self.pkgname)
        assert len(pkg.history) == 1
        assert pkg.history[-1].revision.number == 2

    def test_exists_1(self):
        rev = self.repo.get_revision(2)
        pkg = rev.model.packages.get(self.pkgname)
        assert pkg.exists()

    def test_exists_2(self):
        rev = self.repo.get_revision(2)
        try:
            pkg = rev.model.packages.get(self.pkgname2)
            assert False, 'Should have raised an exception'
        except:
            pass

    def test_commit_material(self):
        rev = self.repo.youngest_revision()
        pkg = rev.model.packages.get(self.pkgname)
        revnum = pkg.revision.number 
        assert revnum == 3
        assert pkg.name == self.pkgname
        assert pkg.notes == self.newnotes

    def test_commit_material_2(self):
        rev = self.repo.get_revision(2)
        pkg = rev.model.packages.get(self.pkgname)
        assert pkg.revision.number == 2
        assert pkg.notes == None

    def test_list(self):
        rev = self.repo.youngest_revision()
        allpkgs = rev.model.packages.list()
        assert len(allpkgs) == 2

    def test_history(self):
        count = 3 # number of revisions
        history = list(self.repo.history())
        assert len(history) > 0
        for item in history:
            assert count == item.number
            count -= 1

    def test_purge(self):
        rev = self.repo.youngest_revision()
        pkg = rev.model.packages.purge(self.pkgname)
        pkgs = rev.model.packages.list()
        assert len(pkgs) == 1
        names = [ pkg.name for pkg in pkgs ]
        assert self.pkgname not in names


class TestRepository2:

    def setup_class(self):
        self.repo = vdm.sqlobject.base.Repository(vdm.sqlobject.demo.DomainModel) 
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
        self.repo = vdm.sqlobject.base.Repository(vdm.sqlobject.demo.DomainModel) 
        self.repo.rebuild()

        self.license1 = vdm.sqlobject.demo.License(name='test_license1')
        self.license2 = vdm.sqlobject.demo.License(name='test_license2')
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
        rev = self.repo.get_revision(2)
        pkg = rev.model.packages.get(self.pkgname)
        out = pkg.license.name 
        exp = self.license1.name
        assert out == exp

    def test_set2(self):
        rev = self.repo.get_revision(3)
        pkg = rev.model.packages.get(self.pkgname)
        out = pkg.license.name 
        exp = self.license2.name
        assert out == exp


class TestManyToMany:

    def setup_class(self):
        self.repo = vdm.sqlobject.base.Repository(vdm.sqlobject.demo.DomainModel) 
        self.repo.rebuild()

        txn = self.repo.begin_transaction()
        self.tagname = 'testtagm2m'
        self.tagname2 = 'testtagm2m2'
        self.pkgname = 'testpkgm2m'
        pkg = txn.model.packages.create(name=self.pkgname)
        self.tag = txn.model.tags.create(name=self.tagname)
        self.tag2 = txn.model.tags.create(name=self.tagname2)
        pkg2tag = txn.model.package_tags.create(package=pkg, tag=self.tag)
        self.pkg2tag_id = pkg2tag.id
        pkg.tags.create(tag=self.tag2)
        txn.commit()

    def test_1(self):
        rev = self.repo.youngest_revision()
        pkg = rev.model.packages.get(self.pkgname)
        pkg2tag = rev.model.package_tags.get(self.pkg2tag_id)
        assert pkg2tag.package.name == self.pkgname

    def test_2(self):
        rev = self.repo.youngest_revision()
        pkg = rev.model.packages.get(self.pkgname)
        pkg2tag = pkg.tags.get(self.tag2)
        assert pkg2tag.package.name == self.pkgname
        pkg2tag2 = pkg.tags.get(self.tag)
        assert pkg2tag2.package.name == self.pkgname
        assert pkg2tag2.tag.name == self.tagname

    def test_list(self):
        rev = self.repo.youngest_revision()
        pkg = rev.model.packages.get(self.pkgname)
        all = rev.model.package_tags.list() 
        assert len(all) == 2
        pkgtags = pkg.tags.list()
        assert len(pkgtags) == 2

    def test_another_txn(self):
        txn = self.repo.begin_transaction()
        pkg = txn.model.packages.get(self.pkgname)
        pkg.notes = 'blah'
        pkg2tag = pkg.tags.get(self.tag)
        pkg2tag.delete()
        txn.commit()
        rev = self.repo.youngest_revision()
        outpkg = rev.model.packages.get(self.pkgname)
        pkgtags = outpkg.tags.list()
        assert len(pkgtags) == 1

