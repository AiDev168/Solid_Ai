from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .aidesigner_assets import CapabilitySpec
from .feature_capability_registry_v1 import FeatureCapabilityRegistryV1, build_default_feature_capability_registry
from .feature_graph_v1 import FeatureGraph, FeatureNode


class FeatureGraphCompileError(ValueError):
    """Raised when a semantic FeatureGraph cannot be compiled safely."""


@dataclass(frozen=True)
class Operation:
    feature_id: str
    capability_id: str
    tool: str
    params: Mapping[str, Any]
    phase: str = "execute"


@dataclass(frozen=True)
class CompiledFeature:
    feature_id: str
    capability: CapabilitySpec
    operations: tuple[Operation, ...]


@dataclass(frozen=True)
class CompiledPlan:
    graph: FeatureGraph
    features: tuple[CompiledFeature, ...]


def _require_positive_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or float(value) <= 0:
        raise FeatureGraphCompileError(f"{name} must be a positive number")
    return float(value)


def _profile(node: FeatureNode, capability: CapabilitySpec) -> CompiledFeature:
    params = dict(node.params)
    width = params.get("width_mm", params.get("width"))
    height = params.get("height_mm", params.get("height"))
    if width is None or height is None:
        raise FeatureGraphCompileError(f"{node.feature_id}: profile requires width and height")
    width_m = _require_positive_number(width, "profile width") / 1000.0
    height_m = _require_positive_number(height, "profile height") / 1000.0
    create = Operation(node.feature_id, capability.capability_id, "create_sketch", {"plane": params.get("plane", "Top Plane")})
    entity = Operation(node.feature_id, capability.capability_id, "add_sketch_entity", {"entity_type": "rectangle", "x1": -width_m / 2.0, "y1": -height_m / 2.0, "x2": width_m / 2.0, "y2": height_m / 2.0})
    return CompiledFeature(node.feature_id, capability, (create, entity))


def _extrude(node: FeatureNode, capability: CapabilitySpec) -> CompiledFeature:
    params = dict(node.params)
    raw = params.get("depth_mm", params.get("thickness"))
    if raw is None:
        raise FeatureGraphCompileError(f"{node.feature_id}: extrude_boss requires depth_mm/thickness")
    depth_m = _require_positive_number(raw, "extrude depth") / 1000.0
    return CompiledFeature(node.feature_id, capability, (Operation(node.feature_id, capability.capability_id, capability.tool, {"depth": depth_m, "feature_type": "boss", "reverse": False, "through": False, "up_to_face_index": -1, "mid_plane": False}),))


def _holes(node: FeatureNode, capability: CapabilitySpec) -> CompiledFeature:
    params = dict(node.params)
    fastener = params.get("fastener", params.get("nominal"))
    count = params.get("count")
    if not isinstance(fastener, str) or not fastener.strip():
        raise FeatureGraphCompileError(f"{node.feature_id}: hole_pattern requires semantic fastener/nominal")
    if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
        raise FeatureGraphCompileError(f"{node.feature_id}: hole_pattern count must be a positive integer")
    support_reference = params.get("support_reference")
    return CompiledFeature(node.feature_id, capability, (Operation(
        node.feature_id,
        capability.capability_id,
        capability.tool,
        {
            "hole_intent": fastener.strip(),
            "count": count,
            "pattern_type": params.get("pattern_type", "rectangular"),
            "spacing_x_m": _optional_mm(params.get("spacing_x")),
            "spacing_y_m": _optional_mm(params.get("spacing_y")),
            "depth": params.get("depth", "through_all"),
            "diameter_mm": params.get("diameter_mm"),
            "support_reference": support_reference,
            "support_face_index": params.get("support_face_index"),
            "centers_mm": params.get("centers_mm"),
            "through_depth_m": params.get("through_depth_m"),
            "depth_m": params.get("depth_m"),
        },
        phase="lower",
    ),))


def _rib(node: FeatureNode, capability: CapabilitySpec) -> CompiledFeature:
    params = dict(node.params)
    support_reference = params.get("support_reference")
    return CompiledFeature(node.feature_id, capability, (Operation(
        node.feature_id,
        capability.capability_id,
        capability.tool,
        {
            "rib_intent": True,
            "height_m": _optional_mm(params.get("height")),
            "thickness_m": _optional_mm(params.get("thickness")),
            "position": params.get("position"),
            "count": params.get("count", 1),
            "support_reference": support_reference,
            "x_center_mm": params.get("x_center_mm"),
            "width_mm": params.get("width_mm"),
            "span_mm": params.get("span_mm"),
        },
        phase="lower",
    ),))


def _fillet(node: FeatureNode, capability: CapabilitySpec) -> CompiledFeature:
    params = dict(node.params)
    radius = params.get("radius_mm", params.get("radius"))
    radius_m = _require_positive_number(radius, "fillet radius") / 1000.0
    selection_reference = params.get("selection_reference")
    selection = params.get("selection")
    if selection_reference is None and isinstance(selection, Mapping):
        reference = selection.get("reference")
        if isinstance(reference, (str, Mapping)):
            selection_reference = reference
    if selection_reference is None and selection is None:
        raise FeatureGraphCompileError(f"{node.feature_id}: fillet requires semantic selection")
    return CompiledFeature(node.feature_id, capability, (Operation(
        node.feature_id,
        capability.capability_id,
        capability.tool,
        {
            "feature_type": "fillet",
            "radius_or_distance": radius_m,
            "selection_intent": selection,
            "selection_reference": selection_reference,
            "edge_indices": params.get("edge_indices"),
        },
        phase="lower",
    ),))


def _axis_endpoints_mm(params: Mapping[str, Any], feature_id: str) -> tuple[float, float, float, float]:
    axis = params.get("axis_endpoints")
    if not (isinstance(axis, (list, tuple)) and len(axis) == 2):
        raise FeatureGraphCompileError(f"{feature_id}: revolve requires explicit axis_endpoints")
    try:
        (x1, y1), (x2, y2) = axis
    except (TypeError, ValueError):
        raise FeatureGraphCompileError(f"{feature_id}: axis_endpoints must be [[x1,y1],[x2,y2]]") from None
    values = (x1, y1, x2, y2)
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
        raise FeatureGraphCompileError(f"{feature_id}: axis endpoints must be numeric")
    if float(x1) == float(x2) and float(y1) == float(y2):
        raise FeatureGraphCompileError(f"{feature_id}: axis endpoints must define a non-zero line")
    return float(x1) / 1000.0, float(y1) / 1000.0, float(x2) / 1000.0, float(y2) / 1000.0


def _revolve(node: FeatureNode, capability: CapabilitySpec) -> CompiledFeature:
    params = dict(node.params)
    angle = float(params.get("angle_deg", params.get("angle", 360.0)))
    if not 0.0 < angle <= 360.0:
        raise FeatureGraphCompileError(f"{node.feature_id}: revolve angle must be in (0, 360]")
    x1, y1, x2, y2 = _axis_endpoints_mm(params, node.feature_id)
    return CompiledFeature(node.feature_id, capability, (Operation(node.feature_id, capability.capability_id, capability.tool, {"depth": 0.0, "feature_type": "revolve", "angle": angle, "axis_x1": x1, "axis_y1": y1, "axis_x2": x2, "axis_y2": y2}),))


def _revolve_cut(node: FeatureNode, capability: CapabilitySpec) -> CompiledFeature:
    base = _revolve(node, capability)
    return CompiledFeature(node.feature_id, capability, (Operation(node.feature_id, capability.capability_id, capability.tool, {**dict(base.operations[0].params), "feature_type": "revolve_cut"}),))


def _optional_mm(value: Any) -> float | None:
    if value is None:
        return None
    return _require_positive_number(value, "dimension") / 1000.0


_HANDLERS = {
    "profile": _profile,
    "extrude_boss": _extrude,
    "hole_pattern": _holes,
    "rib": _rib,
    "fillet": _fillet,
    "revolve": _revolve,
    "revolve_cut": _revolve_cut,
}


def compile_feature_graph(
    graph: FeatureGraph,
    *,
    capability_registry: FeatureCapabilityRegistryV1 | None = None,
) -> CompiledPlan:
    registry = capability_registry or build_default_feature_capability_registry()
    compiled: list[CompiledFeature] = []
    for node in graph.features:
        binding = registry.binding_for(node.kind)
        if binding is None:
            raise FeatureGraphCompileError(
                f"no explicit capability binding for semantic feature kind: {node.kind}"
            )
        handler = _HANDLERS.get(node.kind)
        if handler is None:
            raise FeatureGraphCompileError(f"compiler handler missing: {node.kind}")
        compiled.append(handler(node, binding.capability))
    return CompiledPlan(graph=graph, features=tuple(compiled))


__all__ = ["CompiledFeature", "CompiledPlan", "FeatureGraphCompileError", "Operation", "compile_feature_graph"]
