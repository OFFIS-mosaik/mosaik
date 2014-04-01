Quickstart
==========

This guide assumes that you are somewhat proficient with Python and know what
*pip* and *virtualenv*. Else, you should follow the :doc:`detailed instructions
<installation>`.

Mosaik runs on Linux, OS X and Windows. It requires `Python 3.3
<http://python.org>`_ or newer. To install everything, you need the package
manager `Pip <http://pip.readthedocs.org/en/latest/installing.html>`_ which is
bundled with Python 3.4 and above.

We also strongly recommend you to install everything into a `virtualenv
<http://www.virtualenv.org/en/latest/>`_.

You can then install mosaik with pip:

.. code-block:: bash

   $ pip install mosaik


There is also a demo scenario that you can try. You can get it from
`Bitbucket <https://bitbucket.org/mosaik/mosaik-demo>`_. If you have binary
packages for *numpy* and *scipy* available, you may install them first (they
are required for the load flow analysis with *PYPOWER*):

.. code-block:: bash

   $ hg clone https://bitbucket.org/mosaik/mosaik-demo
   $ cd mosaik-demo/
   $ pip install -r requirements.txt
   $ python demo.py

Then open your browser and go to http://localhost:8000.
