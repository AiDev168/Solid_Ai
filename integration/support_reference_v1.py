from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


class SupportReferenceError(ValueError):
    """Raised when a feature support reference cannot be resolved safely."""


@dataclass(frozen=True)
class SketchFrame:
    origin: tuple[float, float, float]
    xdir: tuple[float, float, float]
    ydir: tuple[float, float, float]
    normal: tuple[float, float, float]


def _vec(value: Any) -> tuple[float, float, float] | None:
    if isinstance(value, Mapping):
        values = (value.get("x"), value.get("y"), value.get("z"))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) >= 3:
        values = value[:3]
    else:
        return None
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
        return None
    return float(values[0]), float(values[1]), float(values[2])


def _unit(value: Sequence[float]) -> tuple[float, float, float]:
    norm = math.sqrt(sum(float(v) ** 2 for v in value))
    if norm <= 1e-12:
        raise SupportReferenceError("zero-length direction vector")
    return tuple(float(v) / norm for v in value)


def _cross(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(float(a[i]) * float(b[i]) for i in range(3))


def _distance(a: Sequence[float], b: Sequence[float]) -> float:
    return math.sqrt(sum((float(a[i]) - float(b[i])) ** 2 for i in range(3)))


def frame_from_sketch_result(result: Mapping[str, Any]) -> SketchFrame:
    geometry = result.get("result_geometry")
    frame = geometry.get("frame") if isinstance(geometry, Mapping) else None
    if not isinstance(frame, Mapping):
        raise SupportReferenceError("sketch result contains no frame")
    origin = _vec(frame.get("origin"))
    xdir = _vec(frame.get("xdir"))
    ydir = _vec(frame.get("ydir"))
    if origin is None or xdir is None or ydir is None:
        raise SupportReferenceError("sketch frame requires origin, xdir and ydir")
    ux, uy = _unit(xdir), _unit(ydir)
    normal = _unit(_cross(ux, uy))
    return SketchFrame(origin, ux, uy, normal)


def expected_extrude_end(frame: SketchFrame, depth_m: float) -> tuple[float, float, float]:
    if depth_m <= 0:
        raise SupportReferenceError("extrusion depth must be > 0")
    return tuple(frame.origin[i] + frame.normal[i] * depth_m for i in range(3))


def _candidate_point(candidate: Mapping[str, Any]) -> tuple[float, float, float] | None:
    for key in ("point", "origin", "centroid"):
        point = _vec(candidate.get(key))
        if point is not None:
            return point
    return None


def _candidate_normal(candidate: Mapping[str, Any]) -> tuple[float, float, float] | None:
    value = _vec(candidate.get("normal"))
    return _unit(value) if value is not None else None


def _candidate_index(candidate: Mapping[str, Any]) -> int:
    index = candidate.get("backend_index", candidate.get("i"))
    if not isinstance(index, int) or index < 0:
        raise SupportReferenceError("candidate has no integer backend index")
    return index


def resolve_extrude_end_face(
    candidates: Sequence[Mapping[str, Any]],
    *,
    frame: SketchFrame,
    depth_m: float,
    reference_id: str,
    state_version: int,
    tolerance_m: float = 1e-6,
    angular_tolerance: float = 1e-6,
    ambiguity_factor: float = 1.25,
) -> dict[str, Any]:
    """Resolve an extrusion end face independently of sketch-frame orientation.

    SolidWorks can report a sketch frame normal opposite to the physical
    direction used by the extrusion operation. We therefore evaluate both
    physically possible end planes (forward and reverse along the frame
    normal), while requiring each candidate face normal to agree with the
    corresponding plane direction. Ambiguity remains fail-closed.
    """
    if ambiguity_factor < 1.0:
        raise SupportReferenceError("ambiguity_factor must be >= 1")

    directions = (
        (frame.normal, 1.0),
        (tuple(-value for value in frame.normal), -1.0),
    )
    matches: list[tuple[float, Mapping[str, Any], float, int]] = []
    near_candidates: list[tuple[float, Mapping[str, Any], int]] = []

    for direction, sign in directions:
        expected_point = tuple(
            frame.origin[i] + direction[i] * depth_m for i in range(3)
        )
        for candidate in candidates:
            if candidate.get("planar") is False:
                continue
            point = _candidate_point(candidate)
            normal = _candidate_normal(candidate)
            if point is None or normal is None:
                continue

            angular = 1.0 - _dot(normal, direction)
            if angular > angular_tolerance:
                continue

            point_distance = _distance(point, expected_point)
            if point_distance <= tolerance_m:
                score = (
                    point_distance / max(tolerance_m, 1e-12)
                    + angular / max(angular_tolerance, 1e-12)
                )
                matches.append((score, candidate, point_distance, int(sign)))
            elif point_distance <= tolerance_m * ambiguity_factor:
                near_candidates.append((point_distance, candidate, int(sign)))

    if not matches:
        expected_forward = tuple(
            frame.origin[i] + frame.normal[i] * depth_m for i in range(3)
        )
        expected_reverse = tuple(
            frame.origin[i] - frame.normal[i] * depth_m for i in range(3)
        )
        raise SupportReferenceError(
            f"no extrusion-end face matches {reference_id}; "
            f"expected either point={expected_forward} or point={expected_reverse}, "
            f"frame.normal={frame.normal}"
        )

    matches.sort(key=lambda item: (item[0], _candidate_index(item[1]), item[3]))
    best_score, best, best_distance, chosen_sign = matches[0]

    if len(matches) > 1:
        second = matches[1]
        if (
            _candidate_index(second[1]) == _candidate_index(best)
            or abs(second[2] - best_distance) <= tolerance_m * 0.25
        ):
            raise SupportReferenceError(
                f"ambiguous extrusion-end face for reference {reference_id}: "
                "multiple accepted candidates are too close to distinguish safely"
            )

    for _, candidate, _sign in near_candidates:
        candidate_distance = min(
            _distance(
                _candidate_point(candidate) or frame.origin,
                tuple(frame.origin[i] + direction[i] * depth_m for i in range(3)),
            )
            for direction, _direction_sign in directions
        )
        if candidate_distance <= tolerance_m * ambiguity_factor:
            raise SupportReferenceError(
                f"ambiguous extrusion-end face for reference {reference_id}: "
                f"candidate {_candidate_index(candidate)} is inside ambiguity halo"
            )

    candidate = dict(best)
    candidate["backend_index"] = _candidate_index(candidate)
    expected_point = tuple(
        frame.origin[i] + (frame.normal[i] if chosen_sign == 1 else -frame.normal[i]) * depth_m
        for i in range(3)
    )
    expected_normal = tuple(
        frame.normal[i] if chosen_sign == 1 else -frame.normal[i] for i in range(3)
    )

    return {
        "reference_id": reference_id,
        "kind": "face",
        "role": "extrude_end_face",
        "backend_index": candidate["backend_index"],
        "state_version": state_version,
        "expected_point": expected_point,
        "expected_normal": expected_normal,
        "orientation_sign": chosen_sign,
        "evidence": candidate,
        "score": best_score,
    }


def _project(point: Sequence[float], frame: SketchFrame) -> tuple[float, float, float]:
    delta = tuple(float(point[i]) - frame.origin[i] for i in range(3))
    return _dot(delta, frame.xdir), _dot(delta, frame.ydir), _dot(delta, frame.normal)


def resolve_extrusion_boundary_edges(
    candidates: Sequence[Mapping[str, Any]],
    *,
    frame: SketchFrame,
    bounds_uv: tuple[float, float, float, float],
    reference_id: str,
    state_version: int,
    boundary_tolerance_m: float = 1e-7,
    parallel_tolerance: float = 1e-6,
) -> tuple[dict[str, Any], ...]:
    """Resolve edges parallel to the extrusion axis on the source-profile boundary."""
    umin, umax, vmin, vmax = bounds_uv
    result: list[dict[str, Any]] = []
    for raw in candidates:
        start = _vec(raw.get("start"))
        end = _vec(raw.get("end"))
        if start is None or end is None:
            continue

        delta = tuple(end[i] - start[i] for i in range(3))
        length = math.sqrt(sum(float(v) ** 2 for v in delta))
        if length <= 1e-12:
            continue

        direction = tuple(float(v) / length for v in delta)
        parallel_error = 1.0 - abs(_dot(direction, frame.normal))
        if parallel_error > parallel_tolerance:
            continue

        mid = tuple((start[i] + end[i]) / 2.0 for i in range(3))
        u, v, _ = _project(mid, frame)
        on_boundary = (
            abs(u - umin) <= boundary_tolerance_m
            or abs(u - umax) <= boundary_tolerance_m
            or abs(v - vmin) <= boundary_tolerance_m
            or abs(v - vmax) <= boundary_tolerance_m
        )
        if not on_boundary:
            continue

        item = dict(raw)
        item["backend_index"] = _candidate_index(item)
        item["uv"] = (u, v)
        item["reference_id"] = reference_id
        item["state_version"] = state_version
        result.append(item)

    result.sort(key=lambda item: item["backend_index"])
    if not result:
        raise SupportReferenceError(
            f"no extrusion-boundary edges match {reference_id}"
        )
    return tuple(result)


__all__ = [
    "SketchFrame",
    "SupportReferenceError",
    "expected_extrude_end",
    "frame_from_sketch_result",
    "resolve_extrude_end_face",
    "resolve_extrusion_boundary_edges",
]
