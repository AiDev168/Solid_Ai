from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT / "vendor" / "q3ds-solidworks-mcp"
PYTHON = REPO / ".venv" / "Scripts" / "python.exe"
SERVER = REPO / "adapters" / "claude" / "legacy_server.py"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from integration.recovery_assets import (
    RecoveryAssets,
    TopologyRecoveryEvidence,
    make_anchor,
)


def parse_result(result):
    if getattr(result, "isError", False):
        raise RuntimeError(str(result))
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict) and "result" in structured:
        value = structured["result"]
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value
    content = getattr(result, "content", None) or []
    for item in content:
        text = getattr(item, "text", None)
        if isinstance(text, str):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
    return result


async def call(session, tool, args):
    print(f"CALL {tool}: {json.dumps(args, ensure_ascii=False)}")
    result = await session.call_tool(tool, args)
    data = parse_result(result)
    print("RESULT:", json.dumps(data, ensure_ascii=False, indent=2, default=str))
    return data


async def main() -> int:
    params = StdioServerParameters(
        command=str(PYTHON),
        args=[str(SERVER)],
        cwd=str(REPO),
        env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            await call(session, "ensure_ready", {})
            await call(session, "open_new_part", {})
            await call(session, "create_sketch", {"plane": "Front Plane"})

            profile = [
                (-0.06, 0.00, 0.06, 0.00),
                (0.06, 0.00, 0.06, 0.01),
                (0.06, 0.01, -0.05, 0.01),
                (-0.05, 0.01, -0.05, 0.07),
                (-0.05, 0.07, -0.06, 0.07),
                (-0.06, 0.07, -0.06, 0.00),
            ]
            for x1, y1, x2, y2 in profile:
                await call(session, "add_sketch_entity", {
                    "entity_type": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                })
            await call(session, "extrude_feature", {"depth": 0.08, "feature_type": "boss"})

            # Capture a pre-mutation edge anchor for the outer upper-left vertical edge.
            before = await call(session, "analyze_model", {"analysis_type": "edges"})
            edges_before = (before.get("data") or {}).get("edges", [])
            target = min(
                (edge for edge in edges_before if isinstance(edge, dict)),
                key=lambda e: sum((float((e.get("mid") or [0, 0, 0])[i]) - ([-0.055, 0.07, 0.04][i])) ** 2 for i in range(3)),
            )
            anchor_candidate = {"kind": "edge", **target, "backend_index": int(target["i"])}
            anchor = make_anchor(anchor_candidate, source_state_version=before.get("state_version", 0))
            print("ANCHOR:", anchor)

            # Topology mutation: add a hole cut which may renumber/split edges.
            await call(session, "create_sketch", {
                "on_face": True, "face_x": 0.0, "face_y": 0.005, "face_z": 0.04,
            })
            await call(session, "add_sketch_entity", {
                "entity_type": "circle", "cx": -0.045, "cy": 0.0, "radius": 0.005,
            })
            await call(session, "extrude_feature", {
                "depth": 0.01, "feature_type": "cut", "through": True,
            })

            after = await call(session, "analyze_model", {"analysis_type": "edges"})
            edges_after = (after.get("data") or {}).get("edges", [])
            candidates = [
                {"kind": "edge", **edge, "backend_index": int(edge["i"])}
                for edge in edges_after
                if isinstance(edge, dict)
            ]

            assets = RecoveryAssets()
            evidence = TopologyRecoveryEvidence(
                edge_anchor=anchor,
                edge_candidates=candidates,
                target_edge_state_version=after.get("state_version"),
            )
            diagnosis, recovery = assets.controller.diagnose_and_recover(
                code="STALE_EDGE_SELECTOR",
                message="edge index may have changed after the hole mutation",
                evidence=evidence,
                max_attempts=1,
            )
            print("DIAGNOSIS:", diagnosis)
            print("RECOVERY:", recovery)
            if recovery is None or not recovery.recovered or not recovery.attempts:
                raise RuntimeError("topology rebinding solver did not recover the edge")
            binding = recovery.attempts[-1].result.edge_binding
            if binding is None:
                raise RuntimeError("recovery completed without edge binding")

            fillet = await call(session, "add_edge_feature", {
                "feature_type": "fillet",
                "radius_or_distance": 0.005,
                "edge_indices": json.dumps([binding.backend_index]),
            })
            print("REBINDING BINDING:", binding)
            print("FILLET:", json.dumps(fillet, ensure_ascii=False, indent=2, default=str))
            if isinstance(fillet, dict) and fillet.get("status") == "COMPLETED":
                print("PASS: topology mutation + anchor rebinding + fillet recovery")
                return 0
            raise RuntimeError("fillet after topology rebinding did not complete")


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
