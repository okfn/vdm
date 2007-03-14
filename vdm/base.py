import sqlobject
uri = 'sqlite:/:memory:'
__connection__ = sqlobject.connectionForURI(uri)


class DomainObjectBase(object):
    """'Layer Supertype (475)'  [Fowler, 2003]
    """
    pass

def get_attribute_names(sqlobj_class):
    # extra attributes added into Revision classes that should not be available
    # in main object
    excluded = [ 'revision', 'base' ]
    results = []
    for col in sqlobj_class.sqlmeta.columns.keys():
        if col.endswith('ID'):
            col = col[:-2]
        if col not in excluded:
            results.append(col)
    return results

class VersionedDomainObject(object):

    sqlobj_class = None
    sqlobj_version_class = None

    def __init__(self, sqlobj, revision, transaction):
        # MUST be set first to avoid recursion
        self._attr_names = get_attribute_names(self.sqlobj_version_class)
        self.sqlobj = sqlobj
        self.id = self.sqlobj.id
        self.revision = revision
        self.transaction = transaction
        self.have_working_copy = False
        self.revisions = []
        self._get_revisions()

    def exists(self):
        # is this right -- what happens if we did not have anything at revision
        # and have just created something as part of the current transaction
        # ...
        return len(self.revisions) > 0

    def delete(self):
        deleted = State.byName('deleted')
        self.state = deleted
    
    def _get_revisions(self):
        # if not based off any revision (should only happen if this is first
        # ever revision in entire repository)
        if self.revision is None:
            return
        ourrev = self.revision.number
        baseobj = self.sqlobj
        # TODO: more efficient way
        select = list(
                self.sqlobj_version_class.select(
                    self.sqlobj_version_class.q.baseID == baseobj.id)
                )
        revdict = {}
        for objrev in select:
            revdict[objrev.revision.number] = objrev
        revnums = revdict.keys()
        revnums.sort()
        if len(revnums) == 0: # should only happen if package only just created
            return
        created_revision = revnums[0]
        if created_revision > ourrev: # then package does not exist yet
            return
        # Take all package revisions with revision number <= ourrev
        # TODO: make more efficient
        for tt in revnums:
            if tt <= ourrev:
                self.revisions.append(revdict[tt])

    def _current(self):
        return self.revisions[-1]

    def __getattr__(self, attrname):
        if attrname in self._attr_names:
            return getattr(self._current(), attrname)
        else:
            raise AttributeError()

    def __setattr__(self, attrname, attrval):
        if attrname != '_attr_names' and attrname in self._attr_names:
            self._ensure_working_copy()
            current = self._current()
            print 'Setting attribute before: ', attrname, attrval, current
            setattr(current, attrname, attrval)
            print 'Setting attribute after: ', attrname, attrval, current
        else:
            super(VersionedDomainObject, self).__setattr__(attrname, attrval)

    def _ensure_working_copy(self):
        if not self.have_working_copy:
            wc = self._new_working_copy()
            self.have_working_copy = True
            self.revisions.append(wc)

    def _new_working_copy(self):
        # 2 options: either we are completely new or based off existing current
        if len(self.revisions) > 0:
            return self._current().copy(self.transaction)
        else:
            if self.transaction is None:
                raise Exception('Unable to set attributes outside of a transaction')
            rev = self.sqlobj_version_class(
                    base=self.sqlobj,
                    revision=self.transaction.revision)
            return rev


class Register(object):

    def __init__(self, type, key_name):
        self.type = type
        self.key_name = key_name

class VersionedDomainObjectRegister(Register):

    def __init__(self, type, key_name, revision, transaction=None):
        super(VersionedDomainObjectRegister, self).__init__(type, key_name)
        self.revision = revision
        self.transaction = transaction

    def create(self, **kwargs):
        """
        This will get easier once we move away from direct relation to sql and
        have a proper mapper.

        1. Create backing sqlobject
        2. Create the actual domain object
        3. Create the revision and add to the local stack
        """
        sqlobj = self.type.sqlobj_class(**kwargs)
        obj = self.type(sqlobj, self.revision, self.transaction)
        # clunky way to ensure associated version is created
        # TODO: think more about this
        if self.key_name != 'id': # id is problematic as used by sqlobject ...
            setattr(obj, self.key_name, kwargs[self.key_name])
        # TODO: ? set other values from kwargs
        return obj
    
    def get(self, key):
        # TODO: use self.key_name
        # nastily SQLObject specific ...
        method_name = 'by' + self.key_name.capitalize()
        method = self.type.sqlobj_class.__dict__[method_name]
        # because method is a class method method(-) will not work
        # Instead have to do some special stuff see:
        # http://mail.python.org/pipermail/python-list/2005-March/312183.html 
        sqlobj = method.__get__(None, self.type.sqlobj_class)(key)
        obj = self.type(sqlobj, self.revision, self.transaction)
        if obj.exists():
            return obj
        else:
            msg = 'No object identified by %s exists at revision %s' % (key,
                    self.revision)
            raise Exception(msg)

    def list(self, state='active'):
        all_objs_ever = self.type.sqlobj_class.select()
        results = []
        for baseobj in all_objs_ever:
            key = getattr(baseobj, self.key_name)
            try:
                obj = self.get(key)
            except:
                continue 
            if obj.state.name == state:
                results.append(obj)
        return results

    def delete(self, key):
        obj = self.get(key)
        obj.delete()


## ----------------------------------------------
## SQLObject stuff

class State(sqlobject.SQLObject):

    name = sqlobject.StringCol(alternateID=True)


class ObjectRevisionSQLObject(sqlobject.SQLObject):

    # to be defined in inheriting classes
    base_object_name = ''
    
    state = sqlobject.ForeignKey('State', default=1)
    base = sqlobject.ForeignKey(base_object_name + 'SQLObject')
    revision = sqlobject.ForeignKey('Revision')

    def copy(self, transaction):
        newvals = {}
        for col in self.sqlmeta.columns:
            if not col.startswith('revision'):
                value = getattr(self, col)
                newvals[col] = value
        newvals['revision'] = transaction.revision
        newrev = self.__class__(**newvals)
        return newrev


