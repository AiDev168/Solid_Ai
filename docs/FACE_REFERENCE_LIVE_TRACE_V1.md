# Face Reference Live Trace V1

## Purpose

This is a root-cause diagnostic gate for model-face references. It separates semantic face resolution from execution and immediately verifies the measured SolidWorks sketch support.

## Flow

```text
base
  -> analyze_model(faces)
  -> ReferenceIntent(top_planar)
  -> ReferenceBinding(face_index, state_version, evidence)
  -> create_sketch(on_face=true, face_index=N)
  -> measured result_geometry.frame
  -> face/support invariant
```

## Invariant

The sketch frame must lie on the resolved planar face and its measured normal must agree with the face normal. A successful MCP status alone is insufficient.

## Why this exists

The earlier Motor Bracket run returned create_sketch=COMPLETED while reporting `Front Plane` with an offset instead of the intended model face. This trace isolates that boundary before circles/cuts/ribs are executed.

## Live command

```powershell
scripts\trace_face_binding_live_v1.cmd
```

A passing run prints `FACE_BINDING`, the actual `CREATE_SKETCH` response, `FACE_SUPPORT_MATCH: True`, and `PASS`.

A failure prints the resolved face evidence and the measured sketch frame so the broken layer is observable instead of guessed.
