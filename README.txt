To install do::

    $ easy_install vdm

Or checkout from our git repository::

    $ git clone https://github.com/okfn/vdm

For more information see the main package docstring. To view this either just
open vdm/__init__.py or do (after installation)::

    $ pydoc vdm


For Developers
==============

Tests currently pass against postgres or sqlite (see 'TEST_ENGINE' setting
in vdm/sqlalchemy/demo.py).

To run tests with postgres you will need to have a set up a postgresql
database with user 'tester' and password 'pass' (see settings in
vdm/sqlalchemy/demo.py). 

Run the tests using nosetests::

    $ nosestests vdm/sqlalchemy

