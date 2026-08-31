from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping

from .feature_graph_compiler_v1 import CompiledFeature, CompiledPlan, Operation
from .runtime_reference_context_v1 import ReferenceBinding, RuntimeReferenceResolutionError


class SemanticReferenceLoweringError(ValueError):
    """Raised when a semantic reference is not bound before execution."""


def _binding(context: Mapping[str, ReferenceBinding], reference_id: str) -> ReferenceBinding:
    binding = context.get(reference_id)
    if binding is None:
        raise SemanticReferenceLoweringError(
            f"unbound semantic reference: {reference_id}"
        )
    if not binding.backend_indices:
        raise SemanticReferenceLoweringError(
            f"semantic reference has no backend binding: {reference_id}"
        )
    return binding


def materialize_hole_pattern(feature: CompiledFeature, bindings: Mapping[str, ReferenceBinding]) -> CompiledFeature:
    source = dict(feature.operations[0].params)
    support_ref = source.get("support_reference")
    if not isinstance(support_ref, str) or not support_ref.strip():
        raise SemanticReferenceLoweringError(
            f"{feature.feature_id}: hole_pattern requires support_reference"
        )
    binding = _binding(bindings, support_ref)
    try:
        face_index = binding.backend_index
    except RuntimeReferenceResolutionError as exc:
        raise SemanticReferenceLoweringError(str(exc)) from exc

    rewritten = []
    for operation in feature.operations:
        params = dict(operation.params)
        if operation.tool == "create_sketch":
            params.pop("support_reference", None)
            params["on_face"] = True
            params["face_index"] = face_index
        rewritten.append(replace(operation, params=params, phase="execute"))
    return replace(feature, operations=tuple(rewritten))


def materialize_fillet(feature: CompiledFeature, bindings: Mapping[str, ReferenceBinding]) -> CompiledFeature:
    source = dict(feature.operations[0].params)
    selection_ref = source.get("selection_reference")
    if not isinstance(selection_ref, str) or not selection_ref.strip():
        raise SemanticReferenceLoweringError(
            f"{feature.feature_id}: fillet requires selection_reference"
        )
    binding = _binding(bindings, selection_ref)
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


def materialize_plan(plan: CompiledPlan, bindings: Mapping[str, ReferenceBinding]) -> CompiledPlan:
    """Resolve all semantic reference markers without discovering topology here."""
    features = []
    for feature in plan.features:
        if feature.capability.capability_id == "part.hole":
            features.append(materialize_hole_pattern(feature, bindings))
        elif feature.capability.capability_id == "edge.fillet":
            features.append(materialize_fillet(feature, bindings))
        else:
            features.append(feature)
    return replace(plan, features=tuple(features))


__all__ = [
    "SemanticReferenceLoweringError",
    "materialize_fillet",
    "materialize_hole_pattern",
    "materialize_plan",
]
