from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .aidesigner_assets import CapabilitySpec, get_capability
from .feature_graph_v1 import FeatureGraph, FeatureNode


class FeatureGraphCompileError(ValueError):
    """Raised when a semantic FeatureGraph cannot be lowered safely."""


@dataclass(frozen=True)
class Operation:
    """Backend-neutral executable operation produced by the compiler."""

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


_KIND_TO_CAPABILITY: dict[str, str] = {
    "profile": "part.create_sketch",
    "extrude_boss": "part.extrude_boss",
    "hole_pattern": "part.hole",
    "rib": "part.extrude_boss",
    "fillet": "edge.fillet",
}


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
    operation = Operation(
        node.feature_id,
        capability.capability_id,
        capability.tool,
        {"plane": params.get("plane", "Top Plane"), "width_m": width_m, "height_m": height_m},
    )
    return CompiledFeature(node.feature_id, capability, (operation,))


def _extrude(node: FeatureNode, capability: CapabilitySpec) -> CompiledFeature:
    params = dict(node.params)
    raw = params.get("depth_mm", params.get("thickness"))
    if raw is None:
        raise FeatureGraphCompileError(f"{node.feature_id}: extrude_boss requires depth_mm/thickness")
    depth_m = _require_positive_number(raw, "extrude depth") / 1000.0
    operation = Operation(
        node.feature_id,
        capability.capability_id,
        capability.tool,
        {"depth": depth_m, "feature_type": "boss", "reverse": False, "through": False,
         "up_to_face_index": -1, "mid_plane": False},
    )
    return CompiledFeature(node.feature_id, capability, (operation,))


def _holes(node: FeatureNode, capability: CapabilitySpec) -> CompiledFeature:
    params = dict(node.params)
    fastener = params.get("fastener", params.get("nominal"))
    count = params.get("count")
    if not isinstance(fastener, str) or not fastener.strip():
        raise FeatureGraphCompileError(f"{node.feature_id}: hole_pattern requires semantic fastener/nominal")
    if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
        raise FeatureGraphCompileError(f"{node.feature_id}: hole_pattern count must be a positive integer")

    operation = Operation(
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
        },
        phase="lower",
    )
    return CompiledFeature(node.feature_id, capability, (operation,))


def _rib(node: FeatureNode, capability: CapabilitySpec) -> CompiledFeature:
    params = dict(node.params)
    height = params.get("height")
    thickness = params.get("thickness")
    operation = Operation(
        node.feature_id,
        capability.capability_id,
        capability.tool,
        {
            "rib_intent": True,
            "height_m": _optional_mm(height),
            "thickness_m": _optional_mm(thickness),
            "position": params.get("position"),
            "count": params.get("count", 1),
            "feature_type": "boss",
        },
        phase="lower",
    )
    return CompiledFeature(node.feature_id, capability, (operation,))


def _fillet(node: FeatureNode, capability: CapabilitySpec) -> CompiledFeature:
    params = dict(node.params)
    radius = params.get("radius_mm", params.get("radius"))
    radius_m = _require_positive_number(radius, "fillet radius") / 1000.0
    selection = params.get("selection")
    if selection is None:
        raise FeatureGraphCompileError(f"{node.feature_id}: fillet requires explicit semantic selection")
    operation = Operation(
        node.feature_id,
        capability.capability_id,
        capability.tool,
        {"feature_type": "fillet", "radius_or_distance": radius_m, "selection_intent": selection},
        phase="lower",
    )
    return CompiledFeature(node.feature_id, capability, (operation,))


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
}


def compile_feature_graph(graph: FeatureGraph) -> CompiledPlan:
    """Compile semantic features to capability-bound operations without executing them."""
    compiled: list[CompiledFeature] = []
    for node in graph.features:
        capability_id = _KIND_TO_CAPABILITY.get(node.kind)
        if capability_id is None:
            raise FeatureGraphCompileError(
                f"no capability mapping for semantic feature kind: {node.kind}"
            )
        capability = get_capability(capability_id)
        if capability is None:
            raise FeatureGraphCompileError(f"capability registry missing: {capability_id}")
        handler = _HANDLERS.get(node.kind)
        if handler is None:
            raise FeatureGraphCompileError(f"compiler handler missing: {node.kind}")
        compiled.append(handler(node, capability))
    return CompiledPlan(graph=graph, features=tuple(compiled))


__all__ = [
    "CompiledFeature",
    "CompiledPlan",
    "FeatureGraphCompileError",
    "Operation",
    "compile_feature_graph",
]
