Plan for a changeset model
==========================

Changeset represents a simplication of existing vdm approach.

It develops a changeset approach similar to that found in mercurial and git and as developed in prototype form in CKAN.

It is agnostic about format of versioning (i.e. copy-on-Write versus diffs)


Key Concepts
============

  * Changeset - a change to the domain model

    * includes metadata about this change
    * aggregates changes to domain objects in a ChangesetManifest

  * ChangesetManifest - a manifest with a (structured) list of ChangeObject(s)
  * ChangeObject - a description of a change to a domain object
  * Working Copy - the representation of the current state of the system
    resulting the application of specified set of changesets

Optional (?) additional items:

* 

Remarks: Changesets form a directed acyclic graph.

Changeset
=========

  * id
  * parents
  * closes
  * timestamp
  * author
  * log_message
  * meta - arbitrary key/value metadata

ChangeObject
============

  * object_identifier
  * change_type: delete | update | create | (move? copy?)
  * representation_type: full | diff
  * representation: serialization of this change either as full dump of object (copy-on-write) or diff

Questions
=========

  * How do we cherry-pick? I.e. select certain changesets and not others (they depeond 
  * How do we transplant? Ie. copy a set of changesets from one line of development to another?

Reading
=======

Mercurial
---------

Basic overview of the Mercurial model: http://mercurial.selenic.com/wiki/UnderstandingMercurial

  * changeset
  * manifest
  * file

Git
---

  * Glossary: http://www.kernel.org/pub/software/scm/git/docs/gitglossary.html
  * Technical Docs: http://repo.or.cz/w/git.git?a=tree;f=Documentation/technical;hb=HEAD
  * http://eagain.net/articles/git-for-computer-scientists/

Key features:

  * blob (bistreams)
  * tree
  * commit (changeset)
    * has metadata (e.g. parents)
    * points to a tree
 
Extras:

  * references (pointers into commit tree)
  * tags


