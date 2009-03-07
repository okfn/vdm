'''Support for stateful lists.

TODO: create some proper tests for base_modifier stuff.
TODO: move stateful material from base.py here?
'''
import logging
logger = logging.getLogger('vdm')

import itertools


class StatefulList(object):
    '''A list which is 'state' aware and only shows objects which are in
    'active' state.

    What behaviour do we expect when adding an object already in the list to
    the list? Either:

    1. Ensure only one active object in the list at a time. So:
        * if object is already active raise Exception
        * If added object is deleted then undelete and move to end
    2. Allow multiple objects in list. So:
        * If active just append it
        * if deleted undelete and then append
       NB: this may have surprising results since when undeleting the deleted
       object do not just undelete it but all the other copies in the list.

    Here we implement option 1.
    '''

    def __init__(self, target_list, **kwargs):
        '''
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
        '''
        self.baselist = target_list 

        extra_args = ['is_active', 'delete', 'undelete', 'base_modifier']
        for argname in extra_args:
            setattr(self, argname, kwargs.get(argname, None))
        if self.is_active is None:
            # object may not exist (e.g. with get_as_of0 in which case it will
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
        self._is_active = self.is_active
        self._delete = self.delete
        self._undelete = self.undelete

    def _get_base_index(self, idx):
        # if we knew items were unique could do
        # return self.baselist.index(self[myindex])
        count = -1
        basecount = -1
        if idx < 0:
            myindex = -(idx) - 1
            tbaselist = reversed(self.baselist)
        else:
            myindex = idx
            tbaselist = self.baselist
        for item in tbaselist:
            basecount += 1
            if self._is_active(self.base_modifier(item)):
                count += 1
            if count == myindex:
                if idx < 0:
                    return -(basecount + 1)
                else:
                    return basecount
        raise IndexError

    def append(self, obj):
        # TODO: use base_modifier
        # TODO: not clear what happens if we have 'same' object in different
        # states i.e. i re-add the same object but with a different state then
        # ends up with two different object in the system which is maybe not
        # what we want ... (this needs some careful checking)
        if obj in self.baselist:
            if self._is_active(obj):
                # assume unique items in list o/w not meaningful
                msg = 'Multiple items with same state in list not supported'
                raise Exception(msg)
            else:
                self._undelete(obj)
                del self.baselist[self.baselist.index(obj)]
                self.baselist.append(obj)
        else:
            # ensure it is in correct state
            self._undelete(obj)
            self.baselist.append(obj)

    def insert(self, index, value):
        # have some choice here so just for go for first place
        baseindex = self._get_base_index(index)
        self.baselist.insert(baseindex+1, value)

    def __getitem__(self, index):
        baseindex = self._get_base_index(index)
        return self.base_modifier(self.baselist[baseindex])
    
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
            baseindex = self._get_base_index(index)
            self.baselist[baseindex] = value
        else:
            if index.stop is None:
                stop = len(self)
            elif index.stop < 0:
                stop = len(self) + index.stop
            else:
                stop = index.stop
            step = index.step or 1

            rng = range(index.start or 0, stop, step)
            if step == 1:
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
        # TODO: maybe base_modifier should be folded into the operators ...
        mytest = lambda x: self._is_active(self.base_modifier(x))
        myiter = itertools.ifilter(mytest, iter(self.baselist))
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
    
    def __repr__(self):
        return repr(self.copy())


class StatefulListDeleted(StatefulList):

    def _set_stateful_operators(self):
        self._is_active = lambda x: not self.is_active(x)
        self._delete = self.undelete
        self._undelete = self.delete

    
class StatefulListProperty(object):
    def __init__(self, target_list_name, stateful_class=StatefulList, **kwargs):
        '''Turn StatefulList into a property to allowed for deferred access.

        For details of other args see L{StatefulList}.
        '''
        self.target_list_name = target_list_name
        self.stateful_class = stateful_class
        self.cached_kwargs = kwargs
        self.cached_instance_key = '_%s_%s_%s' % (type(self).__name__,
                self.target_list_name, id(self))

    def __get__(self, obj, class_):
        try:
            # return cached instance
            return getattr(obj, self.cached_instance_key)
        except AttributeError:
            # probably should do this using lazy_collections a la assoc proxy
            target_list = getattr(obj, self.target_list_name)
            stateful_list = self.stateful_class(target_list, **self.cached_kwargs)
            # cache
            setattr(obj, self.cached_instance_key, stateful_list)
            return stateful_list

    def __set__(self, obj, values):
        # TODO: assign to whole underlying mapper
        raise NotImplementedException()


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

        licenses_active # these are active PackageLicenses
        licenses_deleted # these are deleted PackageLicenses
        licenses # these are active *Licenses*

    @arg attr: the name of the attribute on the Join object corresponding to
        the target (e.g. in this case 'license' on PackageLicense).
    @arg **kwargs: these are passed on to the StatefulListProperty.
    '''
    active_name = m2m_property_name + '_active'
    active_prop = StatefulListProperty(basic_m2m_name, **kwargs)
    deleted_name = m2m_property_name + '_deleted'
    deleted_prop = StatefulListProperty(basic_m2m_name, StatefulListDeleted,
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
    # TODO: 2009-02-17 as yet no *positive* test of this functionality
    # TODO: is it even needed?
    def has_existing(mykwargs):
        # first try to retrieve on basis of mykwargs
        q = m2m_object.query
        for k,v in mykwargs.items():
            # HACK: because these are related attributes cannot use simple
            # queries but need to use *_id attributes
            # This requires us to assume these are in standard form ...
            # Even more complicated: if no flush yet then won't be any ids
            # (though in that case certain this is a new appending)
            if getattr(v, 'id') is None:
                return None # foreign object is not yet even created yet
            # TODO: deal with this properly
            kw = k + '_id'
            tmpkwargs = {kw:v.id}
            q = q.filter_by(**tmpkwargs)
        existing = q.first()
        return existing

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
