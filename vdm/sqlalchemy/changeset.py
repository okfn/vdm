from datetime import datetime
import json

from sqlalchemy import Column, ForeignKey, Table, types
from sqlalchemy.types import *
from sqlalchemy.orm import relationship 
from sqlalchemy.orm.collections import column_mapped_collection

from vdm.changeset import Changeset as _Changeset, ChangeObject as _ChangeObject
from .sqla import SQLAlchemyMixin

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

class JsonTypeTuple(JsonType):
    def process_result_value(self, value, engine):
        if value is None:
            return None
        else:
            out = json.loads(value)
            if isinstance(out, list):
                out = tuple(out)
            return out

    def copy(self):
        return JsonTypeTuple(self.impl.length)


class Changeset(_Changeset, SQLAlchemyMixin):
    @classmethod
    def youngest(self, session):
        '''Get the youngest (most recent) changeset.

        If session is not provided assume there is a contextual session.
        '''
        q = session.query(self)
        return q.first()

class ChangeObject(_ChangeObject, SQLAlchemyMixin):
    pass


def make_tables(metadata):
    changeset_table = Table('changeset', metadata,
            Column('id', String(40), primary_key=True),
            Column('author', Unicode(256)),
            Column('message', UnicodeText),
            Column('timestamp', DateTime, default=datetime.now),
            Column('metadata', JsonType),
            )
    change_object_table = Table('change_object', metadata,
            Column('changeset_id', String(40), ForeignKey('changeset.id'),
                primary_key=True),
            Column('object_id', JsonTypeTuple, primary_key=True),
            Column('operation_type', String(30)),
            Column('data_type', String(30)),
            Column('data', JsonType),
            )

    return (changeset_table, change_object_table)


def setup_changeset(metadata, mapper):
    '''Map Changeset and ChangeObject domain objects to associated tables.

    :return: None.
    '''
    changeset_table, change_object_table = make_tables(metadata)

    mapper(Changeset, changeset_table, properties={
        'manifest': relationship(ChangeObject, backref='changeset')
        },
        order_by=changeset_table.c.timestamp.desc()
        )

    mapper(ChangeObject, change_object_table, properties={
        })

