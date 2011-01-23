from vdm import json
import hashlib

class Changeset(object):
    '''Models a list of changes.'''
    NULL_HASH = '0' * 40
    INIT_METADATA = {
        'id': None,
        # no parents = a single null hash
        'parents': [NULL_HASH],
        'author': '',
        'message': '',
        'timestamp': None
        }
   
    def __init__(self):
        self.id = None
        self.parents = [self.NULL_HASH]
        self.author = None
        self.message = None
        self.timestamp = None
        self.metadata = {}
        self.manifest = []

    def save(self):
        self.compute_id()

    def compute_id(self):
        value_to_hash = ''.join(self.parents) + self.compute_manifest_hash()
        self.id = hashlib.sha1(value_to_hash).hexdigest()

    def compute_manifest_hash(self):
        change_object_hashes = [ change_object.hash
            for change_object
            in self.manifest ]
        out = ''.join(change_object_hashes)
        return hashlib.sha1(out).hexdigest()


class ChangeObject(object):
    class DataType(object):
        FULL = 'full'
        DIFF = 'diff'
    class OperationType:
        CREATE = 'create'
        UPDATE = 'update'
        DELETE = 'delete'

    def __init__(self):
        self.data_type = self.DataType.FULL
        self.operation_type = self.OperationType.CREATE
        self.data = None
        self.object_id = None

    @property
    def hash(self):
        data_to_hash = self.operation_type
        data_to_hash += '::' + json.dumps(self.object_id, sort_keys=True)
        data_to_hash += '::' + json.dumps(self.data, sort_keys=True)
        return hashlib.sha1(data_to_hash).hexdigest()
