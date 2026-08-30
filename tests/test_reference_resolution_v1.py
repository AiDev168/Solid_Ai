import json

import pytest

from integration.reference_resolution_v1 import (
    ReferenceEvidence,
    ReferenceIntent,
    ReferenceResolutionError,
    edge_indices_json,
    face_evidence,
    face_index_json,
    resolve_reference,
    resolve_reference_set,
)


def test_resolve_top_face_uses_runtime_face_evidence_not_hardcoded_index():
    result = {
        "state_version": 4,
        "data": {
            "faces": [
                {"i": 0, "kind": "plane", "planar": True, "normal": [0, 0, -1], "point": [0, 0, 0]},
                {"i": 9, "kind": "plane", "planar": True, "normal": [0, 0, 1], "point": [0, 0, 0.01]},
            ]
        },
    }
    evidence = face_evidence(result, 4)
    binding = resolve_reference(ReferenceIntent("top", "face", "top_planar", "base"), evidence)
    assert binding.backend_index == 9
    assert binding.state_version == 4
    assert face_index_json(binding) == 9


def test_top_face_rejects_ambiguous_candidates():
    evidence = ReferenceEvidence(
        "face",
        (
            {"i": 2, "kind": "plane", "planar": True, "normal": [0, 0, 1], "point": [0, 0, 0.01]},
            {"i": 7, "kind": "plane", "planar": True, "normal": [0, 0, 1], "point": [0, 0, 0.01]},
        ),
        5,
    )
    with pytest.raises(ReferenceResolutionError, match="ambiguous"):
        resolve_reference(ReferenceIntent("top", "face", "top_planar"), evidence)


def test_edge_binding_is_serialized_only_after_resolution():
    evidence = ReferenceEvidence(
        "edge",
        (
            {"i": 3, "start": [0, 0, 0], "end": [0, 0, 0.01], "mid": [0, 0, 0.005]},
            {"i": 8, "start": [0.1, 0, 0], "end": [0.1, 0, 0.01], "mid": [0.1, 0, 0.005]},
        ),
        12,
    )
    binding = resolve_reference(ReferenceIntent("edge", "edge", "nearest", target_xyz=(0, 0, 0.005)), evidence)
    assert binding.backend_index == 3
    assert json.loads(edge_indices_json(binding)) == [3]


def test_outer_vertical_set_excludes_internal_vertical_edges_using_plan_boundary():
    evidence = ReferenceEvidence(
        "edge",
        (
            {"i": 1, "start": [-0.06, -0.04, 0.0], "end": [-0.06, -0.04, 0.01], "mid": [-0.06, -0.04, 0.005]},
            {"i": 2, "start": [0.06, 0.04, 0.0], "end": [0.06, 0.04, 0.01], "mid": [0.06, 0.04, 0.005]},
            {"i": 8, "start": [0.03, 0.0, 0.0], "end": [0.03, 0.0, 0.045], "mid": [0.03, 0.0, 0.0225]},
        ),
        20,
    )
    binding = resolve_reference_set(
        ReferenceIntent(
            "outer",
            "edge",
            "all_outer_vertical",
            criteria={"outer_bounds_m": (-0.06, 0.06, -0.04, 0.04)},
        ),
        evidence,
    )
    assert [item.backend_index for item in binding.bindings] == [1, 2]


def test_set_reference_is_not_collapsed_to_one_backend_index():
    evidence = ReferenceEvidence(
        "edge",
        (
            {"i": 1, "start": [0, 0, 0], "end": [0, 0, 0.01], "mid": [0, 0, 0.005]},
            {"i": 2, "start": [0.1, 0, 0], "end": [0.1, 0, 0.01], "mid": [0.1, 0, 0.005]},
        ),
        6,
    )
    binding = resolve_reference_set(ReferenceIntent("set", "edge", "all_outer_vertical"), evidence)
    assert json.loads(edge_indices_json(binding)) == [1, 2]
