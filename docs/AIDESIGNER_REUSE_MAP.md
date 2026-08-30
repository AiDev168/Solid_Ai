# Ai_Designer reuse map

## Scope

`Solid_Ai` reuses evidence-backed parts of `Ai_Designer`. SolidPilot remains the CAD execution backend. The old application's COM bridge and execution compiler are not duplicated, and the old broad planner/agent stack is not imported wholesale.

## Ported assets

### Capability metadata and lowering

`integration/aidesigner_assets.py` preserves capability-to-tool mappings and lowering helpers for the proven SolidPilot surface.

### Recovery and solver assets

`integration/recovery_assets.py` preserves the deterministic recovery architecture:

- structured failure diagnosis with fail-closed unknown codes;
- bounded recovery registry/controller;
- runtime failure normalization for topology/reference families;
- topology anchors and geometry-backed rebinding across topology mutations;
- `TopologyRecoverySolver` registered as `topology-rebinding-v1`;
- source/target state-version evidence.

### Planning assets

`integration/motor_bracket_plan_v1.py` is a standalone semantic multi-feature plan derived from the proven intent/planning direction in Ai_Designer M5. It captures dependencies for a 120 x 80 x 10 mm motor-mounting bracket, four M8 through holes, two reinforcing ribs and R5 outer fillets.

The dependency order is:

~~~text
base_profile → base → mounting_holes → rib_left/rib_right → outer_fillets
~~~

The plan is intentionally independent of the old CAD-IR/compiler runtime. It is a semantic source for a future SolidPilot execution planner.

## Live recovery proof

Successful live proof on 2026-08-30:

~~~text
Part13
source edge index = 4
source state_version = 9
topology mutation
target edge index = 6
target state_version = 12
distance = 0.0
Fillet1 = COMPLETED
~~~

This establishes that a backend topology index is treated as a temporary selector. After mutation, fresh evidence can recover the corresponding current selector and the downstream Fillet can complete.

## Design lessons captured

1. Primitive CAD execution and engineering reasoning are separate layers.
2. Topology-sensitive features must resolve references from fresh runtime evidence.
3. Backend indices must not be promoted to semantic identity.
4. Recovery must be bounded, deterministic and fail-closed.
5. Multi-feature planning should be represented as a dependency graph rather than a hand-written linear script.

## Deferred assets

`ExecutionRepairAgent`, the old generic LLM gateway, broad EngineeringIntent extraction and the complete old CAD-IR planner are not copied wholesale. Their contracts remain useful, but their concrete runtime is coupled to the old application.

The next integration milestone is to add a current-runtime execution planner that consumes the semantic motor-bracket plan, lowers features to proven SolidPilot calls, captures runtime references, verifies each mutation, and invokes bounded recovery only for classified failures.

## Verification

~~~powershell
python scripts\verify_aidesigner_assets.py
python scripts\verify_motor_bracket_plan.py
python -m pytest -q tests/test_recovery_assets.py tests/test_topology_selection.py
~~~

Live recovery proof:

~~~powershell
vendor\q3ds-solidworks-mcp\.venv\Scripts\python.exe scripts\run_topology_recovery_demo.py
~~~

## Provenance

Source inspected from `AiDev168/Ai_Designer` on 2026-08-30 includes:

- recovery controller/diagnosis/registry/runtime failure/topology solver;
- topology evidence and stable-reference contracts;
- multi-feature planning and executable-plan concepts;
- M4 real failure recovery runbook;
- M5 motor-bracket-class engineering proof runbook;
- SolidPilot convergence and topology mutation tests;
- CAD recovery orchestration architecture.

The implementation in `Solid_Ai` is deliberately standalone so it cannot pull the old application's runtime dependency graph into the new repository.