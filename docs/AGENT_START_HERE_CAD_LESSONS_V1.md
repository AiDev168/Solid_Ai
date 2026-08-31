# Agent Start Here — CAD Automation Lessons V1

## Current proven state

Solid_Ai has a live SolidPilot path to SolidWorks and now also contains selected Ai_Designer assets for deterministic reference resolution and bounded recovery.

The Motor Bracket V2 live proof completed these semantic stages:

- base_profile
- base
- mounting_holes
- rib_left
- rib_right
- outer_fillets

All returned COMPLETED and the final runtime reported ok=true.

## Lesson 1 — COMPLETED is not verification

A SolidWorks operation can report COMPLETED while its semantic support is wrong. Verify measured geometry and support frame after every reference-sensitive mutation.

## Lesson 2 — Backend indices are selectors, not identity

Never treat an edge_index or face_index as a persistent semantic identity. Capture evidence at a specific state_version and re-resolve after topology mutations.

## Lesson 3 — Reference intent is backend-neutral

Represent references as intent such as:

- extrude_end_face
- outer_extrusion_boundary
- centerline
- topological role

Only the resolver may lower that intent to a current backend selector.

## Lesson 4 — Coordinate systems must be explicit

Do not assume SolidWorks global XYZ matches a sketch's local 2D frame. Store origin, xdir, ydir and derived normal. Project semantic coordinates into the active sketch frame before emitting entities.

## Lesson 5 — Degenerate topology is evidence, not necessarily failure

Edge lists may contain zero-length or otherwise non-directional artifacts. Resolver code should classify and skip such candidates unless the operation requires them.

## Lesson 6 — Ambiguity is a first-class failure

When two candidates cannot be distinguished safely, fail closed. Do not pick the first, nearest, or lowest index merely to keep execution moving.

## Lesson 7 — Recovery must be bounded

The recovery controller may retry only after a failure is classified and fresh topology evidence is collected. Unknown failures remain fail-closed.

## Lesson 8 — Use LLM above deterministic solvers

LLMs can help interpret user intent, generate candidate plans, rank allowed recovery strategies, and explain diagnostics. They should not invent arbitrary CAD calls or bypass verification.

## Lesson 9 — Semantic plans are graphs, not scripts

A complex request should become a dependency-aware feature graph. Runtime lowering should consume that graph; tests should not encode the entire design as one hand-written linear script.

## Lesson 10 — Separate capability qualification from generality claims

A green live test proves a specific capability path. It does not prove unrestricted natural-language CAD generation.

Current evidence supports strong multi-feature prismatic-part execution plus topology-aware reference handling. Revolve, sweep, loft, assemblies, drawings, threads, and engineering analysis must be qualified independently.

## Lesson 11 — Root-cause workflow

For each new failure:

1. reproduce on live SolidWorks when possible;
2. classify the failure boundary;
3. inspect evidence and state_version;
4. identify the missing abstraction;
5. fix the abstraction;
6. add a regression test;
7. rerun the smallest contract suite;
8. rerun the live qualification;
9. document the lesson.

Never modify only the test expectation to make a failure disappear.

## Lesson 12 — Current Motor Bracket qualification limits

The current Motor Bracket V2 proves the geometric pipeline:

120 x 80 x 10 mm base, four Ø8 mm through holes, two additive rib representations, and outer R5 fillet execution.

It does not yet prove:

- native ISO M8 tapped threads;
- native SolidWorks Rib feature semantics;
- unrestricted material/strength reasoning;
- automatic engineering validation of load, stress, or safety factor.

Those capabilities require separate verified contracts.

## Next qualification

Stepped axial part:

- 360 degree revolve;
- revolved groove;
- face-based hole;
- post-mutation topology inspection;
- fillet;
- final geometry verification.

The revolve axis must be resolved from the actual centerline segment in the sketch rather than a guessed coordinate pair.

## For future agents

Read this document before changing the runtime. Prefer reuse of existing Ai_Designer recovery/reference/planning assets over new parallel abstractions. Keep the SolidPilot execution backend authoritative and keep all recovery deterministic, observable, bounded, and evidence-driven.
