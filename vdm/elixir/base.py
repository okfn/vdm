from datetime import datetime

from elixir import *
import elixir
import sqlalchemy


class IsRevisioned(object):
    '''
    This does quite a lot of work as we need to add lots of methods to the
    object. In a way would be nicer to work with inheritance but Elixir does
    not yet support concrete table inheritance and multiple inheritance is a
    pain.
    '''

    def __init__(self, entity, *args, **kwargs):
        entity_version_name = args[0]
        # do *not* want this module but module in which entity is being defined
        # module_name = self.__module__
        module_name = entity.__module__
        module = __import__(module_name, None, None, 'blah')
        self.entity_version = module.__dict__[entity_version_name]
        entity.version_class = self.entity_version
        self.setup_helper_methods(entity)

    def setup_helper_methods(self, entity):
        '''
        use inst throughout so as not to conflict with self
        '''

        # TODO: Do we need this if run only once per instance?
        # only do this once so check we have not already set stuff up
        if hasattr(entity, '_get_revisions'):
            return
        
        # decorator helper
        def attach_to_entity(fn):
            setattr(entity, fn.__name__, fn)

        @attach_to_entity
        def _ensure_version_operations_ok(inst):
            # only do this once ...
            if not hasattr(inst, 'history'):
                inst.session = sqlalchemy.object_session(inst)
                inst.global_revision = False
                # are we doing global revisions?
                # if not only doing stuff per entity
                if hasattr(inst.session, 'revision'):
                    inst.global_revision = True
                    inst.revision = inst.session.revision
                inst._get_revisions()

        @attach_to_entity
        def _get_revisions(inst):
            select = inst.version_class.select_by(base=inst)
            def filter_revisions(revision_list):
                if not inst.global_revision:
                    return revision_list

                ourrev = inst.revision.timestamp
                filtered = []
                for objrev in revision_list:
                    if objrev.timestamp <= ourrev:
                        filtered.append(objrev)
                return filtered
            inst.history = filter_revisions(select)

        @attach_to_entity
        def _current(inst):
            return inst.history[-1]

        @attach_to_entity
        def _ensure_working_copy(inst):
            if not hasattr(inst, 'have_working_copy') or inst.have_working_copy:
                wc = inst._new_working_copy()
                inst.have_working_copy = True
                inst.history.append(wc)

        @attach_to_entity
        def _new_working_copy(inst):
            # 2 options: either we are completely new or based off existing current
            if len(inst.history) > 0:
                return inst._current().copy()
            else:
                rev = inst.version_class()
                rev.base = inst 
                return rev

        @attach_to_entity
        def exists(inst):
            # is this right -- what happens if we did not have anything at revision
            # and have just created something as part of the current transaction
            # ...
            return len(inst.history) > 0

        # TODO: support for delete/purge/hibernate type stuff
#        def delete(inst):
#            deleted = State.get_by(name='deleted')
#            inst.state = deleted
#        
#        def purge(inst):
#            select = inst.version_class.select_by(base=inst)
#            for rev in select:
#                inst.version_class.delete(rev)
#            # because we have overriden delete have to play smart
#            inst.__class__.delete(inst)
#            # we flush immediately here as a special case ...
#            elixir.objectstore.flush()
#

class HasRevisionedField(object):
    """
    How this works ...

    We want to pass on versioned attribute calls to the relevant underlying
    object.
    """

    def __init__(self, entity, *args, **kwargs):
        attrname = args[0]
        def fget(inst):
            inst._ensure_version_operations_ok()
            current = inst._current()
            return getattr(current, attrname)

        def fset(inst, value):
            # todo check we are live
            inst._ensure_version_operations_ok()
            inst._ensure_working_copy()
            current = inst._current()
            setattr(current, attrname, value)

        print 'ADDING attributes to %s' % entity.__name__
        setattr(entity, attrname, property(fget, fset))

class IsRevision(object):

    def __init__(self, entity, *args, **kwargs):
        def copy(inst):
            new_version = inst.__class__()
            new_version.name = inst.name
            new_version.base = inst.base
            return new_version

        setattr(entity, 'copy', copy)


is_versioned = elixir.statements.Statement(IsRevisioned)
has_versioned_field = elixir.statements.Statement(HasRevisionedField)
is_version = elixir.statements.Statement(IsRevision)

