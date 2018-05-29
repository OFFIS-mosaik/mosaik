.. Sphinx RTD theme demo documentation master file, created by
   sphinx-quickstart on Sun Nov  3 11:56:36 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

=================================================
Demo Docs
=================================================

:Page Status: Incomplete
:Last Reviewed: 2013-10-29

Contents:

.. toctree::
    :maxdepth: 2
    :caption: Sweet Docs

    demo
    list

.. toctree::
    :titlesonly:

    toc

.. toctree::
    :maxdepth: 2
    :caption: This is an incredibly long caption for a long menu

    long
    api

Maaaaath!
=========

This is a test.  Here is an equation:
:math:`X_{0:5} = (X_0, X_1, X_2, X_3, X_4)`.
Here is another:

.. math::

    \nabla^2 f =
    \frac{1}{r^2} \frac{\partial}{\partial r}
    \left( r^2 \frac{\partial f}{\partial r} \right) +
    \frac{1}{r^2 \sin \theta} \frac{\partial f}{\partial \theta}
    \left( \sin \theta \, \frac{\partial f}{\partial \theta} \right) +
    \frac{1}{r^2 \sin^2\theta} \frac{\partial^2 f}{\partial \phi^2}


Giant tables
============

+------------+------------+-----------+------------+------------+-----------+------------+------------+-----------+------------+------------+-----------+
| Header 1   | Header 2   | Header 3  | Header 1   | Header 2   | Header 3  | Header 1   | Header 2   | Header 3  | Header 1   | Header 2   | Header 3  |
+============+============+===========+============+============+===========+============+============+===========+============+============+===========+
| body row 1 | column 2   | column 3  | body row 1 | column 2   | column 3  | body row 1 | column 2   | column 3  | body row 1 | column 2   | column 3  |
+------------+------------+-----------+------------+------------+-----------+------------+------------+-----------+------------+------------+-----------+
| body row 1 | column 2   | column 3  | body row 1 | column 2   | column 3  | body row 1 | column 2   | column 3  | body row 1 | column 2   | column 3  |
+------------+------------+-----------+------------+------------+-----------+------------+------------+-----------+------------+------------+-----------+
| body row 1 | column 2   | column 3  | body row 1 | column 2   | column 3  | body row 1 | column 2   | column 3  | body row 1 | column 2   | column 3  |
+------------+------------+-----------+------------+------------+-----------+------------+------------+-----------+------------+------------+-----------+
| body row 1 | column 2   | column 3  | body row 1 | column 2   | column 3  | body row 1 | column 2   | column 3  | body row 1 | column 2   | column 3  |
+------------+------------+-----------+------------+------------+-----------+------------+------------+-----------+------------+------------+-----------+

Optional parameter args
-----------------------

At this point optional parameters `cannot be generated from code`_.
However, some projects will manually do it, like so:

This example comes from `django-payments module docs`_.

.. class:: payments.dotpay.DotpayProvider(seller_id, pin[, channel=0[, lock=False], lang='pl'])

   This backend implements payments using a popular Polish gateway, `Dotpay.pl <http://www.dotpay.pl>`_.

   Due to API limitations there is no support for transferring purchased items.


   :param seller_id: Seller ID assigned by Dotpay
   :param pin: PIN assigned by Dotpay
   :param channel: Default payment channel (consult reference guide)
   :param lang: UI language
   :param lock: Whether to disable channels other than the default selected above

.. _cannot be generated from code: https://groups.google.com/forum/#!topic/sphinx-users/_qfsVT5Vxpw
.. _django-payments module docs: http://django-payments.readthedocs.org/en/latest/modules.html#payments.authorizenet.AuthorizeNetProvider

Code test
=========

.. parsed-literal::

    # parsed-literal test
    curl -O http://someurl/release-|version|.tar-gz


.. code-block:: json

    {
    "windows": [
        {
        "panes": [
            {
            "shell_command": [
                "echo 'did you know'",
                "echo 'you can inline'"
            ]
            },
            {
            "shell_command": "echo 'single commands'"
            },
            "echo 'for panes'"
        ],
        "window_name": "long form"
        }
    ],
    "session_name": "shorthands"
    }

Sidebar
=======

.. sidebar:: Ch'ien / The Creative

    .. image:: static/yi_jing_01_chien.jpg

    *Above* CH'IEN THE CREATIVE, HEAVEN

    *Below* CH'IEN THE CREATIVE, HEAVEN

The first hexagram is made up of six unbroken lines. These unbroken lines stand for the primal power, which is light-giving, active, strong, and of the spirit. The hexagram is consistently strong in character, and since it is without weakness, its essence is power or energy. Its image is heaven. Its energy is represented as unrestricted by any fixed conditions in space and is therefore conceived of as motion. Time is regarded as the basis of this motion. Thus the hexagram includes also the power of time and the power of persisting in time, that is, duration.

The power represented by the hexagram is to be interpreted in a dual sense in terms of its action on the universe and of its action on the world of men. In relation to the universe, the hexagram expresses the strong, creative action of the Deity. In relation to the human world, it denotes the creative action of the holy man or sage, of the ruler or leader of men, who through his power awakens and develops their higher nature.

Code with Sidebar
=================

.. sidebar:: A code example

    With a sidebar on the right.

.. literalinclude:: test_py_module/test.py
    :language: python
    :linenos:
    :lines: 1-40

Boxes
=====

.. tip::
    Equations within a note
    :math:`G_{\mu\nu} = 8 \pi G (T_{\mu\nu}  + \rho_\Lambda g_{\mu\nu})`.

.. note::
    Equations within a note
    :math:`G_{\mu\nu} = 8 \pi G (T_{\mu\nu}  + \rho_\Lambda g_{\mu\nu})`.

.. danger::
    Equations within a note
    :math:`G_{\mu\nu} = 8 \pi G (T_{\mu\nu}  + \rho_\Lambda g_{\mu\nu})`.

.. warning::
    Equations within a note
    :math:`G_{\mu\nu} = 8 \pi G (T_{\mu\nu}  + \rho_\Lambda g_{\mu\nu})`.


Inline code and references
==========================

`reStructuredText`_ is a markup language. It can use roles and
declarations to turn reST into HTML.

In reST, ``*hello world*`` becomes ``<em>hello world</em>``. This is
because a library called `Docutils`_ was able to parse the reST and use a
``Writer`` to output it that way.

If I type ````an inline literal```` it will wrap it in ``<tt>``. You can
see more details on the `Inline Markup`_ on the Docutils homepage.

Also with ``sphinx.ext.autodoc``, which I use in the demo, I can link to
:class:`test_py_module.test.Foo`. It will link you right my code
documentation for it.

.. _reStructuredText: http://docutils.sourceforge.net/rst.html
.. _Docutils: http://docutils.sourceforge.net/
.. _Inline Markup: http://docutils.sourceforge.net/docs/ref/rst/restructuredtext.html#inline-markup

.. note:: Every other line in this table will have white text on a white background.
            This is bad.

    +---------+
    | Example |
    +=========+
    | Thing1  |
    +---------+
    | Thing2  |
    +---------+
    | Thing3  |
    +---------+

Emphasized lines with line numbers
==================================

.. code-block:: python
   :linenos:
   :emphasize-lines: 3,5

   def some_function():
       interesting = False
       print 'This line is highlighted.'
       print 'This one is not...'
       print '...but this one is.'


Citation
========

Here I am making a citation [1]_, another [2]_ and another [3]_

.. [1] This is the citation I made, let's make this extremely long so that we can tell that it doesn't follow the normal responsive table stuff.

.. [2] This citation has some ``code blocks`` in it, maybe some **bold** and
       *italics* too. Heck, lets put a link to a meta citation [3]_ too.

.. [3] This citation will have two backlinks.

======
Images
======

.. figure:: static/yi_jing_01_chien.jpg

    This is a caption for a figure.

Download links
==============

:download:`This long long long long long long long long long long long long long long long download link should be blue with icon, and should wrap white-spaces <static/yi_jing_01_chien.jpg>`


.. graphviz::

    digraph classesmosaik {
    graph [dpi = 0, ratio = "1"]
    charset="utf-8"
    rankdir=BT
    "0" [label="{Accessor|\l|dispatch()\lresolve()\l}", shape="record"];
    "1" [label="{Accessor|get_child\lname\lparent\lpath\lroot\l|lookup()\l}", shape="record"];
    "2" [label="{Accessor|obj\l|}", shape="record"];
    "3" [label="{BaseEnvironment|active_process\lnow\l|exit()\lrun()\lschedule()\lstep()\l}", shape="record"];
    "4" [label="{BaseIOEnvironment|active_process\lall_of\lany_of\levent\lfds : NoneType, dict\lnow\lprocess\lstart\lsuspend\ltimeout\l|close()\lexit()\lschedule()\lstep()\l}", shape="record"];
    "5" [label="{BaseSocket|address\lpeer_address\l|accept()\lbind()\lclose()\lconnect()\llisten()\lread()\lwrite()\l}", shape="record"];
    "6" [label="{BaseTCPSocket|accept : method\laddress\lenv\lpeer_address\lread : method\lsock : NoneType\lwrite : method\l|bind()\lclose()\lconnect()\lconnection()\lfileno()\llisten()\lserver()\l}", shape="record"];
    "7" [label="{BoundClass|cls\l|bind_early()\l}", shape="record"];
    "8" [label="{DiGraph|adj\ladjlist_inner_dict_factory\ladjlist_outer_dict_factory\ldegree\ledge_attr_dict_factory\ledges\lgraph : dict\lin_degree\lin_edges\lneighbors\lnode_dict_factory\lout_degree\lout_edges\lpred\lroot_graph\lsucc\l|add_edge()\ladd_edges_from()\ladd_node()\ladd_nodes_from()\lclear()\lcopy()\lfresh_copy()\lhas_predecessor()\lhas_successor()\lis_directed()\lis_multigraph()\lpredecessors()\lremove_edge()\lremove_edges_from()\lremove_node()\lremove_nodes_from()\lreverse()\lsubgraph()\lsuccessors()\lto_undirected()\l}", shape="record"];
    "9" [label="{Entity|children\leid\lfull_id\lsid\lsim\lsim_name\ltype\l|}", shape="record"];
    "10" [label="{Environment|\l|}", shape="record"];
    "11" [label="{Graph|adj\ladjlist_inner_dict_factory\ladjlist_inner_dict_factory : dict\ladjlist_outer_dict_factory\ladjlist_outer_dict_factory : dict\ldegree\ledge_attr_dict_factory\ledge_attr_dict_factory : dict\ledges\lgraph : dict\lname\lname : str\lnode\lnode_dict_factory\lnode_dict_factory : dict\lnodes\lroot_graph\l|add_cycle()\ladd_edge()\ladd_edges_from()\ladd_node()\ladd_nodes_from()\ladd_path()\ladd_star()\ladd_weighted_edges_from()\ladjacency()\lclear()\lcopy()\ledge_subgraph()\lfresh_copy()\lget_edge_data()\lhas_edge()\lhas_node()\lis_directed()\lis_multigraph()\lnbunch_iter()\lneighbors()\lnodes_with_selfloops()\lnumber_of_edges()\lnumber_of_nodes()\lnumber_of_selfloops()\lorder()\lremove_edge()\lremove_edges_from()\lremove_node()\lremove_nodes_from()\lselfloop_edges()\lsize()\lsubgraph()\lto_directed()\lto_undirected()\l}", shape="record"];
    "12" [label="{LocalProcess|\l|stop()\l}", shape="record"];
    "13" [label="{ModelFactory|meta\l|}", shape="record"];
    "14" [label="{ModelMock|\l|create()\l}", shape="record"];
    "15" [label="{MosaikRemote|sim_id\lworld\l|get_data()\lget_progress()\lget_related_entities()\lset_data()\l}", shape="record"];
    "16" [label="{RemoteProcess|\l|stop()\l}", shape="record"];
    "17" [fontcolor="red", label="{ScenarioError|\l|}", shape="record"];
    "18" [label="{SimProxy|input_buffer : dict\llast_step : int\lmeta\lname\lnext_step : int\lproxy\lsid\lsim_proc : NoneType\lstep_required : NoneType\l|stop()\l}", shape="record"];
    "19" [fontcolor="red", label="{SimulationError|\l|}", shape="record"];
    "20" [label="{TCPSocket|\l|}", shape="record"];
    "21" [label="{World|config : dict\ldf_graph\lentity_graph\lenv\lexecution_graph\lsim_config\lsim_progress : int\lsims : dict\lsrv_sock : NoneType\l|connect()\lget_data()\lrun()\lshutdown()\lstart()\l}", shape="record"];
    "22" [label="{count|\l|}", shape="record"];
    "23" [label="{defaultdict|default_factory : NoneType\l|}", shape="record"];
    "24" [label="{rpc|parent : NoneType\l|}", shape="record"];
    "25" [label="{socket|\l|bind()\lclose()\lconnect()\lconnect_ex()\ldetach()\lfileno()\lgetpeername()\lgetsockname()\lgetsockopt()\lgettimeout()\llisten()\lrecv()\lrecv_into()\lrecvfrom()\lrecvfrom_into()\lrecvmsg()\lrecvmsg_into()\lsend()\lsendall()\lsendmsg()\lsendmsg_afalg()\lsendto()\lsetblocking()\lsetsockopt()\lsettimeout()\lshutdown()\l}", shape="record"];
    "26" [label="{socket|family\ltype\l|accept()\lclose()\ldetach()\ldup()\lget_inheritable()\lmakefile()\lsendfile()\lset_inheritable()\l}", shape="record"];
    "0" -> "1" [arrowhead="empty", arrowtail="none"];
    "0" -> "2" [arrowhead="empty", arrowtail="none"];
    "1" -> "2" [arrowhead="empty", arrowtail="none"];
    "4" -> "3" [arrowhead="empty", arrowtail="none"];
    "6" -> "5" [arrowhead="empty", arrowtail="none"];
    "8" -> "11" [arrowhead="empty", arrowtail="none"];
    "10" -> "4" [arrowhead="empty", arrowtail="none"];
    "12" -> "18" [arrowhead="empty", arrowtail="none"];
    "16" -> "18" [arrowhead="empty", arrowtail="none"];
    "20" -> "6" [arrowhead="empty", arrowtail="none"];
    "24" -> "0" [arrowhead="empty", arrowtail="none"];
    "26" -> "25" [arrowhead="empty", arrowtail="none"];
    "7" -> "4" [arrowhead="diamond", arrowtail="none", fontcolor="green", label="process", style="solid"];
    "7" -> "4" [arrowhead="diamond", arrowtail="none", fontcolor="green", label="timeout", style="solid"];
    "7" -> "4" [arrowhead="diamond", arrowtail="none", fontcolor="green", label="event", style="solid"];
    "7" -> "4" [arrowhead="diamond", arrowtail="none", fontcolor="green", label="all_of", style="solid"];
    "7" -> "4" [arrowhead="diamond", arrowtail="none", fontcolor="green", label="any_of", style="solid"];
    "7" -> "4" [arrowhead="diamond", arrowtail="none", fontcolor="green", label="suspend", style="solid"];
    "7" -> "4" [arrowhead="diamond", arrowtail="none", fontcolor="green", label="start", style="solid"];
    "8" -> "8" [arrowhead="diamond", arrowtail="none", fontcolor="green", label="root_graph", style="solid"];
    "8" -> "21" [arrowhead="diamond", arrowtail="none", fontcolor="green", label="df_graph", style="solid"];
    "8" -> "21" [arrowhead="diamond", arrowtail="none", fontcolor="green", label="execution_graph", style="solid"];
    "10" -> "21" [arrowhead="diamond", arrowtail="none", fontcolor="green", label="env", style="solid"];
    "11" -> "11" [arrowhead="diamond", arrowtail="none", fontcolor="green", label="root_graph", style="solid"];
    "11" -> "21" [arrowhead="diamond", arrowtail="none", fontcolor="green", label="entity_graph", style="solid"];
    "15" -> "16" [arrowhead="diamond", arrowtail="none", fontcolor="green", label="_mosaik_remote", style="solid"];
    "20" -> "21" [arrowhead="diamond", arrowtail="none", fontcolor="green", label="srv_sock", style="solid"];
    "22" -> "4" [arrowhead="diamond", arrowtail="none", fontcolor="green", label="_eid", style="solid"];
    "23" -> "21" [arrowhead="diamond", arrowtail="none", fontcolor="green", label="_sim_ids", style="solid"];
    "23" -> "21" [arrowhead="diamond", arrowtail="none", fontcolor="green", label="_df_outattr", style="solid"];
    "23" -> "21" [arrowhead="diamond", arrowtail="none", fontcolor="green", label="_df_cache", style="solid"];
    "25" -> "6" [arrowhead="diamond", arrowtail="none", fontcolor="green", label="sock", style="solid"];
    "26" -> "6" [arrowhead="diamond", arrowtail="none", fontcolor="green", label="sock", style="solid"];
    }
