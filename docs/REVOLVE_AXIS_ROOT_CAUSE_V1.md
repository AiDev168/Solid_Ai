# Revolve Axis Root Cause V1

## Observed failure

The first stepped-revolve qualification successfully created the primary 360-degree revolve. The later revolved groove failed with AXIS_NOT_FOUND even though the semantic axis came from a valid centerline in the first sketch.

## Root cause

The current SolidPilot revolve contract resolves axis coordinates against the ACTIVE sketch. A semantic axis can therefore remain correct while becoming unresolvable in a later sketch that does not contain the centerline segment.

This is a reference-lifetime mismatch, not a mathematical axis problem.

## General solution

Keep the axis as a semantic binding, then materialize that binding into every consuming sketch as construction/reference geometry before calling the SolidPilot revolve operation.

Lifecycle:

semantic axis intent
  -> axis binding
  -> consuming sketch
  -> construction centerline materialization
  -> verify returned sketch geometry
  -> SolidPilot revolve/revolve_cut

## Why this belongs in the reference subsystem

The same pattern applies to any backend contract that resolves references only within the active sketch. Persistent semantic references must be rebound/materialized at the boundary where the backend requires local geometry.

## Qualification policy

A successful initial revolve does not prove reuse of its axis in later sketches. The later consumer must qualify its own support geometry.

Unknown or ambiguous axis matches must fail closed.

## Ai_Designer reuse

This follows the Ai_Designer separation between semantic reference identity, backend binding, evidence, and bounded recovery. Ai_Designer did not provide a pre-existing ready-made SolidPilot revolve fix; it provided the architecture needed to implement one without hard-coding backend indices or coordinates as identity.
