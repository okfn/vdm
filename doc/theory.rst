====================================================
Versioning / Revisioning for Domain Models: Concepts
====================================================

There are several ways to *implement* revisioning (versioning) of domain model (and DBs/data generally):

  * Copy on write - so one has a 'full' copy of the model/DB at each version.
  * Diffs: store diffs between versions (plus, usually, a full version of the model at a given point in time e.g. store HEAD)

In both cases one will usually want an explicit Revision/Changeset object to which :

  * timestamp
  * author of change
  * log message

In more complex revisioning models this metadata may also be used to store key data relevant to the revisioning structure (e.g. revision parents)


Copy on write
=============

In its simplest form copy-on-write (CoW) would copy entire DB on each change. However, this is cleary very inefficient and hence one usually restricts the copy-on-write to relevant changed "objects". The advantage of doing this is that it limits the the changes we have to store (in essence objects unchanged between revision X and revision Y get "merged" into a single object).

For example, if our domain model had Person, Address, Job, a change to Person X would only require a copy of Person X record (an even more standard example is wiki pages). Obviously, for this to work, one needs to able to partition the data (domain model). With normal domain model this is trivial: pick the object types e.g. Person, Address, Job etc. However, for a graph setup (as with RDF) this is not so trivial. 

Why? In essence, for copy on write to work we need:

  a) a way to reference entities/records
  b) support for putting objects in a deleted state

The (RDF) graph model has poor way for referencing triples (we could use named graphs, quads or reification but none are great). We could move to the object level and only work with groups of triples (e.g. those corresponding to a "Person"). You'd also need to add a state triple to every base entity (be that a triple or named graph) and add that to every query statement. This seems painful.

Diffs
=====

The diff models involves computing diffs (forward or backward) for each change. A given version of the model is then computed by composing diffs.

Usually for performance reasons full representations of the model/DB at a given version are cached -- most commonly HEAD is kept available. It is also possible to cache more frequently and, like copy-on-write, to cache selectively (i.e. only cache items which have change since the last cache period).

The disadvantage of the diff model is the need (and cost) of creating and composing diffs (CoW is, generally, easier to implement and use). However, it is more efficient in storage terms and works better with general data (one can always compute diffs), especially that which doesn't have such a clear domain model -- e.g. the RDF case discussed above.

Usage
=====

  * Wikis: Many wikis implement a full copy-on-write model with a full copy of each page being made on each write.
  * Source control: diff model (usually with HEAD cached and backwards diffs)
  * vdm: copy-on-write using SQL tables as core 'domain objects'
  * ordf (http://packages.python.org/ordf): (RDF) diffs (with HEAD caching)

Todo
====

Discuss application of tree algorithms to structured data (such as XML).

