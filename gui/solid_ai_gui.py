from __future__ import annotations

import asyncio
import json
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


REPO_ROOT = Path(__file__).resolve().parents[1] / "vendor" / "q3ds-solidworks-mcp"
PYTHON_EXE = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
SEMANTIC_SERVER = REPO_ROOT / "adapters" / "codex" / "server.py"
LEGACY_SERVER = REPO_ROOT / "adapters" / "claude" / "legacy_server.py"


class McpWorker:
    """Own one persistent MCP stdio session on a background asyncio loop."""

    def __init__(self, mode: str, emit) -> None:
        self.mode = mode
        self.emit = emit
        self.thread: threading.Thread | None = None
        self.ready = threading.Event()
        self.stop = threading.Event()
        self.loop: asyncio.AbstractEventLoop | None = None
        self.session: ClientSession | None = None
        self._stdio_cm = None
        self._session_cm = None
        self.last_error: str | None = None

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        if not PYTHON_EXE.exists():
            raise FileNotFoundError(f"Repository Python not found: {PYTHON_EXE}")
        server = SEMANTIC_SERVER if self.mode == "semantic" else LEGACY_SERVER
        if not server.exists():
            raise FileNotFoundError(f"MCP server entry point not found: {server}")
        self.thread = threading.Thread(target=self._thread_main, args=(server,), daemon=True)
        self.thread.start()

    def _thread_main(self, server: Path) -> None:
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self._connect(server))
            self.ready.set()
            self.emit("CONNECTED", {"mode": self.mode, "server": str(server)})
            self.loop.run_until_complete(self._idle_until_stop())
        except Exception as exc:  # pragma: no cover - exercised by local host integration
            self.last_error = f"{type(exc).__name__}: {exc}"
            self.ready.set()
            self.emit("ERROR", self.last_error)
        finally:
            if self.loop and not self.loop.is_closed():
                self.loop.close()

    async def _connect(self, server: Path) -> None:
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONPATH"] = os.pathsep.join(
            [str(REPO_ROOT), str(REPO_ROOT / "adapters" / "claude"), env.get("PYTHONPATH", "")]
        ).strip(os.pathsep)

        params = StdioServerParameters(
            command=str(PYTHON_EXE),
            args=[str(server)],
            cwd=str(REPO_ROOT),
            env=env,
        )
        self._stdio_cm = stdio_client(params)
        read, write = await self._stdio_cm.__aenter__()
        self._session_cm = ClientSession(read, write)
        self.session = await self._session_cm.__aenter__()
        await self.session.initialize()

    async def _idle_until_stop(self) -> None:
        while not self.stop.is_set():
            await asyncio.sleep(0.05)
        await self._close()

    async def _close(self) -> None:
        if self._session_cm is not None:
            await self._session_cm.__aexit__(None, None, None)
            self._session_cm = None
            self.session = None
        if self._stdio_cm is not None:
            await self._stdio_cm.__aexit__(None, None, None)
            self._stdio_cm = None

    def call(self, tool_name: str, arguments: dict[str, Any]) -> None:
        if not self.loop or not self.session or not self.ready.is_set():
            raise RuntimeError("MCP session is not connected")
        future = asyncio.run_coroutine_threadsafe(
            self._call_tool(tool_name, arguments), self.loop
        )
        future.add_done_callback(self._finish_call)

    async def _call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        self.emit("CALL", {"tool": tool_name, "arguments": arguments})
        result = await self.session.call_tool(tool_name, arguments)
        return result

    def _finish_call(self, future) -> None:
        try:
            result = future.result()
            self.emit("RESULT", result)
        except Exception as exc:
            self.emit("ERROR", f"{type(exc).__name__}: {exc}")

    def close(self) -> None:
        self.stop.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)


class SolidAiApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Solid AI — SolidPilot Laboratory v0.1")
        self.root.geometry("1120x780")
        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.worker: McpWorker | None = None

        self.mode = tk.StringVar(value="semantic")
        self.status = tk.StringVar(value="Disconnected")
        self.tool_name = tk.StringVar(value="solidworks_status")

        self._build_ui()
        self.root.after(100, self._poll_events)
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=12)
        top.pack(fill="x")

        ttk.Label(top, text="Solid AI", font=("Segoe UI", 18, "bold")).pack(side="left")
        ttk.Label(top, text="SolidPilot Laboratory v0.1", font=("Segoe UI", 10)).pack(side="left", padx=10)

        ttk.Button(top, text="Connect", command=self.connect).pack(side="right")
        ttk.Button(top, text="Disconnect", command=self.disconnect).pack(side="right", padx=6)

        mode_frame = ttk.LabelFrame(self.root, text="MCP surface", padding=10)
        mode_frame.pack(fill="x", padx=12, pady=(0, 8))
        ttk.Radiobutton(mode_frame, text="Semantic (default)", value="semantic", variable=self.mode).pack(side="left")
        ttk.Radiobutton(mode_frame, text="Legacy CAD tools (development)", value="legacy", variable=self.mode).pack(side="left", padx=20)
        ttk.Label(mode_frame, text="Status:").pack(side="left", padx=(30, 4))
        ttk.Label(mode_frame, textvariable=self.status).pack(side="left")

        prompt_frame = ttk.LabelFrame(self.root, text="Tool call", padding=10)
        prompt_frame.pack(fill="x", padx=12, pady=8)

        row = ttk.Frame(prompt_frame)
        row.pack(fill="x")
        ttk.Label(row, text="Tool:").pack(side="left")
        ttk.Entry(row, textvariable=self.tool_name, width=48).pack(side="left", padx=8)
        ttk.Button(row, text="Use status", command=lambda: self._preset("solidworks_status", '{"launch_if_needed": false}')).pack(side="left")
        ttk.Button(row, text="Connect + launch", command=lambda: self._preset("solidworks_status", '{"launch_if_needed": true}')).pack(side="left", padx=6)
        ttk.Button(row, text="Pick file", command=self.pick_file).pack(side="right")

        ttk.Label(prompt_frame, text="Arguments (JSON object)").pack(anchor="w", pady=(10, 4))
        self.args = scrolledtext.ScrolledText(prompt_frame, height=7, wrap=tk.WORD, font=("Consolas", 10))
        self.args.pack(fill="x")
        self.args.insert("1.0", '{"launch_if_needed": false}')

        action_row = ttk.Frame(prompt_frame)
        action_row.pack(fill="x", pady=(8, 0))
        ttk.Button(action_row, text="Execute Tool", command=self.execute).pack(side="left")
        ttk.Button(action_row, text="Create Test Sketch", command=self.create_test_sketch).pack(side="left", padx=8)
        ttk.Button(action_row, text="Clear Log", command=self.clear_log).pack(side="right")

        log_frame = ttk.LabelFrame(self.root, text="Live output", padding=8)
        log_frame.pack(fill="both", expand=True, padx=12, pady=(8, 12))
        self.output = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, font=("Consolas", 9))
        self.output.pack(fill="both", expand=True)

        self._log("Repository:", str(REPO_ROOT))
        self._log("Python:", str(PYTHON_EXE))
        self._log("Ready. Connect, then execute a real SolidPilot tool.")

    def _preset(self, name: str, args: str) -> None:
        self.tool_name.set(name)
        self.args.delete("1.0", tk.END)
        self.args.insert("1.0", args)

    def pick_file(self) -> None:
        path = filedialog.askopenfilename(title="Select CAD file")
        if path:
            self.args.delete("1.0", tk.END)
            self.args.insert("1.0", json.dumps({"file_path": path}, ensure_ascii=False, indent=2))

    def connect(self) -> None:
        try:
            self.disconnect()
            self.status.set("Connecting...")
            self.worker = McpWorker(self.mode.get(), self._emit)
            self.worker.start()
        except Exception as exc:
            self.status.set("Connection failed")
            messagebox.showerror("SolidPilot", str(exc))

    def disconnect(self) -> None:
        if self.worker:
            self.worker.close()
            self.worker = None
        self.status.set("Disconnected")

    def execute(self) -> None:
        if not self.worker or not self.worker.ready.wait(timeout=0.2):
            messagebox.showwarning("SolidPilot", "Connect to an MCP surface first.")
            return
        if self.worker.last_error:
            messagebox.showerror("SolidPilot", self.worker.last_error)
            return
        try:
            arguments = json.loads(self.args.get("1.0", tk.END).strip() or "{}")
            if not isinstance(arguments, dict):
                raise ValueError("Arguments must be a JSON object")
        except Exception as exc:
            messagebox.showerror("Arguments", f"Invalid JSON: {exc}")
            return
        try:
            self.worker.call(self.tool_name.get().strip(), arguments)
        except Exception as exc:
            self._emit("ERROR", f"{type(exc).__name__}: {exc}")

    def create_test_sketch(self) -> None:
        """Run a small, real legacy CAD sequence; no custom COM code is used here."""
        if self.mode.get() != "legacy":
            self.mode.set("legacy")
            self.connect()
            self.root.after(700, self.create_test_sketch)
            return
        if not self.worker or not self.worker.ready.wait(timeout=0.2) or self.worker.last_error:
            messagebox.showwarning("SolidPilot", "Legacy CAD surface is not connected.")
            return

        def run_sequence() -> None:
            steps = [
                ("ensure_ready", {}),
                ("open_new_part", {}),
                ("create_sketch", {"plane": "Top Plane"}),
                ("add_sketch_entity", {
                    "entity_type": "rectangle",
                    "x1": -0.05,
                    "y1": -0.03,
                    "x2": 0.05,
                    "y2": 0.03,
                }),
            ]
            self._run_sequence(steps, 0)

        threading.Thread(target=run_sequence, daemon=True).start()

    def _run_sequence(self, steps, index: int) -> None:
        if index >= len(steps):
            self._emit("SEQUENCE_COMPLETE", "Test sketch sequence submitted.")
            return
        name, args = steps[index]
        if not self.worker:
            return
        self._emit("SEQUENCE", {"step": index + 1, "tool": name, "arguments": args})

        async def one_call() -> Any:
            assert self.worker is not None and self.worker.session is not None
            return await self.worker.session.call_tool(name, args)

        assert self.worker.loop is not None
        future = asyncio.run_coroutine_threadsafe(one_call(), self.worker.loop)

        def done(fut) -> None:
            try:
                result = fut.result()
                self._emit("RESULT", result)
                if getattr(result, "isError", False):
                    self._emit("SEQUENCE_ABORTED", {"tool": name})
                    return
                self.root.after(0, lambda: self._run_sequence(steps, index + 1))
            except Exception as exc:
                self._emit("ERROR", f"{type(exc).__name__}: {exc}")
                self._emit("SEQUENCE_ABORTED", {"tool": name})

        future.add_done_callback(done)

    def _emit(self, kind: str, payload: Any) -> None:
        self.events.put((kind, payload))

    def _poll_events(self) -> None:
        while True:
            try:
                kind, payload = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "CONNECTED":
                self.status.set(f"Connected — {payload['mode']}")
            elif kind == "ERROR":
                self.status.set("Error")
            self._log(kind, self._format_payload(payload))
        self.root.after(100, self._poll_events)

    @staticmethod
    def _format_payload(value: Any) -> str:
        try:
            if hasattr(value, "model_dump"):
                value = value.model_dump(mode="json")
            elif hasattr(value, "__dict__"):
                data = dict(value.__dict__)
                value = data
            return json.dumps(value, ensure_ascii=False, indent=2, default=str)
        except Exception:
            return str(value)

    def _log(self, *parts: str) -> None:
        self.output.insert(tk.END, " ".join(parts) + "\n")
        self.output.see(tk.END)

    def clear_log(self) -> None:
        self.output.delete("1.0", tk.END)

    def shutdown(self) -> None:
        self.disconnect()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    SolidAiApp(root)
    root.mainloop()
