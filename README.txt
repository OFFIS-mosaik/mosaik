Mosaik
======

Mosaik is a simulation compositor for Smart Grid simulations.

It lets you re-use existing simulators and couple them to simulate large-scale
Smart Grid scenarios. Mosaik offers powerful mechanisms to specify and compose
these scenarios.

This package contains mosaik itself, a server for the mosaik web client, and
various helpers for development and testing.


Installation
------------

Mosaik requires Python >= 3.3. Use `pip`__ to install it, preferably into
a `virtualenv`__::

    $ pip install hg+ssh://hg@ecode.offis.de/mosaik/mosaik-api-python
    $ pip install hg+ssh://hg@ecode.offis.de/mosaik/mosaik

You can test your installation with::

    $ mosaik-test

You’ll find detailed installtion instructions in the `user`__ and
`development`__ guide.

__ https://pypi.python.org/pypi/pip
__ https://pypi.python.org/pypi/virtualenv
__ https://mosaik.offis.uni-oldenburg.de/docs/user_guide/installation.html
__ https://mosaik.offis.uni-oldenburg.de/docs/dev_guide/installation.html


Documentation, Source code and issues
-------------------------------------

The documentation is available at https://mosaik.offis.de/docs/.

You can browe mosaik’s source via `trac`__.

Please report bugs and ideas for improvment to our `issue tracker`__.

__ https://mosaik.offis.de/trac/browser
__ https://mosaik.offis.de/trac/newticket
