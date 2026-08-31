# Architecture Reuse Audit — Requirements → Intent Integration V1

**Status:** AUDITED / DECISION READY  
**Repository:** `AiDev168/Solid_Ai`  
**Branch:** `integration/aidesigner-canonical-v1`  
**Reference repository:** `AiDev168/Ai_Designer`  
**Reference branch:** `phase8-capability-convergence-v1`  
**Audit date:** 2026-08-31

## 1. Purpose

This audit was performed before making any new implementation change for the current live composed failure around geometry such as `fillet.radius_m`.

The objective was to answer one question:

> Does Ai_Designer already contain the required semantic, requirements, clarification, intent, or lifecycle capability, and is the current problem actually an integration/wiring gap rather than a missing subsystem?

The audit is explicitly governed by the no-parallel-architecture rule. No new requirements parser, semantic normalizer, clarification engine, intent pipeline, planner, CAD-IR, compiler, runtime, or recovery authority should be introduced unless this audit establishes that the existing canonical asset is insufficient.

## 2. Authoritative architecture found

The current normative Ai_Designer architecture is:

```text
User / Conversation
        ↓
EngineeringJobV1 / EngineeringFrontDoorV1
        ↓
Requirement Evidence
        ↓
semantic canonicalization / equivalence classes
        ↓
requirement gap diagnosis / targeted clarification
        ↓
RequirementsV2
        ↓
IntentV2 / IntentContractV1
        ↓
EngineeringSystemV1
        ↓
deterministic binding
        ↓
MultiFeaturePlannerV1
        ↓
AiDesigner → SolidPilot bridge
        ↓
SolidPilot Feature Graph IR
        ↓
SolidPilot compiler / runtime / SolidWorks
```

This is consistent across the current roadmap, phase-boundary matrix, continuation memory, and reuse matrix. SolidPilot remains the canonical CAD backend and Feature Graph IR spine. No competing CAD runtime is allowed.

## 3. Existing Ai_Designer assets that directly cover the challenged area

### 3.1 Canonical semantic registry

`src/ai_designer/engineering/requirements_semantic_contract_v1.py`

This is the sole semantic registry. It already defines:

- semantic families;
- canonical targets;
- normalized representations;
- equivalence classes;
- semantic primitives;
- scope/role/relation metadata.

It already includes geometry-relevant canonical concepts such as `bolt_hole_positions`, `hole_depth`, `outside_diameter`, and `thickness`, together with the broader dimension/position/envelope/load/material/safety families.

The project documentation explicitly states that this registry is the sole semantic authority and that new wording must first be classified by semantic family, target, primitive/relation, representation structure, scope, and provenance.

### 3.2 Requirement evidence path

`src/ai_designer/engineering/requirement_evidence_v1.py` and its coverage extension provide the source-grounded evidence entrypoint.

The implementation extracts source facts, preserves provenance, and extends the evidence set only when a representation is explicit enough to normalize without fabrication.

The P6-5 lessons explicitly require one production `RequirementEvidenceV1` entrypoint and prohibit parallel evidence authorities.

### 3.3 Requirements normalization

`src/ai_designer/engineering/requirements_output_normalizer_v1.py`

This already normalizes provider representations into the canonical RequirementsV2 model, including load-case aliases and envelope aliases.

`src/ai_designer/engineering/requirements_normalization_v1.py`

This canonicalizes explicit-constraint target names and is already used by `EngineeringRequirementsV2`.

### 3.4 Requirements resilience / source restoration

`src/ai_designer/engineering/requirements_v2_resilient_v1.py`

This existing boundary already performs:

```text
LLM output
 → RequirementsV2 parsing
 → source-evidence restoration
 → semantic validation
 → bounded correction/retry
```

It can restore source-grounded geometry constraints such as `outside_diameter`, `thickness`, `bolt_hole_diameter`, `bolt_hole_positions`, `bolt_hole_position_pattern`, and `hole_depth` when the provider omits them.

### 3.5 Requirement semantic gate

`src/ai_designer/engineering/semantic_contract_v1.py`

This gate already checks semantic role/scope relationships and rejects envelope/design scope mismatches. This is not a candidate for duplication in Solid_Ai.

### 3.6 Requirement-gap diagnosis

`src/ai_designer/engineering/requirement_gap_diagnosis_v1.py`

This is already a deterministic gap authority. It compares observed canonical targets with required targets and returns:

- canonical target;
- canonical intake field ID;
- RequirementsV2 path;
- targeted question;
- reason.

Unknown targets are explicitly fail-closed rather than guessed.

### 3.7 EngineeringJob / Front Door

`src/ai_designer/engineering/engineering_job_v1.py` and `src/ai_designer/engineering/engineering_front_door_v1.py`

The existing job lifecycle is immutable and preserves the same `job_id` across clarification snapshots. `EngineeringFrontDoorV1` already owns raw-request intake, clarification application, and handoff into the existing RequirementsV2 path.

`EngineeringIntakeFieldRegistryV1` already defines canonical intake fields including `MATERIAL`, `LOAD_REQUIREMENTS`, `ENVELOPE_CONSTRAINTS`, `MOUNTING_INTERFACE`, `MANUFACTURING_METHOD`, `SAFETY_FACTOR`, and `ACCEPTANCE_CRITERIA`.

### 3.8 Clarification response contract

`src/ai_designer/engineering/engineering_clarification_response_v1.py`

The existing responder converts a user answer into only the requested unresolved fields, using canonical field IDs and explicit `resolved` / `needs_clarification` states. It forbids inventing values and forbids using `null` as a resolved value.

### 3.9 Deterministic clarification resolution

`src/ai_designer/engineering/clarification_resolution_v1.py`

This is the most directly relevant existing asset for the current geometry symptom.

It already provides deterministic parsing and normalization for clarification facts, including:

```text
intent_geometry.height_mm  → thickness
intent_geometry.diameter_mm → outside_diameter
intent_geometry.radius_m    → fillet_radius
intent_geometry.depth_m     → hole_depth
```

It also resolves grouped hole-position patterns and can emit canonical RequirementsV2 constraints through `facts_as_constraints_v1()`.

Therefore a new `FilletParser`, `GeometrySemanticNormalizer`, or second clarification resolver is forbidden by this audit.

### 3.10 Clarification generalization gate

`src/ai_designer/engineering/clarification_generalization_gate_v1.py`

This already proves stable job identity, monotonic reduction of missing information, and final readiness across materially distinct clarification scenarios.

### 3.11 IntentV2

`src/ai_designer/engineering/intent_v2.py`

This is the canonical Requirements → Intent boundary.

It already contains deterministic repair for selected missing/zero geometry from canonical requirements, including:

- primary cylinder diameter/height;
- hole diameter/depth;
- canonical hole positions.

It deliberately fails closed for geometry that remains non-positive after repair.

It also verifies positive geometry against explicit design quantities and verifies canonical hole positions when those are available.

### 3.12 Constraint validation

`src/ai_designer/engineering/constraint_validation_v1.py`

This boundary intentionally handles generic graph consistency (dependency existence, self-reference, and acyclicity) and does not attempt to become a CAD geometry truth engine.

### 3.13 Canonical planning and execution

`ComplexEngineeringPipelineV1` already composes the existing RequirementsV2/IntentV2/Planning path and can accept `clarification_context` containing resolved constraints.

`RequirementsPlanningV2` / `MultiFeaturePlannerV1` / `ExecutionPlanV3` remain canonical and are to be reused.

## 4. What the current Solid_Ai composition actually does

`integration/aidesigner_composition_v1.py` correctly bootstraps the sibling `Ai_Designer` source tree and exposes the canonical stack. The current composed runner then calls:

```text
Solid_Ai runner
   ↓
prepare_and_plan()
   ↓
ComplexEngineeringPipelineV1.prepare()
   ↓
Resilient RequirementsV2
   ↓
IntentV2
   ↓
RequirementsPlanningV2
```

The `Solid_Ai` composition seam also loads `EngineeringFrontDoorV1`, but `prepare_and_plan()` currently bypasses it and directly invokes `ComplexEngineeringPipelineV1.prepare()`.

The current runner therefore exercises the **prepared engineering pipeline**, not the full raw-request intake/clarification lifecycle.

## 5. Root-cause conclusion for the current live failure

The live trace established:

```text
Natural language
 ↓
GapGPT
 ↓
RequirementsV2        PASS
 ↓
semantic gate         PASS after existing correction path
 ↓
IntentV2 LLM output
 ↓
fillet radius = 0
hole geometry = 0
 ↓
IntentV2 validation    FAIL
```

The Requirements payload already contained the explicit semantic fact:

```text
fillet_radius = 5 mm
```

and the source request contained the original R5 statement.

The current IntentV2 implementation, however, has no deterministic repair branch for `fillet_radius`; its `_repair_missing_geometry_v1()` restores only the existing canonical targets for cylinder dimensions, hole dimensions/depth, and canonical hole positions.

This means the failure is **not evidence that Ai_Designer lacks a semantic understanding of fillet radius**. The capability already exists in the semantic/clarification infrastructure.

The actual gap is the missing composition between:

```text
canonical Requirements / explicit constraint
        ↓
existing canonical deterministic geometry fact
        ↓
IntentV2 feature parameters
```

The same trace suggests that hole semantics are also only partially wired: the Requirements layer knows `mounting_hole_diameter`, hole count, and the textual `4x M8 at footprint corners`, while IntentV2 has deterministic repair support for canonical hole diameter/depth and canonical positions only when those targets are present in the requirements constraints.

## 6. Critical architectural distinction

There are two different cases and they must not be conflated.

### Case A — The user request is semantically complete

Example:

```text
R5 outer fillets
```

There is enough source evidence to identify the design quantity. The system should canonicalize it and preserve the value through RequirementsV2 → IntentV2.

The correct fix is therefore a **generic canonical Requirements → Intent wiring enhancement**, reusing the already existing semantic target `fillet_radius` and the existing clarification/constraint representations.

### Case B — The user request is genuinely incomplete or ambiguous

Example:

```text
Add fillets
```

There is no safe radius fact. The system must not invent one. It must use the existing requirement-gap / clarification lifecycle:

```text
RequirementEvidenceV1
 → missing canonical fact
 → RequirementGapDiagnosisV1
 → EngineeringJobV1 / FrontDoor clarification
 → user answer
 → clarification response/resolution
 → resolved canonical constraint
 → same Job identity
 → RequirementsV2 re-evaluation
 → IntentV2
```

This is already specified by the current roadmap and operational memory. It is not a new subsystem to build.

## 7. Decision: what must NOT be implemented

Do NOT add any of the following in Solid_Ai or Ai_Designer as new authorities:

- a new geometry semantic normalizer;
- a fillet-specific parser;
- a new clarification engine;
- a new Requirements model;
- a second Intent pipeline;
- a new planner;
- a second CAD-IR;
- a second runtime;
- a second recovery registry.

These would violate the current Architecture Integration Gate and reuse matrix.

## 8. Decision: what the next implementation must actually investigate

The next implementation task is limited to tracing and, only if necessary, completing the **existing Requirements → Intent deterministic binding contract**.

Before writing code, inspect and test the following existing path:

```text
RequirementsV2.explicit_constraints
        ↓
IntentV2._constraint_items()
        ↓
IntentV2._constraint_value()
        ↓
IntentV2._repair_missing_geometry_v1()
        ↓
IntentV2._validate_remaining_geometry_v1()
        ↓
IntentV2._validate_explicit_geometry_v1()
```

For the current motor-bracket evidence, the audit question is specifically:

```text
Does _constraint_value(requirements, {"fillet_radius"})
exist / get used for fillet recovery?
```

The answer from the current source is **no**: `fillet_radius` is not currently retrieved by `_repair_missing_geometry_v1()`.

Therefore the missing behavior is not semantic discovery. It is a deterministic binding gap between an existing canonical requirement target and an existing canonical Intent feature field.

That gap must be implemented, if still required after focused verification, in `Ai_Designer`'s canonical `IntentV2` owner—not in Solid_Ai.

The same audit must verify whether a canonical `rib_count` / `mounting_holes` requirement needs a similar deterministic binding or whether those are intentionally left to the planner/capability layer. No change should be made until the ownership is proven from existing contracts/tests.

## 9. Required focused proof before any implementation commit

The next proof should not call live SolidWorks. It should use deterministic fixtures and prove at least:

1. A RequirementsV2 payload containing `fillet_radius=5 mm` plus an Intent feature with `radius_m=0` deterministically yields `radius_m=0.005`.
2. A positive but conflicting `radius_m` is rejected rather than overwritten.
3. Existing hole repair behavior remains unchanged.
4. Existing cylinder and dependency behavior remains unchanged.
5. A genuinely missing fillet radius remains a hard failure / clarification candidate rather than being guessed.
6. The existing clarification resolver can already convert a user answer such as `5 mm radius` into canonical `fillet_radius`, so no new resolver is introduced.

Only after these deterministic proofs are green should the live GapGPT composed probe be rerun.

## 10. Current status

```text
Architecture / ownership audit              COMPLETE
Existing semantic registry                  FOUND / REUSE
Existing evidence path                     FOUND / REUSE
Existing clarification lifecycle           FOUND / REUSE
Existing clarification resolver             FOUND / REUSE
Existing RequirementsV2                    FOUND / REUSE
Existing IntentV2                           FOUND / REUSE
Existing deterministic hole repair          FOUND / REUSE
Existing deterministic fillet binding       MISSING
New semantic subsystem required             NO
New clarification subsystem required        NO
New Solid_Ai architecture required          NO
Current demonstrated gap                   Requirements → Intent deterministic binding
```

## 11. Governing rules for the next step

The current Ai_Designer documents explicitly require:

```text
first violated contract → identify owner → reuse existing asset → smallest reusable fix → strengthen proof → rerun canonical path
```

They also explicitly prohibit downstream coercion, wording-specific parser patches, and parallel requirements/intent architectures.

This document therefore supersedes any earlier proposal in this work session that suggested creating a new geometry semantic normalization subsystem.

## 12. Evidence sources inspected

Ai_Designer current branch:

- `docs/DOCUMENTATION_TRUTH_INDEX_V1.md`
- `docs/PHASE_BOUNDARIES_AND_GATES_V2.md`
- `docs/PROJECT_ASSET_REUSE_MATRIX_V4.md`
- `docs/PROJECT_EXECUTION_ROADMAP_V3.md`
- `docs/AGENT_CONTINUATION_MEMORY_V2.md`
- `docs/SEMANTIC_PRIMITIVES_AND_EQUIVALENCE_V1.md`
- `docs/AGENT_CONTINUATION_P6_5_SEMANTIC_GENERALIZATION_LESSONS_V1.md`
- `src/ai_designer/engineering/engineering_job_v1.py`
- `src/ai_designer/engineering/engineering_front_door_v1.py`
- `src/ai_designer/engineering/engineering_intake_field_registry_v1.py`
- `src/ai_designer/engineering/engineering_clarification_response_v1.py`
- `src/ai_designer/engineering/clarification_generalization_gate_v1.py`
- `src/ai_designer/engineering/clarification_resolution_v1.py`
- `src/ai_designer/engineering/requirement_gap_diagnosis_v1.py`
- `src/ai_designer/engineering/requirement_evidence_v1.py`
- `src/ai_designer/engineering/requirements_output_normalizer_v1.py`
- `src/ai_designer/engineering/requirements_normalization_v1.py`
- `src/ai_designer/engineering/requirements_v2.py`
- `src/ai_designer/engineering/requirements_v2_resilient_v1.py`
- `src/ai_designer/engineering/semantic_contract_v1.py`
- `src/ai_designer/engineering/requirements_semantic_contract_v1.py`
- `src/ai_designer/engineering/intent_v2.py`
- `src/ai_designer/engineering/intent_contract_v1.py`
- `src/ai_designer/engineering/constraint_validation_v1.py`
- `src/ai_designer/engineering/complex_engineering_pipeline_v1.py`
- `tests/unit/test_intent_v2.py`
- `tests/unit/test_semantic_primitives_equivalence_v1.py`
- `tests/unit/test_clarification_resolution_v1.py`

Solid_Ai current branch:

- `docs/AIDESIGNER_COMPOSITION_V1.md`
- `docs/AIDESIGNER_REUSE_MAP.md`
- `docs/AGENT_HANDOFF_AIDESIGNER_SOLIDPILOT_V1.md`
- `docs/MOTOR_BRACKET_INTEGRATION_V1.md`
- `integration/aidesigner_composition_v1.py`
- `scripts/run_aidesigner_composed_e2e_v1.py`

## 13. Audit conclusion

The project does **not** need another semantic/clarification subsystem.

The existing Ai_Designer work already contains the semantic registry, evidence model, normalization, clarification lifecycle, deterministic clarification resolver, RequirementsV2, IntentV2, planning, recovery, and the required architectural ownership boundaries.

The currently demonstrated live failure is a narrow but important canonical integration gap: an explicit, source-grounded `fillet_radius` fact already exists at the Requirements layer, but the current deterministic Requirements → Intent repair/binding code does not consume that target when the LLM emits a zero placeholder.

The next implementation, if focused verification confirms this exact gap, belongs in `Ai_Designer`'s existing `IntentV2` owner and must reuse the existing canonical `fillet_radius` target/resolution semantics. `Solid_Ai` should remain a thin composition and evidence boundary.
