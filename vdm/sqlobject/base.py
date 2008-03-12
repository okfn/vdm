"""
Developer Comments
==================

Crude dependency injection via the repository object.

WARNING: currently due to the nature of SQLObject it is not possible to have
multiple revisions of the *same* object 'live' at the same time.

rev1 = repo.get_revision(10)
rev2 = repo.get_revision(11)

obj1 = rev1.model.some_object_type.get('name1')
obj2 = rev1.model.some_object_type.get('name1')
# should be False but will yield True
obj1.revision.id == obj1.revision.id
# this is because sqlobject only allows one python object in memory per
# SQLObject
# To solve this we will need to use transactions in some clever way
"""
from datetime import datetime

import sqlobject

class State(sqlobject.SQLObject):

    name = sqlobject.StringCol(alternateID=True)


class Revision(sqlobject.SQLObject):
    """A Revision to the domain model.

    A revision in the is valid only if {number} is not null (there may be some
    non-valid revisions in the database which correspond to failed or pending transactions).
    """

    # should default to pending category
    state = sqlobject.ForeignKey('State', default=3)
    number = sqlobject.IntCol(default=None, unique=True)
    author = sqlobject.UnicodeCol(default=None)
    log_message = sqlobject.UnicodeCol(default=None)
    # for a transaction this time it started
    # for a revision time it was completed
    timestamp = sqlobject.DateTimeCol(default=datetime.now())
    base_revision = sqlobject.ForeignKey('Revision', default=None)

    # sqlobject takees over __init__ ...
    def _init(self, *args, **kw):
        sqlobject.SQLObject._init(self, *args, **kw)
        # TODO: start db transaction .... actually not sure about this (maybe
        # txns can persist across sessions)
        # self.model = DomainModel(self, self.is_transaction)
        self.model = None

    def is_transaction(self):
        is_txn = self.state == State.byName('pending')
        return is_txn

    def set_model(self, model):
        self.model = model

    def commit(self):
        if not self.is_transaction():
            raise Exception('This is not a transaction')
        # TODO: generate the revision number in some better way
        self.number = self.id
        self.state = State.byName('active')
        self.timestamp = datetime.now()


class DomainModelBase(object):

    classes = []

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

    # should be in order needed for creation
    classes = [
            State,
            Revision,
            ]

    def __init__(self, model_class):
        self.model_class = model_class

    def create_tables(self):
        for cls in self.classes + self.model_class.classes:
            cls.createTable(ifNotExists=True)

    def drop_tables(self):
        # cannot just use reversed as this operates in place
        classes = self.classes + self.model_class.classes
        size = len(classes)
        indices = range(size)
        indices.reverse()
        reversed = [ classes[xx] for xx in indices ]
        for cls in reversed:
            cls.dropTable(ifExists=True)
    
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
        # do not use a transaction but insert directly to avoid the bootstrap
        # problem
        base_rev = Revision(
                number=1,
                log_message='Initialising the Repository',
                author='system',
                state = State.byName('active'),
                )
        self.model_class.initialise_repository()

    def youngest_revision(self):
        # TODO: write a test to check that we only get 'active' revisions not
        # those which are inactive or aborted ...
        revs = self.history()
        for rev in revs:
            model = self.model_class(rev)
            rev.set_model(model)
            return rev
        # no revisions
        return None
    
    def get_revision(self, id):
        revs = list(Revision.select(Revision.q.number == id))
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
        active = State.byName('active') 
        revisions = Revision.selectBy(state=active)
        revisions = revisions.orderBy('number')
        revisions = revisions.reversed()
        return revisions


class ObjectRevisionSQLObject(sqlobject.SQLObject):

    # to be defined in inheriting classes
    # base_object_name = ''
    
    state = sqlobject.ForeignKey('State', default=1)
    revision = sqlobject.ForeignKey('Revision')

    def copy(self, transaction):
        newvals = {}
        for col in self.sqlmeta.columns:
            if not col.startswith('revision'):
                value = getattr(self, col)
                newvals[col] = value
        newvals['revision'] = transaction
        newrev = self.__class__(**newvals)
        return newrev


def get_attribute_names(sqlobj_class):
    # extra attributes added into Revision classes that should not be available
    # in main object
    excluded = [ 'revision', 'base' ]
    results = []
    for col in sqlobj_class.sqlmeta.columns.keys():
        if col.endswith('ID'):
            col = col[:-2]
        if col not in excluded:
            results.append(col)
    return results


class VersionedDomainObject(sqlobject.SQLObject):

    sqlobj_class = None
    sqlobj_version_class = None
    
    def _init(self, *args, **kwargs):
        super(VersionedDomainObject, self)._init(*args, **kwargs)
        # TODO: get rid of this holdover from old setup
        self.sqlobj = self
        self._version_operations_ok = False

    def set_revision(self, revision, transaction):
        self.revision = revision
        self.transaction = transaction
        self.have_working_copy = False
        # use history instead of revisions because revisions causes conflict
        # with sqlobject
        self.history = []
        self._get_revisions()
        self._version_operations_ok = True
        self._setup_versioned_m2m()

    def _setup_versioned_m2m(self):
        for name, module_name, object_name, join_object_name in self.m2m:
            # do some meta trickery to get class from the name
            # __import__('A.B') returns A unless fromlist is *not* empty
            mod = __import__(module_name, None, None, 'blah')
            obj = mod.__dict__[join_object_name]
            self.__dict__[name] = KeyedRegister(
                    type=obj,
                    key_name='id',
                    revision=self.revision,
                    transaction=self.transaction,
                    keyed_value_name=self.__class__.__name__.lower(),
                    keyed_value=self,
                    other_key_name=object_name.lower()
                    )

    def _assert_version_operations_ok(self):
        if not self._version_operations_ok:
            msg = 'No Revision is set on this object so it is not possible' + \
                    ' to do operations involving versioning.'
            raise Exception(msg)

    def exists(self):
        # is this right -- what happens if we did not have anything at revision
        # and have just created something as part of the current transaction
        # ...
        return len(self.history) > 0

    def delete(self):
        deleted = State.byName('deleted')
        self.state = deleted
    
    def _get_revisions(self):
        # if not based off any revision (should only happen if this is first
        # ever revision in entire repository)
        if self.revision is None:
            return
        ourrev = self.revision.number
        baseobj = self.sqlobj
        
        # TODO: more efficient way
        select = list(
                self.sqlobj_version_class.selectBy(base=self)
                )
        revdict = {}
        for objrev in select:
            revdict[objrev.revision.number] = objrev
        revnums = revdict.keys()
        revnums.sort()
        if len(revnums) == 0: # should only happen if package only just created
            return
        created_revision = revnums[0]
        if created_revision > ourrev: # then package does not exist yet
            return
        # Take all package revisions with revision number <= ourrev
        # TODO: make more efficient
        for tt in revnums:
            if tt <= ourrev:
                self.history.append(revdict[tt])

    def _current(self):
        return self.history[-1]

    def __getattr__(self, attrname):
        if attrname in self.versioned_attributes:
            self._assert_version_operations_ok()
            return getattr(self._current(), attrname)
        else:
            raise AttributeError()

    def __setattr__(self, attrname, attrval):
        if attrname != 'versioned_attributes' and attrname in self.versioned_attributes:
            self._assert_version_operations_ok()
            self._ensure_working_copy()
            current = self._current()
            # print 'Setting attribute before: ', attrname, attrval, current
            setattr(current, attrname, attrval)
            # print 'Setting attribute after: ', attrname, attrval, current
        else:
            super(VersionedDomainObject, self).__setattr__(attrname, attrval)

    def _ensure_working_copy(self):
        if not self.have_working_copy:
            wc = self._new_working_copy()
            self.have_working_copy = True
            self.history.append(wc)

    def _new_working_copy(self):
        # 2 options: either we are completely new or based off existing current
        if len(self.history) > 0:
            return self._current().copy(self.transaction)
        else:
            if self.transaction is None:
                raise Exception('Unable to set attributes outside of a transaction')
            rev = self.sqlobj_version_class(
                    base=self.sqlobj,
                    revision=self.transaction)
            return rev
    
    def purge(self):
        select = self.sqlobj_version_class.selectBy(base=self)
        for rev in select:
            self.sqlobj_version_class.delete(rev.id)
        # because we have overriden delete have to play smart
        super(VersionedDomainObject, self).delete(self.id)
        # self.__class__.delete(self.id)


## ------------------------------------------------------
## Registers

class Register(object):

    def __init__(self, type, key_name):
        self.type = type
        self.key_name = key_name

    def create(self, **kwargs):
        return self.type(**kwargs)
    
    def get(self, key):
        if self.key_name != 'id':
            method_name = 'by' + self.key_name.capitalize()
            method = self.type.__dict__[method_name]
            # because method is a class method method(-) will not work
            # Instead have to do some special stuff see:
            # http://mail.python.org/pipermail/python-list/2005-March/312183.html 
            obj = method.__get__(None, self.type)(key)
        else:
            obj = self.type.get(key)
        return obj
    
    def delete(self, key):
        self.purge(key)

    def purge(self, key):
        obj = self.get(key)
        self.type.delete(obj.id)

    def list(self):
        return list(self.type.select(orderBy=self.key_name))

    def __iter__(self):
        return self.list().__iter__()

    def __len__(self):
        return len(self.list())


class VersionedDomainObjectRegister(Register):

    def __init__(self, type, key_name, revision, transaction=None, **kwargs):
        super(VersionedDomainObjectRegister, self).__init__(type, key_name)
        self.revision = revision
        self.transaction = transaction

    def create(self, **kwargs):
        newargs = dict(kwargs)
        obj = self.type(**newargs)
        obj.set_revision(self.revision, self.transaction)
        obj._ensure_working_copy()
        for key, value in kwargs.items():
            setattr(obj, key, value)
        return obj
    
    def get(self, key):
        obj = super(VersionedDomainObjectRegister, self).get(key)
        obj.set_revision(self.revision, self.transaction)
        if obj.exists():
            return obj
        else:
            msg = 'No object identified by %s exists at revision %s' % (key,
                    self.revision)
            raise Exception(msg)

    def list(self, state='active'):
        all_objs_ever = self.type.select(orderBy=self.key_name)
        results = []
        for obj in all_objs_ever:
            obj.set_revision(self.revision, self.transaction)
            if obj.exists() and obj.state.name == state:
                results.append(obj)
        return results

    def delete(self, key):
        obj = self.get(key)
        obj.delete()

    def purge(self, key):
        obj = self.get(key)
        obj.purge()

class KeyedRegister(VersionedDomainObjectRegister):
    """Provide a register keyed by a certain value.

    E.g. you have a package with tags and you want to do for a given instance
    of Package (pkg say):

    pkg.tags.get(tag)
    """

    def __init__(self, *args, **kwargs):
        kvname = kwargs['keyed_value_name']
        kv = kwargs['keyed_value']
        del kwargs['keyed_value_name']
        del kwargs['keyed_value']
        super(KeyedRegister, self).__init__(*args, **kwargs)
        self.keyed_value_name = kvname
        self.keyed_value = kv
        self.other_key_name = kwargs['other_key_name']

    def create(self, **kwargs):
        newargs = dict(kwargs)
        newargs[self.keyed_value_name] = self.keyed_value
        return super(KeyedRegister, self).create(**newargs)

    def get(self, key):
        # key is an object now (though could also be a name)
        # add ID as will be a foreign key
        objref1 = getattr(self.type.q, self.keyed_value_name + 'ID')
        objref2 = getattr(self.type.q, self.other_key_name + 'ID')
        sel = self.type.select(sqlobject.AND(
            objref1 == self.keyed_value.id, objref2 == key.id)
            )
        sel = list(sel)
        if len(sel) == 0:
            msg = '%s not in this register' % key
            raise Exception(msg)
        # should have only one item
        newkey = sel[0].id
        return super(KeyedRegister, self).get(newkey)

    def list(self, state='active'):
        # TODO: optimize by using select directly
        # really inefficient ...
        all = super(KeyedRegister, self).list(state)
        results = []
        for item in all:
            val = getattr(item, self.keyed_value_name)
            if val == self.keyed_value:
                results.append(item)
        return results


