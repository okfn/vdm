'''SQLAlchemy versioned domain model extension.

Demo code in demo.py + demo_test.py.

Implementation Notes
====================

Some useful links:

http://blog.discorporate.us/2008/02/sqlalchemy-partitioned-collections-1/
http://groups.google.com/group/sqlalchemy/browse_thread/thread/ecd515c8c1c013b1
http://www.sqlalchemy.org/trac/browser/sqlalchemy/trunk/lib/sqlalchemy/ext/associationproxy.py
http://www.sqlalchemy.org/docs/04/plugins.html#plugins_associationproxy


TODO
====

    * 'ignored' fields on versioned objects (i.e. attributes which are not
      'versioned'.
    * support for m2m collections other than lists.
    * support for diffing and reverting.
'''
