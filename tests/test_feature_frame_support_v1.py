import pytest

from integration.support_reference_v1 import (
    SupportReferenceError,
    frame_from_sketch_result,
    resolve_extrude_end_face,
    resolve_extrusion_boundary_edges,
)


def top_plane_frame():
    return frame_from_sketch_result({
        "result_geometry": {
            "frame": {
                "origin": [0.0, 0.0, 0.0],
                "xdir": [1.0, 0.0, 0.0],
                "ydir": [0.0, 0.0, -1.0],
            }
        }
    })


def test_extrude_end_face_uses_source_frame_normal_and_plane_distance():
    frame = top_plane_frame()
    faces = (
        {"i": 1, "planar": True, "normal": [0, 0, 1], "point": [0, 0, 0.04]},
        {"i": 2, "planar": True, "normal": [0, 1, 0], "point": [0.03, 0.01, 0.02]},
        {"i": 3, "planar": True, "normal": [0, 1, 0], "point": [0, 0.01, 0]},
    )
    binding = resolve_extrude_end_face(
        faces,
        frame=frame,
        depth_m=0.01,
        reference_id="base_end",
        state_version=4,
    )
    assert binding["backend_index"] == 3


def test_extrusion_boundary_edges_use_frame_normal_and_local_uv_boundary():
    frame = top_plane_frame()
    edges = (
        {"i": 1, "start": [-0.06, 0, -0.04], "end": [-0.06, 0.01, -0.04], "mid": [-0.06, 0.005, -0.04]},
        {"i": 2, "start": [0.06, 0, 0.04], "end": [0.06, 0.01, 0.04], "mid": [0.06, 0.005, 0.04]},
        {"i": 8, "start": [0.03, 0, 0], "end": [0.03, 0.045, 0], "mid": [0.03, 0.0225, 0]},
    )
    result = resolve_extrusion_boundary_edges(
        edges,
        frame=frame,
        bounds_uv=(-0.06, 0.06, -0.04, 0.04),
        reference_id="outer",
        state_version=9,
    )
    assert [item["backend_index"] for item in result] == [1, 2]


def test_extrude_end_face_is_fail_closed_on_ambiguity():
    frame = top_plane_frame()
    faces = (
        {"i": 3, "planar": True, "normal": [0, 1, 0], "point": [0, 0.01, 0]},
        {"i": 4, "planar": True, "normal": [0, 1, 0], "point": [0.02, 0.01, 0.01]},
    )
    with pytest.raises(SupportReferenceError):
        resolve_extrude_end_face(
            faces,
            frame=frame,
            depth_m=0.01,
            reference_id="ambiguous",
            state_version=4,
            tolerance_m=0.02,
        )


def test_extrusion_boundary_edges_ignore_degenerate_zero_length_edges():
    frame = top_plane_frame()
    edges = (
        {"i": 1, "start": [-0.06, 0, -0.04], "end": [-0.06, 0, -0.04], "mid": [-0.06, 0, -0.04]},
        {"i": 2, "start": [0.06, 0, 0.04], "end": [0.06, 0.01, 0.04], "mid": [0.06, 0.005, 0.04]},
    )
    result = resolve_extrusion_boundary_edges(
        edges,
        frame=frame,
        bounds_uv=(-0.06, 0.06, -0.04, 0.04),
        reference_id="outer",
        state_version=10,
    )
    assert [item["backend_index"] for item in result] == [2]
