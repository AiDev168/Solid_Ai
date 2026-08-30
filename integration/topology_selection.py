"""Runtime topology selection helpers.

This is a focused extraction of the useful selection behavior from Ai_Designer:
inspect the model first, then target a persistent edge index instead of guessing a
coordinate. It is deliberately independent from the old planner/agent stack.
"""
from __future__ import annotations

import json
import math
from collections.abc import Mapping
from typing import Any


def _walk(value: Any):
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _walk(child)


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        return value
    if hasattr(value, "model_dump"):
        try:
            dumped = value.model_dump(mode="json")
            return dumped if isinstance(dumped, Mapping) else None
        except Exception:
            return None
    if hasattr(value, "__dict__"):
        raw = getattr(value, "__dict__", None)
        return raw if isinstance(raw, Mapping) else None
    return None


def normalize_tool_result(value: Any) -> Any:
    """Convert MCP result content/structuredContent into Python data when possible."""
    mapping = _as_mapping(value)
    if mapping is not None:
        structured = mapping.get("structuredContent")
        if structured is not None:
            return normalize_tool_result(structured)
        content = mapping.get("content")
        if isinstance(content, list):
            texts = [item.get("text") for item in content if isinstance(item, Mapping) and isinstance(item.get("text"), str)]
            for text in texts:
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    continue
        result = mapping.get("result")
        if result is not None:
            return normalize_tool_result(result)
        return dict(mapping)
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _point_candidates(edge: Mapping[str, Any]) -> list[tuple[float, float, float]]:
    candidates: list[tuple[float, float, float]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and all(isinstance(value.get(k), (int, float)) for k in ("x", "y", "z")):
            candidates.append((float(value["x"]), float(value["y"]), float(value["z"])))

    for key in ("point", "center", "midpoint", "centroid", "start", "end"):
        add(edge.get(key))

    if all(isinstance(edge.get(k), (int, float)) for k in ("x", "y", "z")):
        candidates.append((float(edge["x"]), float(edge["y"]), float(edge["z"])))

    for prefix in ("start", "end"):
        if all(isinstance(edge.get(f"{prefix}_{k}"), (int, float)) for k in ("x", "y", "z")):
            candidates.append(tuple(float(edge[f"{prefix}_{k}"]) for k in ("x", "y", "z")))
    return candidates


def extract_edges(tool_result: Any) -> list[dict[str, Any]]:
    """Find edge records with integer indices anywhere in an analyze_model response."""
    normalized = normalize_tool_result(tool_result)
    edges: list[dict[str, Any]] = []
    for node in _walk(normalized):
        if not isinstance(node, Mapping):
            continue
        index = node.get("index")
        if isinstance(index, int) and index >= 0:
            kind = str(node.get("kind") or node.get("type") or node.get("entity_type") or "").lower()
            if "edge" in kind or _point_candidates(node):
                edges.append(dict(node))
    # Deduplicate by index while preserving first occurrence.
    result: dict[int, dict[str, Any]] = {}
    for edge in edges:
        result.setdefault(int(edge["index"]), edge)
    return list(result.values())


def select_nearest_edge_index(tool_result: Any, target_xyz: tuple[float, float, float]) -> int:
    edges = extract_edges(tool_result)
    if not edges:
        raise ValueError("analyze_model response contained no indexed edges")
    tx, ty, tz = target_xyz
    best: tuple[float, int] | None = None
    for edge in edges:
        points = _point_candidates(edge)
        if not points:
            continue
        distance = min((px - tx) ** 2 + (py - ty) ** 2 + (pz - tz) ** 2 for px, py, pz in points)
        candidate = (distance, int(edge["index"]))
        if best is None or candidate < best:
            best = candidate
    if best is None:
        raise ValueError("indexed edges were found but none exposed coordinates")
    return best[1]


def edge_indices_json(*indices: int) -> str:
    if not indices:
        raise ValueError("at least one edge index is required")
    if any(index < 0 for index in indices):
        raise ValueError("edge indices must be non-negative")
    return json.dumps(list(indices), separators=(",", ":"))
