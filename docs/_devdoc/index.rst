=============
UML-Diagramme
=============

.. uml::

    @startuml
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
    @enduml


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
