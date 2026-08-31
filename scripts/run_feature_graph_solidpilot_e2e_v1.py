from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from scripts.launcher_bootstrap import REPOSITORY_ROOT
from integration.feature_graph_compiler_v1 import compile_feature_graph
from integration.feature_graph_v1 import feature_graph_from_dict
from integration.solidpilot_operation_executor_v1 import SolidPilotOperationExecutor

ROOT = REPOSITORY_ROOT
REPO = ROOT / "vendor" / "q3ds-solidworks-mcp"
PYTHON = REPO / ".venv" / "Scripts" / "python.exe"
SERVER = REPO / "adapters" / "claude" / "legacy_server.py"


def graph():
    return feature_graph_from_dict({
        "schema": "solid-ai.feature-graph.v1",
        "part_id": "generic_profile_extrude_e2e",
        "design_intent": "generic 100x60x10 prismatic test part",
        "units": "mm",
        "features": [
            {
                "feature_id": "base_profile",
                "kind": "profile",
                "depends_on": [],
                "params": {"width": 100, "height": 60},
            },
            {
                "feature_id": "base",
                "kind": "extrude_boss",
                "depends_on": ["base_profile"],
                "params": {"thickness": 10},
            },
        ],
    })


async def main() -> int:
    plan = compile_feature_graph(graph())
    params = StdioServerParameters(
        command=str(PYTHON),
        args=[str(SERVER)],
        cwd=str(REPO),
        env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            executor = SolidPilotOperationExecutor(session)
            report = await executor.execute_plan(plan)
            print(json.dumps({
                "ok": report.ok,
                "prepared": report.prepared,
                "executed_features": report.executed_features,
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
            print("PASS: FeatureGraph -> Compiler -> SolidPilot -> SolidWorks")
            return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
