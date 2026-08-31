from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from scripts.launcher_bootstrap import REPOSITORY_ROOT
from integration.feature_graph_v1 import feature_graph_from_dict, graph_to_dict
from integration.generic_feature_graph_runtime_v1 import GenericFeatureGraphRuntimeV1

ROOT = REPOSITORY_ROOT
REPO = ROOT / "vendor" / "q3ds-solidworks-mcp"
PYTHON = REPO / ".venv" / "Scripts" / "python.exe"
SERVER = REPO / "adapters" / "claude" / "legacy_server.py"


def semantic_motor_bracket_graph():
    """Semantic graph only: no backend face/edge indices are embedded."""
    return feature_graph_from_dict({
        "schema": "solid-ai.feature-graph.v1",
        "part_id": "generic_motor_bracket_120x80",
        "design_intent": "motor bracket 120x80x10 with four M8 mounting holes, two ribs and R5 outer fillets",
        "units": "mm",
        "features": [
            {
                "feature_id": "base_profile",
                "kind": "profile",
                "depends_on": [],
                "params": {"width_mm": 120, "height_mm": 80, "plane": "Top Plane"},
            },
            {
                "feature_id": "base",
                "kind": "extrude_boss",
                "depends_on": ["base_profile"],
                "params": {"thickness": 10},
            },
            {
                "feature_id": "mounting_holes",
                "kind": "hole_pattern",
                "depends_on": ["base"],
                "params": {
                    "fastener": "M8",
                    "count": 4,
                    "pattern_type": "rectangular",
                    "diameter_mm": 8.0,
                    "centers_mm": [[-45, -25], [45, -25], [-45, 25], [45, 25]],
                    "depth": "through_all",
                    "through_depth_m": 0.01,
                    "support_reference": {
                        "reference_id": "base_end_face_for_holes",
                        "kind": "face",
                        "role": "extrude_end_face",
                        "feature_id": "base",
                    },
                },
            },
            {
                "feature_id": "rib_left",
                "kind": "rib",
                "depends_on": ["base"],
                "params": {
                    "x_center_mm": -30,
                    "width_mm": 8,
                    "span_mm": 50,
                    "height_mm": 45,
                    "support_reference": {
                        "reference_id": "base_end_face_for_rib_left",
                        "kind": "face",
                        "role": "extrude_end_face",
                        "feature_id": "base",
                    },
                },
            },
            {
                "feature_id": "rib_right",
                "kind": "rib",
                "depends_on": ["base"],
                "params": {
                    "x_center_mm": 30,
                    "width_mm": 8,
                    "span_mm": 50,
                    "height_mm": 45,
                    "support_reference": {
                        "reference_id": "base_end_face_for_rib_right",
                        "kind": "face",
                        "role": "extrude_end_face",
                        "feature_id": "base",
                    },
                },
            },
            {
                "feature_id": "outer_fillets",
                "kind": "fillet",
                "depends_on": ["mounting_holes", "rib_left", "rib_right"],
                "params": {
                    "radius_mm": 5,
                    "selection_reference": {
                        "reference_id": "base_outer_edges_for_fillet",
                        "kind": "edge",
                        "role": "outer_extrusion_boundary",
                        "feature_id": "base",
                        "criteria": {
                            "bounds_uv_m": [-0.06, 0.06, -0.04, 0.04]
                        },
                    },
                },
            },
        ],
    })


async def main() -> int:
    graph = semantic_motor_bracket_graph()
    print("SEMANTIC_GRAPH:")
    print(json.dumps(graph_to_dict(graph), ensure_ascii=False, indent=2))

    params = StdioServerParameters(
        command=str(PYTHON),
        args=[str(SERVER)],
        cwd=str(REPO),
        env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            report = await GenericFeatureGraphRuntimeV1(session).run(graph)
            print("REPORT:")
            print(json.dumps({
                "ok": report.ok,
                "executed_features": report.executed_features,
                "bindings": {
                    key: {
                        "kind": binding.kind,
                        "role": binding.role,
                        "source_feature_id": binding.source_feature_id,
                        "state_version": binding.state_version,
                        "backend_indices": list(binding.backend_indices),
                    }
                    for key, binding in report.bindings.items()
                },
                "operations": [
                    {
                        "feature_id": item.feature_id,
                        "capability_id": item.capability_id,
                        "tool": item.tool,
                        "state_version": item.state_version,
                    }
                    for item in report.operations
                ],
                "final_evidence": report.final_evidence,
                "errors": report.errors,
            }, ensure_ascii=False, indent=2, default=str))
            if not report.ok:
                return 1
            print("PASS: Generic semantic Motor Bracket -> Reference Resolution -> SolidPilot -> SolidWorks")
            return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
