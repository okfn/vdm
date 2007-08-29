import sqlalchemy
import vdm.elixir.complex as cx
from elixir import *
uri = 'sqlite:///:memory:'
metadata.connect(uri)
create_all()

class Test1(object):
    
    def test_1(self):
        rev1 = cx.Revision()
        print rev1.session
        session = sqlalchemy.object_session(rev1)
        assert session.revision == rev1

    def test_2(self):
        rev1 = cx.Revision()
        session = sqlalchemy.object_session(rev1)
        assert session.revision == rev1
        rev1.commit()
        assert session.revision == None

