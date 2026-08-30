from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


class ReferenceResolutionError(ValueError):
    pass


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


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(float(x) * float(y) for x, y in zip(a, b))


def _is_planar_face(item: Mapping[str, Any]) -> bool:
    if item.get("planar") is True:
        return True
    kind = str(item.get("surface_kind", item.get("kind", ""))).lower()
    return kind in {"plane", "planar", "planarface", "plane_surface"}


def _walk_faces(value: Any) -> list[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        faces = value.get("faces")
        if isinstance(faces, Sequence) and not isinstance(faces, (str, bytes)):
            return [item for item in faces if isinstance(item, Mapping)]
        data = value.get("data")
        if data is not value:
            return _walk_faces(data)
    return []


def _walk_edges(value: Any) -> list[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        edges = value.get("edges")
        if isinstance(edges, Sequence) and not isinstance(edges, (str, bytes)):
            return [item for item in edges if isinstance(item, Mapping)]
        data = value.get("data")
        if data is not value:
            return _walk_edges(data)
    return []


def face_evidence(result: Mapping[str, Any], state_version: int) -> ReferenceEvidence:
    faces = _walk_faces(result)
    candidates: list[Mapping[str, Any]] = []
    for raw in faces:
        idx = _index(raw)
        if idx is None:
            continue
        item = dict(raw)
        item["backend_index"] = idx
        candidates.append(item)
    if not candidates:
        raise ReferenceResolutionError("SolidPilot face analysis contained no indexed faces")
    return ReferenceEvidence("face", tuple(candidates), state_version)


def edge_evidence(result: Mapping[str, Any], state_version: int) -> ReferenceEvidence:
    edges = _walk_edges(result)
    candidates: list[Mapping[str, Any]] = []
    for raw in edges:
        idx = _index(raw)
        if idx is None:
            continue
        item = dict(raw)
        item["backend_index"] = idx
        candidates.append(item)
    if not candidates:
        raise ReferenceResolutionError("SolidPilot edge analysis contained no indexed edges")
    return ReferenceEvidence("edge", tuple(candidates), state_version)


def _score_face(intent: ReferenceIntent, candidate: Mapping[str, Any]) -> float | None:
    if candidate.get("kind") == "edge":
        return None
    if intent.role == "top_planar":
        if not _is_planar_face(candidate):
            return None
        normal = _unit(_normal(candidate) or ())
        if normal is not None and abs(normal[2]) < 0.999999:
            return None
        point = _point(candidate)
        if point is None:
            return 0.0
        return -point[2]
    if intent.role == "planar_at_point":
        if not _is_planar_face(candidate):
            return None
        point = _point(candidate)
        target = intent.target_xyz
        if point is None or target is None:
            return None
        return math.dist(point, target)
    return None


def _score_edge(intent: ReferenceIntent, candidate: Mapping[str, Any]) -> float | None:
    if intent.role == "nearest":
        point = _point(candidate)
        target = intent.target_xyz
        if point is None or target is None:
            return None
        return math.dist(point, target)
    if intent.role == "outer_vertical":
        start = _xyz(candidate.get("start"))
        end = _xyz(candidate.get("end"))
        if start is None or end is None:
            return None
        dx = abs(end[0] - start[0])
        dy = abs(end[1] - start[1])
        dz = abs(end[2] - start[2])
        if dz <= max(dx, dy) or dz < 1e-9:
            return None
        point = _point(candidate)
        target = intent.target_xyz or (0.0, 0.0, 0.0)
        return math.dist(point, target) if point is not None else float("inf")
    return None


def resolve_reference(intent: ReferenceIntent, evidence: ReferenceEvidence) -> ReferenceBinding:
    if intent.kind != evidence.kind:
        raise ReferenceResolutionError(
            f"reference kind mismatch: requested {intent.kind}, evidence {evidence.kind}"
        )
    scored: list[tuple[float, Mapping[str, Any]]] = []
    for candidate in evidence.candidates:
        score = _score_face(intent, candidate) if evidence.kind == "face" else _score_edge(intent, candidate)
        if score is not None:
            scored.append((score, candidate))
    if not scored:
        raise ReferenceResolutionError(
            f"no candidate satisfies reference role={intent.role} kind={intent.kind}"
        )
    scored.sort(key=lambda item: (item[0], int(item[1]["backend_index"])))
    best_score, best = scored[0]
    if len(scored) > 1 and abs(scored[1][0] - best_score) <= 1e-9:
        raise ReferenceResolutionError(
            f"ambiguous reference {intent.reference_id}: multiple candidates have equal score"
        )
    return ReferenceBinding(
        intent.reference_id,
        evidence.kind,
        int(best["backend_index"]),
        evidence.state_version,
        dict(best),
        best_score,
    )


def face_index_json(binding: ReferenceBinding) -> int:
    if binding.kind != "face":
        raise ReferenceResolutionError("binding is not a face")
    return binding.backend_index


def edge_indices_json(binding: ReferenceBinding) -> str:
    if binding.kind != "edge":
        raise ReferenceResolutionError("binding is not an edge")
    return json.dumps([binding.backend_index], separators=(",", ":"))


__all__ = [
    "ReferenceBinding",
    "ReferenceEvidence",
    "ReferenceIntent",
    "ReferenceResolutionError",
    "edge_evidence",
    "edge_indices_json",
    "face_evidence",
    "face_index_json",
    "resolve_reference",
]
