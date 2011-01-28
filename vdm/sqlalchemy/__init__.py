'''SQLAlchemy versioned domain model extension.

For general information about versioned domain models see the root vdm package
docstring.

Implementation Notes
====================

SQLAlchemy conveniently provides its own Session object which can be used as
the 'session' for the vdm (i.e. the object which holds the current revision).

Some useful links:

http://blog.discorporate.us/2008/02/sqlalchemy-partitioned-collections-1/
http://groups.google.com/group/sqlalchemy/browse_thread/thread/ecd515c8c1c013b1
http://www.sqlalchemy.org/trac/browser/sqlalchemy/trunk/lib/sqlalchemy/ext/associationproxy.py
http://www.sqlalchemy.org/docs/04/plugins.html#plugins_associationproxy


TODO
====

1. How do we commit revisions (do we need to).
    * At very least do we not need to update timestamps?
    * support for state of revision (active, deleted (spam), in-progress etc)

2. Support for composite primary keys.
'''
from .tools import Repository
from .changeset import Changeset, ChangeObject, setup_changeset
from .model import VersionedListener
from .sqla import SQLAlchemyMixin, SQLAlchemySession

