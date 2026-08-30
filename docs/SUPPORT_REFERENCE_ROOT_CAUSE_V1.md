# Support Reference Root Cause V1

## Failure reproduced

Motor Bracket V1 successfully created the 120 x 80 x 10 mm base and four 8 mm circles, but the cut failed because the sketch was attached to the wrong semantic face. The prior resolver interpreted top_planar as a face whose normal was global +Z.

## Actual runtime geometry

The SolidPilot Top Plane sketch frame is commonly reported as:

- xdir = [1, 0, 0]
- ydir = [0, 0, -1]

Therefore its normal is +Y. A 10 mm extrusion from that sketch advances along +Y, so the end support plane is at the source origin plus 0.01 m along the frame normal. Selecting a +Z face at z=0.04 m is a side face, even though a local support check can report a geometric match against that wrong face.

## Root cause

The old support role mixed three different concepts:

1. a global-axis label such as top;
2. a model face identity;
3. a sketch-local coordinate frame.

Those are not equivalent in SolidWorks automation.

## Correct abstraction

A support reference is now derived from the producer feature:

~~~text
producer sketch frame
        +
producer extrusion depth
        ↓
expected support plane
        ↓
fresh SolidPilot face evidence
        ↓
face binding
        ↓
create_sketch(face_index)
        ↓
measured support verification
~~~

The generic resolver is in integration/support_reference_v1.py.

The same module also resolves extrusion-axis boundary edges in the producer sketch's local UV frame. This prevents the same global-Z mistake from reappearing in outer-edge Fillet selection.

## Reuse of Ai_Designer assets

This follows the useful parts of Ai_Designer stable-reference and topology-rebinding architecture: semantic intent is separated from backend selectors; runtime indices are temporary bindings; evidence is refreshed after mutation; ambiguous matches fail closed; recovery is bounded.

The new implementation does not import the old Ai_Designer runtime graph.

## Verification

Unit regression:

~~~powershell
vendor\q3ds-solidworks-mcp\.venv\Scripts\python.exe -m pytest -q tests/test_feature_frame_support_v1.py tests/test_reference_resolution_v1.py tests/test_face_support_contract_v1.py
~~~

Live support gate:

~~~powershell
scripts\trace_face_binding_live_v1.cmd
~~~

Motor Bracket V2:

~~~powershell
scripts\run_motor_bracket_runtime_v2.cmd
~~~

## Policy

Do not repair this class of failure by changing cut depth, reversing the cut, guessing a different face coordinate, or hard-coding a backend face index. Those are downstream symptoms. The support resolver must first establish the correct producer-relative reference.
