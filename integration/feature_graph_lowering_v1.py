from __future__ import annotations

from dataclasses import replace
from typing import Callable, Mapping, Any

from .feature_graph_compiler_v1 import CompiledFeature, CompiledPlan, Operation


class FeatureGraphLoweringError(ValueError):
    """Raised when semantic operations cannot be lowered without inference."""


Lowerer = Callable[[CompiledFeature], CompiledFeature]


class FeatureGraphLoweringRegistryV1:
    """Explicit semantic-to-executable lowering registry."""

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
        return replace(plan, features=tuple(self.lower_feature(feature) for feature in plan.features))


def _explicit_dimension_mm(params: Mapping[str, Any], key: str) -> float:
    value = params.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise FeatureGraphLoweringError(f"{key} must be an explicit positive dimension in mm")
    return float(value) / 1000.0


def _explicit_depth_m(params: Mapping[str, Any]) -> float:
    value = params.get("depth_m")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise FeatureGraphLoweringError("hole_pattern requires explicit depth_m when through_all is not used")
    return float(value)


def _circle_radius_from_diameter_mm(params: Mapping[str, Any]) -> float:
    diameter_m = _explicit_dimension_mm(params, "diameter_mm")
    radius_m = diameter_m / 2.0
    if radius_m <= 0:
        raise FeatureGraphLoweringError("circle radius must be positive")
    return radius_m


def _reference_id(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, Mapping):
        raw = value.get("reference_id")
        if isinstance(raw, str) and raw.strip():
            return raw
    return None


def lower_hole_pattern(feature: CompiledFeature) -> CompiledFeature:
    """Lower a hole pattern while preserving semantic support until materialization."""
    source = dict(feature.operations[0].params)
    radius_m = _circle_radius_from_diameter_mm(source)
    centers = source.get("centers_mm")
    if not isinstance(centers, (list, tuple)) or not centers:
        raise FeatureGraphLoweringError(f"{feature.feature_id}: hole_pattern requires explicit centers_mm")
    support_ref = source.get("support_reference")
    support_face_index = source.get("support_face_index")
    if _reference_id(support_ref) is None and (
        isinstance(support_face_index, bool) or not isinstance(support_face_index, int) or support_face_index < 0
    ):
        raise FeatureGraphLoweringError(
            f"{feature.feature_id}: hole_pattern requires support_reference or resolved support_face_index"
        )

    normalized: list[tuple[float, float]] = []
    for item in centers:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise FeatureGraphLoweringError(f"{feature.feature_id}: each centers_mm entry must be [x,y]")
        x, y = item
        if not all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in (x, y)):
            raise FeatureGraphLoweringError(f"{feature.feature_id}: hole center coordinates must be numeric")
        normalized.append((float(x) / 1000.0, float(y) / 1000.0))

    create_params: dict[str, Any] = {"on_face": True}
    if support_face_index is not None:
        create_params["face_index"] = support_face_index
    if support_ref is not None:
        create_params["support_reference"] = support_ref

    create = Operation(feature.feature_id, feature.capability.capability_id, "create_sketch", create_params, phase="execute")
    circles = tuple(
        Operation(
            feature.feature_id,
            feature.capability.capability_id,
            "add_sketch_entity",
            {"entity_type": "circle", "cx": x, "cy": y, "radius": radius_m},
            phase="execute",
        )
        for x, y in normalized
    )

    through = source.get("depth", "through_all") == "through_all"
    cut_params: dict[str, Any] = {
        "feature_type": "cut",
        "reverse": False,
        "through": through,
        "up_to_face_index": -1,
        "mid_plane": False,
    }
    if through:
        depth = source.get("through_depth_m")
        if not isinstance(depth, (int, float)) or isinstance(depth, bool) or depth <= 0:
            raise FeatureGraphLoweringError(f"{feature.feature_id}: through_all requires explicit through_depth_m")
        cut_params["depth"] = float(depth)
    else:
        cut_params["depth"] = _explicit_depth_m(source)

    cut = Operation(feature.feature_id, feature.capability.capability_id, "extrude_feature", cut_params, phase="execute")
    return replace(feature, operations=(create, *circles, cut))


def lower_fillet(feature: CompiledFeature) -> CompiledFeature:
    source = dict(feature.operations[0].params)
    raw_edges = source.get("edge_indices")
    if not isinstance(raw_edges, (list, tuple)) or not raw_edges:
        selection_ref = _reference_id(source.get("selection_reference"))
        if selection_ref is None:
            raise FeatureGraphLoweringError(f"{feature.feature_id}: fillet requires selection_reference or edge_indices")
        return feature
    edge_indices: list[int] = []
    for value in raw_edges:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise FeatureGraphLoweringError(f"{feature.feature_id}: edge_indices must contain non-negative integers")
        edge_indices.append(value)
    radius_m = source.get("radius_or_distance")
    if isinstance(radius_m, bool) or not isinstance(radius_m, (int, float)) or radius_m <= 0:
        raise FeatureGraphLoweringError(f"{feature.feature_id}: radius_or_distance must be explicit and positive")
    return replace(feature, operations=(Operation(
        feature.feature_id, feature.capability.capability_id, "add_edge_feature",
        {"feature_type": "fillet", "radius_or_distance": float(radius_m), "edge_indices": str(edge_indices)},
        phase="execute",
    ),))


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
