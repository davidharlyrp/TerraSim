# engine/solver/element_embedded_beam.py
# ===========================================================================
# Embedded Beam Element Logic (3rd DOF Frame Formulation)
# ===========================================================================

import numpy as np
from numba import njit

@njit
def compute_beam_element_matrix(node_coords, E, A, I, spacing, unit_weight=0.0, kh=0.0, kv=0.0):
    """
    Computes the 6x6 stiffness matrix for a 2D Bernoulli beam element.
    Returns: K_global (6x6), F_grav (6,)
    """
    x1, y1 = node_coords[0, 0], node_coords[0, 1]
    x2, y2 = node_coords[1, 0], node_coords[1, 1]
    
    dx = x2 - x1
    dy = y2 - y1
    L = np.sqrt(dx*dx + dy*dy)
    
    if L < 1e-9:
        return np.zeros((6, 6)), np.zeros(6)
        
    c = dx / L
    s = dy / L
    
    inv_spacing = 1.0 / spacing if spacing > 1e-9 else 1.0
    
    k_axial = (E * A / L) * inv_spacing
    k_bend = (E * I / (L**3)) * inv_spacing
    
    # Local stiffness matrix (6x6)
    k_local = np.zeros((6, 6))
    k_local[0, 0] = k_axial;  k_local[0, 3] = -k_axial
    k_local[3, 0] = -k_axial; k_local[3, 3] = k_axial
    
    # Bending components
    k_local[1, 1] = 12.0 * k_bend; k_local[1, 2] = 6.0 * k_bend * L
    k_local[1, 4] = -12.0 * k_bend; k_local[1, 5] = 6.0 * k_bend * L
    
    k_local[2, 1] = 6.0 * k_bend * L; k_local[2, 2] = 4.0 * k_bend * L * L
    k_local[2, 4] = -6.0 * k_bend * L; k_local[2, 5] = 2.0 * k_bend * L * L
    
    k_local[4, 1] = -12.0 * k_bend; k_local[4, 2] = -6.0 * k_bend * L
    k_local[4, 4] = 12.0 * k_bend; k_local[4, 5] = -6.0 * k_bend * L
    
    k_local[5, 1] = 6.0 * k_bend * L; k_local[5, 2] = 2.0 * k_bend * L * L
    k_local[5, 4] = -6.0 * k_bend * L; k_local[5, 5] = 4.0 * k_bend * L * L
    
    # Transformation matrix T (6x6)
    T = np.zeros((6, 6))
    T[0, 0] = c;  T[0, 1] = s
    T[1, 0] = -s; T[1, 1] = c
    T[2, 2] = 1.0
    T[3, 3] = c;  T[3, 4] = s
    T[4, 3] = -s; T[4, 4] = c
    T[5, 5] = 1.0
    
    # K_global = T.T @ k_local @ T
    K_global = T.T @ k_local @ T
    
    # Gravity Force
    total_w = (unit_weight * L) * inv_spacing
    Fx = kh * total_w / 2.0
    Fy = -(1.0 + kv) * total_w / 2.0
    
    F_grav = np.zeros(6)
    F_grav[0] = Fx; F_grav[1] = Fy
    F_grav[3] = Fx; F_grav[4] = Fy

    return K_global, F_grav

@njit
def compute_beam_internal_force_yield(node_coords, u_el, u_ref, E, A, I, spacing, capacity, is_srm, target_m_stage):
    """
    Computes internal force vector for a 6-DOF beam element with axial yielding.
    """
    x1, y1 = node_coords[0, 0], node_coords[0, 1]
    x2, y2 = node_coords[1, 0], node_coords[1, 1]
    
    dx = x2 - x1
    dy = y2 - y1
    L = np.sqrt(dx*dx + dy*dy)
    if L < 1e-9: return np.zeros(6), False

    c = dx / L
    s = dy / L
    
    # Transformation matrix T (6x6)
    T = np.zeros((6, 6))
    T[0, 0] = c;  T[0, 1] = s
    T[1, 0] = -s; T[1, 1] = c
    T[2, 2] = 1.0
    T[3, 3] = c;  T[3, 4] = s
    T[4, 3] = -s; T[4, 4] = c
    T[5, 5] = 1.0
    
    u_local = T @ (u_el - u_ref)
    
    inv_spacing = 1.0 / spacing if spacing > 1e-9 else 1.0
    k_axial = (E * A / L) * inv_spacing
    k_bend = (E * I / (L**3)) * inv_spacing
    
    # k_local construction
    k_local = np.zeros((6, 6))
    k_local[0, 0] = k_axial;  k_local[0, 3] = -k_axial
    k_local[3, 0] = -k_axial; k_local[3, 3] = k_axial
    
    k_local[1, 1] = 12.0 * k_bend; k_local[1, 2] = 6.0 * k_bend * L
    k_local[1, 4] = -12.0 * k_bend; k_local[1, 5] = 6.0 * k_bend * L
    k_local[2, 1] = 6.0 * k_bend * L; k_local[2, 2] = 4.0 * k_bend * L * L
    k_local[2, 4] = -6.0 * k_bend * L; k_local[2, 5] = 2.0 * k_bend * L * L
    k_local[4, 1] = -12.0 * k_bend; k_local[4, 2] = -6.0 * k_bend * L
    k_local[4, 4] = 12.0 * k_bend; k_local[4, 5] = -6.0 * k_bend * L
    k_local[5, 1] = 6.0 * k_bend * L; k_local[5, 2] = 2.0 * k_bend * L * L
    k_local[5, 4] = -6.0 * k_bend * L; k_local[5, 5] = 4.0 * k_bend * L * L
    
    f_local_trial = k_local @ u_local
    
    eff_capacity = capacity * inv_spacing
    if is_srm and target_m_stage > 0:
        eff_capacity /= target_m_stage
        
    f_axial = f_local_trial[3] 
    is_yielded = False
    if capacity > 0:
        if f_axial > eff_capacity:
            f_axial = eff_capacity
            is_yielded = True
        elif f_axial < -eff_capacity:
            f_axial = -eff_capacity
            is_yielded = True
            
    f_local = f_local_trial.copy()
    f_local[3] = f_axial
    f_local[0] = -f_axial
    
    f_global = T.T @ f_local
    return f_global, is_yielded

@njit
def compute_beam_forces_local(node_coords, u_el, u_ref, E, A, I, spacing):
    """
    Computes local internal forces [N, V1, M1, V2, M2]
    """
    x1, y1 = node_coords[0, 0], node_coords[0, 1]
    x2, y2 = node_coords[1, 0], node_coords[1, 1]
    
    dx = x2 - x1
    dy = y2 - y1
    L = np.sqrt(dx*dx + dy*dy)
    if L < 1e-9: return np.zeros(5)

    c = dx / L
    s = dy / L
    
    # Transformation matrix T (6x6)
    T = np.zeros((6, 6))
    T[0, 0] = c;  T[0, 1] = s
    T[1, 0] = -s; T[1, 1] = c
    T[2, 2] = 1.0
    T[3, 3] = c;  T[3, 4] = s
    T[4, 3] = -s; T[4, 4] = c
    T[5, 5] = 1.0
    
    u_local = T @ (u_el - u_ref)
    
    inv_spacing = 1.0 / spacing if spacing > 1e-9 else 1.0
    k_axial = (E * A / L) * inv_spacing
    k_bend = (E * I / (L**3)) * inv_spacing
    
    k_local = np.zeros((6, 6))
    k_local[0, 0] = k_axial;  k_local[0, 3] = -k_axial
    k_local[3, 0] = -k_axial; k_local[3, 3] = k_axial
    k_local[1, 1] = 12.0 * k_bend; k_local[1, 2] = 6.0 * k_bend * L
    k_local[1, 4] = -12.0 * k_bend; k_local[1, 5] = 6.0 * k_bend * L
    k_local[2, 1] = 6.0 * k_bend * L; k_local[2, 2] = 4.0 * k_bend * L * L
    k_local[2, 4] = -6.0 * k_bend * L; k_local[2, 5] = 2.0 * k_bend * L * L
    k_local[4, 1] = -12.0 * k_bend; k_local[4, 2] = -6.0 * k_bend * L
    k_local[4, 4] = 12.0 * k_bend; k_local[4, 5] = -6.0 * k_bend * L
    k_local[5, 1] = 6.0 * k_bend * L; k_local[5, 2] = 2.0 * k_bend * L * L
    k_local[5, 4] = -6.0 * k_bend * L; k_local[5, 5] = 4.0 * k_bend * L * L
    
    f_local = k_local @ u_local
    
    res = np.zeros(5)
    res[0] = f_local[3]  # N
    res[1] = -f_local[1] # V1
    res[2] = -f_local[2] # M1
    res[3] = f_local[4]  # V2
    res[4] = f_local[5]  # M2
    return res

@njit
def compute_beam_stiffness_only(node_coords, E, A, I, spacing):
    """Calculates stiffness matrix only, mostly for diagnostic use."""
    K, _ = compute_beam_element_matrix(node_coords, E, A, I, spacing)
    return K
