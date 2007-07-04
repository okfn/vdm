from datetime import datetime

from elixir import *
import elixir
import sqlalchemy


class ObjectRevisionEntity(object):

    # to be defined in inheriting classes
    # base_object_name = ''
    
    # elixir concrete inheritance does not work so have to use a mixin approach
    # define these in actual class
    # elixir.belongs_to('state', of_kind='State')

    def __init__(self, *args, **kwargs):
        super(ObjectRevisionEntity, self).__init__()

    def _default_state(self):
        self.state_id = 1

    def copy(self, transaction):
        newvals = {}
        for col in self._descriptor.fields:
            if not col.startswith('revision') and col != 'id':
                value = getattr(self, col)
                newvals[col] = value
        newvals['revision'] = transaction
        newrev = self.__class__(**newvals)
        return newrev


def get_attribute_names(object_version):
    # extra attributes added into Revision classes that should not be available
    # in main object
    excluded = [ 'id', 'revision', 'base' ]
    results = []
    # do not worry about many-to-many fields as we never have them on the
    # version
    for col in object_version._descriptor.fields:
        if col.endswith('_id'):
            col = col[:-3]
        if col not in excluded:
            results.append(col)
    return results


class VersionedDomainObject(object):

    version_class = None
    
    def _init_versioned_domain_object(self):
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

    def _get_revisions(self):
        # if not based off any revision (should only happen if this is first
        # ever revision in entire repository)
        if self.revision is None:
            return
        ourrev = self.revision.number
        
        # TODO: more efficient way
        select = list(
                self.version_class.select_by(base=self)
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
            rev = self.version_class(
                    base=self,
                    revision=self.transaction)
            return rev

    def exists(self):
        # is this right -- what happens if we did not have anything at revision
        # and have just created something as part of the current transaction
        # ...
        return len(self.history) > 0

    def delete(self):
        deleted = State.get_by(name='deleted')
        self.state = deleted
    
    def purge(self):
        select = self.version_class.select_by(base=self)
        for rev in select:
            self.version_class.delete(rev)
        # because we have overriden delete have to play smart
        self.__class__.delete(self)
        # we flush immediately here as a special case ...
        elixir.objectstore.flush()


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
            colobj = getattr(self.type.c, self.key_name)
            query = self.type.query()
            obj = query.selectone_by(colobj==key)
        else:
            obj = self.type.get(key)
        return obj
    
    def delete(self, key):
        self.purge(key)

    def purge(self, key):
        obj = self.get(key)
        self.type.delete(obj)

    def list(self):
        return list(self.type.select())

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
        all_objs_ever = self.type.select()
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


