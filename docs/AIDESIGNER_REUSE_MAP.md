# Ai_Designer reuse map

## Scope

`Solid_Ai` reuses only evidence-backed parts of `Ai_Designer`. The old application's COM bridge and execution compiler are not duplicated; SolidPilot remains the CAD execution backend. The old broad planner/agent stack is not imported wholesale.

## Ported assets

### Capability metadata and lowering

`integration/aidesigner_assets.py` preserves the useful capability-to-tool mapping and lowering idea:

- `part.open_new` → `open_new_part`
- `part.create_sketch` → `create_sketch`
- `sketch.circle` → `add_sketch_entity`
- `part.extrude_boss` → `extrude_feature`
- `model.analyze_geometry` → `analyze_model`
- `part.hole` → circle sketch + `extrude_feature(cut, through)`
- `edge.fillet` → `add_edge_feature`

Fillet lowering prefers `edge_indices` over coordinate selection.

### Recovery and solver assets

`integration/recovery_assets.py` is a standalone extraction of the useful deterministic recovery architecture from `Ai_Designer`:

- structured failure diagnosis with fail-closed unknown codes;
- bounded `RecoveryRegistry` + `RecoveryController`;
- runtime failure normalization for topology/reference families;
- topology anchors and geometry-backed rebinding across topology mutations;
- `TopologyRecoverySolver` registered as `topology-rebinding-v1`;
- explicit recovery evidence carrying source/target state versions.

The implementation is independent from the old LLM, agent swarm, CAD-IR compiler, and SolidPilot client classes. It can therefore be used with the current MCP `ClientSession` surface.

### Live proof

`scripts/run_topology_recovery_demo.py` uses the imported recovery assets against the real q3ds legacy MCP server. It:

```text
live SolidPilot part
  ↓
capture real edge anchor
  ↓
mutate topology with a hole cut
  ↓
analyze fresh edges
  ↓
TopologyRecoverySolver rebinding
  ↓
use recovered backend edge index
  ↓
fillet
```

This proves the important recovery behavior: an old backend index is not blindly reused; fresh geometry evidence is used to recover the current selector.

## Deliberately deferred assets

The following `Ai_Designer` components were inspected but are not copied wholesale:

- `ExecutionRepairAgent` and the agentic recovery coordinator: their contract is valuable, but their implementation depends on the old LLM + EngineeringIntent + CAD-IR stack. We will implement an equivalent seam around the current SolidPilot tools only after deterministic recovery is stable.
- broad planner/intent/extractor layers: these coupled reasoning, compilation, and provider behavior too tightly for the new SolidPilot laboratory.

The architectural direction is the useful part: SolidPilot owns CAD execution/evidence; the higher layer owns engineering reasoning, diagnosis, solver selection, recovery, retry, and verification. This is recorded in `Ai_Designer/docs/CAD_RECOVERY_ORCHESTRATION_V1.md`.

## Verification

Pure Python:

```powershell
python scripts\verify_aidesigner_assets.py
python -m pytest -q tests/test_recovery_assets.py tests/test_topology_selection.py
```

Live recovery proof:

```powershell
vendor\q3ds-solidworks-mcp\.venv\Scripts\python.exe scripts\run_topology_recovery_demo.py
```

The live proof uses the local MCP/CAD path.

## Provenance

Source inspected from `AiDev168/Ai_Designer` on 2026-08-30:

- `src/ai_designer/recovery/controller.py`
- `src/ai_designer/recovery/diagnosis.py`
- `src/ai_designer/recovery/registry.py`
- `src/ai_designer/recovery/runtime_failure_v1.py`
- `src/ai_designer/recovery/topology_solver.py`
- `src/ai_designer/solidpilot/topology_rebinding_v1.py`
- `src/ai_designer/solidpilot/topology_evidence_v1.py`
- `src/ai_designer/solidpilot/proven_sequences.py`
- `src/ai_designer/execution/runtime_executor.py`
- `src/ai_designer/planning/execution_repair.py`
- `docs/CAD_RECOVERY_ORCHESTRATION_V1.md`

The implementation in `Solid_Ai` is deliberately standalone so it cannot pull the old application's runtime dependency graph into the new repository.
