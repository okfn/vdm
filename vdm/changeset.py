import hashlib

class Changeset(object):
    '''Models a list of changes.'''
    INIT_METADATA = {
        'id': None,
        # no parents = a single null hash
        'parents': ['0' * 40],
        'author': '',
        'message': '',
        }
   
    def __init__(self):
        self.metadata = dict(self.INIT_METADATA)
        self.manifest = ChangesetManifest()

    @property
    def id(self):
        return self.metadata['id']

    @property
    def parents(self):
        return self.metadata['parents']

    @parents.setter
    def parents(self, value):
        self.metadata['parents'] = list(value)

    @property
    def author(self):
        return self.metadata['author']

    @author.setter
    def author(self, value):
        self.metadata['author'] = value

    @property
    def message(self):
        return self.metadata['message']

    @message.setter
    def message(self, value):
        self.metadata['message'] = value

    def save(self):
        self.compute_id()

    def compute_id(self):
        value_to_hash = ''.join(self.parents) + self.manifest.hash
        self.metadata['id'] = hashlib.sha1(value_to_hash).hexdigest()


class ChangesetManifest(object):
    def __init__(self):
        self.changes = {}

    def add_change(self, change_object):
        self.changes[change_object.object_id] = change_object

    @property
    def hash(self):
        change_object_hashes = [ self.changes[change_object_id].hash
            for change_object_id
            in sorted(self.changes.keys()) ]
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

    @property
    def hash(self):
        data_to_hash = self.operation_type + self.data
        return hashlib.sha1(data_to_hash).hexdigest()

