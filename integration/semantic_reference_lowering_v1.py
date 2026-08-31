from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping

from .aidesigner_assets import get_capability
from .feature_graph_compiler_v1 import CompiledFeature, CompiledPlan, Operation
from .feature_graph_lowering_v1 import lower_hole_pattern
from .runtime_reference_context_v1 import ReferenceBinding, RuntimeReferenceResolutionError


class SemanticReferenceLoweringError(ValueError):
    """Raised when a semantic reference is not bound before execution."""


def _binding(context: Mapping[str, ReferenceBinding], reference_id: str) -> ReferenceBinding:
    binding = context.get(reference_id)
    if binding is None:
        raise SemanticReferenceLoweringError(f"unbound semantic reference: {reference_id}")
    if not binding.backend_indices:
        raise SemanticReferenceLoweringError(f"semantic reference has no backend binding: {reference_id}")
    return binding


def _reference_id(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, Mapping):
        raw = value.get("reference_id")
        if isinstance(raw, str) and raw.strip():
            return raw
    return None


def materialize_hole_pattern(feature: CompiledFeature, bindings: Mapping[str, ReferenceBinding]) -> CompiledFeature:
    lowered = lower_hole_pattern(feature)
    source = dict(lowered.operations[0].params)
    reference_id = _reference_id(source.get("support_reference"))
    if reference_id is None:
        face_index = source.get("face_index")
        if isinstance(face_index, int) and face_index >= 0:
            return lowered
        raise SemanticReferenceLoweringError(f"{feature.feature_id}: hole_pattern requires support_reference")
    binding = _binding(bindings, reference_id)
    try:
        face_index = binding.backend_index
    except RuntimeReferenceResolutionError as exc:
        raise SemanticReferenceLoweringError(str(exc)) from exc

    rewritten = []
    for operation in lowered.operations:
        params = dict(operation.params)
        if operation.tool == "create_sketch":
            params.pop("support_reference", None)
            params["on_face"] = True
            params["face_index"] = face_index
        rewritten.append(replace(operation, params=params, phase="execute"))
    return replace(lowered, operations=tuple(rewritten))


def materialize_fillet(feature: CompiledFeature, bindings: Mapping[str, ReferenceBinding]) -> CompiledFeature:
    source = dict(feature.operations[0].params)
    reference_id = _reference_id(source.get("selection_reference"))
    if reference_id is None:
        raise SemanticReferenceLoweringError(f"{feature.feature_id}: fillet requires selection_reference")
    binding = _binding(bindings, reference_id)
    return replace(feature, operations=(
        Operation(
            feature.feature_id,
            feature.capability.capability_id,
            "add_edge_feature",
            {
                "feature_type": "fillet",
                "radius_or_distance": float(source["radius_or_distance"]),
                "edge_indices": str(list(binding.backend_indices)),
            },
            phase="execute",
        ),
    ))


def materialize_rib(feature: CompiledFeature, bindings: Mapping[str, ReferenceBinding]) -> CompiledFeature:
    source = dict(feature.operations[0].params)
    reference_id = _reference_id(source.get("support_reference"))
    if reference_id is None:
        raise SemanticReferenceLoweringError(f"{feature.feature_id}: rib requires support_reference")
    binding = _binding(bindings, reference_id)
    face_index = binding.backend_index

    x_center_m = float(source["x_center_mm"]) / 1000.0
    half_width_m = float(source["width_mm"]) / 2000.0
    half_span_m = float(source["span_mm"]) / 2000.0
    height_m = float(source["height_mm"]) / 1000.0

    create_cap = get_capability("part.create_sketch")
    boss_cap = get_capability("part.extrude_boss")
    if create_cap is None or boss_cap is None:
        raise SemanticReferenceLoweringError("rib lowering requires proven create_sketch and extrude_boss capabilities")

    return replace(feature, operations=(
        Operation(feature.feature_id, create_cap.capability_id, "create_sketch", {
            "on_face": True,
            "face_index": face_index,
        }, phase="execute"),
        Operation(feature.feature_id, create_cap.capability_id, "add_sketch_entity", {
            "entity_type": "rectangle",
            "x1": x_center_m - half_width_m,
            "y1": -half_span_m,
            "x2": x_center_m + half_width_m,
            "y2": half_span_m,
        }, phase="execute"),
        Operation(feature.feature_id, boss_cap.capability_id, "extrude_feature", {
            "depth": height_m,
            "feature_type": "boss",
            "reverse": False,
            "through": False,
            "up_to_face_index": -1,
            "mid_plane": False,
        }, phase="execute"),
    ))


def materialize_plan(plan: CompiledPlan, bindings: Mapping[str, ReferenceBinding]) -> CompiledPlan:
    features = []
    for feature in plan.features:
        if feature.capability.capability_id == "part.hole":
            features.append(materialize_hole_pattern(feature, bindings))
        elif feature.capability.capability_id == "edge.fillet":
            features.append(materialize_fillet(feature, bindings))
        elif feature.capability.capability_id == "part.rib":
            features.append(materialize_rib(feature, bindings))
        else:
            features.append(feature)
    return replace(plan, features=tuple(features))


__all__ = [
    "SemanticReferenceLoweringError",
    "materialize_fillet",
    "materialize_hole_pattern",
    "materialize_plan",
    "materialize_rib",
]
