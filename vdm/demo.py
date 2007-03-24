"""
A versioned domain model demonstration.
"""
import sqlobject
uri = 'sqlite:/:memory:'
__connection__ = sqlobject.connectionForURI(uri)

import vdm.base
from vdm.base import State


class License(sqlobject.SQLObject):

    name = sqlobject.StringCol(alternateID=True)


class PackageRevision(vdm.base.ObjectRevisionSQLObject):

    base = sqlobject.ForeignKey('Package')
    # TODO: probably should not have this on the revision as immutable
    name = sqlobject.UnicodeCol(default=None)
    notes = sqlobject.UnicodeCol(default=None)
    license = sqlobject.ForeignKey('License', default=None)


class TagRevision(vdm.base.ObjectRevisionSQLObject):

    base = sqlobject.ForeignKey('Tag')
    # TODO: probably should not have this on the revision as immutable
    name = sqlobject.UnicodeCol(default=None)



class PackageTagRevision(vdm.base.ObjectRevisionSQLObject):

    base = sqlobject.ForeignKey('PackageTag')


class Package(vdm.base.VersionedDomainObject):

    sqlobj_version_class = PackageRevision
    versioned_attributes = vdm.base.get_attribute_names(sqlobj_version_class)
    
    name = sqlobject.UnicodeCol(alternateID=True)

    # should be attribute_name, module_name, module_object
    m2m = [ ('tags', 'vdm.demo', 'Tag', 'PackageTag') ]


class Tag(vdm.base.VersionedDomainObject):

    sqlobj_version_class = TagRevision

    name = sqlobject.UnicodeCol(alternateID=True)
    versioned_attributes = vdm.base.get_attribute_names(sqlobj_version_class)

    m2m = []


class PackageTag(vdm.base.VersionedDomainObject):

    sqlobj_version_class = PackageTagRevision
    versioned_attributes = vdm.base.get_attribute_names(sqlobj_version_class)
    m2m = []

    package = sqlobject.ForeignKey('Package', cascade=True)
    tag = sqlobject.ForeignKey('Tag', cascade=True)

    package_tag_index = sqlobject.DatabaseIndex('package', 'tag',
            unique=True)


class DomainModel(vdm.base.DomainModelBase):

    classes = [
            License,
            Package,
            PackageRevision,
            Tag,
            TagRevision,
            PackageTag,
            PackageTagRevision,
            ]

    def __init__(self, revision, transaction=None):
        super(DomainModel, self).__init__(revision, transaction)
        self.packages = vdm.base.VersionedDomainObjectRegister(Package, 'name', revision, transaction)
        self.tags = vdm.base.VersionedDomainObjectRegister(Tag, 'name', revision, transaction)
        self.package_tags = vdm.base.VersionedDomainObjectRegister(PackageTag, 'id', revision, transaction)


