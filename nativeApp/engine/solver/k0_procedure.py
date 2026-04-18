"""
K0 Procedure Module (T15 Version)
Compute initial stresses using K0 procedure for T15 elements.
Calculates geostatic stresses at all 9 Gauss points per element.
"""
import numpy as np
from typing import List, Dict, Optional
from engine.models import Material, DrainageType
from .element_t15 import GAUSS_WEIGHTS


import terrasim_core

def compute_vertical_stress_k0_t15(
    elem_props: List[Dict], 
    nodes: List[List[float]], 
    water_level_data: Optional[List[Dict]]
) -> Dict[int, Dict[str, np.ndarray]]:
    """
    Compute initial stresses using K0 procedure for T15 elements.
    Strict Rust Backend enforcement.
    """
    num_active = len(elem_props)
    num_nodes = len(nodes)
    node_coords = np.array(nodes)
    
    gp_coords_all = np.zeros((num_active, 12, 2))
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

    # Call Rust Kernel (Strict Enforcement: no fallback)
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
    
    # Format output
    initial_stresses = {}
    for i, ep in enumerate(elem_props):
        eid = ep['id']
        element_gp_stresses = {}
        for gp_idx in range(12):
            element_gp_stresses[f'gp{gp_idx+1}'] = results_arr[i, gp_idx]
            # Also update PWP in original ep objects
            ep['gauss_points'][gp_idx]['pwp'] = pwp_results_arr[i, gp_idx]
        initial_stresses[eid] = element_gp_stresses
        
    return initial_stresses
