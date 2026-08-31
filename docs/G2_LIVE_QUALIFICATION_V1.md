# G2 — Live Capability Qualification V1

## Purpose

G1 inventories backend capabilities. G2 does not promote capabilities from static discovery. It executes representative scenarios through the existing MCP/SolidPilot execution path and records live evidence.

## Pipeline

```text
QualificationScenario
        ↓
preflight
        ↓
ensure_ready
        ↓
open_new_part
        ↓
scenario operations
        ↓
analyze_model
        ↓
live evidence
        ↓
separate promotion policy
```

## Rules

1. A discovered tool is not proof of a semantic capability.
2. Historical Ai_Designer evidence is useful for prioritization but does not automatically promote local Solid_Ai capability status.
3. A live qualification run produces evidence; it does not silently mutate the capability registry.
4. Scenario prerequisites must be explicit. A scenario that lacks the geometry/state needed by its operation must be repaired as a scenario definition, not forced through the backend.
5. Verification must use model evidence, not only a `COMPLETED` tool response.

## Current representative scenarios

The catalog currently includes representative probes for cut, pattern, sketch entities, sketch constraints, reference geometry, chamfer, loft, and sweep. The first live batch should prioritize scenarios with complete prerequisites: blind cut and connected sketch geometry. Pattern, constraint, reference, loft, and sweep scenarios require richer setup plans before they can be treated as valid live qualifications.

## Promotion

A capability may be promoted only when the live result contains explicit verification evidence satisfying the scenario contract. A successful tool invocation by itself is not sufficient.

## Generalization target

G2 is capability qualification infrastructure. It is not the final Generalization benchmark. After representative capability coverage is established, the project moves to unseen engineering prompts that traverse:

```text
Natural Language
→ Ai_Designer LLM/semantic layer
→ FeatureGraph
→ generic compiler/lowering
→ runtime reference resolution/recovery
→ SolidPilot
→ SolidWorks
→ verification
```

The final project score is based on successful unseen engineering tasks, not on unit-test count.
