import dm.dom.stateful

class License(sqlobject.SQLObject):

    name = sqlobject.StringCol(alternateID=True)


class PackageSQLObject(sqlobject.SQLObject):

    name = sqlobject.UnicodeCol(alternateID=True)


class PackageRevision(base.ObjectRevisionSQLObject):

    base_object_name = 'Package'
    # TODO: probably should not have this on the revision as immutable
    name = sqlobject.UnicodeCol(default=None)
    notes = sqlobject.UnicodeCol(default=None)
    license = sqlobject.ForeignKey('License', default=None)


class TagSQLObject(sqlobject.SQLObject):

    name = sqlobject.UnicodeCol(alternateID=True)


class TagRevision(base.ObjectRevisionSQLObject):

    base_object_name = 'Tag'
    # TODO: probably should not have this on the revision as immutable
    name = sqlobject.UnicodeCol(default=None)


class PackageTagSQLObject(sqlobject.SQLObject):

    package = sqlobject.ForeignKey('PackageSQLObject', cascade=True)
    tag = sqlobject.ForeignKey('TagSQLObject', cascade=True)

class PackageTagRevision(base.ObjectRevisionSQLObject):

    base_object_name = 'PackageTag'

class Package(base.VersionedDomainObject):

    sqlobj_class = PackageSQLObject
    sqlobj_version_class = PackageRevision
    

class Tag(base.VersionedDomainObject):

    sqlobj_class = TagSQLObject
    sqlobj_version_class = TagRevision


class PackageTag(base.VersionedDomainObject):

    sqlobj_class = PackageTagSQLObject
    sqlobj_version_class = PackageTagRevision


