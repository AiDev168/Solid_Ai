# Face Reference Recovery Integration V1

## Purpose

This milestone applies the proven Ai_Designer recovery architecture to the Solid_Ai face-reference lifecycle. The goal is to solve face-support failures at the shared reference/recovery boundary rather than patch individual features.

## Source assets reused

- `Ai_Designer/solidpilot/topology_evidence_v1.py`: backend geometry is evidence; backend indices are selectors, not semantic identity.
- `Ai_Designer/solidpilot/topology_rebinding_v1.py`: geometry-backed face/edge anchor rebinding with ambiguity rejection.
- `Ai_Designer/recovery/diagnosis.py`: known topology failures are retryable; unknown failures remain fail-closed.
- `Ai_Designer/recovery/topology_solver.py`: one registered deterministic topology-rebinding solver.
- `Ai_Designer/recovery/controller.py`: bounded orchestration over registered solvers.
- `Ai_Designer/recovery/live_recovery_v1.py`: canonical pattern for fresh evidence -> bounded recovery -> retry -> verification.
- `Ai_Designer/agentic/recovery_coordinator_v1.py`: optional future LLM decision layer constrained to proven solver-backed actions.

## Root cause found in Solid_Ai

The existing reference resolver normalized backend aliases (`i`, `index`, `backend_index`) only when evidence passed through helper functions. Direct `ReferenceEvidence` could still contain `i`, while the resolver sorted on `backend_index`. This made four reference-resolution tests fail with `KeyError`.

A second, more important gap was in the face-consumer lifecycle. `create_sketch` could return `COMPLETED` while its measured sketch frame did not actually lie on the semantic face that was resolved for the feature. The previous motor-bracket runner proceeded to create circles and only discovered the inconsistency later as `EXTRUSION_FAILED`.

## New invariant

For any semantic planar-face consumer:

```text
resolve semantic face
    -> bind fresh backend selector + geometry evidence
    -> create sketch on that selector
    -> verify measured sketch frame against face geometry
    -> only then create downstream geometry
```

A failed selector or a successful-but-wrong face support is classified as `STALE_FACE_SELECTOR` and enters the existing topology-rebinding solver path:

```text
failure
  -> diagnosis(topology, retryable)
  -> fresh face evidence
  -> geometry-backed anchor rebind
  -> one canonical retry
  -> support verification again
  -> fail closed if still wrong
```

No hard-coded face index, blind retry, or feature-specific recovery is introduced.

## Verification rule

`create_sketch` support verification compares:

1. the resolved face normal against the sketch-frame normal (unsigned parallelism), and
2. the sketch-frame origin against the resolved face plane (point-to-plane distance).

The sketch origin does not have to equal the face representative point; it only has to lie in the same plane.

## LLM boundary

The deterministic solver remains the source of truth. A future LLM recovery decision may select only an explicitly allowed, solver-backed action. It cannot emit SolidWorks commands or invent a repair strategy. This follows the Ai_Designer agentic recovery contract.

## Current scope

This milestone changes the shared reference/recovery lifecycle and applies it to the Motor Bracket hole-pattern and rib face consumers. It does not claim that arbitrary natural-language CAD is solved; additional semantic feature lowerings and verifiers can reuse the same lifecycle.
