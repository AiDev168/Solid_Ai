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

from integration.reference_resolution_v1 import ReferenceIntent, face_evidence, resolve_reference
from integration.motor_bracket_runtime_v1 import _face_support_matches


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
    for item in getattr(result, "content", None) or []:
        text = getattr(item, "text", None)
        if isinstance(text, str):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                if text.startswith("Error calling tool"):
                    raise RuntimeError(text)
    return result


async def call(session, tool, arguments):
    return parse_result(await session.call_tool(tool, arguments))


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
            ready = await call(session, "ensure_ready", {})
            print("READY:", json.dumps(ready, ensure_ascii=False))
            await call(session, "open_new_part", {})
            await call(session, "create_sketch", {"plane": "Top Plane"})
            await call(session, "add_sketch_entity", {
                "entity_type": "rectangle",
                "x1": -0.06, "y1": -0.04, "x2": 0.06, "y2": 0.04,
            })
            await call(session, "extrude_feature", {
                "depth": 0.01,
                "feature_type": "boss",
            })

            faces = await call(session, "analyze_model", {"analysis_type": "faces"})
            evidence = face_evidence(faces, int(faces["state_version"]))
            binding = resolve_reference(
                ReferenceIntent(
                    reference_id="base_top_face_for_trace",
                    kind="face",
                    role="top_planar",
                    feature_id="base",
                ),
                evidence,
            )

            print("FACE_BINDING:", json.dumps({
                "backend_index": binding.backend_index,
                "state_version": binding.state_version,
                "evidence": binding.evidence,
            }, ensure_ascii=False, default=str))

            sketch = await call(session, "create_sketch", {
                "on_face": True,
                "face_index": binding.backend_index,
            })
            print("CREATE_SKETCH:", json.dumps(sketch, ensure_ascii=False, default=str))

            if not isinstance(sketch, dict):
                raise RuntimeError("create_sketch returned non-object result")
            if sketch.get("status") != "COMPLETED":
                raise RuntimeError(f"create_sketch failed: {sketch}")

            matches = _face_support_matches(binding.evidence, sketch)
            print("FACE_SUPPORT_MATCH:", matches)
            if not matches:
                raise RuntimeError(json.dumps({
                    "code": "FACE_SUPPORT_MISMATCH",
                    "binding": binding.evidence,
                    "sketch_result": sketch.get("result_geometry"),
                    "face_index": binding.backend_index,
                }, ensure_ascii=False, default=str))

            print("PASS: face binding propagation + measured sketch support")
            return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
