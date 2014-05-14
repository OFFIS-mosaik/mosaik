===============
Release Process
===============

This process describes the steps to execute in order to release a new version
of mosaik.


Preparations
============

#. Make a new release of `mosaik-api-python
   <https://bitbucket.org/mosaik/mosaik-api-python>`_ if required. Use this
   guide as an orientation.

#. Close all `tickets for the next version
   <https://bitbucket.org/mosaik/mosaik/issues?status=new&status=open>`_.

#. Check all dependencies for new versions and update the *exact* version of
   all entries in :file:`requirements.txt`. Update the *minium* required
   versions of dependencies in :file:`setup.py` if (and only if) necessary.

#. Run :command:`tox` from the project root. All tests for all supported
   versions must pass:

   .. code-block:: bash

    $ tox
    [...]
    ________ summary ________
    py33: commands succeeded
    py34: commands succeeded
    congratulations :)

#. Build the docs (HTML is enough). Make sure there are no errors and undefined
   references.

   .. code-block:: bash

    $ cd docs/
    $ make clean html
    $ cd ..

#. Check if all authors are listed in :file:`AUTHORS.txt`.

#. Update the change logs (:file:`CHANGES.txt` and
   :file:`docs/about/history.rst`). Only keep changes for the current major
   release in :file:`CHANGES.txt` and reference the history page from there.

#. Commit all changes:

   .. code-block:: bash

    $ hg ci -m 'Updated change log for the upcoming release.'

#. Update the version number in :file:`mosaik/__init__.py`, :file:`setup.py`
   and :file:`docs/conf.py` and commit:

   .. code-block:: bash

    $ hg ci -m 'Bump version from x.y.z to a.b.c'

   .. warning::

      Do not yet tag and push the changes so that you can safely do a rollback
      if one of the next step fails and you need change something!

#. Write a draft for the announcement mail with a list of changes,
   acknowledgements and installation instructions. Everyone in the team should
   agree with it.


Build and release
=================

#. Test the release process. Build a source distribution and a `wheel
   <https://pypi.python.org/pypi/wheel>`_ package and test them:

   .. code-block:: bash

    $ python setup.py sdist bdist_wheel
    $ ls dist/
    mosaik-a.b.c-py2.py3-none-any.whl mosaik-a.b.c.tar.gz

   Try installing them:

   .. code-block:: bash

    $ rm -rf /tmp/mosaik-sdist  # ensure clean state if ran repeatedly
    $ virtualenv -p /usr/bin/python3 /tmp/mosaik-sdist
    $ /tmp/mosaik-sdist/bin/pip install dist/mosaik-a.b.c.tar.gz
    $ /tmp/mosaik-sdist/bin/python
    >>> import mosaik  # doctest: +SKIP
    >>> mosaik.__version__  # doctest: +SKIP
    'a.b.c'

   and

   .. code-block:: bash

    $ rm -rf /tmp/mosaik-wheel  # ensure clean state if ran repeatedly
    $ virtualenv -p /usr/bin/python3 /tmp/mosaik-wheel
    $ /tmp/mosaik-wheel/bin/pip install dist/mosaik-a.b.c-py2.py3-none-any.whl
    $ /tmp/mosaik-wheel/bin/python
    >>> import mosaik  # doctest: +SKIP
    >>> mosaik.__version__  # doctest: +SKIP
    'a.b.c'

#. Create or check your accounts for the `test server
   <https://testpypi.python.org/pypi>`_ and `PyPI
   <https://pypi.python.org/pypi>`_. Update your :file:`~/.pypirc` with your
   current credentials:

   .. code-block:: ini

    [distutils]
    index-servers =
        pypi
        test

    [test]
    repository = https://testpypi.python.org/pypi
    username = <your test user name goes here>
    password = <your test password goes here>

    [pypi]
    repository = https://pypi.python.org/pypi
    username = <your production user name goes here>
    password = <your production password goes here>

#. Upload the distributions for the new version to the test server and test the
   installation again:

   .. code-block:: bash

    $ twine upload -r test dist/mosaik*a.b.c*
    $ pip install -i https://testpypi.python.org/pypi mosaik

#. Check if the package is displayed correctly:
   https://testpypi.python.org/pypi/mosaik

#. Finally upload the package to PyPI and test its installation one last time:

   .. code-block:: bash

    $ twine upload -r pypi dist/mosaik*a.b.c*
    $ pip install -U mosaik

#. Check if the package is displayed correctly:
   https://pypi.python.org/pypi/mosaik


Post release
============

#. Push your changes:

   .. code-block:: bash

    $ hg tag a.b.c
    $ hg push ssh://hg@bitbucket.org/mosaik/mosaik

#. Remove the :file:`build/` directory:

   .. code-block:: bash

    $ rm -r build/

#. Activate the `documentation build
   <https://readthedocs.org/dashboard/mosaik>`_ for the new version.

#. Make sure, the `demo <https://bitbucket.org/mosaik/mosaik-demo>`_ works with
   the new release.

#. Send the prepared email to the mailing list.

#. Create blog post for mosaik.offis.de.
