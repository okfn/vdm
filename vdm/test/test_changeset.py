from vdm.changeset import Changeset, ChangeObject
import json

class TestChangeset:
    def test_01(self):
        cs = Changeset()
        assert cs.id == None
        assert cs.parents == [ '0' * 40 ]
        assert cs.author == None
        assert cs.message == None
        assert cs.metadata == {}
        assert cs.manifest == {}

    def test_02(self):
        co = ChangeObject()
        objectid = (u'package', 1,2,3)
        co.object_id = objectid
        co.operation = ChangeObject.OperationType.CREATE
        co.data = json.dumps({
            'field1': 'aaaaaa',
            'field2': 'bbbbbb'
            }, sort_keys=True)
        cs = Changeset()
        cs.manifest[co.object_id] = co
        cs.save()

        assert cs.id == '148c918ee2b4b027eda28601f28a30138927f76f', cs.id
        assert len(cs.manifest) == 1
        assert cs.manifest[objectid] == co

