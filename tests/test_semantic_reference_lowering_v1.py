import pytest

from integration.feature_graph_compiler_v1 import CompiledFeature, Operation
from integration.runtime_reference_context_v1 import ReferenceBinding
from integration.semantic_reference_lowering_v1 import (
    SemanticReferenceLoweringError,
    materialize_fillet,
    materialize_hole_pattern,
)
from integration.aidesigner_assets import get_capability


def binding(ref, kind, *indices):
    return ReferenceBinding(
        reference_id=ref,
        kind=kind,
        role="test",
        source_feature_id="base",
        state_version=10,
        backend_indices=tuple(indices),
        evidence=tuple({"i": i} for i in indices),
    )


def test_hole_materializes_semantic_support_to_bound_face():
    cap = get_capability("part.hole")
    feature = CompiledFeature(
        "holes", cap,
        (Operation("holes", cap.capability_id, "create_sketch", {
            "support_reference": "base_end_face",
        }, phase="lower"),),
    )
    lowered = __import__("integration.semantic_reference_lowering_v1", fromlist=["materialize_hole_pattern"]).materialize_hole_pattern(
        feature, {"base_end_face": binding("base_end_face", "face", 7)}
    )
    assert lowered.operations[0].phase == "execute"
    assert lowered.operations[0].params["face_index"] == 7


def test_hole_rejects_unbound_semantic_support():
    cap = get_capability("part.hole")
    feature = CompiledFeature(
        "holes", cap,
        (Operation("holes", cap.capability_id, "create_sketch", {
            "support_reference": "base_end_face",
        }, phase="lower"),),
    )
    with pytest.raises(SemanticReferenceLoweringError):
        materialize_hole_pattern(feature, {})


def test_fillet_materializes_all_resolved_edges():
    cap = get_capability("edge.fillet")
    feature = CompiledFeature(
        "fillet", cap,
        (Operation("fillet", cap.capability_id, "add_edge_feature", {
            "radius_or_distance": 0.005,
            "selection_reference": "outer_edges",
        }, phase="lower"),),
    )
    lowered = materialize_fillet(feature, {
        "outer_edges": binding("outer_edges", "edge", 2, 5, 9)
    })
    assert lowered.operations[0].phase == "execute"
    assert lowered.operations[0].params["edge_indices"] == "[2, 5, 9]"
