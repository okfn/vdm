from stateful import StatefulList

class TestStatefulList:

    def setup_method(self, name=''):
        self.active = 'active'
        self.deleted = 'deleted'

        class Stateful(object):
            def __init__(me, name='', state=self.active):
                me.name = name
                me.state = state
                
            def delete(me):
                me.state = self.deleted

            def undelete(me):
                me.state = self.active

            def __repr__(me):
                return '<Stateful %s %s>' % (me.name, me.state)

        def delete(st):
            st.delete()

        def undelete(st):
            st.undelete()

        def is_active(st):
            return st.state == self.active

        self.sb = Stateful('b', state=self.deleted)
        self.testlist = [
                Stateful('a'),
                self.sb,
                Stateful('c', state=self.deleted),
                Stateful('d'),
                ]
        self.sa = self.testlist[0]
        self.se = Stateful('e')
        self.sf = Stateful('f')
        self.slist = StatefulList(self.testlist, is_active, delete, undelete)

    def test__get_base_index(self):
        exp = [0, 3]
        out = [-1, -1]
        for ii in range(2):
            out[ii] = self.slist._get_base_index(ii)
        assert exp == out

    def test___len__(self):
        assert len(self.testlist) == 4
        assert len(self.slist) == 2

    def test___get_item__(self):
        assert self.slist[1] == self.testlist[3]

    def test_append(self):
        self.slist.append(self.sb)
        assert len(self.testlist) == 4
        assert len(self.slist) == 3
        self.slist.append(self.se)
        assert len(self.testlist) == 5
        assert len(self.slist) == 4

    def test_delete(self):
        del self.slist[0]
        assert len(self.testlist) == 4
        assert len(self.slist) == 1
        assert self.testlist[0].state == self.deleted

    def test___setitem__(self):
        # does not work ...
        # self.slist = [1,2,3]
        # want this to become self.slist[:] = [1,2,3]
        self.slist[:] = []
        assert len(self.testlist) == 4
        assert len(self.slist) == 0
        for item in self.testlist:
            assert item.state == self.deleted
    
    def test_count(self):
        assert self.slist.count(self.sb) == 0
        assert self.slist.count(self.sa) == 1
    
    def test_extend(self):
        self.slist.extend([self.se, self.sf])
        assert len(self.slist) == 4
        assert len(self.testlist) == 6

    def test___contains__(self):
        assert self.sa in self.slist
        assert self.sb not in self.slist

    def test_clear(self):
        self.slist.clear()
        assert len(self.slist) == 0


