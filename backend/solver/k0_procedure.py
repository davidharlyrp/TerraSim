"""
K0 Procedure Module (T6 Version)
Compute initial stresses using K0 procedure for T6 elements.
Calculates geostatic stresses at all 3 Gauss points per element.
"""
import numpy as np
from typing import List, Dict, Optional
from backend.models import Material, DrainageType
from .element_t6 import get_water_level_at, compute_gauss_point_coordinates


from numba import njit

@njit
def is_point_in_triangle_jit(v1_x, v1_y, v2_x, v2_y, v3_x, v3_y, px, py):
    """JIT version of point-in-triangle test."""
    denom = (v2_y - v3_y) * (v1_x - v3_x) + (v3_x - v2_x) * (v1_y - v3_y)
    if abs(denom) < 1e-12:
        return False
    
    a = ((v2_y - v3_y) * (px - v3_x) + (v3_x - v2_x) * (py - v3_y)) / denom
    b = ((v3_y - v1_y) * (px - v3_x) + (v1_x - v3_x) * (py - v3_y)) / denom
    c = 1.0 - a - b
    
    return (a >= -1e-9) and (b >= -1e-9) and (c >= -1e-9)

@njit
def get_water_y_jit(x, water_pts):
    """JIT version of water level interpolation."""
    if water_pts.shape[0] == 0:
        return -1e15 # Effectively None
    
    if x <= water_pts[0, 0]:
        return water_pts[0, 1]
    if x >= water_pts[-1, 0]:
        return water_pts[-1, 1]
    
    for i in range(water_pts.shape[0] - 1):
        x1, y1 = water_pts[i, 0], water_pts[i, 1]
        x2, y2 = water_pts[i+1, 0], water_pts[i+1, 1]
        if x1 <= x <= x2:
            t = (x - x1) / (x2 - x1)
            return y1 + t * (y2 - y1)
    return -1e15

@njit
def compute_k0_stresses_kernel(
    gp_coords_all,     # (num_active, 3, 2)
    node_coords,       # (num_nodes, 2)
    elem_nodes_corner, # (num_active, 3)
    elem_bboxes,       # (num_active, 4) - xmin, xmax, ymin, ymax
    rho_unsat_arr,     # (num_active)
    rho_sat_arr,       # (num_active)
    mat_k0_arr,        # (num_active)
    mat_phi_arr,       # (num_active)
    mat_nu_arr,        # (num_active)
    mat_drainage_arr,  # (num_active) 0: Drained, 1: UndA, 2: UndB, 3: UndC, 4: NonPorous
    water_pts          # (N_pts, 2)
):
    num_active = gp_coords_all.shape[0]
    results = np.zeros((num_active, 3, 3))
    pwp_results = np.zeros((num_active, 3))
    gamma_w = 9.81

    for i in range(num_active):
        for gp_idx in range(3):
            x_gp = gp_coords_all[i, gp_idx, 0]
            y_gp = gp_coords_all[i, gp_idx, 1]

            # 1. PWP at Gauss Point
            water_y = get_water_y_jit(x_gp, water_pts)
            pwp = 0.0
            dtype = mat_drainage_arr[i]
            if dtype != 3 and dtype != 4: # Not UNDRAINED_C or NON_POROUS
                if water_y > -1e14 and y_gp < water_y:
                    pwp = -gamma_w * (water_y - y_gp)
            pwp_results[i, gp_idx] = pwp

            # 2. Find y_surface at this X
            y_surf = -1e9
            for j in range(num_active):
                if elem_bboxes[j, 0] <= x_gp <= elem_bboxes[j, 1]:
                    if elem_bboxes[j, 3] > y_surf:
                        y_surf = elem_bboxes[j, 3]
            
            if y_surf < -1e8: y_surf = y_gp
            
            # 3. Integrate vertical stress
            steps = 20
            dy = (y_surf - y_gp) / steps
            sigma_accum = 0.0
            if dy > 0:
                for s in range(steps):
                    y_sample = y_gp + (s + 0.5) * dy
                    gamma_sample = rho_unsat_arr[i] # Default to current
                    
                    # Search for element containing (x_gp, y_sample)
                    found = False
                    for j in range(num_active):
                        if elem_bboxes[j, 0] <= x_gp <= elem_bboxes[j, 1] and elem_bboxes[j, 2] <= y_sample <= elem_bboxes[j, 3]:
                            n1, n2, n3 = elem_nodes_corner[j]
                            v1x, v1y = node_coords[n1, 0], node_coords[n1, 1]
                            v2x, v2y = node_coords[n2, 0], node_coords[n2, 1]
                            v3x, v3y = node_coords[n3, 0], node_coords[n3, 1]
                            
                            if is_point_in_triangle_jit(v1x, v1y, v2x, v2y, v3x, v3y, x_gp, y_sample):
                                wy = get_water_y_jit(x_gp, water_pts)
                                if wy > -1e14 and y_sample < wy:
                                    gamma_sample = rho_sat_arr[j] if rho_sat_arr[j] > 0 else rho_unsat_arr[j]
                                else:
                                    gamma_sample = rho_unsat_arr[j]
                                found = True
                                break
                    sigma_accum += gamma_sample * dy
            
            sigma_v_total = -sigma_accum
            sigma_v_eff = sigma_v_total - pwp
            
            # 4. K0 stress
            k0 = mat_k0_arr[i]
            if k0 < 0: # -1 indicates None
                phi = mat_phi_arr[i]
                if phi > 0:
                    k0 = 1.0 - np.sin(np.deg2rad(phi))
                else:
                    nu = mat_nu_arr[i]
                    if nu > 0:
                        nu_eff = min(nu, 0.499)
                        k0 = nu_eff / (1.0 - nu_eff)
                    else:
                        k0 = 0.5
            
            sigma_h_eff = k0 * sigma_v_eff
            sigma_h_total = sigma_h_eff + pwp
            
            results[i, gp_idx, 0] = sigma_h_total
            results[i, gp_idx, 1] = sigma_v_total
            results[i, gp_idx, 2] = 0.0

    return results, pwp_results


def compute_vertical_stress_k0_t6(
    elem_props: List[Dict], 
    nodes: List[List[float]], 
    water_level_data: Optional[List[Dict]]
) -> Dict[int, Dict[str, np.ndarray]]:
    """
    Compute initial stresses using K0 procedure for T6 elements.
    Numba-optimized version.
    """
    num_active = len(elem_props)
    num_nodes = len(nodes)
    node_coords = np.array(nodes)
    
    gp_coords_all = np.zeros((num_active, 3, 2))
    elem_nodes_corner = np.zeros((num_active, 3), dtype=np.int32)
    elem_bboxes = np.zeros((num_active, 4))
    rho_unsat_arr = np.zeros(num_active)
    rho_sat_arr = np.zeros(num_active)
    mat_k0_arr = np.zeros(num_active)
    mat_phi_arr = np.zeros(num_active)
    mat_nu_arr = np.zeros(num_active)
    mat_drainage_arr = np.zeros(num_active, dtype=np.int32)
    
    drainage_map = {
        DrainageType.DRAINED: 0,
        DrainageType.UNDRAINED_A: 1,
        DrainageType.UNDRAINED_B: 2,
        DrainageType.UNDRAINED_C: 3,
        DrainageType.NON_POROUS: 4
    }
    
    for i, ep in enumerate(elem_props):
        mat = ep['material']
        elem_nodes_corner[i] = ep['nodes'][:3]
        
        # Bounding box
        n_coords = node_coords[ep['nodes']]
        elem_bboxes[i, 0] = np.min(n_coords[:, 0])
        elem_bboxes[i, 1] = np.max(n_coords[:, 0])
        elem_bboxes[i, 2] = np.min(n_coords[:, 1])
        elem_bboxes[i, 3] = np.max(n_coords[:, 1])
        
        # Gauss points
        for gp_idx, gp in enumerate(ep['gauss_points']):
            gp_coords_all[i, gp_idx, 0] = gp['x']
            gp_coords_all[i, gp_idx, 1] = gp['y']
            
        rho_unsat_arr[i] = mat.unitWeightUnsaturated
        rho_sat_arr[i] = mat.unitWeightSaturated or 0.0
        mat_k0_arr[i] = mat.k0_x if mat.k0_x is not None else -1.0
        mat_phi_arr[i] = mat.frictionAngle if mat.frictionAngle is not None else 0.0
        mat_nu_arr[i] = mat.poissonsRatio if mat.poissonsRatio is not None else 0.0
        mat_drainage_arr[i] = drainage_map.get(mat.drainage_type, 0)

    # Water points as sorted numpy array
    if water_level_data:
        sorted_water = sorted(water_level_data, key=lambda p: p['x'])
        water_pts = np.array([[p['x'], p['y']] for p in sorted_water])
    else:
        water_pts = np.zeros((0, 2))

    # Call Rust or Numba Kernel
    _use_rust_k0 = False
    try:
        import terrasim_core
        _use_rust_k0 = hasattr(terrasim_core, 'compute_k0_stresses')
    except ImportError:
        pass

    if _use_rust_k0:
        results_arr, pwp_results_arr = terrasim_core.compute_k0_stresses(
            np.ascontiguousarray(gp_coords_all, dtype=np.float64),
            np.ascontiguousarray(node_coords, dtype=np.float64),
            np.ascontiguousarray(elem_nodes_corner, dtype=np.int32),
            np.ascontiguousarray(elem_bboxes, dtype=np.float64),
            np.ascontiguousarray(rho_unsat_arr, dtype=np.float64),
            np.ascontiguousarray(rho_sat_arr, dtype=np.float64),
            np.ascontiguousarray(mat_k0_arr, dtype=np.float64),
            np.ascontiguousarray(mat_phi_arr, dtype=np.float64),
            np.ascontiguousarray(mat_nu_arr, dtype=np.float64),
            np.ascontiguousarray(mat_drainage_arr, dtype=np.int32),
            np.ascontiguousarray(water_pts, dtype=np.float64),
        )
    else:
        results_arr, pwp_results_arr = compute_k0_stresses_kernel(
            gp_coords_all, node_coords, elem_nodes_corner, elem_bboxes,
            rho_unsat_arr, rho_sat_arr, mat_k0_arr, mat_phi_arr, mat_nu_arr, mat_drainage_arr,
            water_pts
        )
    
    # Format output
    initial_stresses = {}
    for i, ep in enumerate(elem_props):
        eid = ep['id']
        element_gp_stresses = {}
        for gp_idx in range(3):
            element_gp_stresses[f'gp{gp_idx+1}'] = results_arr[i, gp_idx]
            # Also update PWP in original ep objects
            ep['gauss_points'][gp_idx]['pwp'] = pwp_results_arr[i, gp_idx]
        initial_stresses[eid] = element_gp_stresses
        
    return initial_stresses
