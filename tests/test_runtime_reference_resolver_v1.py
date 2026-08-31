import asyncio
import json

import pytest

from integration.runtime_reference_context_v1 import ReferenceRequest
from integration.runtime_reference_resolver_v1 import (
    ReferenceResolverExecutionError,
    RuntimeReferenceResolverV1,
)
from integration.support_reference_v1 import SketchFrame


class Response:
    def __init__(self, payload):
        self.structuredContent = {"result": json.dumps(payload)}
        self.content = []
        self.isError = False


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return self.responses.pop(0)


def test_face_binding_uses_fresh_analyze_model_evidence_and_state_version():
    async def scenario():
        session = FakeSession([
            Response({
                "ok": True,
                "status": "COMPLETED",
                "state_version": 12,
                "data": {"faces": [
                    {"i": 7, "planar": True, "normal": [0, 0, 1], "point": [0, 0, 0.01]}
                ]},
            })
        ])
        resolver = RuntimeReferenceResolverV1(session)
        frame = SketchFrame((0, 0, 0), (1, 0, 0), (0, -1, 0), (0, 0, -1))
        binding = await resolver.bind_extrude_end_face(
            ReferenceRequest("end", "face", "extrude_end_face", "base"),
            source_frame=frame,
            depth_m=0.01,
        )
        assert session.calls == [("analyze_model", {"analysis_type": "faces"})]
        assert binding.backend_index == 7
        assert binding.state_version == 12
    asyncio.run(scenario())


def test_edge_binding_collects_all_matching_backend_indices():
    async def scenario():
        session = FakeSession([
            Response({
                "ok": True,
                "status": "COMPLETED",
                "state_version": 19,
                "data": {"edges": [
                    {"i": 2, "start": [0, 0, 0], "end": [0, 0, 0.01]},
                    {"i": 5, "start": [0.1, 0, 0], "end": [0.1, 0, 0.01]},
                    {"i": 9, "start": [0.03, 0, 0], "end": [0.03, 0.02, 0]},
                ]},
            })
        ])
        resolver = RuntimeReferenceResolverV1(session)
        frame = SketchFrame((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1))
        binding = await resolver.bind_outer_extrusion_edges(
            ReferenceRequest("outer", "edge", "outer_extrusion_boundary", "base"),
            source_frame=frame,
            bounds_uv=(0.0, 0.1, 0.0, 0.0),
        )
        assert binding.backend_indices == (2, 5)
        assert binding.state_version == 19
    asyncio.run(scenario())


def test_invalid_backend_evidence_fails_closed():
    async def scenario():
        session = FakeSession([
            Response({
                "ok": True,
                "status": "COMPLETED",
                "state_version": 4,
                "data": {"faces": "not-an-array"},
            })
        ])
        resolver = RuntimeReferenceResolverV1(session)
        frame = SketchFrame((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1))
        with pytest.raises(ReferenceResolverExecutionError):
            await resolver.bind_extrude_end_face(
                ReferenceRequest("end", "face", "extrude_end_face", "base"),
                source_frame=frame,
                depth_m=0.01,
            )
    asyncio.run(scenario())
