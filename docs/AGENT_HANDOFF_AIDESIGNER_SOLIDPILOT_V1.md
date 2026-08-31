# Agent Handoff — Ai_Designer + SolidPilot Integration Lessons V1

## 1. Current architectural decision

Do NOT build a second Ai_Designer inside Solid_Ai.

Canonical ownership:
- Ai_Designer: engineering intelligence, LLM gateway, requirements, intent, planning, semantic interpretation, diagnosis, recovery orchestration, repair proposals and validation.
- SolidPilot: CAD backend boundary, SolidWorks execution, deterministic feature/tool execution, runtime state and topology evidence.
- Solid_Ai: integration laboratory and only the missing bridge/gap implementations.

Target path:
Natural language -> Ai_Designer canonical semantic/engineering pipeline -> planning / ExecutionPlanV3 -> SolidPilot client/backend -> SolidWorks -> measured verification -> Ai_Designer diagnosis/recovery -> bounded retry -> verification again.

Key rule: reuse first; implement only a demonstrated gap.

## 2. Why the earlier Solid_Ai-only approach was misleading

A sequence such as Natural language -> local FeatureGraph -> local compiler -> SolidPilot can produce successful deterministic CAD for a few hand-authored examples, but it does NOT establish unrestricted natural-language engineering-to-CAD.

Those local layers are useful integration assets, but they are not substitutes for the already-developed Ai_Designer semantic/planning/recovery stack.

The motor-bracket and stepped-revolve successes therefore proved that SolidPilot can execute particular compiled operations. They did not prove general engineering understanding.

## 3. Ai_Designer assets that must be reused

- LLM provider abstraction / structured responses / retries.
- Engineering Front Door / EngineeringJob intake.
- Requirement evidence and resilient requirement extraction.
- IntentV2.
- RequirementsPlanningV2 and ExecutionPlanV3.
- RequirementsSolidPilotV1 / SolidPilotClient boundary.
- Agentic engineering loop / execution supervisor.
- DiagnosisAgent.
- ExecutionRepairAgent.
- RecoveryController.
- RecoverySolverRegistry.
- TopologyRebindingRecoverySolver.
- AgenticRecoveryCoordinator.
- LegacyRepairBridge.
- Existing live-verified capability evidence and capability resolver/promotion logic.

Do not reimplement these in Solid_Ai unless a concrete compatibility gap is demonstrated.

## 4. LLM provider rule

The integration must remain provider-neutral.

GapGPT compatibility:
BENCHMARK_PROVIDER=api-provider
BENCHMARK_BASE_URL=https://api.gapgpt.app/v1
BENCHMARK_MODEL=gapgpt-qwen-3.5
BENCHMARK_API_KEY=<key>

LM Studio is allowed only when the operator explicitly opts in.

Never silently fall back to LM Studio during provider qualification or benchmark. A stale AIDESIGNER_LLM_* environment must not override an explicitly supplied BENCHMARK_* provider.

## 5. Topology lessons learned

SolidWorks feature indexes are mutable.

Never treat a backend edge/face index as a durable engineering identity.

Correct pattern:
semantic reference / intent -> fresh analyze_model evidence -> resolution -> backend index -> execute -> new state_version -> fresh evidence after mutation -> rebind when required.

The Ai_Designer topology-rebinding solver is therefore more valuable than adding another coordinate-selection patch.

Important failure classes already encountered:
- EDGE_NOT_FOUND
- FACE_NOT_FOUND
- AXIS_NOT_FOUND
- stale selector/index
- feature creation returning null
- coincident/on-face extrusion/cut failures
- ambiguity in geometric reference resolution.

These should become normalized diagnostic categories, not ad-hoc string patches.

## 6. Verification lesson

error == null or tool status COMPLETED is NOT sufficient evidence that CAD output is correct.

A real verification gate must check the resulting model semantically and geometrically.

Examples include body count, volume before/after, face/edge/vertex changes, feature presence where appropriate, expected dimensions, expected hole count/location, expected topology mutation, expected reference/support, and saved/final geometry state. Visual or section evidence can be useful when geometry semantics are otherwise ambiguous.

Therefore:
tool success != feature correctness != geometry correctness != design-intent correctness.

## 7. Capability lessons

Backend discovery is not proof.

The current census discovers approximately 103 backend capability variants, but most are only candidates until live execution and verification evidence exists.

Also: live_verified != lowering_available.

A capability is executable by the canonical planner only when a reusable canonical lowering strategy exists.

Do not let an evidence catalog silently fabricate an executable lowering.

## 8. Qualification lessons

A qualification scenario must contain all prerequisites.

Bad example: base -> cut when no solid exists before cut.

Correct example: base sketch -> base solid -> support/reference -> cut -> measured verification.

Likewise, pattern requires a seed feature; constraint requires valid sketch entities; loft requires profiles; sweep requires profile + path; edge modifier requires a resolvable target.

A scenario lacking prerequisites is an invalid qualification, not evidence that the backend capability is broken.

## 9. Most important recovery pattern

Use a generic closed loop:
failure -> normalize failure -> diagnose root cause -> choose solver/recovery strategy -> apply bounded repair -> verify repaired state -> retry -> stop on success or exhausted budget.

Deterministic topology recovery should be attempted before asking an LLM to invent a repair.

LLM assistance is allowed for diagnosis/repair proposal where useful, but the proposal must be schema/contract validated before execution.

## 10. Current composition gap

The current Solid_Ai composition seam is intentionally thin. It loads the existing Ai_Designer stack instead of copying it.

Current implementation direction: integration/aidesigner_composition_v1.py

Important functions: load_stack(), build_canonical_gateway(), build_canonical_pipeline(), prepare_and_plan(), execute_canonical(), build_deterministic_recovery_controller(), build_llm_recovery_coordinator().

The composed runner is scripts/run_aidesigner_composed_e2e_v1.py.

Use --plan-only first. The first failing canonical boundary is the next real engineering gap.

## 11. Do not repeat these mistakes

1. Add another planning stack in Solid_Ai.
2. Add another LLM gateway.
3. Add another recovery registry.
4. Treat hard-coded backend indexes as persistent references.
5. Mark a capability proven because a tool returned COMPLETED.
6. Create a feature-specific runner when a generic contract is missing.
7. Patch one error string without identifying the owning layer.
8. Silently map a new semantic feature to an unrelated proven capability.
9. Count pytest totals as generalization evidence.
10. Claim 90%+ generalization without an unseen-prompt benchmark.

## 12. Current test/debug lesson

The repositories have separate Python environments and import roots.

A direct script can fail with ModuleNotFoundError: integration while pytest succeeds if the repository root is injected into sys.path.

Solid_Ai live MCP scripts must use the q3ds/SolidPilot virtual environment containing mcp, not the system Python.

These are packaging/launcher issues and must be fixed at the entry-point boundary, not worked around inside business logic.

## 13. What the motor bracket tests actually proved

Together the motor-bracket tests proved a valuable subset: semantic graph to SolidPilot for the tested path; face support/reference resolution for the tested case; topology-aware outer-edge selection for the tested case; holes, ribs and outer fillets in that constructed scenario; and a verified terminal SolidWorks state in that scenario.

They did NOT prove unrestricted natural-language generalization.

## 14. What the stepped-revolve test proved

The stepped revolve test demonstrated that the SolidPilot backend can perform revolve -> secondary axial feature/groove -> hole -> fillet -> final analysis for the tested construction.

It also exposed that axis selection needs semantic/topological resolution rather than assumed coordinate endpoints.

## 15. Next execution plan

### Phase A — Finish canonical composition loading

Goal: Ai_Designer imports cleanly from its real repository layout inside Solid_Ai. No mocks for the real probe.

### Phase B — Canonical plan-only probe

Run the real motor-bracket prompt through Ai_Designer: Natural language -> Requirements/Intent -> canonical planning -> ExecutionPlanV3. Do not execute CAD yet if planning is invalid.

### Phase C — Canonical execution probe

Connect the resulting canonical execution plan to the existing SolidPilot boundary. Record feature sequence, capability selected, references requested, runtime state versions, and verification results.

### Phase D — Recovery integration

Connect Ai_Designer diagnosis + existing recovery assets around SolidPilot runtime failures. First target: topology/reference failures because those already have proven assets.

### Phase E — Unseen benchmark

Only after the canonical path is running: 100 unseen engineering prompts; multiple feature families; multiple LLM providers; measured geometry verification; recovery statistics; first-attempt and final success.

The target >=90% is a benchmark result, not an assumption.

## 16. Definition of success

The project is considered genuinely generalized only when natural-language engineering requests can enter the canonical Ai_Designer stack and reach SolidWorks through the generic runtime, with measured verification and bounded recovery, across a broad unseen benchmark.

Passing unit tests is necessary. Passing hand-authored examples is necessary. Neither is sufficient.

## 17. Agent operating rule

For every new failure, answer these four questions before changing code:
1. Which layer owns the failure?
2. Does Ai_Designer already contain an asset that solves this class?
3. Is the problem semantic/planning, integration, SolidPilot execution, topology/reference, verification, or recovery?
4. What is the smallest reusable fix that increases generality rather than only fixing this scenario?

If an existing Ai_Designer asset already covers the problem, adapt/use it. Do not reimplement it.