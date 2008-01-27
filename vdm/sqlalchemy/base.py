# make explicit to avoid errors from typos (no attribute defns in python!)
def set_revision(session, revision):
    session.revision = revision

def get_revision(session):
    return session.revision

## -----------------------------
## Helpers

from sqlalchemy.orm import MapperExtension
from sqlalchemy.orm import object_session
from sqlalchemy.orm import EXT_CONTINUE

class Revisioner(MapperExtension):
    # TODO: support ignored fields and check we really have changed ..

    def __init__(self, revision_table):
        self.revision_table = revision_table

    def set_revision(self, instance):
        sess = object_session(instance)
        current_rev = sess.revision
        # was using revision_id but this led to weird intermittent erros
        # (1/3: fail on first item, 1/3 on second, 1/3 ok).
        # assert current_rev.id
        # instance.revision_id = current_rev.id
        # LATER: this resulted (I think) from setting revision_id but not
        # setting revision on the object

        # In fact must do *both* Why?
        # SQLAlchemy mapper extension methods can only make changes to columns.
        # Any changes make to relations will not be picked up (from docs):
        # "Column-based attributes can be modified within this method which will
        # result in their being updated. However no changes to the overall
        # flush plan can be made; this means any collection modification or
        # save() operations which occur within this method will not take effect
        # until the next flush call."
        #
        # Thus: set revision_id to ensure that value is saved
        # set revision to ensure object behaves how it should (e.g. we use
        # instance.revision in after_update)
        assert current_rev
        assert current_rev.id
        instance.revision_id = current_rev.id
        instance.revision = current_rev
        # also set this so that we flush

    def make_revision(self, instance):
        # NO GOOD working with the object as that only gets committed at next
        # flush. Need to work with the table directly (could this be dangerous)
        print 'In make revision'
        colvalues = {}
        for key in instance.c.keys():
            val = getattr(instance, key)
            colvalues[key] = val
        # because it is unlikely instance has been refreshed at this point the
        # fk revision_id is not yet set on this object so get it directly
        assert instance.revision.id
        colvalues['revision_id'] = instance.revision.id
        print 'rev table is:', self.revision_table
        print 'rev id:', colvalues['revision_id']
        self.revision_table.insert().execute(colvalues)
        # set to None to avoid accidental reuse
        # ERROR: cannot do this as after is called per object and may be
        # before_update on other objects ...
        # probably need a SessionExtension to deal with this properly
        # object_session(instance).revision = None

    def before_update(self, mapper, connection, instance):
        self.set_revision(instance)

    def before_insert(self, mapper, connection, instance):
        self.set_revision(instance)

    def after_update(self, mapper, connection, instance):
        self.make_revision(instance)
        return EXT_CONTINUE

    def after_insert(self, mapper, connection, instance):
        self.make_revision(instance)
        return EXT_CONTINUE


class RevisionedObjectMixin(object):

    def _set_revision(self, revision):
        sess = object_session(self)
        rev = get_revision(sess)
        # if not rev or rev != revision:
        #     msg = 'The revision on the session does not match the one you' + \
        #     'requesting.'
        #     raise Exception(msg)
        set_revision(sess, revision)

    def get_as_of(self, revision):
        # set revision generally so dom traversal works
        self._set_revision(revision)
        revision_object = self.__revision_object__
        # exploit orderings of ids
        out = revision_object.query.filter(
                revision_object.revision_id <= revision.id
                )
        if out.count() == 0:
            return None
        else:
            return out.first()
