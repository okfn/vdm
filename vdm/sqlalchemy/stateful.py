'''Support for stateful collections.

Stateful collections are essential to the functioning of VDM's m2m support.
m2m relationships become stateful when versioned and the associated collection must
become state-aware.

There are several subtleties in doing this, the most significant of which is
how one copes with adding an "existing" object to a stateful list which already
contains that object in deleted form (or, similarly, when moving an item within
a list which normally corresponds to a delete and an insert).


Stateful Lists and "Existing" Objects Problem
=============================================

The problem here is that the "existing" object and the object being added are
not literally the same object in the python sense. Why? First, because their
state may differ and the ORM is not aware that state is irrelevant to identity.
Second, and more significantly because the ORM often does not fully "create"
the object until a flush which is too late - we already have duplicates in the
list. Here's a concrete example::

    # Package, Tag, PackageTag objects with Package.package_tags_active being
    # StatefulList and Package.tags a proxy to this showing the tags

    pkg.tags = [ tag1 ]
    # pkg.package_tags now contains 2 items
    # PackageTag(pkg=

    pkg1 = Package('abc')
    tag1 = Tag(name='x')
    pkg1.tags.append(tag1)
    # pkg1.package_tags contains one PackageTag

    # delete tag1
    del pkg.tags[0]
    # so PackageTag(pkg=pkg1, tag=tag1) is now in deleted state
    pkg.tags.append(tag1)
    # now pkg.package_tags has length 2!
    # Why? Really we want to undelete PackageTag(pkg=pkg1, tag=tag1)
    # however for association proxy what happens is that
    # we get a new PackageTag(pkg=None, tag=tag1) created and this is not
    # identified with existing PackageTag(pkg=pkg1, tag=tag1) because pkg=None
    # on new PackageTag (pkg only set on flush)
    # Thus a new item is appended rather than existing being undeleted

    # even more seriously suppose pkg.tags is [tag1]
    # what happens if we do
    pkg.tags = [tag1]
    # does *not* result in nothing happen
    # instead existing PackageTag(pkg=pkg1, tag=tag1) is put in deleted state and
    # new PackageTag(pkg=None, tag=tag1) is appended with this being changed to
    # PackageTag(pkg=pkg1, tag=tag1) on commit (remember sqlalchemy does not
    # resolve m2m objects foreign key for owner object until flush time)

How do we solve this? The only real answer is implement an identify map in the
stateful list.

TODO: create some proper tests for base_modifier stuff.
TODO: move stateful material from base.py here?
'''
import logging
logger = logging.getLogger('vdm.stateful')

import itertools


class StatefulProxy(object):
    '''A proxy to an underlying collection which contains stateful objects.

    The proxy only shows objects in a particular state (e.g. active ones) and
    will also transform standard collection operations to make them 'stateful'
    -- for example deleting from the list will not delete the object but simply
    place it in a deleted state.
    '''
    def __init__(self, target, **kwargs):
        '''
        @param target: the target (underlying) collection (list, dict, etc)

        Possible kwargs:
        
        is_active, delete, undelete: a method performing the relevant operation
            on the underlying stateful objects. If these are not provided they
            will be created on the basis that there is a corresponding method
            on the stateful object (e.g. one can do obj.is_active()
            obj.delete() etc.

        base_modifier: function to operate on base objects before any
            processing. e.g. could have function:

            def get_as_of(x):
                return x.get_as_of(revision)

            WARNING: if base_modifier is not trivial (i.e. does not equal the
            identify function: lambda x: x) then only read operations should be
            performed on this proxy (this is because you will be operating on
            modified rather than original objects).

            WARNING: when using base_modifier the objects returned from this list will
            not be list objects themselves but base_modifier(object).
            In particular, this means that when base_modifier is turned on
            operations that change the list (e.g. deletions) will operate on
            modified objects not the base objects!!
        '''
        self.target = target

        extra_args = ['is_active', 'delete', 'undelete', 'base_modifier']
        for argname in extra_args:
            setattr(self, argname, kwargs.get(argname, None))
        if self.is_active is None:
            # object may not exist (e.g. with get_as_of in which case it will
            # be None
            self.is_active = lambda x: not(x is None) and x.is_active()
        if self.delete is None:
            self.delete = lambda x: x.delete()
        if self.undelete is None:
            self.undelete = lambda x: x.undelete()
        if self.base_modifier is None:
            self.base_modifier = lambda x: x
        self._set_stateful_operators()

    def _set_stateful_operators(self):
        self._is_active = lambda x: self.is_active(self.base_modifier(x))
        self._delete = self.delete
        self._undelete = self.undelete


class StatefulList(StatefulProxy):
    '''A list which is 'state' aware.
    
    Discussion
    ==========

    What behaviour do we expect when adding an object already in the list to
    the list? Note that when we say an object already in the list we mean
    identical as determined by python 'in' function. This means, for example
    that 2 objects which have different state attributes will not (usually) be
    considered the same.

    1. Ensure only one active object in the list at a time. So:
        * if object is already active raise Exception
        * If added object is deleted then undelete and move to end
    2. Allow multiple objects in list. So:
        * If active just append it
        * if deleted undelete and then append
       NB: this may have surprising results since when undeleting the deleted
       object do not just undelete it but all the other copies in the list.

    Here we implement option 1.

    # TODO: not clear what happens if we have 'same' object in different
    # states i.e. i re-add the same object but with a different state then
    # ends up with two different object in the system which is maybe not
    # what we want ... (this needs some careful checking)

    # TODO: should we have self.base_modifier(obj) more frequently used? (e.g.
    # in __iter__, append, etc
    '''
    def __init__(self, target, **kwargs):
        '''Same as for StatefulProxy but with additional kwarg:
        identify: a function which takes an object and return a key
        identifying that object for use in an internal identity map. (See
        discussion in main docstring for why this is required).

        self.identity_map = {
            'key': [ list of objects with that key ]
        }
        # simplest thing 

        separate question as to uniqueness in our lists ...
        '''
        super(StatefulList, self).__init__(target, **kwargs)
        identifier = kwargs.get('identifier', lambda x: x)
        self._identifier = identifier
        self._identity_map = {}
        for obj in self.target:
            self._add_to_identity_map(obj)

    def _get_base_index(self, idx):
        # if we knew items were unique could do
        # return self.target.index(self[myindex])
        count = -1
        basecount = -1
        if idx < 0:
            myindex = -(idx) - 1
            tbaselist = reversed(self.target)
        else:
            myindex = idx
            tbaselist = self.target
        for item in tbaselist:
            basecount += 1
            if self._is_active(item):
                count += 1
            if count == myindex:
                if idx < 0:
                    return -(basecount + 1)
                else:
                    return basecount
        raise IndexError

    def _add_to_identity_map(self, obj):
        objkey = self._identifier(obj)
        current = self._identity_map.get(objkey, [])
        current.append(obj)
        self._identity_map[objkey] = current

    def _check_for_existing_on_add(self, obj):
        objkey = self._identifier(obj)
        def _existing_deleted_obj(objkey):
            for existing_obj in self._identity_map.get(objkey, []):
                if not self._is_active(existing_obj):
                    return existing_obj
        out_obj = _existing_deleted_obj(objkey)
        if out_obj is None:
            out_obj = obj 
            self._identity_map[objkey] = self._identity_map.get(objkey,
                    []).append(out_obj)
        else: # remove that existing item from target list as about to re-add
            idx = self.target.index(out_obj)
            del self.target[idx]
        self._undelete(out_obj)
        return out_obj

    def append(self, in_obj):
        obj = self._check_for_existing_on_add(in_obj)
        self.target.append(obj)

    def insert(self, index, value):
        # have some choice here so just for go for first place
        our_obj = self._check_for_existing_on_add(value)
        try:
            baseindex = self._get_base_index(index)
        except IndexError: # may be list is empty ...
            baseindex = len(self)
        self.target.insert(baseindex, our_obj)

    def __getitem__(self, index):
        baseindex = self._get_base_index(index)
        return self.base_modifier(self.target[baseindex])
    
    def __item__(self, index):
        return self.__getitem__(self, index)
    
    def __delitem__(self, index):
        if not isinstance(index, slice):
            self._delete(self[index])
        else:
            start = index.start
            end = index.stop
            rng = range(start, end)
            for ii in rng:
                del self[start]

    def __setitem__(self, index, value):
        if not isinstance(index, slice):
            del self[index]
            self.insert(index, value)
        else:
            if index.stop is None:
                stop = len(self)
            elif index.stop < 0:
                stop = len(self) + index.stop
            # avoid weird MemoryError when doing OurList[:] = ...
            elif index.stop > len(self):
                stop = len(self)
            else:
                stop = index.stop
            step = index.step or 1

            rng = range(index.start or 0, stop, step)
            if step == 1:
                # delete first then insert to avoid problems with indices and
                # statefulness
                for ii in rng:
                    start = rng[0]
                    del self[start]
                ii = index.start
                for item in value:
                    self.insert(ii, item)
                    ii += 1
            else:
                if len(value) != len(rng):
                    raise ValueError(
                                'attempt to assign sequence of size %s to '
                                'extended slice of size %s' % (len(value),
                                                               len(rng)))
                    for ii, item in zip(rng, value):
                        self[ii] = item

    # def __setslice__(self, start, end, values):
    #    for ii in range(start, end):
    #        self[ii] = values[ii-start]

    def __iter__(self):
        mytest = lambda x: self._is_active(x)
        myiter = itertools.ifilter(mytest, iter(self.target))
        return myiter
    
    def __len__(self):
        return sum([1 for _ in self])

    def count(self, item):
        myiter = itertools.ifilter(lambda v: v == item, iter(self))
        counter = [1 for _ in myiter]
        return sum(counter)

    def extend(self, values):
        for val in values:
            self.append(val)

    def copy(self):
        return list(self)

    def clear(self):
        del self[0:len(self)]
    
    def pop(self, index=None):
        raise NotImplementedError

    def reverse(self):
        raise NotImplementedError
    
    def __repr__(self):
        return repr(self.target)


class StatefulListDeleted(StatefulList):

    def _set_stateful_operators(self):
        self._is_active = lambda x: not self.is_active(self.base_modifier(x))
        self._delete = self.undelete
        self._undelete = self.delete

    
class StatefulDict(StatefulProxy):
    '''A stateful dictionary which only shows object in underlying dictionary
    which are in active state.
    '''

    # sqlalchemy assoc proxy fails to guess this is a dictionary w/o prompting
    # (util.duck_type_collection appears to identify dict by looking for a set
    # method but dicts don't have this method!)
    __emulates__ = dict

    def __contains__(self, k):
        return k in self.target and self._is_active(self.target[k])

    def __delitem__(self, k):
        # will raise KeyError if not there (which is what we want)
        val = self.target[k]
        if self._is_active(val):
            self._delete(val)
        else:
            raise KeyError(k)
        # should we raise KeyError if already deleted?

    def __getitem__(self, k):
        out = self.target[k]
        if self._is_active(out):
            return self.base_modifier(out)
        else:
            raise KeyError(k)

    def __iter__(self):
        myiter = itertools.ifilter(lambda x: self._is_active(self.target[x]),
                iter(self.target))
        return myiter

    def __setitem__(self, k, v):
        self.target[k] = v

    def __len__(self):
        return sum([1 for _ in self])

    def clear(self): 
        for k in self:
            del self[k]

    def copy(self):
        # return self.__class__(self.target, base_modifier=self.base_modifier)
        return dict(self)

    def get(self, k, d=None):
        if k in self:
            return self[k]
        else:
            return d

    def has_key(self, k):
        return k in self
    
    def items(self):
        return [ x for x in self.iteritems() ]

    def iteritems(self):
        for k in self:
            yield k,self[k]

    def keys(self):
        return [ k for k in self ]

    def __repr__(self):
        return repr(self.target)



class DeferredProperty(object):
    def __init__(self, target_collection_name, stateful_class=StatefulList, **kwargs):
        '''Turn StatefulList into a property to allowed for deferred access
        (important as collections to which they are proxying may also be
        deferred).

        For details of other args see L{StatefulList}.
        '''
        self.target_collection_name = target_collection_name
        self.stateful_class = stateful_class
        self.cached_kwargs = kwargs
        self.cached_instance_key = '_%s_%s_%s' % (type(self).__name__,
                self.target_collection_name, id(self))

    def __get__(self, obj, class_):
        try:
            # return cached instance
            return getattr(obj, self.cached_instance_key)
        except AttributeError:
            # probably should do this using lazy_collections a la assoc proxy
            target_collection = getattr(obj, self.target_collection_name)
            stateful_list = self.stateful_class(target_collection, **self.cached_kwargs)
            # cache
            setattr(obj, self.cached_instance_key, stateful_list)
            return stateful_list

    def __set__(self, obj, values):
        raise NotImplementedError()


import sqlalchemy.ext.associationproxy
import weakref
# write our own assoc proxy which excludes scalar support and therefore calls
# which will not work since underlying list is a StatefuList not a normal
# collection 
class OurAssociationProxy(sqlalchemy.ext.associationproxy.AssociationProxy):

    def __get__(self, obj, class_):
        if obj is None:
            self.owning_class = class_
            return
        try:
            return getattr(obj, self.key)
        except AttributeError:
            proxy = self._new(self._lazy_collection(weakref.ref(obj)))
            setattr(obj, self.key, proxy)
            return proxy
    
    def __set__(self, obj, values):
        proxy = self.__get__(obj, None)
        if proxy is not values:
            proxy.clear()
            self._set(proxy, values)


# TODO: 2009-07-24 support dict collections
def add_stateful_m2m(object_to_alter, m2m_object, m2m_property_name,
        attr, basic_m2m_name, **kwargs):
    '''Attach active and deleted stateful lists along with the association
    proxy based on the active list to original object (object_to_alter).

    To illustrate if one has::

        class Package(object):

            # package_licenses is the basic_m2m_name attribute
            # 
            # it should come from a simple relation pointing to PackageLicense
            # and returns PackageLicense objects (so do *not* use secondary
            # keyword)
            #
            # It will usually not be defined here but in the Package mapper:
            #
            # 'package_licenses':relation(License) ...
            
            package_licenses = ... from_mapper ...

    Then after running::

        add_stateful_m2m(Package, PackageLicense, 'licenses', 'license',
        'package_licenses')
    
    there will be additional properties:

        # NB: licenses_active and licenses_deleted are lists of PackageLicense
        # objects while licenses (being an assoc proxy) is a list of Licenses
        licenses_active # these are active PackageLicenses
        licenses_deleted # these are deleted PackageLicenses
        licenses # these are active *Licenses*

    @arg attr: the name of the attribute on the Join object corresponding to
        the target (e.g. in this case 'license' on PackageLicense).
    @arg **kwargs: these are passed on to the DeferredProperty.
    '''
    active_name = m2m_property_name + '_active'
    active_prop = DeferredProperty(basic_m2m_name, **kwargs)
    deleted_name = m2m_property_name + '_deleted'
    deleted_prop = DeferredProperty(basic_m2m_name, StatefulListDeleted,
            **kwargs)
    setattr(object_to_alter, active_name, active_prop)
    setattr(object_to_alter, deleted_name, deleted_prop)
    create_m2m = make_m2m_creator_for_assocproxy(m2m_object, attr)
    setattr(object_to_alter, m2m_property_name,
            OurAssociationProxy(active_name, attr, creator=create_m2m)
            )


def make_m2m_creator_for_assocproxy(m2m_object, attrname):
    '''This creates a_creator function for SQLAlchemy associationproxy pattern.

    Similar to standard one but with a few tweaks. In particular we have to be
    a little careful because we don't want to create a new object if we have an
    existing object but which just happens to be in a different state. Thus, we
    first look up to see if there is an existing object based on info we have.

    TODO: is this really an issue or does sqlalchemy take care of this anyway?

    TODO: this problem should go away once we support complex primary keys
    since then we can have a multi-col primary key on m2m table (usually pks of
    2 related tables) and excluding state
    
    @param m2m_object: the m2m object underlying association proxy.
    @param attrname: the attrname to use for the default object passed in to m2m
    '''
    def create_m2m(foreign, **kw):
        mykwargs = dict(kw)
        mykwargs[attrname] = foreign
        # existing = has_existing(mykwargs)
        existing = None
        if existing:
            return existing
        else:
            return m2m_object(**mykwargs)

    return create_m2m
