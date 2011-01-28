'''Generic sqlalchemy code (not specifically related to vdm).
'''
import uuid
import sqlalchemy

make_uuid = lambda: unicode(uuid.uuid4())

class SQLAlchemyMixin(object):
    def __init__(self, **kw):
        for k, v in kw.iteritems():
            setattr(self, k, v)

    def __str__(self):
        return self.__unicode__().encode('utf8')

    def __unicode__(self):
        repr = u'<%s' % self.__class__.__name__
        table = sqlalchemy.orm.class_mapper(self.__class__).mapped_table
        for col in table.c:
            repr += u' %s=%s' % (col.name, getattr(self, col.name))
        repr += '>'
        return repr

    def __repr__(self):
        return self.__str__()


class SQLAlchemySession(object):
    '''Handle setting/getting attributes on the SQLAlchemy session.
    
    TODO: update all methods so they can take an object as well as session
    object.
    '''

    @classmethod
    def setattr(self, session, attr, value):
        setattr(session, attr, value)
        # check if we are being given the Session class (threadlocal case)
        # if so set on both class and instance
        # this is important because sqlalchemy's object_session (used below) seems
        # to return a Session() not Session
        if isinstance(session, sqlalchemy.orm.scoping.ScopedSession):
            sess = session()
            setattr(sess, attr, value)

    @classmethod
    def getattr(self, session, attr):
        return getattr(session, attr)

    # make explicit to avoid errors from typos (no attribute defns in python!)
    @classmethod
    def set_revision(self, session, revision):
        self.setattr(session, 'HEAD', True)
        self.setattr(session, 'revision', revision)
        if revision.id is None:
            # make uuid here so that if other objects in this session are flushed
            # at the same time they know thier revision id
            revision.id = make_uuid()
            # there was a begin_nested here but that just caused flush anyway.
            session.add(revision)
            session.flush()

    @classmethod
    def get_revision(self, session):
        '''Get revision on current Session/session.
        
        NB: will return None if not set
        '''
        return getattr(session, 'revision', None)

    @classmethod
    def set_not_at_HEAD(self, session):
        self.setattr(session, 'HEAD', False)

    @classmethod
    def at_HEAD(self, session):
        return getattr(session, 'HEAD', True)

