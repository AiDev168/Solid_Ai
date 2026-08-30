# Solid AI — Offline Network Policy

For the current development phase, `Solid_Ai` must not make outbound Internet connections.

## Allowed network traffic

Only loopback traffic required by the local SolidPilot stack is allowed:

- `localhost`
- `127.0.0.1`
- `::1`

The current SolidPilot Python adapter uses HTTP on loopback to communicate with the local C# Execution Service. This is local IPC-like traffic, not Internet access.

## Python process enforcement

Run the GUI with:

```text
gui\run_solid_ai_offline.cmd
```

That launcher adds `gui/offline_guard/sitecustomize.py` to `PYTHONPATH`. Python's startup hook then blocks DNS resolution and socket connections to non-loopback destinations in the GUI/MCP Python processes.

## Static audit

From the repository root:

```powershell
python scripts\audit_offline_network.py
```

The audit fails on non-loopback URL literals in source files. Documentation and caches are excluded because they can contain provenance/reference links without creating runtime connections.

## Model providers

Server-side Sampling fallback is not enabled by default. During the offline phase, do not configure it with a hosted model endpoint. A local OpenAI-compatible endpoint such as LM Studio may be used later because it remains loopback-only.

## Important limitation

The Python guard does not control networking performed by a separately launched native executable. The q3ds C# Execution Service is expected to communicate only with the Python adapter through its configured local HTTP endpoint and with SolidWorks through COM. The static audit must remain green before introducing any new native networking code.

This policy does not modify or bypass the SolidWorks licensing system.
