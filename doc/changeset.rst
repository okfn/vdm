Plan for a changeset model
==========================

Changeset represents a simplication of existing vdm approach.

It develops a changeset approach similar to that found in mercurial and git and
as developed in prototype form in CKAN (see `these wiki pages`_)

.. _these wiki pages: http://ckan.org/wiki/DistributingChanges

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

* Tags
* Branches

Remarks: Changesets form a directed acyclic graph.

Changeset
=========

  * id: 160-bit number usually representing as 40 digit hex string (a SHA1 hash)
  * parents = ordered list of ids
  * timestamp
  * author
  * message
  * meta - arbitrary key/value metadata

ChangeManifest
==============

  * changes: dict of ChangeObjects keyed by object_id

ChangeObject
============

  * object_id - a tuple forming a unique identifier for this object *within*
    the domain model
  * operation_type: delete | update | create | (move? copy?)
  * data_type: full | diff | snapshot

    * This relates to how changes are stored (copy-on-write versus diff etc) - see :doc:`theory`
    
  * representation: serialization of this change either as full dump of object (copy-on-write) or diff

Doing Things
============

Applying changes to a working copy
----------------------------------

Trivial.

Reconstructing the repository at a given changeset/revision
-----------------------------------------------------------

Specifically we require to reconstruct a given object at that changeset. The
process:

  1. Get object ID
  2. If using CoW (copy-on-write): find first changeset <= {given-changeset} in
     which there is a ChangeObject entry containing the object ID and return
     this. END.
  3. If using diff: find all ChangeObjects with changesets <= {given-changeset}
     and concatenate. Return resulting object.

Get all changes to a given object
---------------------------------

Search ChangeObjects by object_id, and order by the order on Changesets (if
there is one).

Merging
-------


Pending Changes
---------------

This is a common use case where you want to record changes but only make them visible when approved in some way. It can also be useful if you are worried about spam revisions.


Questions
=========

Practical
---------

  * How do we cherry-pick? I.e. select certain changesets and not others (they
    depend 
  * How do we transplant? Ie. copy a set of changesets from one line of
    development to another?

Technical

  * How do we compute changeset ids (and changeobject ids)?
  * Does the ordering of ChangeObjects in a ChangesetManifest matter? Current
    answer: No.


What's Different from Git?
--------------------------

We don't store a current state of the domain model on each commit (rather we
store changes to the domain model and copies or diffs of domain objects).


Reading
=======

Mercurial
---------

Overview of the Mercurial model:

  * http://mercurial.selenic.com/wiki/UnderstandingMercurial
  * http://hgbook.red-bean.com/read/behind-the-scenes.html
  * (Longer) http://mercurial.selenic.com/wiki/Mercurial?action=AttachFile&do=get&target=Hague2009.pdf

Key concepts:

  * changeset / changelog (our changeset)
  * manifest
  * file

Details of `Mercurial hash generation`_:

> Mercurial hashes both the contents of an object and the hash of its parents
> to create an identifier that uniquely identifies an object's contents and
> history.  This greatly simplifies merging of histories because it avoid graph
> cycles that can occur when a object is reverted to an earlier state.

> All file revisions have an associated hash value (the nodeid). These are
> listed in the manifest of a given project revision, and the manifest hash is
> listed in the changeset. The changeset hash (the changeset ID) is again a
> hash of the changeset contents and its parents, so it uniquely identifies the
> entire history of the project to that point.

.. Mercurial hash generation: http://mercurial.selenic.com/wiki/FAQ#FAQ.2BAC8-TechnicalDetails.How_do_Mercurial_hashes_get_calculated.3F

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

Git hash computation::

    sha1("blob " + filesize + "\0" + data)

