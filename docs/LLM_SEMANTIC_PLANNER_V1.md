# LLM Semantic Planner V1

## Purpose

This is the first controlled use of an LLM in Solid_Ai after the live SolidPilot/SolidWorks execution path was qualified.

The LLM is a **planner**, not a CAD executor.

```text
Engineering prompt
      ↓
Local LLM
      ↓
Semantic FeatureGraph JSON
      ↓
Deterministic validation
      ↓
Future compiler/runtime adapter
      ↓
SolidPilot
      ↓
SolidWorks
```

## Why this boundary

Ai_Designer already established a supervised specialist-agent lifecycle in which workflow state, artifacts, diagnosis and repair are separate concerns. Its `DesignIntegrationLoop` also explicitly permits deterministic or LLM-backed diagnosis/repair implementations while keeping CAD execution behind an injected adapter. The same separation is preserved here.

## Current LLM responsibilities

The LLM may:

- parse natural-language engineering intent;
- identify candidate feature types;
- propose feature dependencies;
- preserve uncertain requirements in params instead of inventing facts.

The LLM may not:

- call SolidWorks;
- emit MCP calls;
- invent backend face/edge indices;
- bypass feature graph validation;
- choose a recovery action outside the deterministic capability set.

## Local-only transport

V1 uses an OpenAI-compatible HTTP API with a default endpoint of `http://127.0.0.1:1234/v1`, suitable for LM Studio or another local compatible server. No cloud endpoint is configured by default.

## Capability boundary

The validator currently permits:

`profile`, `extrude_boss`, `revolve`, `revolve_cut`, `hole_pattern`, `rib`, `fillet`, `chamfer`, `pattern`.

This is a whitelist, not a claim that every capability has been qualified live.

## Validation boundary

Every LLM response is parsed as JSON and validated for:

- required graph fields;
- non-empty features;
- supported feature kinds;
- unique feature IDs;
- valid dependencies;
- dependency-cycle rejection;
- supported units.

A malformed or unsafe plan is rejected before any CAD runtime is called.

## Next integration step

After the local LLM plan contract is green, the next layer is a deterministic FeatureGraph compiler/adapter that maps validated semantic nodes to the already-qualified reference-resolution and SolidPilot execution primitives.

That compiler is where engineering rules, topology evidence, state versions, reference binding and recovery remain deterministic.
