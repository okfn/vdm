import json
from sqlalchemy import *
from sqlalchemy.orm import scoped_session, sessionmaker, create_session, mapper

from vdm.sqlalchemy.changeset import *
Session = scoped_session(
    sessionmaker(autoflush=True, expire_on_commit=False, autocommit=False)
    )

class TestChangeset:
    @classmethod
    def setup_class(self):
        engine = create_engine('sqlite://')
        metadata = MetaData(bind=engine)
        setup_changeset(metadata, mapper)
        metadata.create_all()

    def test_01(self):
        cs = Changeset()
        assert cs.id == None
        assert cs.parents == [ '0' * 40 ]
        assert cs.author == None, '%s' % cs.author
        assert cs.message == None
        assert cs.metadata == {}
        assert cs.manifest == {}
        cs.save()
        assert cs.id == '9feb6d00f5bd21b036e7a3d2f8e01ac6dd507fb6'

        Session.add(cs)
        Session.commit()
        Session.remove()
        cs = Session.query(Changeset).one()
        assert cs.timestamp
        assert cs.id == '9feb6d00f5bd21b036e7a3d2f8e01ac6dd507fb6'

    def test_02(self):
        co = ChangeObject()
        objectid = json.dumps((u'package', 1,2,3))
        co.object_id = objectid
        co.operation = ChangeObject.OperationType.CREATE
        co.data = json.dumps({
            'field1': 'aaaaaa',
            'field2': 'bbbbbb'
            }, sort_keys=True)
        cs = Changeset()
        cs.manifest[co.object_id] = co
        cs.save()
        
        cs_id = '148c918ee2b4b027eda28601f28a30138927f76f'
        assert cs.id == cs_id
        assert len(cs.manifest) == 1
        assert cs.manifest[objectid] == co
        
        Session.add_all([cs, co])
        Session.commit()
        Session.remove()
        cs = Session.query(Changeset).get(cs_id)
        assert cs.timestamp
        assert len(cs.manifest) == 1

