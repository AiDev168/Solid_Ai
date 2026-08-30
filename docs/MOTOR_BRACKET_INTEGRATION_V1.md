# Motor Bracket Integration V1

## Purpose

This milestone reconnects the useful planning and recovery assets from Ai_Designer to the real SolidPilot runtime without importing the old application runtime graph.

## Proven assets reused

- Multi-feature dependency ordering from Ai_Designer M5.
- Executable-plan and capture concept.
- Topology evidence and rebinding after mutation.
- Bounded recovery and solver orchestration.
- Fail-closed failure diagnosis.
- SolidPilot remains the CAD execution authority.

Ai_Designer M5 explicitly used a motor-bracket-class engineering proof and separated engineering requirements from native CAD execution. Solid_Ai keeps that boundary.

## Current semantic plan

~~~text
base_profile
    ↓
base (10 mm)
    ↓
mounting_holes (4 × M8 through)
    ├──────────────┐
rib_left       rib_right
    └──────┬───────┘
           ↓
outer_fillets R5
           ↓
verification
~~~

## Important implementation boundary

The semantic plan describes ribs as a capability requirement. The live runner must lower each feature only to a SolidPilot operation already proven in this repository. No unsupported create_rib contract is invented.

The first live proof may represent each rib as an additive sketch and extrusion when a native rib contract is not yet proven.

## Recovery contract

~~~text
fresh evidence
  ↓
candidate selection
  ↓
deterministic selector
  ↓
execute
  ↓
verify
  ↓
on classified topology failure: bounded rebind + retry
~~~

No blind retry and no hard-coded topology index is allowed.

## Status

This milestone is a laboratory integration proof, not a claim that unrestricted engineering natural-language input is already solved.