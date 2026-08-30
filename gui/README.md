# Solid AI — SolidPilot Laboratory GUI v0.1

This GUI is a development laboratory for the real q3ds/SolidPilot runtime vendored in this repository.

It intentionally does **not** import the previous Ai_Designer planner, CAD-IR, agent swarm, or recovery architecture.

## What v0.1 proves

```text
GUI
  -> MCP stdio client
  -> q3ds SolidPilot adapter
  -> C# Execution Service
  -> SolidWorks COM
  -> SOLIDWORKS
```

The GUI has two MCP surfaces:

- **Semantic**: `adapters/codex/server.py`, the current small semantic production surface.
- **Legacy CAD**: `adapters/claude/legacy_server.py`, retained here as a development laboratory because it exposes the actual CAD primitives needed to discover and prove modeling capabilities.

The GUI can connect, display live responses, execute any discovered tool by name with a JSON object, and run a small real test sequence that opens a Part, creates a sketch on the Top Plane, and creates a 100 x 60 mm rectangle.

No mock SolidWorks layer is used.

## Run on Windows

From a checkout of `AiDev168/Solid_Ai`:

```text
gui\run_solid_ai.cmd
```

The launcher explicitly uses:

```text
vendor\q3ds-solidworks-mcp\.venv\Scripts\python.exe
```

so the GUI does not depend on the active PowerShell virtual environment.

## First test

1. Start the GUI with `gui\run_solid_ai.cmd`.
2. Choose **Legacy CAD tools (development)**.
3. Click **Connect**.
4. Click **Create Test Sketch**.
5. Watch SOLIDWORKS and the Live output panel.

The expected sequence is:

```text
ensure_ready
open_new_part
create_sketch (Top Plane)
add_sketch_entity (rectangle)
```

The test intentionally stops at a real sketch rectangle. We will only add extrusion, holes, fillets, dimensions, or natural-language planning after each capability has been independently proven on the real SolidWorks host.

## Generic tool laboratory

The **Tool call** area accepts any tool name and JSON object. This is intentional: when a new SolidPilot capability is discovered, we can exercise it immediately without first designing another application abstraction.

Examples for the Legacy CAD surface:

```json
{}
```

for:

```text
ensure_ready
open_new_part
```

and:

```json
{"plane":"Top Plane"}
```

for:

```text
create_sketch
```

The repository's own tool documentation remains the source of truth for parameter names and units.

## Scope boundary

This GUI is not yet a natural-language engineering planner. In particular, a sentence such as:

> build a motor bracket for 2 kN load using M8 bolts

is deliberately **not** translated into engineering dimensions by this GUI yet. That capability must be added only after the underlying CAD primitives and an evidence-backed planning contract are proven.
