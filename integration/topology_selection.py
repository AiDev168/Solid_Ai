"""Runtime topology selection helpers.

This is a focused extraction of the useful selection behavior from Ai_Designer:
inspect the model first, then target a persistent edge index instead of guessing a
coordinate. It is deliberately independent from the old planner/agent stack.
"""
from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
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
            texts = []
            for item in content:
                text = item.get("text") if isinstance(item, Mapping) else getattr(item, "text", None)
                if isinstance(text, str):
                    texts.append(text)
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


def _xyz(value: Any) -> tuple[float, float, float] | None:
    if isinstance(value, Mapping):
        if all(isinstance(value.get(k), (int, float)) and not isinstance(value.get(k), bool) for k in ("x", "y", "z")):
            return (float(value["x"]), float(value["y"]), float(value["z"]))
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) == 3:
        if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value):
            return (float(value[0]), float(value[1]), float(value[2]))
    return None


def _point_candidates(edge: Mapping[str, Any]) -> list[tuple[float, float, float]]:
    candidates: list[tuple[float, float, float]] = []
    for key in ("point", "center", "midpoint", "centroid", "mid", "start", "end"):
        point = _xyz(edge.get(key))
        if point is not None:
            candidates.append(point)
    if all(isinstance(edge.get(k), (int, float)) and not isinstance(edge.get(k), bool) for k in ("x", "y", "z")):
        candidates.append((float(edge["x"]), float(edge["y"]), float(edge["z"])))
    for prefix in ("start", "end"):
        point = _xyz({k: edge.get(f"{prefix}_{k}") for k in ("x", "y", "z")})
        if point is not None:
            candidates.append(point)
    # Remove exact duplicates while preserving order.
    return list(dict.fromkeys(candidates))


def _edge_index(node: Mapping[str, Any]) -> int | None:
    for key in ("index", "i"):
        value = node.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            return value
    return None


def extract_edges(tool_result: Any) -> list[dict[str, Any]]:
    """Find edge records with integer indices anywhere in an analyze_model response."""
    normalized = normalize_tool_result(tool_result)
    edges: list[dict[str, Any]] = []
    for node in _walk(normalized):
        if not isinstance(node, Mapping):
            continue
        index = _edge_index(node)
        if index is not None and (_point_candidates(node) or "edge" in str(node.get("kind", "")).lower()):
            item = dict(node)
            item["index"] = index
            edges.append(item)
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
