import pytest

from integration.runtime_reference_context_v1 import (
    ReferenceRequest,
    RuntimeReferenceContextV1,
    RuntimeReferenceResolutionError,
    binding_to_backend_params,
)
from integration.support_reference_v1 import SketchFrame


def frame():
    return SketchFrame(
        origin=(0.0, 0.0, 0.0),
        xdir=(1.0, 0.0, 0.0),
        ydir=(0.0, 0.0, -1.0),
        normal=(0.0, 1.0, 0.0),
    )


def test_face_binding_is_semantic_and_state_scoped():
    ctx = RuntimeReferenceContextV1()
    binding = ctx.bind_extrude_end_face(
        ReferenceRequest("base_end", "face", "extrude_end_face", "base"),
        faces=({"i": 7, "planar": True, "normal": [0, 1, 0], "point": [0.0, 0.01, 0.0]},),
        source_frame=frame(),
        depth_m=0.01,
        state_version=10,
    )
    assert binding.backend_indices == (7,)
    assert binding.state_version == 10
    assert binding_to_backend_params(binding, parameter_name="face_index") == {"face_index": 7}


def test_outer_edge_binding_keeps_all_indices():
    ctx = RuntimeReferenceContextV1()
    binding = ctx.bind_outer_extrusion_edges(
        ReferenceRequest("outer", "edge", "outer_extrusion_boundary", "base"),
        edges=(
            {"i": 1, "start": [-0.06, 0.0, 0.0], "end": [-0.06, 0.01, 0.0]},
            {"i": 2, "start": [0.06, 0.0, 0.0], "end": [0.06, 0.01, 0.0]},
        ),
        source_frame=frame(),
        bounds_uv=(-0.06, 0.06, -0.04, 0.04),
        state_version=11,
    )
    assert binding.backend_indices == (1, 2)
    assert binding_to_backend_params(binding, parameter_name="edge_indices") == {"edge_indices": [1, 2]}


def test_wrong_reference_role_is_rejected_instead_of_guessing():
    ctx = RuntimeReferenceContextV1()
    with pytest.raises(RuntimeReferenceResolutionError):
        ctx.bind_outer_extrusion_edges(
            ReferenceRequest("x", "edge", "some_other_role", "base"),
            edges=(),
            source_frame=frame(),
            bounds_uv=(-1, 1, -1, 1),
            state_version=11,
        )
