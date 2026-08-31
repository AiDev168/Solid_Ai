# Agent Handoff: Ai_Designer + SolidPilot Integration Lessons V1

## Purpose

This document is the mandatory continuation memory for the next agent. It records the architectural lessons, concrete failures, reusable assets, and rules learned while integrating `Ai_Designer` with `SolidPilot/SolidWorks`.

The goal is to prevent the next agent from rebuilding solved systems, producing false-positive tests, or drifting back into a second parallel CAD intelligence stack.

---

## 1. Strategic decision

Do **not** replace Ai_Designer with Solid_Ai.

The current target architecture is:

```text
User natural language
        |
        v
Ai_Designer canonical engineering-intelligence stack
  - LLM Gateway
  - engineering intake/front door
  - requirements extraction
  - semantic intent
  - planning / CAD-IR / ExecutionPlanV3
  - diagnosis
  - bounded recovery
  - LLM-assisted repair where appropriate
        |
        v
SolidPilot
  - deterministic CAD operation execution
  - SolidWorks boundary
  - topology / geometry evidence
  - runtime state
        |
        v
SolidWorks
```

`Solid_Ai` is an integration/laboratory boundary, not a second semantic authority.

Frozen rule:

> Before adding any abstraction, inspect Ai_Designer first. Reuse a proven asset when it exists. Add new code only when a reproducible missing contract is demonstrated.

---

## 2. What Ai_Designer already contains and must be reused

The following assets were verified during the integration review and should not be reimplemented in Solid_Ai:

### LLM / providers
- `LLMGateway`
- provider-neutral OpenAI-compatible transport
- structured response validation
- environment/provider normalization
- GapGPT compatibility through the existing gateway
- LM Studio compatibility through existing Ai_Designer configuration

GapGPT environment used by the project:

```powershell
$env:BENCHMARK_PROVIDER="api-provider"
$env:BENCHMARK_BASE_URL="https://api.gapgpt.app/v1"
$env:BENCHMARK_MODEL="gapgpt-qwen-3.5"
$env:BENCHMARK_API_KEY="..."
```

Do not create another LLM gateway in Solid_Ai.

### Engineering semantics
Reuse the existing:
- Engineering Front Door
- Engineering Job/intake path
- resilient requirements extraction
- semantic equivalence/evidence contracts
- IntentV2
- ComplexEngineeringPipelineV1

The important boundary is:

```text
natural language
 -> requirements
 -> intent
```

Do not replace this with ad-hoc regex parsing or a new semantic parser unless a specific missing requirement is demonstrated.

### Planning / execution planning
Reuse:
- RequirementsPlanningV2
- Multi-feature planning already present in Ai_Designer
- CAD-IR planning representation
- ExecutionPlanV3
- existing RequirementsSolidPilotV1 execution boundary

Do not create a second production FeatureGraph/CAD planner in Solid_Ai.

### Verification / loop orchestration
Reuse:
- DesignIntegrationLoop
- PLAN -> EXECUTE -> VERIFY -> REPAIR orchestration

The important invariant is that successful tool return is not equivalent to successful engineering output.

### Recovery
Reuse:
- RecoveryController
- RecoverySolverRegistry
- TopologyRebindingRecoverySolver
- DiagnosisAgent
- ExecutionRepairAgent
- LegacyRepairBridge
- existing evidence/state-version driven recovery patterns

Recovery policy:

```text
failure
 -> structured diagnosis
 -> deterministic solver if available
 -> fresh topology/state evidence
 -> rebind/repair
 -> bounded retry
 -> measured verification
```

LLM may assist diagnosis/repair, but must not become an unrestricted SolidWorks command generator.

---

## 3. What SolidPilot actually provides

SolidPilot is the CAD execution substrate.

It provides valuable capabilities including:
- SolidWorks COM/API execution
- sketches and sketch entities
- feature operations
- reference inspection
- `analyze_model` evidence for faces/edges/features/geometry
- runtime state/version information

It does NOT by itself prove the complete path:

```text
natural language
 -> engineering interpretation
 -> robust planning
 -> reference selection
 -> execution
 -> verification
 -> recovery
```

Therefore the original expectation that SolidPilot alone should turn an unrestricted sentence such as:

"Build a 120x80x10 motor bracket with four M8 holes, two ribs and R5 outer fillets"

directly into a correct verified CAD part is not currently justified.

That complete behavior is the composition target.

---

## 4. Important SolidPilot/Solid_Ai discoveries

### 4.1 Tool completion is not geometric correctness

A result such as:

```json
{"status":"COMPLETED","error":null}
```

is insufficient.

A feature can exist in the Feature Tree while the visual or geometric result is wrong, incomplete, or not the intended feature.

The attached visual investigation exposed exactly this problem for an apparently successful cut/extrude scenario.

Therefore:

```text
tool success
 !=
feature success
 !=
geometry success
 !=
design-intent success
```

A valid verification layer must inspect measured geometry/topology and acceptance criteria.

### 4.2 Qualification scenarios need real prerequisites

An early `Q-CUT-001` failed because it attempted a blind cut without first constructing an existing solid body.

SolidPilot correctly returned an extrusion failure.

The scenario itself was invalid.

It was then corrected to:

```text
base sketch
 -> boss/extrude solid
 -> new sketch on/relative to existing body
 -> cut
 -> measured verification
```

This is a critical lesson:

> A qualification failure is not automatically a backend capability failure. First verify that the qualification scenario has all physical/CAD prerequisites.

### 4.3 Topology references are not stable by backend index

The motor-bracket work proved that backend indices change after topology mutation.

Useful pattern:

```text
reference intent
 -> analyze_model
 -> select geometrically
 -> bind backend index
 -> execute
 -> topology mutates
 -> fresh analyze_model
 -> rebind
 -> retry
```

The successful result:

```text
PASS: topology mutation + anchor rebinding + fillet recovery
```

is strong evidence that topology-aware recovery is useful and should be reused.

### 4.4 Face support must be explicit and evidence-backed

A real live test successfully demonstrated:

```text
FACE_BINDING -> backend face index
 -> create_sketch
 -> measured support
 -> FACE_SUPPORT_MATCH=True
```

This proved that support binding can be propagated into downstream sketch placement.

The earlier face/cut failures showed that coincident planes and direction assumptions are common failure modes.

### 4.5 Revolve has explicit axis semantics

A previous revolve test failed with:

```text
AXIS_NOT_FOUND
No sketch segment found at midpoint of provided axis coords.
```

The lesson is not to patch coordinates blindly.

The generic resolver must understand:
- the sketch frame
- axis orientation
- whether the axis is a sketch segment/reference
- endpoint semantics expected by the backend

The subsequent stepped revolve + groove + hole + fillet scenario was successfully executed, proving the basic feature family is feasible when its references are resolved correctly.

---

## 5. Capability Census lesson

A backend AST-based census found approximately 103 discovered backend capability variants.

At the time of census:

```text
discovered = 103
locally proven = 5
candidate = 98
blocked = 0
```

This does NOT mean the system only has five capabilities.

It means only five have local live evidence under the current evidence policy.

The correct state model is:

```text
discovered
candidate
live verified
canonical executable
fully benchmarked
```

Do not collapse these states.

Also:

> historical Ai_Designer evidence is useful evidence for prioritization, but it must not automatically promote a local Solid_Ai capability.

---

## 6. The biggest integration mistake to avoid

The first composition implementation attempted to import several canonical Ai_Designer modules using assumed paths.

One concrete failure was:

```text
ModuleNotFoundError:
'ai_designer.recovery.topology_solver'
```

with the actual message indicating that `ai_designer.recovery` was not a package in the test fixture.

A second failure was the composed E2E returning:

```text
AIDESIGNER_COMPOSITION_ERROR:
A canonical Ai_Designer component could not be imported
```

The lesson:

> Do not infer module paths from memory, filenames, or old notes. Inspect the actual current Ai_Designer tree and import symbols from the real current branch.

The repository currently contains top-level areas including:

```text
src/ai_designer/
  agentic/
  agents/
  cad_ir/
  capabilities/
  diagnostics/
  e2e/
  engineering/
  execution/
  llm/
  pipelines/
  planning/
  recovery/
  runtime/
  solidpilot/
```

But the exact Python module path and class symbol must be verified before coding.

---

## 7. Test-environment lessons

Several apparent failures were infrastructure/runner problems rather than CAD problems.

### Python environment

Direct scripts can run under the system Python while the MCP package exists only in:

```text
vendor/q3ds-solidworks-mcp/.venv
```

The live qualification launcher was therefore changed to use the MCP venv.

General rule:

> Any script that talks to the MCP server must use the environment containing the MCP Python dependencies.

### pytest import path

Running:

```text
python script.py
```

and running pytest do not necessarily produce the same import path.

A test suite can pass or fail based on repository-root path handling.

Do not treat a pytest import failure as a domain failure without first checking how the test is launched.

### async tests

Several runtime resolver tests emitted:

```text
async def functions are not natively supported
```

and `PytestUnknownMarkWarning: pytest.mark.anyio`.

This is a test-environment/plugin issue.

Do not modify domain logic to compensate for missing pytest async support.

---

## 8. LLM role

The correct LLM boundary is:

```text
LLM
 -> requirements/intent/planning assistance
 -> structured repair proposal
 -> validated result
```

not:

```text
LLM
 -> unrestricted raw SolidWorks commands
```

The LLM can help with:
- interpreting natural-language engineering intent
- resolving semantic ambiguity
- generating structured plans where appropriate
- diagnosis
- proposing bounded repairs

The deterministic layers remain responsible for:
- capability validity
- reference validity
- operation contracts
- geometry execution
- verification
- recovery bounds

---

## 9. Current Solid_Ai branches and intent

The important integration branch is:

```text
integration/aidesigner-canonical-v1
```

Its purpose is to create a thin composition seam, not another brain.

The important Ai_Designer convergence branch is:

```text
phase8-capability-convergence-v1
```

It records/fixes the rule that:

```text
live verification
 !=
canonical lowering availability
```

A live-verified capability without a canonical lowering must fail closed.

---

## 10. Do not continue the old path

Do NOT do the following:

1. Add another bespoke Motor Bracket runner.
2. Add another semantic parser inside Solid_Ai.
3. Add another LLM gateway.
4. Add another recovery registry.
5. Mark a capability proven because a tool returned COMPLETED.
6. Mark a capability proven because historical Ai_Designer evidence exists.
7. Write 20 tests for the same already-proven motor bracket path.
8. Implement feature mapping just to make the current test green.
9. Assume a backend index remains stable across topology mutations.
10. Claim >90% generalization before running unseen natural-language tasks.

---

## 11. What the next agent must do first

Before modifying code:

### Step A — inspect the actual current Ai_Designer branch
Read the real current module tree and symbols for:
- LLM gateway
- engineering pipeline
- planning
- execution
- recovery
- diagnostics
- SolidPilot client

Do not rely on the previously assumed import list.

### Step B — make the composition seam import-only
The first integration proof must be:

```text
load actual Ai_Designer stack
 -> instantiate canonical pipeline
 -> no duplicate planner/compiler/recovery
```

### Step C — make PLAN-only work first
Run:

```text
natural language
 -> Ai_Designer
 -> validated requirements
 -> IntentV2
 -> planning
 -> ExecutionPlanV3
```

No SolidWorks execution yet.

### Step D — inspect the first real boundary failure
Whatever fails becomes the next GAP.

### Step E — only then connect execution
Use the existing Ai_Designer SolidPilot boundary.

### Step F — use measured verification
A successful execution is not the benchmark result.

### Step G — use recovery
When a real failure occurs, reuse the existing Ai_Designer recovery assets before adding new ones.

---

## 12. Benchmark definition

The real success criterion is not pytest count.

The final benchmark must contain unseen Natural Language engineering tasks.

Target:

```text
final verified success >= 90%
first-attempt success >= 70%
recoverable-failure recovery >= 80%
```

The benchmark must contain multiple families, not variants of one motor bracket:

```text
prismatic
holes / patterns
revolve / axial
cut / groove
fillet / chamfer
loft / sweep
reference-heavy parts
topology mutation/recovery
multi-feature parts
assembly / sheet-metal / drawings where supported
```

Every successful task must be verified against geometry/intent, not merely operation status.

---

## 13. The fundamental definition of generalization

The project is not generalized when:

```text
103 capabilities are discovered
```

It is not generalized when:

```text
1000 pytest tests pass
```

It is generalized when the system can repeatedly solve previously unseen engineering requests:

```text
Natural Language
 -> Ai_Designer semantics
 -> planning
 -> SolidPilot
 -> SolidWorks
 -> measured verification
 -> recovery when needed
```

without a scenario-specific runner or hand-written feature sequence.

---

## 14. Most valuable conclusion from this work

The previous months of Ai_Designer work were not wasted.

The correct move is not to abandon it and rebuild around SolidPilot.

The correct move is to treat the two systems as complementary:

```text
Ai_Designer
  = engineering intelligence + LLM + semantic planning + recovery

SolidPilot
  = CAD execution + SolidWorks + topology/geometry evidence

Solid_Ai
  = integration and empirical qualification
```

The remaining work is primarily **convergence and gap closure**, not greenfield architecture.

This document is a continuation constraint for the next agent: reuse first, prove second, patch last.
