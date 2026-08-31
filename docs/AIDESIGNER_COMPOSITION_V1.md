# Ai_Designer Canonical Composition V1

## Decision

`Ai_Designer` is the canonical engineering-intelligence/orchestration source for the system. `Solid_Ai` is the integration laboratory and SolidPilot/SolidWorks execution boundary.

We do **not** create a second requirements parser, second LLM gateway, second engineering-planning authority, or second recovery architecture in `Solid_Ai` when a proven `Ai_Designer` asset already exists.

## Reused Ai_Designer assets

The composition seam reuses the existing:

- provider-neutral `LLMGateway`;
- `EngineeringFrontDoorV1` intake boundary;
- `ResilientEngineeringRequirementsExtractorV2`;
- `EngineeringIntentExtractorV2`;
- `ComplexEngineeringPipelineV1`;
- `RequirementsPlanningV2` and `ExecutionPlanV3`;
- `RequirementsSolidPilotV1` / `SolidPilotClient` execution contract;
- `DesignIntegrationLoop` PLAN -> EXECUTE -> VERIFY -> REPAIR supervisor;
- `RecoveryController` / `RecoverySolverRegistry`;
- `LegacyRepairBridge` for the already-proven diagnosis/repair seam.

The existing Ai_Designer sources explicitly define the boundary as engineering intent/planning/verification/diagnosis/recovery around SolidPilot's CAD execution substrate. This repository now uses that boundary rather than rebuilding those layers.

## LLM provider policy

`Solid_Ai` accepts the project's benchmark environment variables:

```text
BENCHMARK_PROVIDER
BENCHMARK_BASE_URL
BENCHMARK_MODEL
BENCHMARK_API_KEY
```

For an OpenAI-compatible external provider such as GapGPT, the composition adapter maps them to Ai_Designer's canonical variables for the current process only:

```text
AIDESIGNER_LLM_BASE_URL
AIDESIGNER_LLM_MODEL
AIDESIGNER_LLM_API_KEY
```

No second LLM HTTP client is introduced.

## Runtime boundary

The composed path is:

```text
Natural-language request
        |
        v
Ai_Designer LLM Gateway
        |
        v
RequirementsV2
        |
        v
IntentV2
        |
        v
RequirementsPlanningV2
        |
        v
ExecutionPlanV3
        |
        v
SolidPilot / SolidWorks
        |
        v
verification/evidence
        |
        +---- failure ----> Ai_Designer diagnosis/recovery
```

`Solid_Ai` must remain the place where a real SolidPilot gap is reproduced and fixed. Engineering semantics and orchestration should flow back through the canonical Ai_Designer assets.

## Current gap

The composition seam is now loadable and executable, but the first live prompt may still stop at an existing Ai_Designer planner/capability gap. That is intentional. The correct next action is to measure and repair the **first violated contract**, not to add a parallel planner in `Solid_Ai`.

## Environment

Set the Ai_Designer source location explicitly:

```powershell
$env:AI_DESIGNER_ROOT="C:\path\to\Ai_Designer"
```

For GapGPT:

```powershell
$env:BENCHMARK_PROVIDER="api-provider"
$env:BENCHMARK_BASE_URL="https://api.gapgpt.app/v1"
$env:BENCHMARK_MODEL="gapgpt-qwen-3.5"
$env:BENCHMARK_API_KEY="***"
```

For a local LM Studio gateway, the canonical Ai_Designer gateway can use its existing `LM_STUDIO_*` settings.

## Validation rule

A composed end-to-end result is not considered verified merely because a tool returns `error=null` or a feature appears in the Feature Tree. Verification must be grounded in measured SolidWorks evidence and the acceptance criteria for the request.
