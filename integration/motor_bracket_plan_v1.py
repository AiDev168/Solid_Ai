"""Semantic Motor Bracket V1 plan derived from proven Ai_Designer planning assets."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FeatureSpec:
    feature_id: str
    kind: str
    depends_on: tuple[str, ...]
    params: dict[str, Any]


@dataclass(frozen=True)
class MotorBracketPlanV1:
    schema: str
    part_id: str
    description: str
    features: tuple[FeatureSpec, ...]


_BASE_BOUNDS_M = (-0.06, 0.06, -0.04, 0.04)

MOTOR_BRACKET_V1 = MotorBracketPlanV1(
    schema="solid-ai.motor-bracket.v1",
    part_id="motor_bracket_v1",
    description=(
        "Motor mounting bracket, 120 x 80 mm footprint, 10 mm base thickness, "
        "four M8 mounting holes, two reinforcing ribs, outer edge fillets R5."
    ),
    features=(
        FeatureSpec(
            "base_profile",
            "profile",
            (),
            {"plane": "Top Plane", "width_m": 0.12, "height_m": 0.08},
        ),
        FeatureSpec("base", "extrude_boss", ("base_profile",), {"depth_m": 0.01}),
        FeatureSpec(
            "mounting_holes",
            "hole_pattern",
            ("base",),
            {
                "diameter_m": 0.008,
                "through": True,
                "centers_m": (
                    (-0.045, -0.025),
                    (0.045, -0.025),
                    (-0.045, 0.025),
                    (0.045, 0.025),
                ),
                "support_ref": {
                    "reference_id": "base_top_face_for_holes",
                    "kind": "face",
                    "role": "top_planar",
                    "feature_id": "base",
                },
            },
        ),
        FeatureSpec(
            "rib_left",
            "rib",
            ("base",),
            {
                "x_center_m": -0.03,
                "width_m": 0.008,
                "height_m": 0.045,
                "depth_m": 0.01,
                "support_ref": {
                    "reference_id": "base_top_face_for_rib_left",
                    "kind": "face",
                    "role": "top_planar",
                    "feature_id": "base",
                },
            },
        ),
        FeatureSpec(
            "rib_right",
            "rib",
            ("base",),
            {
                "x_center_m": 0.03,
                "width_m": 0.008,
                "height_m": 0.045,
                "depth_m": 0.01,
                "support_ref": {
                    "reference_id": "base_top_face_for_rib_right",
                    "kind": "face",
                    "role": "top_planar",
                    "feature_id": "base",
                },
            },
        ),
        FeatureSpec(
            "outer_fillets",
            "fillet",
            ("mounting_holes", "rib_left", "rib_right"),
            {
                "radius_m": 0.005,
                "selection": {
                    "semantic_role": "outer_vertical_edges",
                    "strategy": "fresh_topology_evidence",
                    "reference": {
                        "reference_id": "outer_vertical_edges_for_fillet",
                        "kind": "edge",
                        "role": "all_outer_vertical",
                        "criteria": {"outer_bounds_m": _BASE_BOUNDS_M},
                    },
                },
            },
        ),
    ),
)


def ordered_features(plan: MotorBracketPlanV1 = MOTOR_BRACKET_V1) -> tuple[FeatureSpec, ...]:
    remaining = {feature.feature_id: feature for feature in plan.features}
    ordered: list[FeatureSpec] = []
    while remaining:
        ready = [
            feature
            for feature in remaining.values()
            if all(dep not in remaining for dep in feature.depends_on)
        ]
        if not ready:
            raise ValueError("Motor bracket plan contains a dependency cycle")
        ready.sort(key=lambda feature: feature.feature_id)
        for feature in ready:
            ordered.append(feature)
            remaining.pop(feature.feature_id)
    return tuple(ordered)


__all__ = ["FeatureSpec", "MotorBracketPlanV1", "MOTOR_BRACKET_V1", "ordered_features"]
