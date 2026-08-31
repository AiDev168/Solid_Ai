from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class LLMSemanticFidelityError(ValueError):
    """Raised when an LLM plan changes explicit engineering meaning."""


def _numbers_close(a: Any, b: Any, tolerance: float = 1e-9) -> bool:
    try:
        return abs(float(a) - float(b)) <= tolerance
    except (TypeError, ValueError):
        return False


def assert_explicit_constraints_preserved(
    graph_payload: Mapping[str, Any],
    requirements_payload: Mapping[str, Any],
) -> None:
    """Require every explicit design constraint to survive into the CAD plan.

    This is intentionally conservative: it never converts engineering quantities.
    It only accepts exact semantic matches or explicitly traceable representations.
    """
    constraints = requirements_payload.get("explicit_constraints", ())
    if not isinstance(constraints, (list, tuple)):
        raise LLMSemanticFidelityError("requirements.explicit_constraints must be a list")

    features = graph_payload.get("features", ())
    if not isinstance(features, (list, tuple)):
        raise LLMSemanticFidelityError("graph.features must be a list")

    flattened: list[Mapping[str, Any]] = []
    for feature in features:
        if not isinstance(feature, Mapping):
            continue
        params = feature.get("params")
        flattened.append(feature)
        if isinstance(params, Mapping):
            flattened.append(params)

    for constraint in constraints:
        if not isinstance(constraint, Mapping):
            continue
        target = str(constraint.get("target", "")).strip()
        value = constraint.get("value")
        unit = str(constraint.get("unit", "")).strip().lower()
        if not target:
            continue

        matched = False
        for item in flattened:
            if target in item and _same_quantity(item[target], value, unit):
                matched = True
                break
            refs = item.get("requirement_refs")
            if isinstance(refs, (list, tuple)) and str(constraint.get("id", "")) in refs:
                matched = True
                break

        if not matched:
            raise LLMSemanticFidelityError(
                f"explicit constraint '{target}' was not preserved in the LLM plan"
            )


def _same_quantity(actual: Any, expected: Any, expected_unit: str) -> bool:
    if isinstance(actual, Mapping) and "value" in actual:
        return _same_quantity(actual["value"], expected, str(actual.get("unit", "")).lower())
    if isinstance(actual, (list, tuple)) and isinstance(expected, (list, tuple)):
        return len(actual) == len(expected) and all(
            _same_quantity(a, b, expected_unit) for a, b in zip(actual, expected)
        )
    if isinstance(actual, str) or isinstance(expected, str):
        return str(actual).strip() == str(expected).strip()

    # No implicit engineering conversion is allowed here. Matching numeric values
    # is safe; unit conversion must already have been made explicit upstream.
    return _numbers_close(actual, expected)


def assert_no_implicit_m8_drill_conversion(
    graph_payload: Mapping[str, Any],
    requirements_payload: Mapping[str, Any],
) -> None:
    """Reject the known bad M8 -> 8.5 mm inference pattern."""
    for constraint in requirements_payload.get("explicit_constraints", ()):
        if not isinstance(constraint, Mapping):
            continue
        value = constraint.get("value")
        target = str(constraint.get("target", ""))
        if isinstance(value, str) and value.strip().upper() == "M8":
            for feature in graph_payload.get("features", ()):
                if not isinstance(feature, Mapping):
                    continue
                params = feature.get("params")
                if not isinstance(params, Mapping):
                    continue
                diameter_keys = ("diameter", "diameter_mm", "diameter_m", "hole_diameter")
                for key in diameter_keys:
                    diameter = params.get(key)
                    if _numbers_close(diameter, 8.5) or _numbers_close(diameter, 0.0085):
                        raise LLMSemanticFidelityError(
                            f"implicit M8-to-{key}=8.5 conversion detected for constraint '{target}'"
                        )


__all__ = [
    "LLMSemanticFidelityError",
    "assert_explicit_constraints_preserved",
    "assert_no_implicit_m8_drill_conversion",
]
