from __future__ import annotations

import asyncio
import json
import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1] / "vendor" / "q3ds-solidworks-mcp"
PYTHON_EXE = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
SEMANTIC_SERVER = REPO_ROOT / "adapters" / "codex" / "server.py"
LEGACY_SERVER = REPO_ROOT / "adapters" / "claude" / "legacy_server.py"


class McpWorker:
    """Persistent MCP stdio client on a dedicated asyncio event loop."""

    def __init__(self, mode: str, emit) -> None:
        self.mode = mode
        self.emit = emit
        self.thread: threading.Thread | None = None
        self.ready = threading.Event()
        self.stop = threading.Event()
        self.loop: asyncio.AbstractEventLoop | None = None
        self.session: Any = None
        self._stdio_cm: Any = None
        self._session_cm: Any = None
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
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client

            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(
                self._connect(server, ClientSession, StdioServerParameters, stdio_client)
            )
            self.ready.set()
            self.emit("CONNECTED", {"mode": self.mode, "server": str(server)})
            self.loop.run_until_complete(self._idle_until_stop())
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            self.ready.set()
            self.emit("ERROR", self.last_error)
        finally:
            if self.loop and not self.loop.is_closed():
                self.loop.close()

    async def _connect(self, server: Path, ClientSession, StdioServerParameters, stdio_client) -> None:
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
        if self._session_cm is not None:
            await self._session_cm.__aexit__(None, None, None)
        if self._stdio_cm is not None:
            await self._stdio_cm.__aexit__(None, None, None)
        self.session = None

    def submit(self, coro_factory) -> None:
        if not self.loop or self.session is None or not self.ready.is_set():
            raise RuntimeError("MCP session is not connected")
        future = asyncio.run_coroutine_threadsafe(coro_factory(), self.loop)
        future.add_done_callback(self._finish)

    def _finish(self, future) -> None:
        try:
            self.emit("RESULT", future.result())
        except Exception as exc:
            self.emit("ERROR", f"{type(exc).__name__}: {exc}")

    def close(self) -> None:
        self.stop.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)


class SolidAiApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Solid AI — SolidPilot Laboratory v0.2")
        self.root.geometry("1120x800")
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
        ttk.Label(top, text="SolidPilot Laboratory v0.2", font=("Segoe UI", 10)).pack(side="left", padx=10)
        ttk.Button(top, text="Connect", command=self.connect).pack(side="right")
        ttk.Button(top, text="Disconnect", command=self.disconnect).pack(side="right", padx=6)

        mode = ttk.LabelFrame(self.root, text="MCP surface", padding=10)
        mode.pack(fill="x", padx=12, pady=(0, 8))
        ttk.Radiobutton(mode, text="Semantic (current)", value="semantic", variable=self.mode).pack(side="left")
        ttk.Radiobutton(mode, text="Legacy CAD tools (development)", value="legacy", variable=self.mode).pack(side="left", padx=20)
        ttk.Label(mode, text="Status:").pack(side="left", padx=(30, 4))
        ttk.Label(mode, textvariable=self.status).pack(side="left")

        tools = ttk.LabelFrame(self.root, text="Tool call laboratory", padding=10)
        tools.pack(fill="x", padx=12, pady=8)
        row = ttk.Frame(tools)
        row.pack(fill="x")
        ttk.Label(row, text="Tool:").pack(side="left")
        ttk.Entry(row, textvariable=self.tool_name, width=48).pack(side="left", padx=8)
        self.status_btn = ttk.Button(row, text="Status", command=lambda: self._preset("solidworks_status", '{"launch_if_needed": false}'))
        self.status_btn.pack(side="left")
        self.launch_btn = ttk.Button(row, text="Launch / verify SW", command=lambda: self._preset("solidworks_status", '{"launch_if_needed": true}'))
        self.launch_btn.pack(side="left", padx=6)
        ttk.Button(row, text="Pick file", command=self.pick_file).pack(side="right")

        ttk.Label(tools, text="Arguments (JSON object)").pack(anchor="w", pady=(10, 4))
        self.args = scrolledtext.ScrolledText(tools, height=7, wrap=tk.WORD, font=("Consolas", 10))
        self.args.pack(fill="x")
        self.args.insert("1.0", '{"launch_if_needed": false}')

        buttons = ttk.Frame(tools)
        buttons.pack(fill="x", pady=(8, 0))
        ttk.Button(buttons, text="Execute Tool", command=self.execute).pack(side="left")
        ttk.Button(buttons, text="Sketch → Extrude Test", command=self.create_test_block).pack(side="left", padx=8)
        ttk.Button(buttons, text="Clear Log", command=self.clear_log).pack(side="right")

        log = ttk.LabelFrame(self.root, text="Live output", padding=8)
        log.pack(fill="both", expand=True, padx=12, pady=(8, 12))
        self.output = scrolledtext.ScrolledText(log, wrap=tk.WORD, font=("Consolas", 9))
        self.output.pack(fill="both", expand=True)

        self._log("Repository:", str(REPO_ROOT))
        self._log("Python:", str(PYTHON_EXE))
        self._log("Ready. Offline-safe launcher is recommended.")
        self._update_mode_controls()

        self.mode.trace_add("write", lambda *_: self._update_mode_controls())

    def _update_mode_controls(self) -> None:
        semantic = self.mode.get() == "semantic"
        self.status_btn.configure(state="normal" if semantic else "disabled")
        self.launch_btn.configure(state="normal" if semantic else "disabled")

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
        self.disconnect()
        try:
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

    def _connected_worker(self) -> McpWorker | None:
        if not self.worker:
            messagebox.showwarning("SolidPilot", "Connect to an MCP surface first.")
            return None
        if not self.worker.ready.wait(timeout=0.2):
            messagebox.showwarning("SolidPilot", "MCP connection is still starting.")
            return None
        if self.worker.last_error:
            messagebox.showerror("SolidPilot", self.worker.last_error)
            return None
        return self.worker

    def execute(self) -> None:
        worker = self._connected_worker()
        if worker is None:
            return
        try:
            arguments = json.loads(self.args.get("1.0", tk.END).strip() or "{}")
            if not isinstance(arguments, dict):
                raise ValueError("Arguments must be a JSON object")
        except Exception as exc:
            messagebox.showerror("Arguments", f"Invalid JSON: {exc}")
            return

        tool_name = self.tool_name.get().strip()

        async def call() -> Any:
            return await worker.session.call_tool(tool_name, arguments)

        self._emit("CALL", {"tool": tool_name, "arguments": arguments})
        worker.submit(call)

    def create_test_block(self) -> None:
        if self.mode.get() != "legacy":
            self.mode.set("legacy")
            self.connect()
            self.root.after(900, self.create_test_block)
            return
        worker = self._connected_worker()
        if worker is None:
            return

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
            ("extrude_feature", {
                "depth": 0.01,
                "feature_type": "boss",
            }),
        ]

        async def sequence() -> str:
            for index, (name, arguments) in enumerate(steps, start=1):
                self.emit_direct("SEQUENCE", {"step": index, "tool": name, "arguments": arguments})
                result = await worker.session.call_tool(name, arguments)
                self.emit_direct("RESULT", result)
                if getattr(result, "isError", False):
                    raise RuntimeError(f"Sketch → Extrude test failed at tool '{name}'")
            return "Sketch → Extrude test completed."

        worker.submit(sequence)

    def emit_direct(self, kind: str, payload: Any) -> None:
        self.events.put((kind, payload))

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
                value = dict(value.__dict__)
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
