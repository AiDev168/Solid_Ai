# Ai_Designer reuse map

## Scope

`Solid_Ai` reuses only small, evidence-backed parts of `Ai_Designer`. The previous planner, agent swarm, generic LLM gateway, CAD-IR compiler and broad natural-language pipeline are not imported.

## Ported assets

### Capability metadata

`integration/aidesigner_assets.py` contains a standalone capability registry derived from `Ai_Designer/src/ai_designer/capabilities/registry.py`.

The useful mappings are:

- `part.open_new` → `open_new_part`
- `part.create_sketch` → `create_sketch`
- `sketch.circle` → `add_sketch_entity`
- `part.extrude_boss` → `extrude_feature`
- `model.analyze_geometry` → `analyze_model`
- `part.hole` → `extrude_feature` with `cut + through`
- `edge.fillet` → `add_edge_feature`

### Lowering

The same module preserves the useful lowering idea from `Ai_Designer`: a semantic capability is lowered into one or more concrete SolidPilot calls rather than embedding backend-specific calls throughout higher layers.

`lower_hole()` and `lower_fillet()` are the first preserved lowering helpers. Fillet lowering prefers `edge_indices` and keeps coordinate selection only as a fallback.

## Why the full old stack is not imported

The old `EngineeringIntentExtractor` currently has a deliberately narrow deterministic contract and depends on the old LLM/CAD-IR architecture. It is therefore not a safe foundation for the new Solid_Ai laboratory yet.

Likewise, `DesignIntegrationLoop` is valuable as an orchestration pattern (PLAN → EXECUTE → VERIFY → REPAIR), but the concrete Ai_Designer adapters are not copied wholesale. We will reintroduce that pattern only around real SolidPilot calls after the required verification and repair seams are demonstrated.

## Verification

Run:

```powershell
python scripts\verify_aidesigner_assets.py
```

This is a pure-Python mapping test; it does not start SolidWorks and does not access the network.

## Provenance

Source inspected from `AiDev168/Ai_Designer` on 2026-08-30:

- `src/ai_designer/capabilities/registry.py`
- `src/ai_designer/capabilities/lowering.py`
- `src/ai_designer/capabilities/hole_fillet.py`
- `agentic/design_loop.py`
- `agentic/legacy_repair_bridge.py`

The implementation in `Solid_Ai` is intentionally standalone so it cannot pull the old application's runtime dependency graph into the new repository.
