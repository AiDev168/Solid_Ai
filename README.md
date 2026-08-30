# Solid AI

**Solid AI** is the experimental application layer for our SolidWorks AI engineering system. The repository is intentionally designed for active development rather than as a commercial product.

## Project boundary

```text
User / engineering prompt / CAD input
                  ↓
              Solid AI
          GUI + experiments
                  ↓
        q3ds SolidPilot source
        (fully vendored, editable)
                  ↓
      deterministic CAD planning
           and execution
                  ↓
        SolidWorks COM / API
                  ↓
          LIVE SolidWorks
                  ↓
       verification + evidence
```

The q3ds-solidworks-mcp source is fully copied into:

```text
vendor/q3ds-solidworks-mcp/
```

This is deliberate. During this development phase we need to be able to inspect, debug and modify SolidPilot itself whenever real evidence shows that the existing backend does not provide the capability we need.

## What lives here

```text
Solid_Ai/
├── vendor/
│   └── q3ds-solidworks-mcp/     # complete editable SolidPilot source
├── gui/
│   ├── solid_ai_gui.py          # local MCP laboratory GUI
│   ├── run_solid_ai.cmd         # Windows launcher using the repo venv
│   └── README.md                # GUI usage
├── app/                         # future local orchestration / AI integration
├── tests/                       # integration and product-level tests
├── docs/                        # architecture, decisions and experiments
└── README.md
```

The vendored backend is kept as a normal source tree, not as a Git submodule. Its own Git metadata is intentionally not copied into `vendor/`.

## Why we are doing this

This repository is our working laboratory for the real SolidWorks path. We are **not** optimizing for a clean commercial packaging model yet. We are optimizing for:

1. getting a real GUI-to-SolidWorks path working;
2. understanding exactly what SolidPilot already does;
3. testing the boundaries of its planning/execution capabilities;
4. changing the backend directly when a real gap is demonstrated;
5. keeping every change testable and reproducible.

We should not build a second CAD execution stack beside SolidPilot unless testing proves that a capability genuinely cannot be implemented safely inside the existing architecture.

## GUI v0.1 — SolidPilot Laboratory

The first GUI is intentionally a **development laboratory**, not an artificial claims-based text-to-CAD product.

Run on Windows from the repository root:

```text
gui\run_solid_ai.cmd
```

The launcher explicitly uses:

```text
vendor\q3ds-solidworks-mcp\.venv\Scripts\python.exe
```

so the GUI does not depend on which PowerShell virtual environment happens to be active.

The GUI provides two real MCP surfaces:

```text
Semantic
  → adapters/codex/server.py

Legacy CAD tools (development)
  → adapters/claude/legacy_server.py
```

The semantic surface is the current narrow MCP contract. The legacy surface is deliberately available in the laboratory because it exposes actual CAD primitives such as opening a part, creating sketches and adding sketch entities. We can use those primitives to prove capabilities one at a time without importing the old Ai_Designer planner.

### First real GUI experiment

1. Start `gui\run_solid_ai.cmd`.
2. Select **Legacy CAD tools (development)**.
3. Click **Connect**.
4. Click **Create Test Sketch**.
5. Observe the live SolidWorks document and the GUI's Live output.

The current test sequence is:

```text
ensure_ready
  ↓
open_new_part
  ↓
create_sketch (Top Plane)
  ↓
add_sketch_entity (100 × 60 mm rectangle)
```

The GUI also accepts an arbitrary SolidPilot tool name plus a JSON-object argument payload. That gives us a transparent laboratory for discovering and proving additional capabilities before we turn them into higher-level workflows.

## First vertical slice

The near-term target is intentionally small:

```text
GUI
  ↓
real SolidPilot tool
  ↓
C# Execution Service
  ↓
SolidWorks COM
  ↓
LIVE model
  ↓
readback / evidence
```

A representative future target is an engineering request such as:

> Create a motor bracket, 6 mm thick, with four M8 mounting holes and the specified material.

The GUI must expose what actually happened. It must not claim that unrestricted natural-language engineering-to-CAD is already solved.

## Proven local backend verification

The q3ds backend has already been verified on the development workstation with:

```text
Python 3.12.10                         PASS
repository host setup                 PASS
C# SolidWorks Execution Service       PASS
HTTP /health                          UP
MCP stdio initialization              PASS
SolidWorks COM attachment             PASS
SolidWorks version                    34.3.2
```

Those checks establish the execution substrate; they do not establish that arbitrary engineering prompts are solvable.

## Scope boundary with Ai_Designer

The previous `Ai_Designer` repository contains useful, proven SolidWorks integration code and an older interactive Text-to-CAD demo. We will reuse only specific components that have independent evidence of usefulness, such as SolidWorks activation, template discovery, interactive process handling, file/evidence handling, and proven COM mechanics.

We intentionally do **not** import the previous planner, agent swarm, generic engineering reasoning, or broad Text-to-CAD pipeline into the first Solid_Ai GUI. Those capabilities are reintroduced only when a concrete real-world CAD gap requires them and the new behavior is independently verified.

```text
Ai_Designer
    = source of previously proven integration techniques

Solid_Ai
    = practical GUI laboratory + experiments
      + editable SolidPilot backend

SolidPilot
    = CAD execution/planning substrate
```

## Capability development rule

Every new capability follows this loop:

```text
Real user case
    ↓
Observe a real failure / missing capability
    ↓
Locate the actual SolidPilot boundary
    ↓
Make the smallest useful change
    ↓
Run focused tests
    ↓
Run against real SolidWorks
    ↓
Read back / independently verify
    ↓
Keep the change only if evidence supports it
```

This prevents us from rebuilding large speculative architectures before the CAD layer has demonstrated the underlying capability.

## Local environment

The repository is intended for a Windows workstation with:

- a licensed SOLIDWORKS installation;
- Python 3.12 for the q3ds environment;
- .NET Framework 4.8.1;
- installed SolidWorks API Interop assemblies;
- local SOLIDWORKS COM/API access.

## Provenance

The vendored source originates from:

```text
https://github.com/zarcherlot/q3ds-solidworks-mcp
```

Initial source snapshot:

```text
3e154abb4422afbf5173fae21f17cd8b5969bdb0
```

The vendored source is editable in this repository. Its upstream license and attribution remain in `vendor/q3ds-solidworks-mcp/`.

## Licensing

The vendored upstream project is distributed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**. Preserve its license and attribution. See `vendor/q3ds-solidworks-mcp/LICENSE` and `vendor/q3ds-solidworks-mcp/NOTICE.md`.
