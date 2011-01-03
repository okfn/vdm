from vdm.changeset import Changeset, ChangesetManifest, ChangeObject
import json

class TestChangeset:
    def test_01(self):
        cs = Changeset()
        assert cs.id == None
        assert cs.parents == [ '0' * 40 ]
        assert cs.author == ''
        assert cs.message == ''
        out = json.dumps(cs.metadata, sort_keys=True) 
        expected = json.dumps({
            'id': None,
            'parents': ['0' * 40],
            'author': '',
            'message': '',
            'timestamp': None
            }, sort_keys=True)
        assert out == expected
        assert cs.manifest != None

    def test_02(self):
        co = ChangeObject()
        objectid = (u'package', 1,2,3)
        co.object_id = objectid
        co.operation = ChangeObject.OperationType.CREATE
        co.data = json.dumps({
            'field1': 'aaaaaa',
            'field2': 'bbbbbb'
            }, sort_keys=True)
        cm = ChangesetManifest()
        cm.add_change(co)
        cs = Changeset()
        cs.manifest = cm
        cs.save()
        assert cs.id == '148c918ee2b4b027eda28601f28a30138927f76f', cs.id

        assert len(cm.changes) == 1
        assert cm.changes[objectid] == co

