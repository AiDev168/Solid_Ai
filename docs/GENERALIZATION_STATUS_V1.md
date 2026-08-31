# Solid_Ai Generalization Status V1

## هدف فعلی

هدف پروژه «تعداد زیاد تست سبز» نیست. معیار اصلی، توانایی عبور سناریوهای مهندسی ندیده از مسیر زیر است:

Natural Language → LLM/Ai_Designer → Semantic IR/FeatureGraph → Generic Compiler/Lowering → Reference Resolution → SolidPilot → SolidWorks → Verification → Bounded Recovery.

## وضعیت اثبات‌شده

- SolidPilot ↔ SolidWorks COM: live evidence
- prismatic multi-feature runtime: live evidence
- topology-aware face/edge resolution and rebinding: live evidence
- stepped revolve + groove + hole + fillet: live evidence
- semantic FeatureGraph → generic executor → SolidWorks: live evidence
- capability census from backend source: 103 discovered capabilities
- repository tests: 80 passed at last reported baseline before this qualification harness

## اصل معماری

Discovery is not proof.

A capability is not promoted because a backend tool exists, because a historical Ai_Designer record exists, or because an LLM can name it. Promotion requires live evidence and explicit verification. Historical Ai_Designer evidence is reused for prioritization and strategy, not silent local promotion.

## Ai_Designer assets being reused

- provider-neutral LLM gateway and structured-output validation
- requirements/intent extraction patterns
- fidelity gates and constraint preservation
- evidence-backed capability discovery
- deterministic recovery controller
- solver registry and bounded recovery
- topology rebinding and stale-reference recovery
- diagnosis/retry patterns

## Qualification matrix V1

The first representative modeling families are:

1. prismatic cut
2. linear/circular pattern
3. sketch line/arc
4. sketch constraints
5. reference axis/plane
6. edge chamfer
7. loft
8. sweep

These are qualification probes, not claims of support. A candidate becomes proven only after live execution plus verification.

## Why the qualification harness exists

The harness prevents a return to feature-specific runners. Each scenario declares:

- semantic capability id
- strategy family
- minimal representative operations
- verification signals
- promotion target

The harness can plan/filter scenarios and can execute them through a generic executor. It records evidence separately from promotion state.

## Generalization gate

The long-term benchmark is an unseen-task benchmark rather than a unit-test count. Target metrics:

- final success rate >= 90%
- first-attempt success rate >= 70%
- recovery success rate >= 80% for failures classified as recoverable

A benchmark result is meaningful only when the scenario was not encoded as a component-specific runner.

## Next sequence

G2: qualify core modeling candidates using the generic harness.

G3: connect the same harness to Ai_Designer LLM planning for real natural-language inputs.

G4: add recovery/diagnosis to the live generic execution loop.

G5: run the unseen 100-scenario benchmark and publish the capability-family scorecard.

Until a milestone is live and verified, it is not counted as proven.
