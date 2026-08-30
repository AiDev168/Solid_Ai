# Solid AI

**Solid AI** is the experimental application layer for our SolidWorks AI engineering system. The repository is intentionally designed for active development rather than as a commercial product.

## Project boundary

```text
User / engineering prompt / CAD input
                  ↓
              Solid AI
          GUI + orchestration
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

The important change from the initial bootstrap is that **q3ds-solidworks-mcp is not a submodule anymore**. Its required source is copied into:

```text
vendor/q3ds-solidworks-mcp/
```

This is deliberate. During this development phase we need to be able to inspect, debug and modify SolidPilot itself whenever the evidence shows that the existing backend does not provide the capability we need.

## What lives here

```text
Solid_Ai/
├── vendor/
│   └── q3ds-solidworks-mcp/     # complete editable SolidPilot source
├── gui/                         # Solid AI GUI
├── app/                         # local orchestration / AI integration
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

## First vertical slice

The first useful slice is intentionally small:

```text
Prompt
  ↓
Solid AI GUI
  ↓
LLM / planning adapter
  ↓
SolidPilot
  ↓
Supported deterministic operation
  ↓
SolidWorks
  ↓
Readback / verification
  ↓
GUI evidence + status
```

A representative target is an engineering request such as:

> Create a motor bracket, 6 mm thick, with four M8 mounting holes and the specified material.

The GUI must expose what actually happened. It must not claim that unrestricted text-to-CAD is already solved.

## Local environment

The development environment already contains the core Windows/SolidWorks stack used by SolidPilot. In particular, the project is expected to run against:

- Windows 10/11;
- a licensed SOLIDWORKS installation;
- Python matching the backend requirements;
- .NET Framework 4.8.1 for the native execution service;
- local SOLIDWORKS COM/API access.

The vendored backend includes its Python MCP/planning code and the C# SolidWorks execution components. The execution project references the installed SolidWorks Interop assemblies and targets .NET Framework 4.8.1.

## Working with the vendored SolidPilot

From the repository root:

```powershell
git clone https://github.com/AiDev168/Solid_Ai.git
cd Solid_Ai
```

The backend source is then directly available under:

```text
vendor/q3ds-solidworks-mcp/
```

Do not expect the repository to behave like a black-box dependency. During development, changing files under `vendor/q3ds-solidworks-mcp/` is an accepted and expected workflow when backed by tests and evidence.

## Provenance

The current vendored source originates from:

```text
https://github.com/zarcherlot/q3ds-solidworks-mcp
```

The source snapshot initially selected for this repository is commit:

```text
3e154abb4422afbf5173fae21f17cd8b5969bdb0
```

A repository workflow is also included to refresh the vendored source from upstream when explicitly needed. The workflow copies the complete source tree (including non-text assets) into `vendor/q3ds-solidworks-mcp/` rather than creating another submodule.

## Development strategy

### Milestone 0 — repository and backend foundation

Complete vendoring of SolidPilot, local environment verification and a clean source-of-truth inside `Solid_Ai`.

### Milestone 1 — GUI foundation

Build the local GUI with backend health/status and a transparent execution log.

### Milestone 2 — first real command path

Connect a controlled engineering request to a supported SolidPilot operation and verify the resulting LIVE SolidWorks model.

### Milestone 3 — inspect and modify real CAD

Open/inspect an existing CAD document, perform a controlled mutation, and verify persisted state.

### Milestone 4 — evidence-first UI

Expose plan, execution, verification, failures and capability boundaries directly in the GUI.

### Milestone 5 — capability expansion

Add CAD capabilities one at a time, driven by failing real use cases and regression tests.

### Milestone 6 — connect the broader Ai_Designer architecture

Bring in the requirements, engineering-intent, planning, orchestration and recovery concepts from `Ai_Designer` only where they solve a demonstrated problem.

## Relationship to Ai_Designer

```text
Ai_Designer
    = higher-level autonomous engineering architecture
      requirements + engineering intent + planning + orchestration + recovery

Solid_Ai
    = practical GUI + local AI/CAD interaction + experiments
      + direct integration with the editable SolidPilot backend

SolidPilot
    = deterministic CAD planning/execution + SolidWorks integration
```

The purpose of `Solid_Ai` is not to replace `Ai_Designer`. It is the practical execution and validation environment where we can prove what the CAD layer can actually do.

## Important engineering rule

Every new capability should follow this loop:

```text
Real user case
    ↓
Failing / missing capability
    ↓
Locate the actual boundary in SolidPilot
    ↓
Smallest architectural fix
    ↓
Focused tests
    ↓
Real SolidWorks execution
    ↓
Independent verification
    ↓
Keep the change only if evidence supports it
```

This keeps us from rebuilding features speculatively or creating parallel implementations of the same CAD mechanism.

## Licensing

The vendored upstream project is distributed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**. Its license and attribution must remain with the vendored source. See `vendor/q3ds-solidworks-mcp/LICENSE` for the upstream license text.

`Solid_Ai` is a development repository and should preserve the provenance and licensing boundaries of the upstream code while we work on the combined system.
