from __future__ import annotations

from dataclasses import replace
from typing import Any, Callable, Mapping

from .feature_graph_compiler_v1 import CompiledFeature, CompiledPlan, Operation


class FeatureGraphLoweringError(ValueError):
    """Raised when semantic operations cannot be lowered without inference."""


Lowerer = Callable[[CompiledFeature], CompiledFeature]


class FeatureGraphLoweringRegistryV1:
    """Explicit semantic-to-executable lowering registry.

    A registered lowerer may only use information already present in the
    semantic feature or explicitly resolved backend data. It must never infer
    an engineering quantity merely because a backend tool happens to accept
    one.
    """

    def __init__(self) -> None:
        self._lowerers: dict[str, Lowerer] = {}

    def register(self, capability_id: str, lowerer: Lowerer) -> None:
        if not isinstance(capability_id, str) or not capability_id.strip():
            raise ValueError("capability_id must be non-empty")
        if capability_id in self._lowerers:
            raise ValueError(f"lowerer already registered: {capability_id}")
        self._lowerers[capability_id] = lowerer

    def has(self, capability_id: str) -> bool:
        return capability_id in self._lowerers

    def lower_feature(self, feature: CompiledFeature) -> CompiledFeature:
        lowerer = self._lowerers.get(feature.capability.capability_id)
        if lowerer is None:
            if all(operation.phase == "execute" for operation in feature.operations):
                return feature
            raise FeatureGraphLoweringError(
                f"no explicit lowerer for capability: {feature.capability.capability_id}"
            )
        lowered = lowerer(feature)
        if not isinstance(lowered, CompiledFeature):
            raise TypeError("lowerer must return CompiledFeature")
        return lowered

    def lower_plan(self, plan: CompiledPlan) -> CompiledPlan:
        return replace(
            plan,
            features=tuple(self.lower_feature(feature) for feature in plan.features),
        )


def _require_mapping(params: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = params.get(key)
    if not isinstance(value, Mapping):
        raise FeatureGraphLoweringError(f"missing explicit mapping: {key}")
    return value


def _explicit_dimension_mm(params: Mapping[str, Any], key: str) -> float:
    value = params.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise FeatureGraphLoweringError(f"{key} must be an explicit positive dimension in mm")
    return float(value) / 1000.0


def lower_hole_pattern(feature: CompiledFeature) -> CompiledFeature:
    """Lower a hole pattern only when diameter and centers are explicit.

    Semantic nominal values such as M8 are preserved as intent. They are never
    converted to a drill diameter inside this lowering layer.
    """
    source = dict(feature.operations[0].params)
    diameter_m = _explicit_dimension_mm(source, "diameter_mm")
    centers = source.get("centers_mm")
    if not isinstance(centers, (list, tuple)) or not centers:
        raise FeatureGraphLoweringError(
            f"{feature.feature_id}: hole_pattern requires explicit centers_mm"
        )

    normalized: list[tuple[float, float]] = []
    for item in centers:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise FeatureGraphLoweringError(
                f"{feature.feature_id}: each centers_mm entry must be [x,y]"
            )
        x, y = item
        if not all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in (x, y)):
            raise FeatureGraphLoweringError(
                f"{feature.feature_id}: hole center coordinates must be numeric"
            )
        normalized.append((float(x) / 1000.0, float(y) / 1000.0))

    create = Operation(
        feature.feature_id,
        feature.capability.capability_id,
        "create_sketch",
        {"plane": source.get("plane", "Top Plane")},
        phase="execute",
    )
    circles = tuple(
        Operation(
            feature.feature_id,
            feature.capability.capability_id,
            "add_sketch_entity",
            {"entity_type": "circle", "cx": x, "cy": y, "radius": diameter_m},
            phase="execute",
        )
        for x, y in normalized
    )
    cut = Operation(
        feature.feature_id,
        feature.capability.capability_id,
        "extrude_feature",
        {
            "depth": source.get("depth", "through_all"),
            "feature_type": "cut",
            "reverse": False,
            "through": source.get("depth", "through_all") == "through_all",
            "up_to_face_index": -1,
            "mid_plane": False,
        },
        phase="execute",
    )
    return replace(feature, operations=(create, *circles, cut))


def lower_fillet(feature: CompiledFeature) -> CompiledFeature:
    """Lower a fillet only with explicitly resolved backend edge indices."""
    source = dict(feature.operations[0].params)
    raw_edges = source.get("edge_indices")
    if not isinstance(raw_edges, (list, tuple)) or not raw_edges:
        raise FeatureGraphLoweringError(
            f"{feature.feature_id}: fillet requires explicitly resolved edge_indices"
        )
    edge_indices: list[int] = []
    for value in raw_edges:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise FeatureGraphLoweringError(
                f"{feature.feature_id}: edge_indices must contain non-negative integers"
            )
        edge_indices.append(value)
    radius_m = source.get("radius_or_distance")
    if isinstance(radius_m, bool) or not isinstance(radius_m, (int, float)) or radius_m <= 0:
        raise FeatureGraphLoweringError(
            f"{feature.feature_id}: radius_or_distance must be explicit and positive"
        )
    operation = Operation(
        feature.feature_id,
        feature.capability.capability_id,
        "add_edge_feature",
        {
            "feature_type": "fillet",
            "radius_or_distance": float(radius_m),
            "edge_indices": str(edge_indices),
        },
        phase="execute",
    )
    return replace(feature, operations=(operation,))


def build_default_lowering_registry() -> FeatureGraphLoweringRegistryV1:
    registry = FeatureGraphLoweringRegistryV1()
    registry.register("part.hole", lower_hole_pattern)
    registry.register("edge.fillet", lower_fillet)
    return registry


__all__ = [
    "FeatureGraphLoweringError",
    "FeatureGraphLoweringRegistryV1",
    "build_default_lowering_registry",
    "lower_fillet",
    "lower_hole_pattern",
]
