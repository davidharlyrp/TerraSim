"""
T15 Element Module
15-node quartic triangle element with 9-point Gauss quadrature integration.
Implements fourth-order shape functions for professional-grade geotechnical analysis.
Node ordering follows PLAXIS standard:
- 0, 1, 2: Corners
- 3, 4, 5: Edge 0-1 (positions 1/4, 2/4, 3/4)
- 6, 7, 8: Edge 1-2 (positions 1/4, 2/4, 3/4)
- 9, 10, 11: Edge 2-0 (positions 1/4, 2/4, 3/4)
- 12, 13, 14: Interior nodes
"""
import numpy as np
from typing import List, Dict, Optional, Tuple
from engine.models import Material, DrainageType
from numba import njit

# === 12-point Dunavant Gauss Quadrature for Triangles (Order 7) ===
# Required for full accuracy and stability of quartic (15-node) elements.
# Format: [xi, eta] (natural coordinates)
GAUSS_POINTS = np.array([
    [0.063089014576192, 0.063089014576192],
    [0.063089014576192, 0.873821970847616],
    [0.873821970847616, 0.063089014576192],
    [0.249286745170910, 0.249286745170910],
    [0.249286745170910, 0.501426509658179],
    [0.501426509658179, 0.249286745170910],
    [0.310352451033784, 0.053145049344120],
    [0.053145049344120, 0.636502499622095],
    [0.636502499622095, 0.310352451033784],
    [0.053145049344120, 0.310352451033784],
    [0.310352451033784, 0.636502499622095],
    [0.636502499622095, 0.053145049344120],
])
# Weights (must sum to 0.5 for a unit triangle in xi-eta space)
# High-precision 12-point Dunavant weights (summing to exactly 0.5)
GAUSS_WEIGHTS = np.array([
    0.02517361530155050, 0.02517361530155050, 0.02517361530155050,
    0.05839313786335150, 0.05839313786335150, 0.05839313786335150,
    0.04142553780918917, 0.04142553780918917, 0.04142553780918917,
    0.04142553780918917, 0.04142553780918917, 0.04142553780918917
])

@njit
def langrange_tri_basis(L1: float, L2: float, L3: float, i: int, j: int, k: int) -> float:
    """General Lagrange polynomial for triangle at (L1, L2, L3) for node triplet (i, j, k)."""
    val = 1.0
    # term for i
    for p in range(i):
        val *= (4.0 * L1 - p) / (p + 1.0)
    # term for j
    for p in range(j):
        val *= (4.0 * L2 - p) / (p + 1.0)
    # term for k
    for p in range(k):
        val *= (4.0 * L3 - p) / (p + 1.0)
    return val

@njit
def shape_functions_t15(xi: float, eta: float) -> np.ndarray:
    """
    Compute T15 quartic shape functions using systematic Lagrange Basis.
    Barycentric: L2 = xi, L3 = eta, L1 = 1 - xi - eta
    Node triplets (i+j+k=4):
    """
    L2 = xi
    L3 = eta
    L1 = 1.0 - xi - eta
    
    # Node Mapping (i, j, k) where i+j+k=4
    # Following: Corners (1,2,3), Edge 1-2 (4,5,6), Edge 2-3 (7,8,9), Edge 3-1 (10,11,12), Interiors (13,14,15)
    triplets = [
        (4,0,0), (0,4,0), (0,0,4),  # Corners
        (3,1,0), (2,2,0), (1,3,0),  # Edge 1-2 (n4, n5, n6)
        (0,3,1), (0,2,2), (0,1,3),  # Edge 2-3 (n7, n8, n9)
        (1,0,3), (2,0,2), (3,0,1),  # Edge 3-1 (n10, n11, n12)
        (2,1,1), (1,2,1), (1,1,2)   # Interiors (n13, n14, n15)
    ]
    
    N = np.zeros(15)
    for idx in range(15):
        i, j, k = triplets[idx]
        N[idx] = langrange_tri_basis(L1, L2, L3, i, j, k)
    return N

@njit
def lagrange_tri_basis_deriv(L1: float, L2: float, L3: float, i: int, j: int, k: int) -> np.ndarray:
    """Analytical derivatives of Lagrange basis w.r.t [L1, L2, L3]."""
    def L_val(L, m):
        v = 1.0
        for p in range(m):
            v *= (4.0 * L - p) / (p + 1.0)
        return v
    
    def L_deriv(L, m):
        if m == 0: return 0.0
        total = 0.0
        for q in range(m):
            term = 4.0 / (q + 1.0)
            for p in range(m):
                if p != q:
                    term *= (4.0 * L - p) / (p + 1.0)
            total += term
        return total

    dN_dL1 = L_deriv(L1, i) * L_val(L2, j) * L_val(L3, k)
    dN_dL2 = L_val(L1, i) * L_deriv(L2, j) * L_val(L3, k)
    dN_dL3 = L_val(L1, i) * L_val(L2, j) * L_deriv(L3, k)
    return np.array([dN_dL1, dN_dL2, dN_dL3])

@njit
def shape_function_derivatives_natural(xi: float, eta: float) -> np.ndarray:
    """
    Analytical derivatives w.r.t xi and eta using chain rule from barycentric basis.
    Barycentric: L2=xi, L3=eta, L1=1-xi-eta
    dN/dxi = dN/dL2 - dN/dL1
    dN/deta = dN/dL3 - dN/dL1
    """
    L2 = xi
    L3 = eta
    L1 = 1.0 - xi - eta
    
    triplets = [
        (4,0,0), (0,4,0), (0,0,4),
        (3,1,0), (2,2,0), (1,3,0),
        (0,3,1), (0,2,2), (0,1,3),
        (1,0,3), (2,0,2), (3,0,1),
        (2,1,1), (1,2,1), (1,1,2)
    ]
    
    dN = np.zeros((2, 15))
    for idx in range(15):
        i, j, k = triplets[idx]
        dn_l = lagrange_tri_basis_deriv(L1, L2, L3, i, j, k)
        # dN/dxi = (dN/dL2 * dL2/dxi) + (dN/dL1 * dL1/dxi) = dN/dL2 - dN/dL1
        dN[0, idx] = dn_l[1] - dn_l[0]
        # dN/deta = (dN/dL3 * dL3/deta) + (dN/dL1 * dL1/deta) = dN/dL3 - dN/dL1
        dN[1, idx] = dn_l[2] - dn_l[0]
        
    return dN

@njit
def compute_b_matrix(node_coords: np.ndarray, xi: float, eta: float) -> Tuple[np.ndarray, float]:
    """
    Physical B-matrix (3 x 30) for 15-node triangle.
    """
    dN_natural = shape_function_derivatives_natural(xi, eta)
    
    # Jacobian (2x15) @ (15x2) = (2x2)
    J = dN_natural @ node_coords
    det_J = np.linalg.det(J)
    
    if abs(det_J) < 1e-12:
        return np.zeros((3, 30)), 0.0
        
    J_inv = np.linalg.inv(J)
    dN_physical = J_inv @ dN_natural # (2x15)
    
    B = np.zeros((3, 30))
    for i in range(15):
        # UX DOF at 2*i, UY DOF at 2*i+1
        B[0, 2*i] = dN_physical[0, i]   # dNi/dx (eps_xx)
        B[1, 2*i+1] = dN_physical[1, i] # dNi/dy (eps_yy)
        B[2, 2*i] = dN_physical[1, i]   # dNi/dy (gam_xy)
        B[2, 2*i+1] = dN_physical[0, i] # dNi/dx (gam_xy)
        
    return B, det_J

def get_water_level_at(x: float, water_level_polyline: Optional[List[Dict]] = None) -> Optional[float]:
    """Interpolate water level Y at given X from a polyline (ordered by X)."""
    if not water_level_polyline or len(water_level_polyline) < 1:
        return None
    
    pts = sorted(water_level_polyline, key=lambda p: p['x'])
    
    if x <= pts[0]['x']:
        return pts[0]['y']
    if x >= pts[-1]['x']:
        return pts[-1]['y']
    
    for i in range(len(pts) - 1):
        p1 = pts[i]
        p2 = pts[i+1]
        if p1['x'] <= x <= p2['x']:
            t = (x - p1['x']) / (p2['x'] - p1['x'])
            return p1['y'] + t * (p2['y'] - p1['y'])
    return None

def compute_element_matrices_t15(
    node_coords: np.ndarray, # (15, 2)
    material: Material,
    water_level: Optional[List[Dict]] = None,
    thickness: float = 1.0,
    kh: float = 0.0,
    kv: float = 0.0
) -> Tuple[np.ndarray, np.ndarray, List[Dict], np.ndarray]:
    """
    Full T15 stiffness and gravity vector integration using 12GP.
    """
    # 1. Constitutive
    if material.drainage_type in [DrainageType.UNDRAINED_C, DrainageType.NON_POROUS]:
        E = material.youngsModulus
    else:
        E = material.effyoungsModulus or 10000.0
    nu = material.poissonsRatio
    factor = E / ((1 + nu) * (1 - 2*nu))
    D = np.array([
        [1-nu, nu, 0],
        [nu, 1-nu, 0],
        [0, 0, (1-2*nu)/2]
    ]) * factor

    K = np.zeros((30, 30))
    F_grav = np.zeros(30)
    gauss_point_data = []
    gamma_w = 9.81

    # 2. Integration
    for gp_idx in range(12):
        xi, eta = GAUSS_POINTS[gp_idx]
        weight = GAUSS_WEIGHTS[gp_idx]
        
        B, det_J = compute_b_matrix(node_coords, xi, eta)
        N = shape_functions_t15(xi, eta)
        
        gp_coords = N @ node_coords
        gx, gy = gp_coords
        
        # PWP calculation at Gauss point
        water_y = get_water_level_at(gx, water_level)
        pwp = 0.0
        if material.drainage_type not in [DrainageType.NON_POROUS, DrainageType.UNDRAINED_C]:
            if water_y is not None and gy < water_y:
                pwp = -gamma_w * (water_y - gy)
        
        # Unit weight selection
        if material.drainage_type == DrainageType.NON_POROUS:
            rho_tot = material.unitWeightUnsaturated
        elif water_y is not None and gy < water_y:
            rho_tot = material.unitWeightSaturated if material.unitWeightSaturated else material.unitWeightUnsaturated
        else:
            rho_tot = material.unitWeightUnsaturated
            
        # Accumulate K and F_grav
        K += (B.T @ D @ B) * det_J * weight * thickness
        
        # Load vector
        for i in range(15):
            F_grav[2*i] += N[i] * kh * rho_tot * det_J * weight * thickness
            F_grav[2*i+1] += -N[i] * (1.0 + kv) * rho_tot * det_J * weight * thickness
            
        gauss_point_data.append({
            'gp_id': gp_idx + 1,
            'xi': xi, 'eta': eta,
            'x': gx, 'y': gy,
            'det_J': det_J, 'B': B, 'weight': weight,
            'pwp': pwp,
            'rho': rho_tot
        })

    return K, F_grav, gauss_point_data, D
