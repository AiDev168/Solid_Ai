# Ai_Designer Reuse Audit V2

## Decision

The safest architecture is to continue from the existing Ai_Designer engineering stack rather than rebuild its intelligence inside Solid_Ai.

`Solid_Ai` remains the SolidPilot/SolidWorks laboratory and integration repository. `Ai_Designer` remains the canonical engineering-intelligence and orchestration authority.

## Reuse map

| Ai_Designer asset | Ownership | Solid_Ai integration | Status |
|---|---|---|---|
| `LLMGateway` | LLM transport + structured validation | `aidesigner_composition_v1` environment bridge | connected |
| `EngineeringFrontDoorV1` | canonical user-request intake | loaded by composition seam | connected |
| `ResilientEngineeringRequirementsExtractorV2` | requirements semantics | loaded by composition seam | connected |
| `EngineeringIntentExtractorV2` | requirements -> intent | loaded by composition seam | connected |
| `ComplexEngineeringPipelineV1` | NL -> requirements -> intent -> planning/execution | canonical composed pipeline | connected |
| `RequirementsPlanningV2` | multifeature planning + CAD-IR -> ExecutionPlanV3 | loaded and used by canonical pipeline | connected |
| `RequirementsSolidPilotV1` | existing validated execution seam | canonical composed execution path | connected |
| `ExecutionPlanV3` | structured executable plan | obtained from canonical planning path | connected |
| `DesignIntegrationLoop` | PLAN -> EXECUTE -> VERIFY -> REPAIR orchestration | exposed as composition seam with caller ports | connected as orchestration asset |
| `RecoveryController` / `RecoverySolverRegistry` | bounded deterministic recovery | composition builder exposes and registers topology solver | connected |
| `TopologyRebindingRecoverySolver` | geometry-backed stale-reference repair | composition builder registers it | connected |
| `DiagnosisAgent` | LLM-assisted structured failure diagnosis | reusable repair bridge builder | connected |
| `ExecutionRepairAgent` | complete intent repair after failure | reusable repair bridge builder | connected |
| `LegacyRepairBridge` | compatibility between diagnosis/repair and agentic loop | loaded by composition seam | connected |
| semantic equivalence / evidence contracts | canonical semantic truth | consumed indirectly by RequirementsV2/IntentV2 | reuse; do not duplicate |
| old TextToCAD / agentic demos | historical proof vehicles | use as evidence/source, not a second runtime | selective |

## Provider policy

The canonical Ai_Designer `LLMGateway` is provider-neutral and OpenAI-compatible. `Solid_Ai` accepts the existing benchmark variables and maps them into the canonical Ai_Designer environment variables only for the current process.

GapGPT:

```text
BENCHMARK_PROVIDER=api-provider
BENCHMARK_BASE_URL=https://api.gapgpt.app/v1
BENCHMARK_MODEL=gapgpt-qwen-3.5
BENCHMARK_API_KEY=...
```

LM Studio continues to use the already-supported `LM_STUDIO_*` configuration in Ai_Designer.

## Recovery policy

Recovery remains evidence-first:

```text
failure
  -> structured diagnosis
  -> deterministic solver when one exists
  -> fresh topology/state evidence
  -> repair/rebind
  -> bounded retry
  -> verification
```

LLM diagnosis/repair can be used through the existing Ai_Designer agents, but LLM output never becomes an unrestricted SolidWorks command stream.

## Current gaps that should be solved, not reimplemented

1. `EngineeringPlannerV1` / capability registry in Ai_Designer still has a limited set of promoted capabilities. Promotion must follow live evidence, not discovery counts.
2. The Ai_Designer CAD-IR compiler currently maps a bounded capability surface. New SolidPilot capabilities require evidence-backed lowering contracts.
3. Solid_Ai still contains a parallel generic FeatureGraph compiler/executor used for laboratory proofs. It must not become a second semantic authority. The canonical production path should use Ai_Designer's requirements/intent/planning stack and the existing SolidPilot execution boundary.
4. Verification must be based on measured SolidWorks geometry/acceptance criteria, not merely tool completion or `error=null`.
5. The final generalization gate must be an unseen Natural Language -> verified CAD benchmark, with recovery and negative cases included.

## Frozen rule

Before adding another abstraction, search Ai_Designer first. If a proven asset exists, adapt its boundary. Only implement a new component when a concrete missing contract is demonstrated by a reproducible failing case.
