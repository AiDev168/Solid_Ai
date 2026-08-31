from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from scripts.launcher_bootstrap import REPOSITORY_ROOT
from integration.axis_reference_v1 import (
    bind_revolve_axis,
    materialize_axis_in_active_sketch,
    verify_materialized_axis,
)
from integration.revolve_reference_v1 import resolve_revolve_axis

ROOT = REPOSITORY_ROOT
REPO = ROOT / "vendor" / "q3ds-solidworks-mcp"
PYTHON = REPO / ".venv" / "Scripts" / "python.exe"
SERVER = REPO / "adapters" / "claude" / "legacy_server.py"


def parse(result):
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
                return text
    return result


async def call(session, tool, arguments, step):
    print(f"STEP {step}: {tool} {json.dumps(arguments, ensure_ascii=False)}")
    result = await session.call_tool(tool, arguments)
    data = parse(result)
    print("RESULT:", json.dumps(data, ensure_ascii=False, indent=2, default=str))
    if getattr(result, "isError", False):
        raise RuntimeError(f"{tool} failed: {data}")
    return data


async def main() -> int:
    params = StdioServerParameters(
        command=str(PYTHON),
        args=[str(SERVER)],
        cwd=str(REPO),
        env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
    )

    profile = [
        {"x1": 0.0, "y1": 0.0, "x2": 0.0, "y2": 0.12},
        {"x1": 0.0, "y1": 0.12, "x2": 0.015, "y2": 0.12},
        {"x1": 0.015, "y1": 0.12, "x2": 0.015, "y2": 0.08},
        {"x1": 0.015, "y1": 0.08, "x2": 0.03, "y2": 0.08},
        {"x1": 0.03, "y1": 0.08, "x2": 0.03, "y2": 0.025},
        {"x1": 0.03, "y1": 0.025, "x2": 0.02, "y2": 0.025},
        {"x1": 0.02, "y1": 0.025, "x2": 0.02, "y2": 0.0},
        {"x1": 0.02, "y1": 0.0, "x2": 0.0, "y2": 0.0},
    ]

    axis_endpoints = resolve_revolve_axis(profile, axis_role="centerline")
    axis = bind_revolve_axis(axis_endpoints, reference_id="stepped_centerline", state_version=3)

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            step = 1
            await call(session, "ensure_ready", {}, step); step += 1
            await call(session, "open_new_part", {}, step); step += 1
            await call(session, "create_sketch", {"plane": "Front Plane"}, step); step += 1

            for segment in profile:
                await call(session, "add_sketch_entity", {"entity_type": "line", **segment}, step)
                step += 1

            await call(session, "extrude_feature", {
                "depth": 0.0,
                "feature_type": "revolve",
                "angle": 360.0,
                "axis_x1": axis.x1, "axis_y1": axis.y1,
                "axis_x2": axis.x2, "axis_y2": axis.y2,
            }, step)
            step += 1

            # The backend revolve contract resolves the axis against the ACTIVE
            # sketch. Re-materialize the semantic axis as construction geometry
            # in every subsequent sketch that consumes the same axis.
            await call(session, "create_sketch", {"plane": "Front Plane"}, step); step += 1
            axis_command = materialize_axis_in_active_sketch(axis)
            axis_result = await call(session, "add_sketch_entity", axis_command, step); step += 1
            if not verify_materialized_axis(axis_result, axis):
                raise RuntimeError("REVOLVE_AXIS_SUPPORT_MISMATCH: active sketch axis geometry did not match semantic binding")

            groove = (
                (0.025, 0.044, 0.032, 0.044),
                (0.032, 0.044, 0.032, 0.051),
                (0.032, 0.051, 0.025, 0.051),
                (0.025, 0.051, 0.025, 0.044),
            )
            for x1, y1, x2, y2 in groove:
                await call(session, "add_sketch_entity", {
                    "entity_type": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2
                }, step)
                step += 1

            await call(session, "extrude_feature", {
                "depth": 0.0,
                "feature_type": "revolve_cut",
                "angle": 360.0,
                "axis_x1": axis.x1, "axis_y1": axis.y1,
                "axis_x2": axis.x2, "axis_y2": axis.y2,
            }, step)
            step += 1

            faces = await call(session, "analyze_model", {"analysis_type": "faces"}, step); step += 1
            raw_faces = (((faces or {}).get("data") or {}).get("faces") or []) if isinstance(faces, dict) else []
            end_face = next(
                (
                    face for face in raw_faces
                    if isinstance(face.get("normal"), list)
                    and isinstance(face.get("point"), list)
                    and len(face["normal"]) >= 3
                    and len(face["point"]) >= 3
                    and abs(abs(float(face["normal"][1])) - 1.0) < 1e-6
                    and abs(float(face["point"][1]) - 0.12) < 1e-6
                ),
                None,
            )
            if end_face is None:
                raise RuntimeError("No axial end face found for hole")

            face_index = int(end_face.get("i", end_face.get("backend_index")))
            await call(session, "create_sketch", {"on_face": True, "face_index": face_index}, step); step += 1
            await call(session, "add_sketch_entity", {"entity_type": "circle", "cx": 0.0, "cy": 0.0, "radius": 0.006}, step); step += 1
            await call(session, "extrude_feature", {
                "depth": 0.04, "feature_type": "cut", "reverse": False,
                "through": False, "up_to_face_index": -1, "mid_plane": False,
            }, step); step += 1

            edges = await call(session, "analyze_model", {"analysis_type": "edges"}, step); step += 1
            raw_edges = (((edges or {}).get("data") or {}).get("edges") or []) if isinstance(edges, dict) else []
            usable = []
            for edge in raw_edges:
                start, end = edge.get("start"), edge.get("end")
                if not isinstance(start, list) or not isinstance(end, list) or len(start) < 3 or len(end) < 3:
                    continue
                length2 = sum((float(end[i]) - float(start[i])) ** 2 for i in range(3))
                if length2 > 1e-12:
                    usable.append(edge)
            if not usable:
                raise RuntimeError("No usable edges found before fillet")

            selected = max(usable, key=lambda e: float(e.get("length", 0.0)))
            edge_index = int(selected["i"])
            await call(session, "add_edge_feature", {
                "feature_type": "fillet",
                "radius_or_distance": 0.003,
                "edge_indices": json.dumps([edge_index]),
            }, step)
            step += 1

            final = await call(session, "analyze_model", {"analysis_type": "geometry"}, step)
            print("\\nPASS: stepped revolve + groove + hole + fillet")
            print(json.dumps(final, ensure_ascii=False, indent=2, default=str))
            return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
