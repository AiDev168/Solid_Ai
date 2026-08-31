import pytest

from integration.axis_reference_v1 import (
    AxisReferenceError,
    bind_revolve_axis,
    materialize_axis_in_active_sketch,
    verify_materialized_axis,
)


def test_axis_binding_rejects_zero_length():
    with pytest.raises(AxisReferenceError):
        bind_revolve_axis((0.0, 0.0, 0.0, 0.0), reference_id="axis", state_version=1)


def test_axis_materializes_as_construction_line():
    binding = bind_revolve_axis((0.0, 0.0, 0.0, 0.12), reference_id="centerline", state_version=7)
    command = materialize_axis_in_active_sketch(binding)
    assert command == {
        "entity_type": "line",
        "x1": 0.0,
        "y1": 0.0,
        "x2": 0.0,
        "y2": 0.12,
        "construction": True,
    }


def test_materialized_axis_is_verified_from_real_result_geometry():
    binding = bind_revolve_axis((0.0, 0.0, 0.0, 0.12), reference_id="centerline", state_version=7)
    assert verify_materialized_axis(
        {"result_geometry": {"kind": "line", "x1": 0.0, "y1": 0.0, "x2": 0.0, "y2": 0.12}},
        binding,
    )
    assert verify_materialized_axis(
        {"result_geometry": {"kind": "line", "x1": 0.0, "y1": 0.12, "x2": 0.0, "y2": 0.0}},
        binding,
    )
