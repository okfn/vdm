import dm.dom.base
import dm.dom.stateful
import dm.dom.meta

class Revision(dm.dom.stateful.StatefulObject):
    """A Revision to the domain model.

    A revision in the is valid only if {number} is not null (there may be some
    non-valid revisions in the database which correspond to failed or pending transactions).
    """

    # override definition in parent as need different default
    state = dm.dom.meta.HasA('State', default='pending')
    # would like number to have alternateID=True but then cannot have
    # default=None
    number = dm.dom.meta.Integer(default=None)
    author = dm.dom.meta.String(default=None)
    log_message = dm.dom.meta.String(default=None)
    # have to allow None so that we can bootstrap
    base_revision = dm.dom.meta.HasA('Revision', default=None)
    # TODO: date time col (need to set in transaction)
    # date = dm.dom.meta.DateTimeCol(default=None)

    def __init__(self):
        super(Revision, self).__init__()
        self.is_transaction = self.state == self.registry.states['pending']
        # TODO: start db transaction .... actually not sure about this (maybe
        # txns can persist across sessions)
        self.model = DomainModel(self, self.is_transaction)

    def commit(self):
        # TODO: generate the revision number in some better way
        # TODO: check this revision is not an empty revision
        self.number = self.id
        self.state = self.registry.states['active']
        self.save()


class DomainModel(object):

    def __init__(self, revision, transaction=None):
        self.revision = revision

