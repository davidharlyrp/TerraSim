"""
Rust-accelerated stress computation for Quad9 elements (9 Gauss points).
"""
import numpy as np

import terrasim_core

from .element_quad9 import NUM_GAUSS_POINTS


def compute_elements_stresses_rust(
    element_nodes_arr,
    total_u_candidate,
    elem_u_ref_arr,
    step_start_stress_arr,
    step_start_strain_arr,
    step_start_pwp_arr,
    step_start_state_vars_arr,
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
    mat_e50_ref_arr,
    mat_e_oed_ref_arr,
    mat_e_ur_ref_arr,
    mat_m_power_arr,
    mat_p_ref_arr,
    penalties_arr,
    is_srm,
    is_gravity_phase,
    target_m_stage,
    num_dof,
):
    num_active = len(element_nodes_arr)
    B_flat = B_matrices_arr.reshape(num_active * NUM_GAUSS_POINTS, 54)

    element_nodes_c = np.ascontiguousarray(element_nodes_arr, dtype=np.int64)
    total_u_c = np.ascontiguousarray(total_u_candidate, dtype=np.float64)
    elem_u_ref_c = np.ascontiguousarray(elem_u_ref_arr, dtype=np.float64)
    step_start_stress_c = np.ascontiguousarray(step_start_stress_arr, dtype=np.float64)
    step_start_strain_c = np.ascontiguousarray(step_start_strain_arr, dtype=np.float64)
    step_start_pwp_c = np.ascontiguousarray(step_start_pwp_arr, dtype=np.float64)
    step_start_state_vars_c = np.ascontiguousarray(step_start_state_vars_arr, dtype=np.float64)
    B_flat_c = np.ascontiguousarray(B_flat, dtype=np.float64)
    det_J_c = np.ascontiguousarray(det_J_arr, dtype=np.float64)
    weights_c = np.ascontiguousarray(weights_arr, dtype=np.float64)
    D_elastic_c = np.ascontiguousarray(D_elastic_arr, dtype=np.float64)
    pwp_static_c = np.ascontiguousarray(pwp_static_arr, dtype=np.float64)
    mat_drainage_c = np.ascontiguousarray(mat_drainage_arr, dtype=np.int64)
    mat_model_c = np.ascontiguousarray(mat_model_arr, dtype=np.int64)

    return terrasim_core.compute_stresses_loop(
        element_nodes_c,
        total_u_c,
        elem_u_ref_c,
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
        np.ascontiguousarray(mat_e50_ref_arr, dtype=np.float64),
        np.ascontiguousarray(mat_e_oed_ref_arr, dtype=np.float64),
        np.ascontiguousarray(mat_e_ur_ref_arr, dtype=np.float64),
        np.ascontiguousarray(mat_m_power_arr, dtype=np.float64),
        np.ascontiguousarray(mat_p_ref_arr, dtype=np.float64),
        step_start_state_vars_c,
        np.ascontiguousarray(penalties_arr, dtype=np.float64),
        bool(is_srm),
        bool(is_gravity_phase),
        float(target_m_stage),
        int(num_dof),
    )
