
import numpy as np
from numba import njit

@njit
def compute_beam_element_matrix(node_coords, E, A, spacing, unit_weight=0.0):
    """
    Computes the 4x4 stiffness matrix for a 2D Truss element (Axial only).
    node_coords: (2, 2) array [[x1, y1], [x2, y2]]
    E: Young's Modulus
    A: Cross-sectional Area
    spacing: Out-of-plane spacing
    
    Returns: K_global (4x4)
    DOFs: u1, v1, u2, v2
    """
    
    x1, y1 = node_coords[0, 0], node_coords[0, 1]
    x2, y2 = node_coords[1, 0], node_coords[1, 1]
    
    dx = x2 - x1
    dy = y2 - y1
    L = np.sqrt(dx*dx + dy*dy)
    
    if L < 1e-9:
        return np.zeros((4, 4)), np.zeros(4)
        
    c = dx / L
    s = dy / L
    
    # Stiffness E*A / L
    # Adjusted for spacing (per meter width)
    inv_spacing = 1.0 / spacing if spacing > 1e-9 else 1.0
    k = (E * A / L) * inv_spacing
    
    # Local matrix in global coordinates:
    # [ c^2   cs    -c^2  -cs ]
    # [ cs    s^2   -cs   -s^2]
    # [ -c^2  -cs   c^2   cs  ]
    # [ -cs   -s^2  cs    s^2 ]
    
    cc = c*c
    ss = s*s
    cs = c*s
    
    K = np.zeros((4, 4))
    K[0,0] = cc*k; K[0,1] = cs*k; K[0,2] = -cc*k; K[0,3] = -cs*k
    K[1,0] = cs*k; K[1,1] = ss*k; K[1,2] = -cs*k; K[1,3] = -ss*k
    K[2,0] = -cc*k; K[2,1] = -cs*k; K[2,2] = cc*k; K[2,3] = cs*k
    K[3,0] = -cs*k; K[3,1] = -ss*k; K[3,2] = cs*k; K[3,3] = ss*k
    
    # Gravity Force (F_y = -w * L / 2 / spacing)
    # Total weight of segment = (unit_weight * L) / spacing
    # Distributed equally to both nodes
    total_w = (unit_weight * L) * inv_spacing
    F_grav = np.array([0.0, -total_w/2.0, 0.0, -total_w/2.0])

    return K, F_grav

@njit
def compute_beam_internal_force_yield(node_coords, u_el, E, A, spacing, capacity, is_srm, target_m_stage):
    """
    Computes internal force vector for a beam element with axial yielding.
    u_el: (4,) array [u1, v1, u2, v2]
    capacity: Maximum axial force (Tension/Compression)
    is_srm: If True, capacity is reduced by target_m_stage
    """
    x1, y1 = node_coords[0, 0], node_coords[0, 1]
    x2, y2 = node_coords[1, 0], node_coords[1, 1]
    
    dx = x2 - x1
    dy = y2 - y1
    L = np.sqrt(dx*dx + dy*dy)
    if L < 1e-9: return np.zeros(4), False

    c = dx / L
    s = dy / L
    
    # Local displacements (axial only)
    # u_local = u*c + v*s
    u1_local = u_el[0]*c + u_el[1]*s
    u2_local = u_el[2]*c + u_el[3]*s
    du_local = u2_local - u1_local
    
    # Trial axial force (kN)
    # Stiffness already accounts for spacing
    inv_spacing = 1.0 / spacing if spacing > 1e-9 else 1.0
    k_axial = (E * A / L) * inv_spacing
    
    f_axial_trial = k_axial * du_local
    
    # Yielding check
    eff_capacity = capacity
    if is_srm and target_m_stage > 0:
        eff_capacity /= target_m_stage
        
    f_axial = f_axial_trial
    is_yielded = False
    if np.abs(f_axial_trial) > eff_capacity:
        f_axial = np.sign(f_axial_trial) * eff_capacity
        is_yielded = True
        
    # Convert back to global forces
    # Node 1: -f_axial in local direction
    # Node 2: f_axial in local direction
    f_int = np.zeros(4)
    f_int[0] = -f_axial * c
    f_int[1] = -f_axial * s
    f_int[2] = f_axial * c
    f_int[3] = f_axial * s
    
    return f_int, is_yielded

@njit
def compute_beam_stiffness_only(node_coords, E, A, spacing):
    """Legacy helper for backward compatibility or when gravity isn't needed."""
    K, _ = compute_beam_element_matrix(node_coords, E, A, spacing)
    return K
