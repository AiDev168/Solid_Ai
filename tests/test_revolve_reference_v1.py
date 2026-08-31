import pytest

from integration.revolve_reference_v1 import (
    RevolveReferenceError,
    resolve_revolve_axis,
)


def test_resolve_revolve_axis_uses_real_centerline_segment():
    profile = (
        {"x1": 0.0, "y1": 0.0, "x2": 0.0, "y2": 0.12},
        {"x1": 0.02, "y1": 0.0, "x2": 0.02, "y2": 0.025},
        {"x1": 0.02, "y1": 0.025, "x2": 0.03, "y2": 0.025},
    )
    assert resolve_revolve_axis(profile, axis_role="centerline") == (0.0, 0.0, 0.0, 0.12)


def test_revolve_axis_rejects_missing_centerline():
    profile = (
        {"x1": 0.01, "y1": 0.0, "x2": 0.01, "y2": 0.12},
        {"x1": 0.02, "y1": 0.0, "x2": 0.03, "y2": 0.0},
    )
    with pytest.raises(RevolveReferenceError):
        resolve_revolve_axis(profile, axis_role="centerline")


def test_revolve_axis_rejects_ambiguous_centerlines():
    profile = (
        {"x1": 0.0, "y1": 0.0, "x2": 0.0, "y2": 0.06},
        {"x1": 0.0, "y1": 0.06, "x2": 0.0, "y2": 0.12},
    )
    with pytest.raises(RevolveReferenceError):
        resolve_revolve_axis(profile, axis_role="centerline")
