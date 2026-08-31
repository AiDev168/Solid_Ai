from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from integration.capability_qualification_v1 import QualificationHarnessV1, build_core_modeling_scenarios
from integration.live_capability_qualification_v1 import LiveQualificationExecutorV1

REPO = ROOT / "vendor" / "q3ds-solidworks-mcp"
PYTHON = REPO / ".venv" / "Scripts" / "python.exe"
SERVER = REPO / "adapters" / "claude" / "legacy_server.py"


def selected_ids() -> set[str]:
    raw = os.getenv("SOLID_AI_QUALIFY_IDS", "Q-CUT-001,Q-SKETCH-001")
    return {item.strip() for item in raw.split(",") if item.strip()}


async def main() -> int:
    harness = QualificationHarnessV1(build_core_modeling_scenarios())
    wanted = selected_ids()
    scenarios = harness.plan(capability_ids=wanted)
    print(json.dumps({"selected": [s.scenario_id for s in scenarios]}, indent=2))

    params = StdioServerParameters(
        command=str(PYTHON),
        args=[str(SERVER)],
        cwd=str(REPO),
        env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            executor = LiveQualificationExecutorV1(session)
            results = await harness.run(executor, capability_ids=wanted)
            payload = [
                {
                    "scenario_id": result.scenario_id,
                    "capability_id": result.capability_id,
                    "status": result.status,
                    "state_version": result.evidence.get("state_version") if result.evidence else None,
                    "verified": bool(result.evidence and result.evidence.get("verified")),
                    "error": result.error,
                }
                for result in results
            ]
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 0 if all(item["status"] == "verified" for item in payload) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
