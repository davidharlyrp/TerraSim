# engine/solver/element_embedded_beam.py
# ===========================================================================
# Embedded Beam Element Logic (Pure Rust Wrapper)
# ===========================================================================

import numpy as np
import terrasim_core

def compute_beam_element_matrix(node_coords, E, A, I, spacing, unit_weight, kh, kv):
    return terrasim_core.compute_beam_element_matrix(
        np.ascontiguousarray(node_coords, dtype=np.float64),
        float(E), float(A), float(I), float(spacing),
        float(unit_weight), float(kh), float(kv)
    )

def compute_beam_internal_force_yield(node_coords, u_el, u_ref, E, A, I, spacing, capacity, is_srm, target_m_stage):
    return terrasim_core.compute_beam_internal_force_yield(
        np.ascontiguousarray(node_coords, dtype=np.float64),
        np.ascontiguousarray(u_el, dtype=np.float64),
        np.ascontiguousarray(u_ref, dtype=np.float64),
        float(E), float(A), float(I), float(spacing), float(capacity),
        bool(is_srm), float(target_m_stage)
    )

def compute_beam_forces_local(node_coords, u_el, u_ref, E, A, I, spacing):
    return terrasim_core.compute_beam_forces_local(
        np.ascontiguousarray(node_coords, dtype=np.float64),
        np.ascontiguousarray(u_el, dtype=np.float64),
        np.ascontiguousarray(u_ref, dtype=np.float64),
        float(E), float(A), float(I), float(spacing)
    )

def compute_beam_stiffness_only(node_coords, E, A, I, spacing):
    K, _ = compute_beam_element_matrix(node_coords, E, A, I, spacing)
    return K
