from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Dict, List, Tuple, Set


# ----------------------------
# Graph structures
# ----------------------------

@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    Result: str
    weight: float


class Graph:
    def __init__(self) -> None:
        self.adj: Dict[str, List[Edge]] = {}

    def add_edge(self, src: str, dst: str, Result: str, weight: float) -> None:
        self.adj.setdefault(src, []).append(Edge(src, dst, Result, weight))
        self.adj.setdefault(dst, [])  # ensure dst exists

    def neighbors(self, node: str) -> List[Edge]:
        return self.adj.get(node, [])

    def nodes(self) -> List[str]:
        return list(self.adj.keys())


# ----------------------------
# Dijkstra
# ----------------------------

@dataclass
class DijkstraResult:
    dist: Dict[str, float]
    prev: Dict[str, Tuple[str, Edge]]  # node -> (parent, edge used)


def dijkstra(graph: Graph, start: str) -> DijkstraResult:
    dist: Dict[str, float] = {start: 0.0}
    prev: Dict[str, Tuple[str, Edge]] = {}
    pq: List[Tuple[float, str]] = [(0.0, start)]
    visited: Set[str] = set()

    while pq:
        cur_d, u = heapq.heappop(pq)
        if u in visited:
            continue
        visited.add(u)

        if cur_d != dist.get(u, float("inf")):
            continue

        for e in graph.neighbors(u):
            v = e.dst
            nd = cur_d + e.weight
            if nd < dist.get(v, float("inf")):
                dist[v] = nd
                prev[v] = (u, e)
                heapq.heappush(pq, (nd, v))

    return DijkstraResult(dist=dist, prev=prev)


def rebuild_path(prev: Dict[str, Tuple[str, Edge]], start: str, target: str) -> List[Edge]:
    if target == start:
        return []
    out_rev: List[Edge] = []
    cur = target
    while cur != start:
        if cur not in prev:
            return []  # should not happen if graph is strongly connected and nodes exist
        parent, edge = prev[cur]
        out_rev.append(edge)
        cur = parent
    return list(reversed(out_rev))


# ----------------------------
# Connectivity guarantee (strongly connected)
# ----------------------------

def add_core_connectivity(
    g: Graph,
    nodes: List[str],
    core_node: str,
    default_to_core: float,
    default_from_core: float,
    overrides: Dict[str, Tuple[float, float]],
) -> None:
    """
    Makes the directed graph strongly connected by ensuring:
      node -> core and core -> node exist for all nodes.

    Weights control "distance":
      - low weight = easy/cheap
      - high weight = expensive/long

    overrides[node] = (to_core_weight, from_core_weight)
    """
    # ensure core exists
    g.add_edge(core_node, core_node, "noop", 0)

    for n in nodes:
        to_w, from_w = overrides.get(n, (default_to_core, default_from_core))
        g.add_edge(n, core_node, "route_to_core", to_w)
        g.add_edge(core_node, n, "route_from_core", from_w)


# ----------------------------
# Hard-coded demo attack graph
# ----------------------------

def build_demo_graph() -> Graph:
    g = Graph()

    # Nodes (including the 6 assets)
    assets = [
        "Finance_Database",
        "HR_Database",
        "Customer_Database",
        "Orders_Database",
        "vault:secrets",
        "Logs",
    ]

    other_nodes = [
        "attacker",
        "ws:employee_pc",
        "user:employee",
        "share:common",
        "creds:leaked",
        "srv:jumpbox",
        "srv:fileserver",
        "srv:ad",
        "user:admin",
        "web:public_site",
        "web:internal_app",
        "srv:api",
    ]

    all_nodes = other_nodes + assets

    # Realistic-ish low/medium-cost edges (these create "short" paths)
    g.add_edge("attacker", "web:public_site", "network_connect", 2)
    g.add_edge("attacker", "ws:employee_pc", "phishing_success", 1)

    g.add_edge("ws:employee_pc", "user:employee", "logon", 1)
    g.add_edge("user:employee", "share:common", "file_access", 2)
    g.add_edge("share:common", "creds:leaked", "credential_discovery", 1)

    g.add_edge("creds:leaked", "srv:jumpbox", "remote_logon", 2)
    g.add_edge("srv:jumpbox", "srv:fileserver", "network_connect", 2)

    g.add_edge("srv:fileserver", "HR_Database", "network_connect", 3)
    g.add_edge("srv:fileserver", "Finance_Database", "network_connect", 3)

    g.add_edge("web:public_site", "web:internal_app", "pivot_web", 3)
    g.add_edge("web:internal_app", "srv:api", "service_call", 1)
    g.add_edge("srv:api", "Orders_Database", "db_call", 2)
    g.add_edge("web:internal_app", "Customer_Database", "sql_access", 2)

    g.add_edge("srv:jumpbox", "srv:ad", "admin_session", 3)
    g.add_edge("srv:ad", "user:admin", "privilege_escalation", 2)

    g.add_edge("user:admin", "vault:secrets", "vault_access", 1)
    g.add_edge("vault:secrets", "Logs", "log_access", 2)
    g.add_edge("vault:secrets", "Finance_Database", "use_secrets", 1)

    # Pivot edges so “starting at an asset” can still go outward cheaply sometimes
    g.add_edge("Orders_Database", "srv:api", "db_creds_found", 2)
    g.add_edge("Customer_Database", "web:internal_app", "app_secrets_reuse", 2)
    g.add_edge("Finance_Database", "srv:fileserver", "service_account_reuse", 2)
    g.add_edge("HR_Database", "srv:fileserver", "service_account_reuse", 2)
    g.add_edge("Logs", "srv:ad", "admin_artifacts_found", 3)

    # --- Guarantee: everything reaches everything (directed strong connectivity) ---
    core = "net:core"

    # Defaults: moderate “routing” cost through the core
    default_to_core = 30
    default_from_core = 30

    # Make some nodes very expensive to route to/from (long distances)
    overrides = {
        # “high security / hard to pivot” nodes
        "vault:secrets": (250, 250),
        "Logs": (180, 180),
        "srv:ad": (120, 120),

        # “protected databases”
        "Finance_Database": (160, 160),
        "HR_Database": (110, 110),
        "Customer_Database": (90, 90),
        "Orders_Database": (70, 70),

        # attacker entry tends to be easier to reach from core than a vault (optional)
        "attacker": (30, 10),
    }

    add_core_connectivity(
        g=g,
        nodes=all_nodes + [core],  # include core too so it's part of the set
        core_node=core,
        default_to_core=default_to_core,
        default_from_core=default_from_core,
        overrides=overrides,
    )

    return g


# ----------------------------
# Interactive main
# ----------------------------

def main() -> None:
    g = build_demo_graph()

    assets = [
        "Finance_Database",
        "HR_Database",
        "Customer_Database",
        "Orders_Database",
        "vault:secrets",
        "Logs",
    ]

    print("\n=== Assets (6 places) ===")
    for i, a in enumerate(assets, start=1):
        print(f"{i}. {a}")

    print("\nEnter the 2 nodes you have in mind.")
    start = input("START node (press Enter for 'attacker'): ").strip() or "attacker"
    target = input("TARGET node (one of the assets or any node): ").strip()

    all_nodes = set(g.nodes())

    if start not in all_nodes:
        print(f"\n[!] START node '{start}' is not in the graph.")
        print("Available nodes:", ", ".join(sorted(all_nodes)))
        return

    if target not in all_nodes:
        print(f"\n[!] TARGET node '{target}' is not in the graph.")
        print("Available nodes:", ", ".join(sorted(all_nodes)))
        return

    res = dijkstra(g, start=start)
    cost = res.dist.get(target, float("inf"))
    path = rebuild_path(res.prev, start=start, target=target)

    print("\n=== Shortest Path Result (Dijkstra) ===")
    print(f"[+] Path found: {start} -> {target}")
    print(f"    Total cost: {cost:.2f}")
    print(f"    Hops      : {len(path)}")

    if path:
        print("\nSteps:")
        for i, e in enumerate(path, start=1):
            print(f"  {i:02d}. {e.src} -> {e.dst} | Result ={e.Result} | w={e.weight}")

    # Rank the 6 assets from chosen start
    print("\n=== Asset reach ranking from your START node ===")
    ranked: List[Tuple[str, float]] = []
    for a in assets:
        ranked.append((a, res.dist.get(a, float("inf"))))
    ranked.sort(key=lambda x: x[1])

    for a, c in ranked:
        print(f"  - {a}: cost={c:.2f}")


if __name__ == "__main__":
    main()