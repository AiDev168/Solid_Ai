from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Any, Mapping, Sequence


class RevolveReferenceError(ValueError):
    pass


@dataclass(frozen=True)
class SketchSegment:
    x1: float
    y1: float
    x2: float
    y2: float
    construction: bool = False

    @property
    def midpoint(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    @property
    def length(self) -> float:
        return hypot(self.x2 - self.x1, self.y2 - self.y1)


def _segments_from_profile(profile: Sequence[Mapping[str, Any]]) -> tuple[SketchSegment, ...]:
    result: list[SketchSegment] = []
    for raw in profile:
        if not all(key in raw for key in ("x1", "y1", "x2", "y2")):
            continue
        result.append(
            SketchSegment(
                float(raw["x1"]),
                float(raw["y1"]),
                float(raw["x2"]),
                float(raw["y2"]),
                bool(raw.get("construction", False)),
            )
        )
    return tuple(result)


def resolve_revolve_axis(
    profile: Sequence[Mapping[str, Any]],
    *,
    axis_role: str,
    tolerance: float = 1e-9,
) -> tuple[float, float, float, float]:
    """Resolve an axis from the actual sketch segment geometry.

    The resolver deliberately requires a real profile segment. It never invents
    a world-space axis from a tiny arbitrary coordinate delta.
    """
    segments = _segments_from_profile(profile)

    if axis_role != "centerline":
        raise RevolveReferenceError(f"unsupported axis role: {axis_role}")

    candidates = [
        segment
        for segment in segments
        if segment.length > tolerance
        and abs(segment.x1) <= tolerance
        and abs(segment.x2) <= tolerance
    ]

    if not candidates:
        raise RevolveReferenceError("no centerline segment found at x=0")

    candidates.sort(key=lambda segment: (-segment.length, segment.y1, segment.y2))
    best = candidates[0]

    if len(candidates) > 1 and abs(candidates[1].length - best.length) <= tolerance:
        raise RevolveReferenceError("ambiguous centerline: multiple equally strong candidates")

    return best.x1, best.y1, best.x2, best.y2


__all__ = ["RevolveReferenceError", "SketchSegment", "resolve_revolve_axis"]
