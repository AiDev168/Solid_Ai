import pytest

from integration.support_reference_v1 import (
    SketchFrame,
    SupportReferenceError,
    expected_extrude_end,
    frame_from_sketch_result,
    resolve_extrude_end_face,
)


def test_top_plane_extrusion_end_face_uses_sketch_frame_normal_not_world_z():
    frame = frame_from_sketch_result({
        "result_geometry": {
            "frame": {
                "origin": [0.0, 0.0, 0.0],
                "xdir": [1.0, 0.0, 0.0],
                "ydir": [0.0, 0.0, -1.0],
            }
        }
    })
    assert frame.normal == pytest.approx((0.0, 1.0, 0.0))
    assert expected_extrude_end(frame, 0.01) == pytest.approx((0.0, 0.01, 0.0))


def test_resolver_selects_extrusion_end_face_and_rejects_wrong_world_z_face():
    frame = SketchFrame(
        origin=(0.0, 0.0, 0.0),
        xdir=(1.0, 0.0, 0.0),
        ydir=(0.0, 0.0, -1.0),
        normal=(0.0, 1.0, 0.0),
    )
    candidates = (
        {"i": 1, "planar": True, "normal": [0.0, 0.0, 1.0], "point": [0.0, 0.0, 0.04]},
        {"i": 4, "planar": True, "normal": [0.0, 1.0, 0.0], "point": [0.0, 0.01, 0.0]},
        {"i": 7, "planar": True, "normal": [0.0, -1.0, 0.0], "point": [0.0, 0.0, 0.0]},
    )
    binding = resolve_extrude_end_face(
        candidates,
        frame=frame,
        depth_m=0.01,
        reference_id="base_top",
        state_version=4,
    )
    assert binding["backend_index"] == 4
    assert binding["expected_point"] == pytest.approx((0.0, 0.01, 0.0))
    assert binding["expected_normal"] == pytest.approx((0.0, 1.0, 0.0))


def test_extrusion_end_face_is_fail_closed_on_ambiguous_match():
    frame = SketchFrame((0, 0, 0), (1, 0, 0), (0, 0, -1), (0, 1, 0))
    candidates = (
        {"i": 4, "planar": True, "normal": [0, 1, 0], "point": [0, 0.01, 0]},
        {"i": 5, "planar": True, "normal": [0, 1, 0], "point": [0, 0.01, 0]},
    )
    with pytest.raises(SupportReferenceError, match="ambiguous"):
        resolve_extrude_end_face(
            candidates,
            frame=frame,
            depth_m=0.01,
            reference_id="ambiguous",
            state_version=4,
        )
