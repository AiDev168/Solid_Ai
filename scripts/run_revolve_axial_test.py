from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT / "vendor" / "q3ds-solidworks-mcp"
PYTHON = REPO / ".venv" / "Scripts" / "python.exe"
SERVER = REPO / "adapters" / "claude" / "legacy_server.py"


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


async def call(session: ClientSession, tool: str, args: dict, step: int):
    print(f"STEP {step}: {tool} {json.dumps(args, ensure_ascii=False)}")
    result = await session.call_tool(tool, args)
    data = parse_result(result)
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

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            n = 1
            await call(session, "ensure_ready", {}, n); n += 1
            await call(session, "open_new_part", {}, n); n += 1
            await call(session, "create_sketch", {"plane": "Front Plane"}, n); n += 1

            profile = [
                (0.000, 0.000, 0.020, 0.000),
                (0.020, 0.000, 0.020, 0.025),
                (0.020, 0.025, 0.030, 0.025),
                (0.030, 0.025, 0.030, 0.080),
                (0.030, 0.080, 0.015, 0.080),
                (0.015, 0.080, 0.015, 0.120),
                (0.015, 0.120, 0.000, 0.120),
                (0.000, 0.120, 0.000, 0.000),
            ]
            for x1, y1, x2, y2 in profile:
                await call(session, "add_sketch_entity", {
                    "entity_type": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2
                }, n)
                n += 1

            await call(session, "extrude_feature", {
                "depth": 0.0,
                "feature_type": "revolve",
                "angle": 360.0,
                "axis_x1": 0.0, "axis_y1": 0.0,
                "axis_x2": 0.0, "axis_y2": 0.001,
            }, n)
            n += 1

            # Revolved annular groove: fresh sketch on the same plane.
            await call(session, "create_sketch", {"plane": "Front Plane"}, n); n += 1
            groove = [
                (0.025, 0.045, 0.031, 0.045),
                (0.031, 0.045, 0.031, 0.051),
                (0.031, 0.051, 0.025, 0.051),
                (0.025, 0.051, 0.025, 0.045),
            ]
            for x1, y1, x2, y2 in groove:
                await call(session, "add_sketch_entity", {
                    "entity_type": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2
                }, n)
                n += 1

            await call(session, "add_sketch_constraint", {
                "constraint_type": "horizontal", "px1": 0.028, "py1": 0.045
            }, n); n += 1
            await call(session, "add_sketch_constraint", {
                "constraint_type": "vertical", "px1": 0.031, "py1": 0.048
            }, n); n += 1
            await call(session, "add_sketch_constraint", {
                "constraint_type": "horizontal", "px1": 0.028, "py1": 0.051
            }, n); n += 1
            await call(session, "add_sketch_constraint", {
                "constraint_type": "vertical", "px1": 0.025, "py1": 0.048
            }, n); n += 1

            await call(session, "extrude_feature", {
                "depth": 0.0,
                "feature_type": "revolve_cut",
                "angle": 360.0,
                "axis_x1": 0.0, "axis_y1": 0.0,
                "axis_x2": 0.0, "axis_y2": 0.001,
            }, n)
            n += 1

            edges = await call(session, "analyze_model", {"analysis_type": "edges"}, n); n += 1
            edge_list = (((edges or {}).get("data") or {}).get("edges") or []) if isinstance(edges, dict) else []
            if not edge_list:
                raise RuntimeError("Revolve test produced no analyzable edges")

            # Deterministically choose the edge closest to the outer 60mm section near Y=55mm.
            target = (0.030, 0.055, 0.000)
            def dist(edge):
                mid = edge.get("mid") or [0.0, 0.0, 0.0]
                return sum((float(mid[i]) - target[i]) ** 2 for i in range(3))
            selected = min(edge_list, key=dist)
            edge_index = int(selected["i"])
            print("SELECTED EDGE:", edge_index, json.dumps(selected, ensure_ascii=False))

            await call(session, "add_edge_feature", {
                "feature_type": "chamfer",
                "radius_or_distance": 0.002,
                "edge_indices": json.dumps([edge_index]),
                "chamfer_type": "distance_angle",
                "angle": 45.0,
                "distance2": 0.0,
                "chamfer_flip": False,
            }, n)
            n += 1

            final = await call(session, "analyze_model", {"analysis_type": "geometry"}, n)
            print("\nPASS: Revolve + Revolved Cut + Sketch Constraints + Topology + Chamfer")
            print(json.dumps(final, ensure_ascii=False, indent=2, default=str))
            return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
