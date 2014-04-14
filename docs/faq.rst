===
FAQ
===

This is a list of some questions we recently got. If you cannot find an answer
for your questions here, you are welcome to post it on our `mailing list`__.

__ http://mosaik.offis.de/mailinglist


General questions
=================

Are there graphical tools for scenario design?
----------------------------------------------

An environment for graphical analysis as well as scenario design is currently
developed and will presumably be released in 2015. However, we argue that
graphical tools are not feasible for the design of large and complex scenarios.
For most applications the more flexible scenario design by code is
advantageous.


Where can I find a mosaik Tutorial/Manual?
------------------------------------------

There is none yet but it's quite on top of our to-do list. You'll soon find one
here.


Is there a mosaik-Wiki?
-----------------------

We like Wikis but consider them the wrong tool for documenting software (and
we are `not alone with that`__).

There are a lot of other resources, though:

- All documentation is concentrated here, at Read the Docs.
- `Source code`__ and `issues`__ are managed by Bitbucket.
- Discussion takes place in our `mailing list`__.
- News are spread through our `blog`__.

There's not much that a wiki could add here.

__ http://stevelosh.com/blog/2013/09/teach-dont-tell/
__ https://bitbucket.org/mosaik/mosaik/src
__ https://bitbucket.org/mosaik/mosaik/issues?status=new&status=open
__ http://mosaik.offis.de/mailinglist
__ http://mosaik.offis.de/blog


Coupling models with mosaik
===========================

Can I use continuous models with mosaik?
----------------------------------------

Yes. Since mosaik 2 you can even use a variable step size for your simulator
that can dynamically change during the simulation.


.. _can-i-use-mosaik-only-with-python-programs:

Can I use mosaik only with Python programs?
-------------------------------------------

No, mosaik can be used with any language that provides `network sockets`__ and
ways to (de)serialize `JSON`__.

Since implementing network event loops and message (de)serialization is
repetitive work and unnecessary overhead, we provide so called *high-level*
APIs for certain languages that provide a base class that you can inherit and
just need to implement a few methods representing the API calls.

Currently, a high-level API is only available for Python, but implementations
for JAVA and other languages will follow soon.

__ http://en.wikipedia.org/wiki/Network_socket
__ http://en.wikipedia.org/wiki/JSON


Can I use my MATLAB/Simulink models with mosaik? How do I do it?
----------------------------------------------------------------

Yes, you can. We will provide an example soon. In the end, if you manage to
let your model communicate via sockets and are capable of
serializing/deserializing JSON data objects you can use it with mosaik (see
:ref:`can-i-use-mosaik-only-with-python-programs` for details).

The mosaik demo
===============

I can only see active power values in the web visualization. Does mosaik also support reactive power values with PyPower?
-------------------------------------------------------------------------------------------------------------------------

Of course, it only depends on your models. The basic models distributed
with mosaik 2 only produce active power outputs (*cos phi = 1*), so we don't
display reactive power.


What are the power grid’s parameters? How are the cables’/lines’ parameters formatted?
--------------------------------------------------------------------------------------

Check https://bitbucket.org/mosaik/mosaik-pypower under "input file format".
Typically, line values are given in *R per km* and *X per km*.
