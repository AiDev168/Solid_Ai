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
        if all(
            isinstance(value.get(k), (int, float))
            and not isinstance(value.get(k), bool)
            for k in ("x", "y", "z")
        ):
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


def _is_planar_face(item: Mapping[str, Any]) -> bool:
    if item.get("planar") is True:
        return True
    kind = str(item.get("surface_kind", item.get("kind", ""))).lower()
    if kind in {"plane", "planar", "planarface", "plane_surface"}:
        return True
    return _normal(item) is not None


def _walk_faces(value: Any) -> list[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        faces = value.get("faces")
        if isinstance(faces, Sequence) and not isinstance(faces, (str, bytes)):
            return [item for item in faces if isinstance(item, Mapping)]
        data = value.get("data")
        if isinstance(data, Mapping) and data is not value:
            return _walk_faces(data)
    return []


def _walk_edges(value: Any) -> list[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        edges = value.get("edges")
        if isinstance(edges, Sequence) and not isinstance(edges, (str, bytes)):
            return [item for item in edges if isinstance(item, Mapping)]
        data = value.get("data")
        if isinstance(data, Mapping) and data is not value:
            return _walk_edges(data)
    return []


def _normalize_candidates(raw: Sequence[Mapping[str, Any]], kind: str) -> ReferenceEvidence:
    candidates: list[Mapping[str, Any]] = []
    seen: set[int] = set()
    for item in raw:
        idx = _index(item)
        if idx is None or idx in seen:
            continue
        normalized = dict(item)
        normalized["backend_index"] = idx
        normalized["kind"] = kind
        candidates.append(normalized)
        seen.add(idx)
    if not candidates:
        raise ReferenceResolutionError(f"SolidPilot {kind} analysis contained no indexed {kind}s")
    return ReferenceEvidence(kind, tuple(candidates), 0)


def face_evidence(result: Mapping[str, Any], state_version: int) -> ReferenceEvidence:
    evidence = _normalize_candidates(_walk_faces(result), "face")
    return ReferenceEvidence(evidence.kind, evidence.candidates, state_version)


def edge_evidence(result: Mapping[str, Any], state_version: int) -> ReferenceEvidence:
    evidence = _normalize_candidates(_walk_edges(result), "edge")
    return ReferenceEvidence(evidence.kind, evidence.candidates, state_version)


def _score_face(intent: ReferenceIntent, candidate: Mapping[str, Any]) -> float | None:
    if intent.role in {"top_planar", "planar_at_point"} and not _is_planar_face(candidate):
        return None
    normal = _unit(_normal(candidate) or ())
    if intent.role == "top_planar":
        if normal is not None and normal[2] < 0.999999:
            return None
        point = _point(candidate)
        return -point[2] if point is not None else 0.0
    if intent.role == "planar_at_point":
        point = _point(candidate)
        if point is None or intent.target_xyz is None:
            return None
        if normal is not None and abs(normal[2]) < 0.999999:
            return None
        return math.dist(point, intent.target_xyz)
    return None


def _score_edge(intent: ReferenceIntent, candidate: Mapping[str, Any]) -> float | None:
    if intent.role == "nearest":
        point = _point(candidate)
        if point is None or intent.target_xyz is None:
            return None
        return math.dist(point, intent.target_xyz)
    if intent.role in {"outer_vertical", "all_outer_vertical"}:
        start = _xyz(candidate.get("start"))
        end = _xyz(candidate.get("end"))
        if start is None or end is None:
            return None
        dx = abs(end[0] - start[0])
        dy = abs(end[1] - start[1])
        dz = abs(end[2] - start[2])
        if dz <= max(dx, dy) or dz <= 1e-9:
            return None
        if intent.role == "outer_vertical":
            point = _point(candidate)
            if point is None or intent.target_xyz is None:
                return None
            return math.dist(point, intent.target_xyz)
        return 0.0
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
    scored.sort(key=lambda item: (item[0], int(item[1]["backend_index"])))
    best_score, best = scored[0]
    if len(scored) > 1 and abs(scored[1][0] - best_score) <= 1e-9:
        raise ReferenceResolutionError(f"ambiguous reference {intent.reference_id}: multiple candidates have equal score")
    return ReferenceBinding(intent.reference_id, evidence.kind, int(best["backend_index"]), evidence.state_version, dict(best), best_score)


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
    scored.sort(key=lambda item: int(item[1]["backend_index"]))
    bindings = tuple(
        ReferenceBinding(intent.reference_id, evidence.kind, int(candidate["backend_index"]), evidence.state_version, dict(candidate), score)
        for score, candidate in scored
    )
    return ReferenceSetBinding(intent.reference_id, evidence.kind, bindings, evidence.state_version)


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
