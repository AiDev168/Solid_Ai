import json

from integration.recovery_assets import (
    RecoveryAssets,
    RecoveryRequest,
    TopologyRecoveryEvidence,
    TopologyRecoverySolver,
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


def test_json_face_not_found_normalizes_to_retryable_topology_failure():
    raw = json.dumps({
        "ok": False,
        "status": "FAILED",
        "error": {"code": "FACE_NOT_FOUND", "message": "face selector stale"},
    })
    failure = normalize_runtime_failure(raw)
    assert failure.code == "STALE_FACE_SELECTOR"
    diagnosis = diagnose_failure(code=failure.code, message=failure.message)
    assert diagnosis.category == "topology"
    assert diagnosis.retryable
    assert diagnosis.solver_hints == ("topology-rebinding-v1",)


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


def test_topology_solver_rebinds_face_by_geometry():
    anchor = make_anchor(
        {
            "kind": "face",
            "i": 3,
            "surface_kind": "plane",
            "planar": True,
            "normal": [0.0, 0.0, 1.0],
            "point": [0.0, 0.0, 0.01],
            "area": 0.0096,
        },
        source_state_version=7,
    )
    evidence = TopologyRecoveryEvidence(
        face_anchor=anchor,
        face_candidates=(
            {
                "kind": "face",
                "i": 1,
                "surface_kind": "plane",
                "planar": True,
                "normal": [0.0, 0.0, -1.0],
                "point": [0.0, 0.0, 0.0100000002],
                "area": 0.0095,
            },
        ),
        target_face_state_version=8,
    )
    result = TopologyRecoverySolver().recover(
        RecoveryRequest("topology", "STALE_FACE_SELECTOR", evidence, 1)
    )
    assert result.recovered
    assert result.face_binding is not None
    assert result.face_binding.backend_index == 1
    assert result.face_binding.source_backend_index == 3
    assert result.face_binding.target_state_version == 8
