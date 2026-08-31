# Stepped Revolve Qualification Test V1

Purpose: qualify a different CAD capability family from the motor-bracket proof.

The live sequence covers:

1. stepped revolved solid;
2. 360 degree revolved groove/cut;
3. face-based hole;
4. post-mutation topology inspection;
5. fillet;
6. final geometry verification.

The revolve axis is not supplied as an arbitrary near-zero vector. The semantic axis resolver selects the real centerline segment from the profile and passes its actual endpoints to SolidPilot.

This test is deliberately a capability probe, not a claim of unrestricted CAD generality. A successful run proves that the current stack can execute and verify a mixed axial feature chain on live SolidWorks. A failure should be classified into reference resolution, feature lowering, execution, or recovery rather than patched inside the test.
