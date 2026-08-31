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