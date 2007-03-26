## About

A versioned domain model framework.

The vdm package allows you to 'version' your domain model objects in the same
way that source code version control systems such as subversion help you
version your code. At present the package is built as a simple extension on top
of SQLObject so that those already familiar with SQLObject for creating domain
 models will find it easy to use the versioning facilities provided by this
 library.

For a demo of how to use package see vdm/demo.py and vdm/demo_test.py.


## Copyright and License

(c) 2007 The Open Knowledge Foundation

Licensed under the MIT license:

  <http://www.opensource.org/licenses/mit-license.php>


## Authors

Rufus Pollock <rufus [at] rufuspollock [dot] org>


## Conceptual Documentation

A great starting point is Fowler's *Patters for things that change with time*:

  http://www.martinfowler.com/ap2/timeNarrative.html

In particular Temporal Object:

  http://www.martinfowler.com/ap2/temporalObject.html

In addition we make heavy use of various other standard patterns (references
are to PoEAA) such as Unit of Work.
