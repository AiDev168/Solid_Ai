from integration.recovery_assets import (
    RecoveryAssets,
    RecoveryRequest,
    TopologyRecoveryEvidence,
    make_anchor,
    normalize_runtime_failure,
    diagnose_failure,
)


def test_diagnosis_is_fail_closed_except_known_topology_family():
    topology = diagnose_failure(code="EDGE_NOT_FOUND", message="edge missing")
    assert topology.category == "topology"
    assert topology.retryable is True
    unknown = diagnose_failure(code="SOMETHING_NEW")
    assert unknown.retryable is False


def test_runtime_failure_maps_edge_face_and_axis():
    class E:
        def __str__(self):
            return "Error: {'error': {'code': 'EDGE_NOT_FOUND', 'message': 'missing'}}"

    assert normalize_runtime_failure(E()).code == "STALE_EDGE_SELECTOR"


def test_topology_solver_rebinds_changed_backend_index():
    anchor = make_anchor(
        {
            "kind": "edge",
            "i": 3,
            "start": [0.0, 0.0, 0.0],
            "end": [0.0, 0.0, 0.1],
            "mid": [0.0, 0.0, 0.05],
            "length": 0.1,
        },
        source_state_version=10,
    )
    evidence = TopologyRecoveryEvidence(
        edge_anchor=anchor,
        edge_candidates=(
            {"kind": "edge", "i": 9, "start": [0.0, 0.0, 0.0], "end": [0.0, 0.0, 0.1], "mid": [0.0, 0.0, 0.05], "length": 0.1},
            {"kind": "edge", "i": 12, "start": [0.4, 0.0, 0.0], "end": [0.4, 0.0, 0.1], "mid": [0.4, 0.0, 0.05], "length": 0.1},
        ),
        target_edge_state_version=11,
    )
    assets = RecoveryAssets()
    result = assets.controller.recover(RecoveryRequest("topology", "STALE_EDGE_SELECTOR", evidence, 1))
    assert result.recovered is True
    binding = result.attempts[-1].result.edge_binding
    assert binding.backend_index == 9
    assert binding.source_backend_index == 3
    assert binding.target_state_version == 11
