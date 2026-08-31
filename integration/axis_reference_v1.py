from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


class AxisReferenceError(ValueError):
    """Raised when an axis reference cannot be materialized safely."""


@dataclass(frozen=True)
class AxisBinding:
    reference_id: str
    x1: float
    y1: float
    x2: float
    y2: float
    state_version: int

    @property
    def midpoint(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)


def bind_revolve_axis(
    endpoints: Sequence[float],
    *,
    reference_id: str,
    state_version: int,
) -> AxisBinding:
    if len(endpoints) != 4:
        raise AxisReferenceError("revolve axis requires x1,y1,x2,y2")
    x1, y1, x2, y2 = (float(value) for value in endpoints)
    if abs(x1 - x2) <= 1e-12 and abs(y1 - y2) <= 1e-12:
        raise AxisReferenceError("revolve axis endpoints must define a non-zero segment")
    return AxisBinding(reference_id, x1, y1, x2, y2, int(state_version))


def materialize_axis_in_active_sketch(binding: AxisBinding) -> dict[str, Any]:
    """Return a construction-line command representing a bound revolve axis.

    SolidPilot's current revolve contract resolves its axis against the active
    sketch. Therefore a semantic axis reused by a second sketch must first be
    represented in that sketch as construction/reference geometry.
    """
    return {
        "entity_type": "line",
        "x1": binding.x1,
        "y1": binding.y1,
        "x2": binding.x2,
        "y2": binding.y2,
        "construction": True,
    }


def verify_materialized_axis(
    result: Mapping[str, Any],
    binding: AxisBinding,
    *,
    tolerance: float = 1e-7,
) -> bool:
    """Verify the line geometry by unordered endpoint-set equality.

    SolidWorks may return the same segment with its endpoint order reversed.
    Orientation is not part of line identity, so both endpoint orientations are
    accepted while coordinate values still have to match within tolerance.
    """
    geometry = result.get("result_geometry")
    if not isinstance(geometry, Mapping):
        return False
    if geometry.get("kind") != "line":
        return False
    values = tuple(geometry.get(key) for key in ("x1", "y1", "x2", "y2"))
    if not all(isinstance(value, (int, float)) for value in values):
        return False
    actual = tuple(float(value) for value in values)
    direct = (
        abs(actual[0] - binding.x1) <= tolerance
        and abs(actual[1] - binding.y1) <= tolerance
        and abs(actual[2] - binding.x2) <= tolerance
        and abs(actual[3] - binding.y2) <= tolerance
    )
    reverse = (
        abs(actual[0] - binding.x2) <= tolerance
        and abs(actual[1] - binding.y2) <= tolerance
        and abs(actual[2] - binding.x1) <= tolerance
        and abs(actual[3] - binding.y1) <= tolerance
    )
    return direct or reverse


__all__ = [
    "AxisBinding",
    "AxisReferenceError",
    "bind_revolve_axis",
    "materialize_axis_in_active_sketch",
    "verify_materialized_axis",
]
