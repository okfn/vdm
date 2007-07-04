"""
A versioned domain model demonstration.
"""
import elixir

import vdm.elixir
from vdm.elixir import State


class License(elixir.Entity):

    elixir.has_field('name', elixir.Unicode)


class PackageRevision(elixir.Entity, vdm.elixir.ObjectRevisionEntity):

    elixir.belongs_to('state', of_kind='State')
    elixir.belongs_to('base', of_kind='Package')
    elixir.has_field('notes', elixir.Unicode)
    elixir.belongs_to('license', of_kind='License')

    def __init__(self, *args, **kwargs):
        super(PackageRevision, self).__init__(*args, **kwargs)
        self._default_state()


class TagRevision(elixir.Entity, vdm.elixir.ObjectRevisionEntity):

    elixir.belongs_to('state', of_kind='State')
    elixir.belongs_to('base', of_kind='Tag')

    def __init__(self, *args, **kwargs):
        super(TagRevision, self).__init__(*args, **kwargs)
        self._default_state()


class PackageTagRevision(elixir.Entity, vdm.elixir.ObjectRevisionEntity):

    elixir.belongs_to('state', of_kind='State')
    elixir.belongs_to('base', of_kind='PackageTag')

    def __init__(self, *args, **kwargs):
        super(PackageTagRevision, self).__init__(*args, **kwargs)
        self._default_state()


class Package(elixir.Entity, vdm.elixir.VersionedDomainObject):

    version_class = PackageRevision
    versioned_attributes = vdm.elixir.get_attribute_names(version_class)
    
    elixir.has_field('name', elixir.Unicode)

    # should be attribute_name, module_name, module_object
    m2m = [ ('tags', 'vdm.elixir.demo', 'Tag', 'PackageTag') ]


class Tag(elixir.Entity, vdm.elixir.VersionedDomainObject):

    version_class = TagRevision
    versioned_attributes = vdm.elixir.get_attribute_names(version_class)

    elixir.has_field('name', elixir.Unicode)

    m2m = []


class PackageTag(elixir.Entity, vdm.elixir.VersionedDomainObject):

    version_class = PackageTagRevision
    versioned_attributes = vdm.elixir.get_attribute_names(version_class)
    m2m = []

    elixir.belongs_to('base', of_kind='Package', ondelete='cascade')
    elixir.belongs_to('base', of_kind='Tag', ondelete='cascade')

    # TODO: put in sqlalchemy stuff
    # package_tag_index = sqlobject.DatabaseIndex('package', 'tag', unique=True)


class DomainModel(vdm.elixir.DomainModelBase):

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
        self.packages = vdm.elixir.VersionedDomainObjectRegister(Package, 'name', revision, transaction)
        self.tags = vdm.elixir.VersionedDomainObjectRegister(Tag, 'name', revision, transaction)
        self.package_tags = vdm.elixir.VersionedDomainObjectRegister(PackageTag, 'id', revision, transaction)


