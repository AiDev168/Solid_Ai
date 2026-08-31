# LLM → Feature Graph V1

## Purpose

This is the first application-layer entry point for a real local LLM. It does **not** replace SolidPilot's planner/compiler. The vendored q3ds Feature Graph IR remains the authoritative CAD-neutral contract, and the deterministic compiler remains below the IR.

SolidPilot's architecture explicitly separates AI planning from deterministic compilation: the planner produces CAD-neutral Feature Graph IR, while the SolidWorks compiler lowers it without an LLM. That boundary is preserved here.

## Why this layer exists

The GUI/application needs to accept a natural-language engineering request such as:

> یک براکت موتور 120 در 80 بساز، ضخامت 10، چهار سوراخ M8، دو ریب و لبه‌های بیرونی R5.

The local LLM is responsible for interpreting the request and producing a candidate Feature Graph. It must not emit MCP calls or SolidWorks API calls.

## Local-only policy

The V1 client accepts only localhost endpoints (`127.0.0.1`, `localhost`, `::1`). The default endpoint is the OpenAI-compatible LM Studio endpoint:

`http://127.0.0.1:1234/v1`

This prevents the planner from silently becoming an internet client.

Environment variables:

- `SOLID_AI_LLM_BASE_URL`
- `SOLID_AI_LLM_MODEL`
- `SOLID_AI_LLM_API_KEY`
- `SOLID_AI_LLM_TIMEOUT`

## Contract

```text
User Prompt
   ↓
Local LLM Planner
   ↓
CAD-neutral Feature Graph IR
   ↓
Structural Validation
   ↓
[future step] SolidPilot Feature Graph compiler
   ↓
Reference resolution / execution / verification
```

The validator rejects raw fields such as `tool`, `arguments`, `call_tool`, or `mcp`, rejects unknown feature types, requires meters, and rejects references to future/unknown nodes.

## Reused Ai_Designer principles

The first LLM boundary deliberately follows the old project's strongest architecture rather than importing its old execution stack:

- workflow states separate INTENT and PLAN from CAD execution and verification;
- artifacts are explicit rather than hidden mutable state;
- execution/verification/recovery remain ports below the planning layer;
- diagnosis and repair remain separate from LLM planning;
- the LLM proposes semantic design structure, while deterministic machinery decides whether and how it can be executed.

This is adapted from the previously implemented Ai_Designer design-loop architecture, where PLAN → EXECUTE → VERIFY → DIAGNOSIS → REPAIR is explicit and backend-neutral.

## What this does NOT claim

A valid Feature Graph is a **plan proposal**, not proof of engineering correctness. The next stages must:

1. validate against the vendored Feature Graph capability vocabulary;
2. lower the graph through SolidPilot's existing deterministic compiler path;
3. execute on live SolidWorks;
4. independently verify geometry and engineering requirements;
5. feed classified failures into bounded recovery.
