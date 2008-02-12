import itertools
class StatefulList(object):

    def __init__(self, baselist, is_active, delete, undelete):
        self.baselist = baselist
        self._undelete = undelete 
        self._delete = delete
        self._is_active = is_active

    def _get_base_index(self, myindex):
        # if we knew items were unique could do
        # return self.baselist.index(self[myindex])
        count = -1
        basecount = -1
        for item in self.baselist:
            basecount += 1
            if self._is_active(item):
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
            self.baselist.append(obj)

    def insert(self, index, value):
        # have some choice here so just for go for first place
        baseindex = self._get_base_index(index)
        self.baselist.insert(baseindex+1, value)

    def __getitem__(self, index):
        baseindex = self._get_base_index(index)
        return self.baselist[baseindex]
    
    def __item__(self, index):
        return self.__getitem__(self, index)

    def __delitem__(self, index):
        self[index].delete()

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
        pass
    
    def __repr__(self):
        return repr(self.copy())
    

