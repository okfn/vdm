## About

A versioned domain model framework.

The vdm package allows you to 'version' your domain model objects in the same
way that source code version control systems such as subversion help you
version your code. At present the package is built as a simple extension on top
of SQLObject so that those already familiar with SQLObject for creating domain
 models will find it easy to use the versioning facilities provided by this
 library.


## Copyright and License

(c) 2007-2008 The Open Knowledge Foundation

Licensed under the MIT license:

  <http://www.opensource.org/licenses/mit-license.php>


## Authors

Rufus Pollock <rufus [at] rufuspollock [dot] org>


## Conceptual Documentation

A great starting point is Fowler's *Patters for things that change with time*:

  http://www.martinfowler.com/ap2/timeNarrative.html

In particular Temporal Object:

  http://www.martinfowler.com/ap2/temporalObject.html

We implement two approaches:

  1. (simpler) Versioned domain objects are versioned independently (like a
     wiki). This is less of a versioned 'domain model' and more of plain
     versioned domain objects.
  2. (more complex) Have explicit 'Revision' object and multiple objects can be
     changed simultaneously in each revision (atomicity). This is proper
     versioned domain model.

Remark: using the first approach it is:

  * Impossible to support versioning of many-to-many links between versioned
    domain objects.
  * It is impossible to change multiple objects 'at once' -- that is as part of
    one atomic change

### Full Versioned Domain Model

With 'Revisions' we can support changing multiple objects at once. This gives
us something very similar to the subversion object model (as encapsulated in
their python bindings) but with a filesystem replaced by a domain model.

As we need to make some distinction betwen the 'domain model' -- that is the
objects we want to model -- and the extra apparatus we need to make this
versioned we use the term Repository as the overarching object that holds
references to all objects and nest the domain model within that:

# everything in our 
Repository
    # 'helper' objects
    Revision
    State
    # domain model objects
    ...

repo = Repository()
rev = repo.new_revision()
# change some domain objects
rev.commit()

### Code in Action

To see the (sqlobject) code in action take a look at:

  ./vdm/sqlobject/demo_test.py
  ./vdm/sqlobject/demo.py

The code for elixir, which is not yet fully functional, can be found in:

  ./vdm/elixir/

