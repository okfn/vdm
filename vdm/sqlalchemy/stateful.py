import itertools
class StatefulList(object):

    def __init__(self, baselist, is_active, delete, undelete,
            base_modifier=None):
        '''
        base_modifier: function to operate on base objects before any
        processing. e.g. could have function:
            def get_as_of(x):
                return x.get_as_of(revision)
        '''
        self.baselist = baselist
        self._undelete = undelete 
        self._delete = delete
        self._is_active = is_active
        if base_modifier is None:
            self._base_modifier = lambda x: x
        else:
            self._base_modifier = base_modifier

    def _get_base_index(self, myindex):
        # if we knew items were unique could do
        # return self.baselist.index(self[myindex])
        count = -1
        basecount = -1
        for item in self.baselist:
            basecount += 1
            if self._is_active(self._base_modifier(item)):
                count += 1
            if count == myindex:
                return basecount
        raise IndexError

    def append(self, obj):
        # check if the list already has it
        if obj in self.baselist:
            if self._is_active(obj):
                # assume unique items in list o/w not meaningful
                msg = 'Cannot have multiple association'
                raise Exception(msg)
            else:
                self._undelete(obj)
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
        return self._base_modifier(self.baselist[baseindex])
    
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

            print index.start
            print stop, step
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
        myiter = itertools.ifilter(self._is_active,
                iter(self.baselist))
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
    
class StatefulListProperty(object):
    def __init__(self, target_list, is_active, delete, undelete):
        self.target_list = target_list
        self.is_active = is_active
        self.delete = delete
        self.undelete = undelete
        self.cached_instance_key = '_%s_%s_%s' % (type(self).__name__,
                target_list, id(self))

    def __get__(self, obj, class_):
        try:
            # return cached instance
            return getattr(obj, self.cached_instance_key)
        except AttributeError:
            # probably should do this using lazy_collections a la assoc proxy
            baselist = getattr(obj, self.target_list)
            stateful_list = StatefulList(baselist, self.is_active, self.delete,
                    self.undelete)
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
