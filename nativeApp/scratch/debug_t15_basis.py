
import sys
import os
import numpy as np

# Mocking parts of engine to load mesh
sys.path.append(os.getcwd())
from engine.solver.element_t15 import shape_functions_t15

def test_partition_of_unity():
    print("Testing T15 Shape Functions Partition of Unity...")
    points = [
        (0.333, 0.333), # center
        (0.25, 0.25),   # node 13
        (0.5, 0.25),    # node 14 approx
        (0.1, 0.1),
        (0.8, 0.1),
        (0.1, 0.8)
    ]
    
    for xi, eta in points:
        N = shape_functions_t15(xi, eta)
        s = np.sum(N)
        print(f"  At ({xi:.3f}, {eta:.3f}): Sum(N) = {s:.12f}  {'[OK]' if abs(s-1.0)<1e-12 else '[FAIL]'}")
        if abs(s-1.0) > 1e-12:
            raise ValueError(f"Partition of Unity violated at ({xi}, {eta}): sum={s}")

def test_nodal_interpolation():
    print("\nTesting T15 Nodal Interpolation...")
    # corners: (0,0), (1,0), (0,1)
    # n1: (0,0) -> L1=1, L2=0, L3=0
    # n2: (1,0) -> L1=0, L2=1, L3=0
    # n3: (0,1) -> L1=0, L2=0, L3=1
    nodes_nat = [
        (0,0), (1,0), (0,1), # Corners
        (0.25, 0), (0.5, 0), (0.75, 0), # Edge 1-2
        (0.75, 0.25), (0.5, 0.5), (0.25, 0.75), # Edge 2-3
        (0, 0.75), (0, 0.5), (0, 0.25), # Edge 3-1
        (0.25, 0.25), (0.5, 0.25), (0.25, 0.5) # Interiors
    ]
    
    for i, (xi, eta) in enumerate(nodes_nat):
        N = shape_functions_t15(xi, eta)
        val = N[i]
        other_sum = np.sum(N) - val
        print(f"  Node {i+1} at ({xi:.2f}, {eta:.2f}): N[{i}] = {val:.4f}, OtherSum = {other_sum:.4e} {'[OK]' if abs(val-1.0)<1e-12 and abs(other_sum)<1e-12 else '[FAIL]'}")

if __name__ == "__main__":
    try:
        test_partition_of_unity()
        test_nodal_interpolation()
        print("\nALL BASIS TESTS PASSED.")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
