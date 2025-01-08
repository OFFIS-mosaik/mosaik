============
Installation
============

mosaik is a Python library, so you need a working installation of Python to use it. If you don't have one, https://python.org is Python's official home, and you can find instructions on how to install Python on your system there.

mosaik itself is then published on PyPI, the Python Package Index. This means that you can simply install it using whichever packaging tool you use for Python. As is good practice, we recommend that you use a virtual environment for each of your mosaik projects. Within that environment, you can then run ``pip install mosaik`` to get the newest version of mosaik. If you use something else to manage your packages, follow that tool's instructions. This tutorial assumes that you are using version 3.4 of mosaik, or newer.

The mosaik package is only required if you want to run mosaik co-simulations. If you only want to publish a simulator to be used with mosaik, your package should depend on the lighter-weight mosaik-api-v3 package, instead.


Getting help
============

Sometimes things go wrong, but we are usually quite willing to help. The best place to ask questions is our GitHub discussions forum, where we and other people might be able to answer your questions.

If you think that you have found a bug in mosaik, or if you want to propose a new feature, you can do that using our issue tracker on GitLab. (Yes, mosaik is present on both platforms for historic reasons.) Note that our team is small and mostly concerned with other projects, so we cannot promise that we will follow up on every feature request.

Finally, if your question is not suited for a public forum, you can also reach us via e-mail at mosaik@offis.de.


Working with the source
=======================

If you want to play around with mosaik's source code yourself, you can find it on GitLab here, where you can also clone the repository. Note that we strongly advise installing mosaik as a library from PyPI in almost all cases, as it will make it much easier to update to a new version.
