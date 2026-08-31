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


def select_scenarios(harness: QualificationHarnessV1, wanted: set[str]):
    """Accept either scenario_id (Q-...) or capability_id as selectors."""
    if not wanted:
        raise ValueError("SOLID_AI_QUALIFY_IDS must contain at least one scenario_id or capability_id")
    selected = [
        scenario
        for scenario in harness.scenarios
        if scenario.scenario_id in wanted or scenario.capability_id in wanted
    ]
    if not selected:
        known = sorted({s.scenario_id for s in harness.scenarios} | {s.capability_id for s in harness.scenarios})
        raise ValueError(
            "No qualification scenarios matched SOLID_AI_QUALIFY_IDS. "
            f"Requested={sorted(wanted)!r}; known selectors={known!r}"
        )
    return selected


async def main() -> int:
    harness = QualificationHarnessV1(build_core_modeling_scenarios())
    wanted = selected_ids()
    scenarios = select_scenarios(harness, wanted)
    selected_scenario_ids = {scenario.scenario_id for scenario in scenarios}
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

            results = []
            for scenario in scenarios:
                try:
                    evidence = await executor.execute(scenario)
                    results.append(
                        {
                            "scenario_id": scenario.scenario_id,
                            "capability_id": scenario.capability_id,
                            "status": "verified" if evidence.get("ok") else "failed",
                            "evidence": evidence,
                            "error": evidence.get("error"),
                        }
                    )
                except Exception as exc:
                    results.append(
                        {
                            "scenario_id": scenario.scenario_id,
                            "capability_id": scenario.capability_id,
                            "status": "failed",
                            "evidence": None,
                            "error": f"{type(exc).__name__}: {exc}",
                        }
                    )

            payload = [
                {
                    "scenario_id": result["scenario_id"],
                    "capability_id": result["capability_id"],
                    "status": result["status"],
                    "state_version": (
                        result["evidence"].get("state_version") if result["evidence"] else None
                    ),
                    "verified": bool(result["evidence"] and result["evidence"].get("verified")),
                    "error": result["error"],
                }
                for result in results
                if result["scenario_id"] in selected_scenario_ids
            ]
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 0 if payload and all(item["status"] == "verified" for item in payload) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
