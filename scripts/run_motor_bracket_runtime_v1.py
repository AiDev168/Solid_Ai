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
from integration.motor_bracket_runtime_v1 import MotorBracketRuntimeV1
async def main() -> int:
    params = StdioServerParameters(command=str(PYTHON), args=[str(SERVER)], cwd=str(REPO), env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            report = await MotorBracketRuntimeV1(session).run()
            print(json.dumps({"ok": report.ok, "feature_status": report.feature_status, "evidence": [e.__dict__ for e in report.evidence], "recovery": [str(x) for x in report.recovery], "errors": report.errors}, ensure_ascii=False, indent=2, default=str))
            return 0 if report.ok else 1
if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
