import numpy as np
from backend.solver.phase_solver import compute_elements_stresses_numba
from backend.models import DrainageType, MaterialModel

def test_pwp_sign():
    # 1. Setup a single T6 element (unit triangle)
    # n1(0,0), n2(1,0), n3(0,1), n4(0.5,0), n5(0.5,0.5), n6(0,0.5)
    elem_nodes = np.array([0, 1, 2, 3, 4, 5], dtype=np.int32)
    node_coords = np.array([
        [0.0, 0.0], [1.0, 0.0], [0.0, 1.0],
        [0.5, 0.0], [0.5, 0.5], [0.0, 0.5]
    ])
    
    # 2. Material - Undrained A (Mohr-Coulomb)
    # E=10000, nu=0.3
    E = 10000.0; nu = 0.3
    factor = E / ((1 + nu) * (1 - 2*nu))
    D_el = np.array([
        [1-nu, nu, 0.0],
        [nu, 1-nu, 0.0],
        [0.0, 0.0, (1-2*nu)/2.0]
    ]) * factor
    
    # 3. Simulate Compression step
    # Move nodes inward: top nodes down, right nodes left
    # Boundary: n1, n3, n6 are on X=0 or Y=0 axis.
    # Compress by moving n2 and n5 in -X direction
    total_u = np.zeros(12)
    # Move node 2 left by -0.01 (Compression in X)
    total_u[2] = -0.01 
    # Move node 4 (midpoint 1-2) left by -0.005
    total_u[6] = -0.005
    # Move node 5 left by -0.005
    total_u[10] = -0.005
    
    # Inputs for stressed kernel
    elem_nodes_arr = np.array([elem_nodes])
    step_start_stress = np.zeros((1, 3, 3))
    step_start_strain = np.zeros((1, 3, 3))
    step_start_pwp = np.zeros((1, 3))
    
    # Pre-calculated B matrix (simplify by just using one GP or fake it)
    # Actually, B matrix for Triangle (0,1) with L=1 is [[-1, 0, ...], [0, -1, ...], ...]
    # For simplicity, let's just use B where B @ u gives d_epsilon = [-0.01, 0, 0]
    # d_vol = -0.01 (Compression)
    
    # Fake B and det_J for a single GP
    B = np.zeros((3, 12))
    B[0, 2] = 1.0 # node 2 x-dof contributes to epsilon_x
    # Wait, if node 2 moves -0.01, and B[0,2]=1, then epsilon_x = -0.01. Correct.
    
    B_matrices_arr = np.array([[B, B, B]])
    det_J_arr = np.array([[1.0, 1.0, 1.0]])
    weights_arr = np.array([1/6.0, 1/6.0, 1/6.0])
    pwp_static_arr = np.zeros((1, 3))
    
    mat_drainage_arr = np.array([1], dtype=np.int32) # UNDRAINED_A
    mat_model_arr = np.array([1], dtype=np.int32)    # MC
    mat_c_arr = np.array([30.0])
    mat_phi_arr = np.array([0.0])
    mat_su_arr = np.array([30.0])
    
    # HB params
    mat_arr_zero = np.zeros(1)
    
    Kw = 2.2e6; porosity = 0.3; penalty = Kw / porosity
    # Penalty cap check in solve_phases: if penalty > 10*K_skel
    K_skel = E / (3 * (1 - 2*nu))
    if penalty > 10 * K_skel: penalty = 10 * K_skel
    penalties_arr = np.array([penalty])
    
    print(f"Testing Compression: Penalty={penalty:.2e}, expect d_vol < 0")
    
    F_int, stresses, yields, strains, pwp_excess = compute_elements_stresses_numba(
        elem_nodes_arr, total_u, step_start_stress, step_start_strain, step_start_pwp,
        B_matrices_arr, det_J_arr, weights_arr, np.array([D_el]), pwp_static_arr,
        mat_drainage_arr, mat_model_arr, mat_c_arr, mat_phi_arr, mat_su_arr,
        mat_arr_zero, mat_arr_zero, mat_arr_zero, mat_arr_zero, mat_arr_zero, mat_arr_zero,
        penalties_arr, False, False, 1.0, 12
    )
    
    print(f"Result PWP Excess: {pwp_excess[0, 0]:.4f}")
    if pwp_excess[0, 0] < 0:
        print("Convention OK: Compression -> Negative PWP (Pressure)")
    else:
        print("Convention ERROR: Compression -> Positive PWP")

if __name__ == "__main__":
    test_pwp_sign()
