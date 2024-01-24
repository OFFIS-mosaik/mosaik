from typing import Any, Callable, Dict, Generic, Iterable, Literal, Tuple, TypeVar

N = TypeVar("N")
K = TypeVar("K")

class Graph(Generic[N]):
    def add_edge(self, u_of_edge: N, v_of_edge: N, **attr: Any) -> None: ...

class DiGraph(Generic[N]):
    def add_node(self, node_for_adding: N, **attr: Any) -> None: ...
    def add_edge(self, u_of_edge: N, v_of_edge: N, **attr: Any) -> None: ...
    def has_edge(self, u: N, v: N) -> bool: ...
    def edges(self, data: Literal[True]) -> Iterable[Tuple[N, N, Dict[str, Any]]]: ...
    def __getitem__(self, n: N) -> Dict[N, Dict[str, Any]]: ...
    @property
    def nodes(self) -> Iterable[N]: ...
    def predecessors(self, node: N) -> Iterable[N]: ...

class MultiDiGraph(Generic[N, K]):
    def add_node(self, node_for_adding: N) -> None: ...
    def add_edge(self, u_for_edge: N, v_for_edge: N, key: K, **attr: Any) -> K: ...
    def out_edges(
        self, node: N, keys: Literal[True], data: Literal[True]
    ) -> Iterable[Tuple[N, N, K, Dict[str, Any]]]: ...
    def edges(self, data: Literal[True]) -> Iterable[Tuple[N, N, Dict[str, Any]]]: ...

def ancestors(graph: DiGraph[N], node: N) -> Iterable[N]: ...
def shortest_path_length(graph: DiGraph[N], source: N, target: N, weight: str) -> Any: ...
def parse_edgelist(lines: Iterable[str], create_using: DiGraph[N], nodetype: Callable[[str], N], data: Tuple[()]) -> DiGraph[N]: ...
def simple_cycles(graph: DiGraph[N]) -> Iterable[Iterable[N]]: ...
