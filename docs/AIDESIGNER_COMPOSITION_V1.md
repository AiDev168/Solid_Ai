# Ai_Designer Canonical Composition V1

This branch adds only a thin integration seam in Solid_Ai so the existing Ai_Designer production stack can be exercised against the existing SolidPilot backend.

Ownership:
- Ai_Designer: LLM gateway, Job/Front Door, Requirement Evidence, RequirementsV2, IntentV2, planning, diagnosis, bounded recovery.
- SolidPilot: CAD backend, Feature Graph IR, deterministic lowering, SolidWorks execution, runtime state and topology evidence.
- Solid_Ai: integration boundary and laboratory evidence only.

Canonical path:
Natural language -> Ai_Designer canonical pipeline -> RequirementsV2 -> IntentV2 -> RequirementsPlanningV2 -> ExecutionPlanV3 -> SolidPilotClient -> SolidPilot -> SolidWorks -> verification.

No second planner, CAD compiler, runtime, or recovery registry is introduced by this branch.

Environment:
AI_DESIGNER_ROOT should point to the Ai_Designer repository root.
SOLIDPILOT_BASE_URL defaults to http://localhost:5000.
GapGPT can be supplied with BENCHMARK_PROVIDER, BENCHMARK_BASE_URL, BENCHMARK_MODEL and BENCHMARK_API_KEY.

First diagnostic command:
python .\scripts\run_aidesigner_composed_e2e_v1.py --plan-only

The first violated contract is the next engineering gap. Downstream layers are not patched until that boundary is identified.

## Recent integration fixes

- The composition fixture now mirrors the real Ai_Designer package layout, including `ai_designer.agentic`.
- Outer-vertical edge selection now checks the complete edge against the declared plan boundary instead of only testing whether its midpoint lies inside the plan.
- The composition boundary now fails closed when no external LLM provider is configured, instead of silently attempting the Ai_Designer LM Studio fallback.
- Set `SOLID_AI_ALLOW_LMSTUDIO=1` only when an explicit local LM Studio run is intended.

For GapGPT:

```powershell
$env:BENCHMARK_PROVIDER="api-provider"
$env:BENCHMARK_BASE_URL="https://api.gapgpt.app/v1"
$env:BENCHMARK_MODEL="gapgpt-qwen-3.5"
$env:BENCHMARK_API_KEY="<your-key>"
```
