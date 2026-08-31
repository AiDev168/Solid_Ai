from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


class ReferenceResolutionError(ValueError):
    """Raised when a semantic CAD reference cannot be resolved safely."""


@dataclass(frozen=True)
class ReferenceIntent:
    reference_id: str
    kind: str
    role: str
    feature_id: str = ""
    target_xyz: tuple[float, float, float] | None = None
    criteria: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class ReferenceEvidence:
    kind: str
    candidates: tuple[Mapping[str, Any], ...]
    state_version: int


@dataclass(frozen=True)
class ReferenceBinding:
    reference_id: str
    kind: str
    backend_index: int
    state_version: int
    evidence: Mapping[str, Any]
    score: float


@dataclass(frozen=True)
class ReferenceSetBinding:
    reference_id: str
    kind: str
    bindings: tuple[ReferenceBinding, ...]
    state_version: int


def _xyz(value: Any) -> tuple[float, float, float] | None:
    if isinstance(value, Mapping):
        if all(isinstance(value.get(k), (int, float)) and not isinstance(value.get(k), bool) for k in ("x", "y", "z")):
            return float(value["x"]), float(value["y"]), float(value["z"])
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) >= 3:
        if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value[:3]):
            return float(value[0]), float(value[1]), float(value[2])
    return None


def _index(item: Mapping[str, Any]) -> int | None:
    for key in ("backend_index", "index", "i"):
        value = item.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            return value
    return None


def _point(item: Mapping[str, Any]) -> tuple[float, float, float] | None:
    for key in ("point", "center", "centroid", "origin", "mid", "midpoint"):
        point = _xyz(item.get(key))
        if point is not None:
            return point
    return _xyz({"x": item.get("x"), "y": item.get("y"), "z": item.get("z")})


def _normal(item: Mapping[str, Any]) -> tuple[float, float, float] | None:
    return _xyz(item.get("normal"))


def _unit(v: Sequence[float]) -> tuple[float, float, float] | None:
    n = math.sqrt(sum(float(x) * float(x) for x in v))
    if n <= 1e-12:
        return None
    return tuple(float(x) / n for x in v)


def _walk(value: Any, key: str) -> list[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        direct = value.get(key)
        if isinstance(direct, Sequence) and not isinstance(direct, (str, bytes)):
            return [item for item in direct if isinstance(item, Mapping)]
        data = value.get("data")
        if isinstance(data, Mapping) and data is not value:
            return _walk(data, key)
    return []


def _normalize_candidates(raw: Sequence[Mapping[str, Any]], kind: str, state_version: int) -> ReferenceEvidence:
    candidates: list[Mapping[str, Any]] = []
    seen: set[int] = set()
    for item in raw:
        idx = _index(item)
        if idx is None or idx in seen:
            continue
        normalized = dict(item)
        original_kind = normalized.get("kind")
        normalized["backend_index"] = idx
        normalized["kind"] = kind
        if kind == "face" and "surface_kind" not in normalized and original_kind not in {None, "face"}:
            normalized["surface_kind"] = str(original_kind)
        candidates.append(normalized)
        seen.add(idx)
    if not candidates:
        raise ReferenceResolutionError(f"SolidPilot {kind} analysis contained no indexed {kind}s")
    return ReferenceEvidence(kind, tuple(candidates), state_version)


def face_evidence(result: Mapping[str, Any], state_version: int) -> ReferenceEvidence:
    return _normalize_candidates(_walk(result, "faces"), "face", state_version)


def edge_evidence(result: Mapping[str, Any], state_version: int) -> ReferenceEvidence:
    return _normalize_candidates(_walk(result, "edges"), "edge", state_version)


def _score_face(intent: ReferenceIntent, candidate: Mapping[str, Any]) -> float | None:
    if intent.role not in {"top_planar", "planar_at_point"}:
        return None
    if candidate.get("planar") is False:
        return None
    if candidate.get("surface_kind") not in {None, "plane", "planar", "planarface", "plane_surface"} and _normal(candidate) is None:
        return None
    normal = _unit(_normal(candidate) or ())
    if intent.role == "top_planar":
        if normal is not None and normal[2] < 0.999999:
            return None
        point = _point(candidate)
        return -point[2] if point is not None else 0.0
    point = _point(candidate)
    if point is None or intent.target_xyz is None:
        return None
    if normal is not None and abs(normal[2]) < 0.999999:
        return None
    return math.dist(point, intent.target_xyz)


def _in_bounds(point: tuple[float, float, float], bounds: Sequence[float] | None, tolerance: float = 1e-8) -> bool:
    if not bounds or len(bounds) != 4:
        return True
    xmin, xmax, ymin, ymax = map(float, bounds)
    return xmin - tolerance <= point[0] <= xmax + tolerance and ymin - tolerance <= point[1] <= ymax + tolerance


def _score_edge(intent: ReferenceIntent, candidate: Mapping[str, Any]) -> float | None:
    start = _xyz(candidate.get("start"))
    end = _xyz(candidate.get("end"))
    if start is None or end is None:
        return None
    dx = abs(end[0] - start[0])
    dy = abs(end[1] - start[1])
    dz = abs(end[2] - start[2])
    if intent.role in {"outer_vertical", "all_outer_vertical"}:
        if dz <= max(dx, dy) or dz <= 1e-9:
            return None
        midpoint = _point(candidate)
        if midpoint is None or not _in_bounds(midpoint, (intent.criteria or {}).get("outer_bounds_m")):
            return None
        if intent.role == "outer_vertical":
            if intent.target_xyz is None:
                return 0.0
            return math.dist(midpoint, intent.target_xyz)
        return 0.0
    if intent.role == "nearest":
        point = _point(candidate)
        if point is None or intent.target_xyz is None:
            return None
        return math.dist(point, intent.target_xyz)
    return None


def resolve_reference(intent: ReferenceIntent, evidence: ReferenceEvidence) -> ReferenceBinding:
    if intent.role == "all_outer_vertical":
        raise ReferenceResolutionError("all_outer_vertical is set-valued; use resolve_reference_set")
    if intent.kind != evidence.kind:
        raise ReferenceResolutionError(f"reference kind mismatch: requested {intent.kind}, evidence {evidence.kind}")
    scored: list[tuple[float, Mapping[str, Any]]] = []
    for candidate in evidence.candidates:
        score = _score_face(intent, candidate) if evidence.kind == "face" else _score_edge(intent, candidate)
        if score is not None:
            scored.append((score, candidate))
    if not scored:
        raise ReferenceResolutionError(f"no candidate satisfies reference role={intent.role} kind={intent.kind}")
    scored.sort(key=lambda item: (item[0], _index(item[1]) if _index(item[1]) is not None else float("inf")))
    best_score, best = scored[0]
    best_index = _index(best)
    if best_index is None:
        raise ReferenceResolutionError(f"candidate for reference {intent.reference_id} has no backend index")
    if len(scored) > 1 and abs(scored[1][0] - best_score) <= 1e-9:
        raise ReferenceResolutionError(f"ambiguous reference {intent.reference_id}: multiple candidates have equal score")
    return ReferenceBinding(intent.reference_id, evidence.kind, best_index, evidence.state_version, dict(best), best_score)


def resolve_reference_set(intent: ReferenceIntent, evidence: ReferenceEvidence) -> ReferenceSetBinding:
    if intent.kind != evidence.kind:
        raise ReferenceResolutionError(f"reference kind mismatch: requested {intent.kind}, evidence {evidence.kind}")
    scored: list[tuple[float, Mapping[str, Any]]] = []
    for candidate in evidence.candidates:
        score = _score_face(intent, candidate) if evidence.kind == "face" else _score_edge(intent, candidate)
        if score is not None:
            scored.append((score, candidate))
    if not scored:
        raise ReferenceResolutionError(f"no candidates satisfy reference role={intent.role} kind={intent.kind}")
    scored.sort(key=lambda item: _index(item[1]) if _index(item[1]) is not None else float("inf"))
    return ReferenceSetBinding(
        intent.reference_id,
        evidence.kind,
        tuple(ReferenceBinding(intent.reference_id, evidence.kind, _index(candidate), evidence.state_version, dict(candidate), score) for score, candidate in scored),
        evidence.state_version,
    )


def face_index_json(binding: ReferenceBinding) -> int:
    if binding.kind != "face":
        raise ReferenceResolutionError("binding is not a face")
    return binding.backend_index


def edge_indices_json(binding: ReferenceBinding | ReferenceSetBinding) -> str:
    if isinstance(binding, ReferenceSetBinding):
        if binding.kind != "edge" or not binding.bindings:
            raise ReferenceResolutionError("binding set is not a non-empty edge set")
        indices = [item.backend_index for item in binding.bindings]
    else:
        if binding.kind != "edge":
            raise ReferenceResolutionError("binding is not an edge")
        indices = [binding.backend_index]
    return json.dumps(indices, separators=(",", ":"))


__all__ = [
    "ReferenceBinding", "ReferenceEvidence", "ReferenceIntent", "ReferenceResolutionError",
    "ReferenceSetBinding", "edge_evidence", "edge_indices_json", "face_evidence",
    "face_index_json", "resolve_reference", "resolve_reference_set",
]
