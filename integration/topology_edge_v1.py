from __future__ import annotations

from typing import Any, Mapping


def edge_backend_index(edge: Mapping[str, Any]) -> int | None:
    for key in ("i", "index", "backend_index"):
        value = edge.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
    return None


def edge_length(edge: Mapping[str, Any]) -> float | None:
    value = edge.get("length")
    if isinstance(value, (int, float)) and float(value) > 1e-12:
        return float(value)
    start = edge.get("start")
    end = edge.get("end")
    if isinstance(start, (list, tuple)) and isinstance(end, (list, tuple)) and len(start) >= 3 and len(end) >= 3:
        length2 = sum((float(end[i]) - float(start[i])) ** 2 for i in range(3))
        if length2 > 1e-12:
            return length2 ** 0.5
    return None


def is_usable_edge(edge: Mapping[str, Any]) -> bool:
    """Return True for straight or analytic/curved edges with real measured length.

    For circular edges SolidWorks may report identical start/end points because
    those fields are representative points rather than curve endpoints. In that
    case the authoritative evidence is the positive ``length`` field.
    """
    return edge_backend_index(edge) is not None and edge_length(edge) is not None


def select_longest_usable_edge(edges: list[Mapping[str, Any]]) -> tuple[int, float]:
    candidates = [(edge_backend_index(edge), edge_length(edge)) for edge in edges if is_usable_edge(edge)]
    candidates = [(index, length) for index, length in candidates if index is not None and length is not None]
    if not candidates:
        raise ValueError("NO_USABLE_EDGE_EVIDENCE")
    index, length = max(candidates, key=lambda pair: pair[1])
    return index, length


__all__ = ["edge_backend_index", "edge_length", "is_usable_edge", "select_longest_usable_edge"]
