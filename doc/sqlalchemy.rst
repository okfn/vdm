=========================
Using VDM with SQLAlchemy
=========================

The Revision object is used to encapsulate changes to the domain model/database. It also allows changes to multiple objects/rows to be part of a single 'revision':

.. autoclass:: vdm.sqlalchemy.Revision

.. autoclass:: vdm.sqlalchemy.Revisioner

.. autofunction:: vdm.sqlalchemy.modify_base_object_mapper

.. autofunction:: vdm.sqlalchemy.add_stateful_m2m

Example
=======

Here is a full demonstration of using vdm which can be found in vdm/sqlalchemy/demo.py:

.. literalinclude:: ../vdm/sqlalchemy/demo.py

