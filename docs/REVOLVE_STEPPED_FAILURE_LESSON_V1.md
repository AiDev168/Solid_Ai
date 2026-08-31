# Revolve Stepped Failure Lesson V1

## Observed live failure

After Revolve + Revolve Cut + Hole, `analyze_model(analysis_type=edges)` returned circular/analytic edges whose `start` and `end` representative coordinates were identical, while each edge also had a positive measured `length`.

The runner incorrectly classified these as unusable by requiring a non-zero endpoint-to-endpoint distance.

## Root cause

The runtime treated endpoint distance as a universal definition of edge usability. That is valid for straight segments but invalid for analytic curves where SolidWorks may expose representative endpoint fields that are equal.

## General fix

Edge evidence now has an explicit qualification layer:

1. resolve a stable backend index from `i`, `index`, or `backend_index`;
2. prefer measured `length` when present and positive;
3. otherwise compute straight-line endpoint distance;
4. reject only edges that have neither measurable curve length nor endpoint extent.

This logic is shared through `integration/topology_edge_v1.py` instead of being embedded in a single test runner.

## Why this matters

The failure demonstrates another general rule:

`analyze_model` evidence is typed geometric evidence, not necessarily raw segment endpoints.

Resolvers must interpret evidence according to geometry kind and available measurements rather than assuming every edge is a line segment.

## Regression

`tests/test_topology_edge_v1.py` covers:
- circular edges with equal representative start/end points;
- straight edges without explicit length;
- true zero-length artifacts;
- selection of the longest usable analytic edge.
