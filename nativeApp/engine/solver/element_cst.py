"""
CST Element Module
Constant Strain Triangle (CST) element computations for FEA solver.
Includes element stiffness matrix and gravity load vector calculations.
"""
import numpy as np
from typing import List, Dict, Optional, Tuple
from engine.models import Material, DrainageType


def get_water_level_at(x: float, water_level_polyline: Optional[List[Dict]] = None) -> Optional[float]:
    """Interpolate water level Y at given X from a polyline (ordered by X)."""
    if not water_level_polyline or len(water_level_polyline) < 1:
        return None
    
    # Sort by X just in case
    pts = sorted(water_level_polyline, key=lambda p: p['x'])
    
    if x <= pts[0]['x']:
        return pts[0]['y']
    if x >= pts[-1]['x']:
        return pts[-1]['y']
    
    # Linear interpolation
    for i in range(len(pts) - 1):
        p1 = pts[i]
        p2 = pts[i+1]
        if p1['x'] <= x <= p2['x']:
            # y = y1 + (x - x1) * (y2 - y1) / (x2 - x1)
            t = (x - p1['x']) / (p2['x'] - p1['x'])
            return p1['y'] + t * (p2['y'] - p1['y'])
    return None


def compute_element_matrices(
    nodes_coords, 
    material: Material, 
    water_level: Optional[List[Dict]] = None, 
    thickness: float = 1.0
) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray], float]:
    """
    Compute Stiffness (K) and Gravity Load (F_grav) for a single CST element.
    Includes logic for Sat/Unsat weight and PWP.
    
    Args:
        nodes_coords: List of 3 node coordinates [[x1,y1], [x2,y2], [x3,y3]]
        material: Material properties
        water_level: Optional water level polyline
        thickness: Element thickness (default 1.0)
    
    Returns:
        K: Element stiffness matrix (6x6)
        F_grav: Gravity load vector (6,)
        B: Strain-displacement matrix (3x6)
        D: Constitutive matrix (3x3)
        pwp: Pore water pressure at element centroid
    """
    x = [nodes_coords[0][0], nodes_coords[1][0], nodes_coords[2][0]]
    y = [nodes_coords[0][1], nodes_coords[1][1], nodes_coords[2][1]]
    
    # Centroid
    cx = sum(x) / 3.0
    cy = sum(y) / 3.0
    
    # Area = 0.5 * det(J)
    b = [y[1]-y[2], y[2]-y[0], y[0]-y[1]]
    c = [x[2]-x[1], x[0]-x[2], x[1]-x[0]]
    
    area2 = x[0]*(y[1]-y[2]) + x[1]*(y[2]-y[0]) + x[2]*(y[0]-y[1])
    area = 0.5 * area2
    
    if area <= 0:
        return None, None, None, None, 0.0
        
    # Strain-displacement matrix B
    B = np.zeros((3, 6))
    for i in range(3):
        B[0, 2*i] = b[i]
        B[1, 2*i+1] = c[i]
        B[2, 2*i] = c[i]
        B[2, 2*i+1] = b[i]
    B /= area2
    
    # Select Young's modulus based on drainage type
    if material.drainage_type == DrainageType.UNDRAINED_C or material.drainage_type == DrainageType.NON_POROUS:
        E = material.youngsModulus
    else:
        E = material.effyoungsModulus

    nu = material.poissonsRatio
    
    # Constitutive matrix D (plane strain)
    factor = E / ((1 + nu) * (1 - 2*nu))
    D = np.array([
        [1-nu, nu, 0],
        [nu, 1-nu, 0],
        [0, 0, (1-2*nu)/2]
    ]) * factor
    
    # Element stiffness matrix
    K = (B.T @ D @ B) * (area * thickness)
    
    # --- PWP Calculation ---
    water_y = get_water_level_at(cx, water_level)
    gamma_w = 9.81  # kN/m3
    pwp = 0.0
    if material.drainage_type not in [DrainageType.NON_POROUS, DrainageType.UNDRAINED_C, DrainageType.UNDRAINED_B]:
        if water_y is not None and cy < water_y:
            # Pressure is negative (compression convention)
            pwp = -gamma_w * (water_y - cy)
    
    # --- Unit Weight Selection ---
    # Total unit weight used for vertical stress calculation
    if material.drainage_type == DrainageType.NON_POROUS:
        # Non-porous materials only have one unit weight
        rho_tot = material.unitWeightUnsaturated
    elif water_y is not None and cy < water_y:
        # Use saturated weight if below water level, fallback to unsaturated if not provided
        rho_tot = material.unitWeightSaturated if material.unitWeightSaturated is not None else material.unitWeightUnsaturated
    else:
        rho_tot = material.unitWeightUnsaturated
        
    force_per_node = (area * thickness * rho_tot) / 3.0
    
    # Gravity acts in -Y direction
    F_grav = np.zeros(6)
    F_grav[1] = -force_per_node
    F_grav[3] = -force_per_node
    F_grav[5] = -force_per_node
    
    return K, F_grav, B, D, pwp


def is_point_in_triangle(triangle_coords, point):
    """
    Check if a point is inside a triangle using barycentric coordinates.
    
    Args:
        triangle_coords: List of 3 triangle vertices [[x1,y1], [x2,y2], [x3,y3]]
        point: Point coordinates [x, y]
    
    Returns:
        bool: True if point is inside triangle
    """
    x1, y1 = triangle_coords[0]
    x2, y2 = triangle_coords[1]
    x3, y3 = triangle_coords[2]
    px, py = point
    
    denom = (y2 - y3)*(x1 - x3) + (x3 - x2)*(y1 - y3)
    if abs(denom) < 1e-12:
        return False
    
    a = ((y2 - y3)*(px - x3) + (x3 - x2)*(py - y3)) / denom
    b = ((y3 - y1)*(px - x3) + (x1 - x3)*(py - y3)) / denom
    c = 1 - a - b
    
    return (a >= -1e-9) and (b >= -1e-9) and (c >= -1e-9)
