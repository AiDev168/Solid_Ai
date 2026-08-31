from integration.motor_bracket_runtime_v1 import _face_support_matches


def _binding():
    return {
        "kind": "face",
        "backend_index": 9,
        "surface_kind": "plane",
        "planar": True,
        "normal": [0.0, 0.0, 1.0],
        "point": [0.0, 0.0, 0.01],
    }


def test_face_support_accepts_matching_sketch_frame():
    sketch = {
        "result_geometry": {
            "frame": {
                "origin": [0.01, -0.01, 0.01],
                "xdir": [1.0, 0.0, 0.0],
                "ydir": [0.0, 1.0, 0.0],
            }
        }
    }
    assert _face_support_matches(_binding(), sketch)


def test_face_support_rejects_wrong_reference_plane_even_when_create_completed():
    sketch = {
        "result_geometry": {
            "frame": {
                "origin": [0.0, 0.0, 0.04],
                "xdir": [1.0, 0.0, 0.0],
                "ydir": [0.0, 1.0, 0.0],
            }
        }
    }
    assert not _face_support_matches(_binding(), sketch)


def test_face_support_rejects_wrong_normal():
    sketch = {
        "result_geometry": {
            "frame": {
                "origin": [0.0, 0.0, 0.01],
                "xdir": [1.0, 0.0, 0.0],
                "ydir": [0.0, 0.0, 1.0],
            }
        }
    }
    assert not _face_support_matches(_binding(), sketch)
