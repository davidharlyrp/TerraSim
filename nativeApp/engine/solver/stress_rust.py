"""
Rust-Accelerated Stress Computation (Batch Kernel)

Uses the terrasim_core.compute_stresses_loop() Rust function which runs
the ENTIRE element stress computation loop in Rust, eliminating
Python-Rust FFI overhead per element.

This is a drop-in replacement for compute_elements_stresses_numba().
"""
import numpy as np

try:
    import terrasim_core
    _HAS_BATCH_KERNEL = hasattr(terrasim_core, 'compute_stresses_loop')
except ImportError:
    _HAS_BATCH_KERNEL = False


def compute_elements_stresses_rust(
    element_nodes_arr,
    total_u_candidate,
    step_start_stress_arr,
    step_start_strain_arr,
    step_start_pwp_arr,
    B_matrices_arr,
    det_J_arr,
    weights_arr,
    D_elastic_arr,
    pwp_static_arr,
    mat_drainage_arr,
    mat_model_arr,
    mat_c_arr,
    mat_phi_arr,
    mat_su_arr,
    mat_sigma_ci_arr,
    mat_gsi_arr,
    mat_disturb_factor_arr,
    mat_mb_arr,
    mat_s_arr,
    mat_a_arr,
    penalties_arr,
    is_srm,
    is_gravity_phase,
    target_m_stage,
    num_dof
):
    """
    Rust-accelerated stress computation using batch kernel.
    
    Reshapes B_matrices from (N,3,3,12) to (N*3,36) for Rust,
    then calls terrasim_core.compute_stresses_loop() in a single FFI call.
    """
    if not _HAS_BATCH_KERNEL:
        raise RuntimeError("terrasim_core batch kernel not available")

    num_active = len(element_nodes_arr)

    # Reshape B_matrices: (N, 3, 3, 12) -> (N*3, 36)
    B_flat = B_matrices_arr.reshape(num_active * 3, 36)

    # Ensure contiguous arrays with correct dtypes
    element_nodes_c = np.ascontiguousarray(element_nodes_arr, dtype=np.int64)
    total_u_c = np.ascontiguousarray(total_u_candidate, dtype=np.float64)
    step_start_stress_c = np.ascontiguousarray(step_start_stress_arr, dtype=np.float64)
    step_start_strain_c = np.ascontiguousarray(step_start_strain_arr, dtype=np.float64)
    step_start_pwp_c = np.ascontiguousarray(step_start_pwp_arr, dtype=np.float64)
    B_flat_c = np.ascontiguousarray(B_flat, dtype=np.float64)
    det_J_c = np.ascontiguousarray(det_J_arr, dtype=np.float64)
    weights_c = np.ascontiguousarray(weights_arr, dtype=np.float64)
    D_elastic_c = np.ascontiguousarray(D_elastic_arr, dtype=np.float64)
    pwp_static_c = np.ascontiguousarray(pwp_static_arr, dtype=np.float64)
    mat_drainage_c = np.ascontiguousarray(mat_drainage_arr, dtype=np.int64)
    mat_model_c = np.ascontiguousarray(mat_model_arr, dtype=np.int64)

    F_int, new_stresses, new_yield, new_strain, new_pwp_excess = terrasim_core.compute_stresses_loop(
        element_nodes_c,
        total_u_c,
        step_start_stress_c,
        step_start_strain_c,
        step_start_pwp_c,
        B_flat_c,
        det_J_c,
        weights_c,
        D_elastic_c,
        pwp_static_c,
        mat_drainage_c,
        mat_model_c,
        np.ascontiguousarray(mat_c_arr, dtype=np.float64),
        np.ascontiguousarray(mat_phi_arr, dtype=np.float64),
        np.ascontiguousarray(mat_su_arr, dtype=np.float64),
        np.ascontiguousarray(mat_sigma_ci_arr, dtype=np.float64),
        np.ascontiguousarray(mat_gsi_arr, dtype=np.float64),
        np.ascontiguousarray(mat_disturb_factor_arr, dtype=np.float64),
        np.ascontiguousarray(mat_mb_arr, dtype=np.float64),
        np.ascontiguousarray(mat_s_arr, dtype=np.float64),
        np.ascontiguousarray(mat_a_arr, dtype=np.float64),
        np.ascontiguousarray(penalties_arr, dtype=np.float64),
        bool(is_srm),
        bool(is_gravity_phase),
        float(target_m_stage),
        int(num_dof),
    )

    return F_int, new_stresses, new_yield, new_strain, new_pwp_excess
