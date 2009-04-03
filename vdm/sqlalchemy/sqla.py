'''Generic sqlalchemy code (not specifically related to vdm).
'''
import sqlalchemy

class SQLAlchemyMixin(object):
    def __str__(self):
        repr = u'<%s' % self.__class__.__name__
        table = sqlalchemy.orm.class_mapper(self.__class__).mapped_table
        for col in table.c:
            repr += u' %s=%s' % (col.name, getattr(self, col.name))
        repr += '>'
        return repr

    def __repr__(self):
        return self.__str__()

