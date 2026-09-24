#!/usr/bin/env python3
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class GameplayEdge:
    a: str
    b: str
    bidirectional: bool = True
    requires: tuple[str, ...] = ()
    enabled: bool = True


def _normalize_edges(raw_edges: Iterable[dict[str, Any] | GameplayEdge]) -> list[GameplayEdge]:
    edges: list[GameplayEdge] = []
    for raw in raw_edges:
        if isinstance(raw, GameplayEdge):
            edge = raw
        else:
            edge = GameplayEdge(
                a=str(raw["a"]),
                b=str(raw["b"]),
                bidirectional=bool(raw.get("bidirectional", True)),
                requires=tuple(str(x) for x in raw.get("requires", []) or []),
                enabled=bool(raw.get("enabled", True)),
            )
        if not edge.a or not edge.b:
            raise ValueError("gameplay edge endpoints must not be empty")
        edges.append(edge)
    return edges


def _usable(edge: GameplayEdge, tokens: set[str]) -> bool:
    return edge.enabled and set(edge.requires).issubset(tokens)


def _adjacency(
    nodes: set[str],
    edges: list[GameplayEdge],
    tokens: set[str],
) -> dict[str, set[str]]:
    adj = {node: set() for node in nodes}
    for edge in edges:
        if edge.a not in nodes or edge.b not in nodes:
            raise ValueError(f"edge references unknown node: {edge.a}->{edge.b}")
        if not _usable(edge, tokens):
            continue
        adj[edge.a].add(edge.b)
        if edge.bidirectional:
            adj[edge.b].add(edge.a)
    return adj


def _reachable(start: str, adj: dict[str, set[str]]) -> set[str]:
    if start not in adj:
        raise ValueError(f"unknown start node: {start}")
    seen = {start}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for nxt in adj[node]:
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return seen


def _undirected_adjacency(
    nodes: set[str],
    edges: list[GameplayEdge],
    tokens: set[str],
) -> dict[str, set[str]]:
    adj = {node: set() for node in nodes}
    for edge in edges:
        if not _usable(edge, tokens):
            continue
        adj[edge.a].add(edge.b)
        adj[edge.b].add(edge.a)
    return adj


def _articulation_points(adj: dict[str, set[str]]) -> set[str]:
    time = 0
    discovery: dict[str, int] = {}
    low: dict[str, int] = {}
    parent: dict[str, str | None] = {}
    points: set[str] = set()

    def dfs(node: str) -> None:
        nonlocal time
        discovery[node] = low[node] = time
        time += 1
        children = 0

        for nxt in adj[node]:
            if nxt not in discovery:
                parent[nxt] = node
                children += 1
                dfs(nxt)
                low[node] = min(low[node], low[nxt])

                if parent.get(node) is None and children > 1:
                    points.add(node)
                if parent.get(node) is not None and low[nxt] >= discovery[node]:
                    points.add(node)
            elif nxt != parent.get(node):
                low[node] = min(low[node], discovery[nxt])

    for node in adj:
        if node not in discovery:
            parent[node] = None
            dfs(node)
    return points


def _component_count(adj: dict[str, set[str]]) -> int:
    unseen = set(adj)
    count = 0
    while unseen:
        count += 1
        seed = next(iter(unseen))
        reached = _reachable(seed, adj)
        unseen -= reached
    return count


def evaluate_gameplay_graph(
    *,
    nodes: Iterable[str],
    edges: Iterable[dict[str, Any] | GameplayEdge],
    start: str,
    required_nodes: Iterable[str] = (),
    terminal_nodes: Iterable[str] = (),
    available_tokens: Iterable[str] = (),
) -> dict[str, Any]:
    node_set = {str(node) for node in nodes}
    if not node_set:
        raise ValueError("gameplay graph requires at least one node")
    if len(node_set) != len(list(nodes)) if not isinstance(nodes, set) else False:
        # Retained for callers that provide a concrete sequence with duplicates.
        pass

    normalized = _normalize_edges(edges)
    tokens = {str(token) for token in available_tokens}
    required = {str(node) for node in required_nodes}
    terminals = {str(node) for node in terminal_nodes}
    unknown_required = (required | terminals | {start}) - node_set
    if unknown_required:
        raise ValueError("unknown gameplay graph nodes: " + ", ".join(sorted(unknown_required)))

    directed = _adjacency(node_set, normalized, tokens)
    undirected = _undirected_adjacency(node_set, normalized, tokens)
    reached = _reachable(start, directed)
    unreachable_required = sorted(required - reached)

    reachable_subgraph = reached
    dead_ends = sorted(
        node
        for node in reachable_subgraph
        if node != start and not directed[node] and node not in terminals
    )
    low_degree = sorted(
        node
        for node in reachable_subgraph
        if len(undirected[node]) <= 1 and node not in terminals and node != start
    )

    active_undirected_edges = {
        tuple(sorted((edge.a, edge.b)))
        for edge in normalized
        if _usable(edge, tokens)
    }
    components = _component_count(undirected)
    cycle_rank = max(0, len(active_undirected_edges) - len(node_set) + components)
    articulation = sorted(_articulation_points(undirected))

    locked_edges = [
        {
            "a": edge.a,
            "b": edge.b,
            "requires": list(edge.requires),
        }
        for edge in normalized
        if edge.enabled and not _usable(edge, tokens)
    ]

    failures: list[str] = []
    if unreachable_required:
        failures.append("required_nodes_unreachable")
    if dead_ends:
        failures.append("unintended_directed_dead_ends")
    if start not in reached:
        failures.append("start_invalid")

    return {
        "schema": 1,
        "node_count": len(node_set),
        "edge_count": len(normalized),
        "reachable_count": len(reached),
        "reachable_nodes": sorted(reached),
        "unreachable_required_nodes": unreachable_required,
        "dead_ends": dead_ends,
        "low_degree_nodes": low_degree,
        "articulation_points": articulation,
        "cycle_rank": cycle_rank,
        "has_loop": cycle_rank > 0,
        "locked_edges": locked_edges,
        "available_tokens": sorted(tokens),
        "pass": not failures,
        "failures": failures,
        "metrics": {
            "reachable_fraction": round(len(reached) / len(node_set), 6),
            "cycle_rank": cycle_rank,
            "articulation_point_count": len(articulation),
            "dead_end_count": len(dead_ends),
            "locked_edge_count": len(locked_edges),
        },
    }
