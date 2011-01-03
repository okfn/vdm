from datetime import datetime
import json

from sqlalchemy import Column, ForeignKey, Table, types
from sqlalchemy.types import *
from sqlalchemy.orm import relationship 
from sqlalchemy.orm.collections import column_mapped_collection

from vdm.changeset import Changeset as _Changeset, ChangeObject as _ChangeObject

class JsonType(types.TypeDecorator):
    '''Store data as JSON serializing on save and unserializing on use.
    '''
    impl = types.UnicodeText

    def process_bind_param(self, value, engine):
        if value is None: # ensure we stores nulls in db not json "null"
            return None
        else:
            # ensure_ascii=False => allow unicode but still need to convert
            return unicode(json.dumps(value, ensure_ascii=False, sort_keys=True))

    def process_result_value(self, value, engine):
        if value is None:
            return None
        else:
            return json.loads(value)

    def copy(self):
        return JsonType(self.impl.length)


class Changeset(_Changeset):
    pass

class ChangeObject(_ChangeObject):
    pass

def make_tables(metadata):
    changeset_table = Table('changeset', metadata,
            Column('id', String(40), primary_key=True),
            Column('author', Unicode(256)),
            Column('message', UnicodeText),
            Column('timestamp', DateTime, default=datetime.now),
            Column('metadata', JsonType),
            )
    change_object_table = Table('changeset_object', metadata,
            Column('changeset_id', String(40), ForeignKey('changeset.id'),
                primary_key=True),
            Column('object_id', UnicodeText, primary_key=True),
            Column('operation_type', String(30), primary_key=True),
            Column('data_type', String(30), primary_key=True),
            Column('data', UnicodeText, primary_key=True),
            )

    return (changeset_table, change_object_table)

def setup_changeset(metadata):
    changeset_table, change_object_table = make_tables(metadata)
    from sqlalchemy.orm import mapper
    mapper(Changeset, changeset_table, properties={
        'manifest': relationship(ChangeObject, backref='changeset',
            collection_class=column_mapped_collection(change_object_table.c.object_id))
        })
    mapper(ChangeObject, change_object_table, properties={
        })

