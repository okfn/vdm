from stateful import *

ACTIVE = 'active'
DELETED = 'deleted'


class Stateful(object):
    def __init__(me, name='', state=ACTIVE):
        me.name = name
        me.state = state
        
    def delete(me):
        me.state = DELETED

    def undelete(me):
        me.state = ACTIVE

    def __repr__(me):
        return '<Stateful %s %s>' % (me.name, me.state)

def delete(st):
    st.delete()

def undelete(st):
    st.undelete()

def is_active(st):
    return st.state == ACTIVE


class TestStatefulList:
    active = ACTIVE
    deleted = DELETED

    def setup_method(self, name=''):
        self.sb = Stateful('b', state=self.deleted)
        self.baselist = [
                Stateful('a'),
                self.sb,
                Stateful('c', state=self.deleted),
                Stateful('d'),
                ]
        self.sa = self.baselist[0]
        self.sc = self.baselist[2]
        self.se = Stateful('e')
        self.sf = Stateful('f')
        self.slist = StatefulList(self.baselist, is_active=is_active)
        # TODO: more testing of StatefulListDeleted
        self.slist_deleted = StatefulListDeleted(self.baselist, is_active=is_active)

    def test__get_base_index(self):
        exp = [0, 3]
        out = [-1, -1]
        for ii in range(2):
            out[ii] = self.slist._get_base_index(ii)
        assert exp == out

    def test___len__(self):
        assert len(self.baselist) == 4
        assert len(self.slist) == 2
        assert len(self.slist_deleted) == 2

    def test___get_item__(self):
        assert self.slist[1] == self.baselist[3]

    def test___get_item___with_negative_index(self):
        assert self.slist[-1] == self.baselist[-1]

    def test_append(self):
        assert len(self.baselist) == 4
        assert len(self.slist) == 2

        # already in the list but deleted 
        self.slist.append(self.sb)
        assert len(self.baselist) == 4
        assert len(self.slist) == 3
        # ensure it has moved to the end ...
        assert self.slist[-1] == self.sb
        assert self.baselist[-1] == self.sb

        # not in the list
        self.slist.append(self.se)
        assert len(self.baselist) == 5
        assert len(self.slist) == 4

        # already in the list but active
        have_exception = False
        try:
            self.slist.append(self.sa)
        except:
            have_exception = True
        assert have_exception, 'Should raise exception on append of active'

        # in list deleted and now add active version
        # (this cannot work work because no concept of same item in active and
        # deleted state ...)
        # self.sc.state = ACTIVE
        # self.slist.append(self.sc)
        # assert len(self.baselist) == 4
        # assert len(self.slist) == 4

    def _test_insert(self):
        # TODO: get this working
        self.slist.insert(0, self.sb)
        assert len(self.baselist) == 4
        assert len(self.slist) == 3
        # TODO:
        pass

    def test_delete(self):
        del self.slist[0]
        assert len(self.baselist) == 4
        assert len(self.slist) == 1
        assert self.baselist[0].state == self.deleted

    def test___setitem__(self):
        # does not work ...
        # self.slist = [1,2,3]
        # want this to become self.slist[:] = [1,2,3]
        self.slist[:] = []
        assert len(self.baselist) == 4
        assert len(self.slist) == 0
        for item in self.baselist:
            assert item.state == self.deleted
    
    def test_count(self):
        assert self.slist.count(self.sb) == 0
        assert self.slist.count(self.sa) == 1
    
    def test_extend(self):
        self.slist.extend([self.se, self.sf])
        assert len(self.slist) == 4
        assert len(self.baselist) == 6

    def test___contains__(self):
        assert self.sa in self.slist
        assert self.sb not in self.slist

    def test_clear(self):
        self.slist.clear()
        assert len(self.slist) == 0


