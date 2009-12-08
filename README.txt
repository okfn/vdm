To install do::

    $ easy_install vdm

Or checkout from our mercurial repository::

    $ hg clone http://knowledgeforge.net/okfn/vdm

For more information see the main package docstring. To view this either just
open vdm/__init__.py or do (after installation)::

    $ pydoc vdm


For Developers
==============

To run tests you will need to have a set up a postgresql database with user
tester and password pass (see vdm/sqlalchemy/demo.py). You can then run the
tests using nosetests::

    $ nosestests vdm/sqlalchemy

