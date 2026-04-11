"""
T6 Element Module
6-node quadratic triangle element with 3-point Gauss quadrature integration.
Implements second-order shape functions for improved accuracy in FEA analysis.
"""
import numpy as np
from typing import List, Dict, Optional, Tuple
from engine.models import Material, DrainageType


# === Gauss Quadrature Points and Weights for Triangles ===
# 3-point quadrature (exact for polynomials up to degree 2)
GAUSS_POINTS = np.array([
    [1.0/6.0, 1.0/6.0],  # Point 1: (ξ, η)
    [2.0/3.0, 1.0/6.0],  # Point 2
    [1.0/6.0, 2.0/3.0]   # Point 3
])
GAUSS_WEIGHTS = np.array([1.0/6.0, 1.0/6.0, 1.0/6.0])


from numba import njit

@njit
def shape_functions_t6(xi: float, eta: float) -> np.ndarray:
    """
    Compute T6 shape functions at natural coordinates (ξ, η).
    """
    zeta = 1.0 - xi - eta
    
    # Corner nodes (quadratic)
    N1 = zeta * (2.0 * zeta - 1.0)
    N2 = xi * (2.0 * xi - 1.0)
    N3 = eta * (2.0 * eta - 1.0)
    
    # Midpoint nodes (quadratic)
    N4 = 4.0 * zeta * xi       # midpoint of edge 1-2 (nodes n1-n2)
    N5 = 4.0 * xi * eta        # midpoint of edge 2-3 (nodes n2-n3)
    N6 = 4.0 * eta * zeta      # midpoint of edge 3-1 (nodes n3-n1)
    
    return np.array([N1, N2, N3, N4, N5, N6])


@njit
def shape_function_derivatives_natural(xi: float, eta: float) -> np.ndarray:
    """
    Compute derivatives of T6 shape functions w.r.t. natural coordinates.
    """
    zeta = 1.0 - xi - eta
    
    # Derivatives w.r.t. ξ (Note: ∂ζ/∂ξ = -1)
    dN1_dxi = -4.0 * zeta + 1.0
    dN2_dxi = 4.0 * xi - 1.0
    dN3_dxi = 0.0
    dN4_dxi = 4.0 * (zeta - xi)
    dN5_dxi = 4.0 * eta
    dN6_dxi = -4.0 * eta
    
    # Derivatives w.r.t. η (Note: ∂ζ/∂η = -1)
    dN1_deta = -4.0 * zeta + 1.0
    dN2_deta = 0.0
    dN3_deta = 4.0 * eta - 1.0
    dN4_deta = -4.0 * xi
    dN5_deta = 4.0 * xi
    dN6_deta = 4.0 * (zeta - eta)
    
    dN = np.array([
        [dN1_dxi, dN2_dxi, dN3_dxi, dN4_dxi, dN5_dxi, dN6_dxi],
        [dN1_deta, dN2_deta, dN3_deta, dN4_deta, dN5_deta, dN6_deta]
    ])
    
    return dN


@njit
def compute_jacobian(node_coords: np.ndarray, dN_natural: np.ndarray) -> Tuple[np.ndarray, float]:
    """
    Compute Jacobian matrix and its determinant.
    """
    J = dN_natural @ node_coords
    det_J = np.linalg.det(J)
    
    return J, det_J


@njit
def compute_b_matrix(node_coords: np.ndarray, xi: float, eta: float) -> Tuple[np.ndarray, float]:
    """
    Compute B matrix (strain-displacement) at a given Gauss point.
    """
    # Get shape function derivatives in natural coordinates
    dN_natural = shape_function_derivatives_natural(xi, eta)
    
    # Compute Jacobian
    J, det_J = compute_jacobian(node_coords, dN_natural)
    
    if abs(det_J) < 1e-10:
        return np.zeros((3, 12)), 0.0
    
    # Compute derivatives w.r.t. physical coordinates
    J_inv = np.linalg.inv(J)
    dN_physical = J_inv @ dN_natural  # (2×6)
    
    B = np.zeros((3, 12))
    for i in range(6):
        B[0, 2*i] = dN_physical[0, i]      # ∂Ni/∂x for εxx
        B[1, 2*i+1] = dN_physical[1, i]    # ∂Ni/∂y for εyy
        B[2, 2*i] = dN_physical[1, i]      # ∂Ni/∂y for γxy
        B[2, 2*i+1] = dN_physical[0, i]    # ∂Ni/∂x for γxy
    
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


def compute_element_matrices_t6(
    node_coords: np.ndarray,  # (6, 2) array
    material: Material,
    water_level: Optional[List[Dict]] = None,
    thickness: float = 1.0,
    kh: float = 0.0,
    kv: float = 0.0
) -> Tuple[np.ndarray, np.ndarray, List[Dict], np.ndarray]:
    """
    Compute element stiffness matrix K and gravity load vector F_grav for T6 element.
    Uses 3-point Gauss quadrature for integration.
    
    Args:
        node_coords: Physical coordinates of 6 nodes [[x1,y1], ..., [x6,y6]]
        material: Material properties
        water_level: Optional water level polyline
        thickness: Element thickness (default 1.0)
    
    Returns:
        K: Element stiffness matrix (12×12)
        F_grav: Gravity load vector (12,)
        gauss_point_data: List of 3 dicts with Gauss point info
        D: Constitutive matrix (3×3)
    """
    # Constitutive matrix D (plane strain)
    if material.drainage_type in [DrainageType.UNDRAINED_C, DrainageType.NON_POROUS]:
        E = material.youngsModulus
    else:
        # Undrained A, Undrained B, and Drained use effective Young's modulus
        E = material.effyoungsModulus or 10000.0
    
    nu = material.poissonsRatio
    factor = E / ((1 + nu) * (1 - 2*nu))
    D = np.array([
        [1-nu, nu, 0],
        [nu, 1-nu, 0],
        [0, 0, (1-2*nu)/2]
    ]) * factor
    
    # Initialize outputs
    K = np.zeros((12, 12))
    F_grav = np.zeros(12)
    gauss_point_data = []
    
    gamma_w = 9.81  # kN/m³
    
    # Numerical integration over 3 Gauss points
    for gp_idx in range(3):
        xi, eta = GAUSS_POINTS[gp_idx]
        weight = GAUSS_WEIGHTS[gp_idx]
        
        # Compute B matrix and Jacobian determinant at this Gauss point
        B, det_J = compute_b_matrix(node_coords, xi, eta)
        
        # Physical coordinates of Gauss point
        N = shape_functions_t6(xi, eta)
        gp_coords = N @ node_coords  # [x_gp, y_gp]
        x_gp, y_gp = gp_coords
        
        # PWP calculation at Gauss point
        water_y = get_water_level_at(x_gp, water_level)
        pwp = 0.0
        if material.drainage_type not in [DrainageType.NON_POROUS, DrainageType.UNDRAINED_C]:
            if water_y is not None and y_gp < water_y:
                pwp = -gamma_w * (water_y - y_gp)
        
        # Unit weight selection
        if material.drainage_type == DrainageType.NON_POROUS:
            rho_tot = material.unitWeightUnsaturated
        elif water_y is not None and y_gp < water_y:
            rho_tot = material.unitWeightSaturated if material.unitWeightSaturated else material.unitWeightUnsaturated
        else:
            rho_tot = material.unitWeightUnsaturated
        
        # Store Gauss point info
        gauss_point_data.append({
            'gp_id': gp_idx + 1,
            'xi': xi,
            'eta': eta,
            'x': x_gp,
            'y': y_gp,
            'weight': weight,
            'det_J': det_J,
            'B': B,
            'pwp': pwp,
            'rho': rho_tot
        })
        
        # Add contribution to stiffness matrix
        # K += B^T @ D @ B * det(J) * weight * thickness
        K += (B.T @ D @ B) * det_J * weight * thickness
        
        # Add contribution to gravity load vector
        # F_grav = ∫ N^T * ρ * g_total dV
        # g_total = [kh*g, -(1+kv)*g]
        for i in range(6):
            # Horizontal (x) Load
            F_grav[2*i] += N[i] * kh * rho_tot * det_J * weight * thickness
            # Vertical (y) Load
            F_grav[2*i+1] += -N[i] * (1.0 + kv) * rho_tot * det_J * weight * thickness
    
    return K, F_grav, gauss_point_data, D


def compute_gauss_point_coordinates(node_coords: np.ndarray) -> np.ndarray:
    """
    Compute physical coordinates of all 3 Gauss points.
    
    Args:
        node_coords: Physical coordinates of 6 nodes (6×2)
    
    Returns:
        gp_coords: Physical coordinates of Gauss points (3×2) [[x1,y1], [x2,y2], [x3,y3]]
    """
    gp_coords = np.zeros((3, 2))
    
    for gp_idx in range(3):
        xi, eta = GAUSS_POINTS[gp_idx]
        N = shape_functions_t6(xi, eta)
        gp_coords[gp_idx] = N @ node_coords
    
    return gp_coords
