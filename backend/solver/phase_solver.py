"""
Phase Solver Module
Main FEA solver loop implementing M-Stage load advancement and Newton-Raphson iteration.
Handles multiple analysis phases including K0 procedure, plastic analysis, and safety analysis.
"""
import numpy as np
import time
from typing import List, Dict, Optional
from backend.models import (
    SolverRequest, SolverResponse, NodeResult, StressResult, MaterialModel, DrainageType, Point,
    MeshResponse, Material, PhaseType, SolverSettings, PhaseResult
)
try:
    from backend.error import ErrorCode, get_error_info
except ImportError:
    # Fallback if not yet fully integrated
    ErrorCode = None
    get_error_info = lambda x: str(x)

import scipy.sparse as sp
from scipy.sparse.linalg import spsolve

from numba import njit
from .element_t6 import compute_element_matrices_t6, GAUSS_WEIGHTS
from .k0_procedure import compute_vertical_stress_k0_t6
from .mohr_coulomb import mohr_coulomb_yield, return_mapping_mohr_coulomb
from .hoek_brown import hoek_brown_yield, return_mapping_hoek_brown
from .element_embedded_beam import compute_beam_element_matrix, compute_beam_internal_force_yield


@njit
def assemble_stiffness_values_numba(
    active_elem_D_tangent_arr, # (N, 3, 3, 3) - 3 GPs
    B_matrices_arr,
    det_J_arr,
    weights_arr
):
    num_active = len(active_elem_D_tangent_arr)
    # Total values = N * 12 * 12
    K_values = np.zeros(num_active * 144)
    thickness = 1.0
    
    for i in range(num_active):
        K_el = np.zeros((12, 12))
        for gp_idx in range(3):
            B = B_matrices_arr[i, gp_idx]
            D = active_elem_D_tangent_arr[i, gp_idx]
            det_J = det_J_arr[i, gp_idx]
            weight = weights_arr[gp_idx]
            K_el += (B.T @ D @ B) * det_J * weight * thickness
        
        K_values[i*144 : (i+1)*144] = K_el.flatten()
        
    return K_values


@njit
def compute_elements_stresses_numba(
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
    mat_model_arr, # 0: LinearElastic, 1: Mohr Coulomb, 2: Hoek-Brown
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
    F_int = np.zeros(num_dof)
    num_active = len(element_nodes_arr)
    
    new_stresses = np.zeros((num_active, 3, 3))
    new_yield = np.zeros((num_active, 3), dtype=np.bool_)
    new_strain = np.zeros((num_active, 3, 3))
    new_pwp_excess = np.zeros((num_active, 3))
    
    thickness = 1.0
    
    for i in range(num_active):
        nodes_e = element_nodes_arr[i]
        
        u_el = np.zeros(12)
        for li in range(6):
            n_idx = nodes_e[li]
            u_el[li*2] = total_u_candidate[n_idx*2]
            u_el[li*2+1] = total_u_candidate[n_idx*2+1]
        
        f_int_el = np.zeros(12)
        
        dtype = mat_drainage_arr[i]
        mmodel = mat_model_arr[i]
        D_el = D_elastic_arr[i]
        c_val = mat_c_arr[i]
        phi_val = mat_phi_arr[i]
        su_val = mat_su_arr[i]
        sigma_ci_val = mat_sigma_ci_arr[i]
        gsi_val = mat_gsi_arr[i]
        disturb_factor_val = mat_disturb_factor_arr[i]
        mb_val = mat_mb_arr[i]
        s_val = mat_s_arr[i]
        a_val = mat_a_arr[i]
        penalty_val = penalties_arr[i]
        
        for gp_idx in range(3):
            B_gp = B_matrices_arr[i, gp_idx]
            det_J = det_J_arr[i, gp_idx]
            weight = weights_arr[gp_idx]
            p_static = pwp_static_arr[i, gp_idx]
            
            epsilon_total = B_gp @ u_el
            start_strain = step_start_strain_arr[i, gp_idx]
            d_epsilon_step = epsilon_total - start_strain
            
            sigma_total_start = step_start_stress_arr[i, gp_idx]
            pwp_excess_start = step_start_pwp_arr[i, gp_idx]
            
            if dtype == 3: # UNDRAINED_C
                sigma_total_trial = sigma_total_start + D_el @ d_epsilon_step
                su_eff = su_val
                if is_srm: su_eff /= target_m_stage
                
                if mmodel == 1: # Mohr-Coulomb
                    sig_new, _, yld = return_mapping_mohr_coulomb(
                        sigma_total_trial[0], sigma_total_trial[1], sigma_total_trial[2],
                        su_eff, 0.0, D_el
                    )
                else:
                    sig_new = sigma_total_trial
                    yld = False
                p_exc_new = 0.0
            
            elif dtype == 1 or dtype == 2: # UNDRAINED_A or B
                D_total = D_el.copy()
                D_total[0,0] += penalty_val; D_total[0,1] += penalty_val
                D_total[1,0] += penalty_val; D_total[1,1] += penalty_val
                
                sigma_total_trial = sigma_total_start + D_total @ d_epsilon_step
                d_vol = d_epsilon_step[0] + d_epsilon_step[1]
                p_exc_new = pwp_excess_start + penalty_val * d_vol
                p_total = p_static + p_exc_new
                
                sigma_eff_trial = sigma_total_trial - np.array([p_total, p_total, 0.0])
                
                if mmodel == 1:
                    c_eff = c_val; phi_eff = phi_val
                    if dtype == 2: 
                        c_eff = su_val
                        phi_eff = 0.0
                    
                    if is_srm:
                        c_eff /= target_m_stage
                        if phi_eff > 0:
                            phi_rad = np.deg2rad(phi_eff)
                            phi_eff = np.rad2deg(np.arctan(np.tan(phi_rad) / target_m_stage))
                    
                    sig_eff_new, _, yld = return_mapping_mohr_coulomb(
                        sigma_eff_trial[0], sigma_eff_trial[1], sigma_eff_trial[2],
                        c_eff, phi_eff, D_el
                    )
                else:
                    sig_eff_new = sigma_eff_trial
                    yld = False
                sig_new = sig_eff_new + np.array([p_total, p_total, 0.0])
                
            else: # DRAINED or NON_POROUS
                sigma_eff_start = sigma_total_start - np.array([p_static, p_static, 0.0])
                sigma_eff_trial = sigma_eff_start + D_el @ d_epsilon_step
                
                # Refined Elastic Gravity: Skip yield check if gravity phase and drained
                skip_yield = is_gravity_phase and (dtype == 0)

                if mmodel == 1 and not skip_yield:
                    c_eff = c_val; phi_eff = phi_val
                    if is_srm:
                        c_eff /= target_m_stage
                        if phi_eff > 0:
                            phi_rad = np.deg2rad(phi_eff)
                            phi_eff = np.rad2deg(np.arctan(np.tan(phi_rad) / target_m_stage))
                    
                    sig_eff_new, _, yld = return_mapping_mohr_coulomb(
                        sigma_eff_trial[0], sigma_eff_trial[1], sigma_eff_trial[2],
                        c_eff, phi_eff, D_el
                    )
                elif mmodel == 2 and not skip_yield: # Hoek-Brown
                    sig_ci_f = sigma_ci_val
                    mb_f = mb_val
                    s_f = s_val
                    gsi_n = gsi_val
                    disturb_factor_n = disturb_factor_val
                    a_f = a_val
                    if is_srm:
                        sig_ci_f = sigma_ci_val / target_m_stage
                        mb_f = mb_val / target_m_stage # assuming mb is linear, (simplification)
                        gsi_n = gsi_val / target_m_stage
                        disturb_factor_n = disturb_factor_val * target_m_stage
                        if disturb_factor_n > 1: 
                            disturb_factor_n = 1
                        else:
                            disturb_factor_n = disturb_factor_n
                        s_f = np.exp((gsi_n - 100) / (9 - 3 * disturb_factor_n))
                        a_f = 0.5+(np.exp(-gsi_n/15)-np.exp(-20/3))/6
                        
                    
                    sig_eff_new, _, yld = return_mapping_hoek_brown(
                        sigma_eff_trial[0], sigma_eff_trial[1], sigma_eff_trial[2],
                        sig_ci_f, mb_f, s_f, a_f, D_el
                    )
                else:
                    sig_eff_new = sigma_eff_trial
                    yld = False
                p_exc_new = 0.0
                sig_new = sig_eff_new + np.array([p_static, p_static, 0.0])

            new_stresses[i, gp_idx] = sig_new
            new_yield[i, gp_idx] = yld
            new_strain[i, gp_idx] = epsilon_total
            new_pwp_excess[i, gp_idx] = p_exc_new
            
            f_int_el += B_gp.T @ sig_new * det_J * weight * thickness
            
        for li in range(6):
            gi = nodes_e[li]
            F_int[gi*2] += f_int_el[li*2]
            F_int[gi*2+1] += f_int_el[li*2+1]
            
    return F_int, new_stresses, new_yield, new_strain, new_pwp_excess


def solve_phases(request: SolverRequest, should_stop=None):
    mesh = request.mesh
    settings = request.settings
    
    log = []
    
    # === 0. Settings Validation (Safety Guard) ===
    validation_errors = []
    if settings.tolerance < 0.001 or settings.tolerance > 0.1:
        validation_errors.append(get_error_info(ErrorCode.VAL_TOLERANCE_OOB))
    if settings.max_iterations < 1 or settings.max_iterations > 100:
        validation_errors.append(get_error_info(ErrorCode.VAL_ITERATIONS_OOB))
    if settings.initial_step_size < 0.001 or settings.initial_step_size > 1.0:
        validation_errors.append(get_error_info(ErrorCode.VAL_STEP_SIZE_OOB))
    if settings.max_load_fraction < 0.01 or settings.max_load_fraction > 1.0:
        validation_errors.append(get_error_info(ErrorCode.VAL_LOAD_FRAC_OOB))
    if settings.max_steps < 1 or settings.max_steps > 1000:
        validation_errors.append(get_error_info(ErrorCode.VAL_MAX_STEPS_OOB))
    if (settings.min_desired_iterations or 0) > (settings.max_desired_iterations or 100):
         validation_errors.append(get_error_info(ErrorCode.VAL_ITER_MISMATCH))
    if len(mesh.elements) > 7000:
        validation_errors.append(get_error_info(ErrorCode.VAL_OVER_ELEMENT_LIMIT))

    if validation_errors:
        for err in validation_errors:
            msg = f"{err}"
            log.append(msg)
            yield {"type": "log", "content": msg}
            print(msg)
        
        # Stop and yield error status
        yield {"type": "phase_result", "content": {
            "phase_id": request.phases[0].id if request.phases else "error",
            "success": False,
            "error": "Calculation blocked due to invalid solver settings. Please check the logs.",
            "displacements": [],
            "stresses": []
        }}
        return

    num_nodes = len(mesh.nodes)
    num_dof = num_nodes * 2
    nodes = mesh.nodes
    elements = mesh.elements
    
    # Material and Polygon Map
    elem_props_all = [] # List of all possible elements
    
    # Process water level polyline: convert Points to Dicts if necessary
    # Process water level polyline: convert Points to Dicts
    # NEW: Map ID -> List[Dict]
    water_levels_map = {}
    if request.water_levels:
        for wl in request.water_levels:
            water_levels_map[wl.id] = [{"x": p.x, "y": p.y} for p in wl.points]
    
    # Fallback/Default handling
    default_water_level = None
    # Legacy `water_level` removed. If no water_levels defined, default is Dry (None).
    
    # Track current water level to detect changes
    current_water_level_data = default_water_level
    current_water_level_id = "default_legacy"

    # Pre-calculate all element matrices (Initial state) - T6 Elements
    for i, elem_nodes in enumerate(elements):
        elem_id = i + 1
        # Find element metadata
        elem_meta = next((em for em in mesh.element_materials if em.element_id == elem_id), None)
        if not elem_meta: continue
        
        mat = elem_meta.material
        poly_id = elem_meta.polygon_id
        
        # T6 elements have 6 nodes
        if len(elem_nodes) != 6:
            log.append(f"ERROR: Element {elem_id} does not have 6 nodes (T6 required). Skipping.")
            continue
            
        coords = np.array([nodes[n] for n in elem_nodes])  # (6, 2)
        # Use initial/default water level for first pass
        K_el, F_grav, gauss_point_data, D = compute_element_matrices_t6(coords, mat, water_level=default_water_level)
        
        if K_el is None: continue
        
        # Calculate element area (using first 3 corner nodes)
        c = coords[:3]
        area = 0.5 * abs(c[0][0]*(c[1][1]-c[2][1]) + c[1][0]*(c[2][1]-c[0][1]) + c[2][0]*(c[0][1]-c[1][1]))
            
        elem_props_all.append({
            'id': elem_id,
            'nodes': elem_nodes,
            'D': D,
            'K': K_el,
            'F_grav': F_grav,
            'material': mat,
            'polygon_id': poly_id,
            'gauss_points': gauss_point_data,  # List of 3 Gauss point dicts
            'area': area,
            'original_material': mat
        })

    # Pre-calculate Beam Matrices
    beam_props_all = []
    beam_mat_map = {m.id: m for m in request.beam_materials}
    
    # Create map from Beam ID to Assignment
    beam_assign_map = {a.beam_id: a for a in (mesh.embedded_beam_assignments or [])}
    
    if request.embedded_beams:
        for b_idx, beam in enumerate(request.embedded_beams):
            if beam.id not in beam_assign_map: continue
            assign = beam_assign_map[beam.id]
            
            # Beam Nodes (1-based from assignment)
            b_nodes = [nid - 1 for nid in assign.nodes] # 0-based
            if len(b_nodes) < 2: continue
            
            # We treat the beam chain as a series of 2-node truss elements
            mat = beam_mat_map.get(beam.materialId)
            if not mat: continue
            
            # First pass: compute lengths and basic properties
            segments = []
            for i in range(len(b_nodes) - 1):
                n1 = b_nodes[i]
                n2 = b_nodes[i+1]
                coords = np.array([nodes[n1], nodes[n2]])
                L = np.linalg.norm(coords[1] - coords[0])
                segments.append({'nodes': [n1, n2], 'coords': coords, 'L': L})
            
            # Second pass: calculate capacities (Integrate from tip upwards)
            # T_max is kN/m, F_max is kN.
            t_max = mat.skinFrictionMax
            f_tip = mat.tipResistanceMax
            spacing = mat.spacing
            inv_spacing = 1.0 / spacing if spacing > 1e-9 else 1.0
            
            cumulative_capacity = f_tip * inv_spacing
            # Iterate segments in reverse (from tip to top)
            for i in range(len(segments) - 1, -1, -1):
                seg = segments[i]
                # Increment capacity by skin friction of THIS segment
                cumulative_capacity += (t_max * seg['L']) * inv_spacing
                
                # Compute K_truss and F_grav
                E = mat.youngsModulus
                A = mat.crossSectionArea
                unit_weight = mat.unitWeight
                
                K_b, F_grav_b = compute_beam_element_matrix(seg['coords'], E, A, spacing, unit_weight)
                
                beam_props_all.append({
                    'id': f"{beam.id}_seg_{i}",
                    'beam_index': b_idx,
                    'nodes': seg['nodes'],
                    'coords': seg['coords'],
                    'K': K_b,
                    'F_grav': F_grav_b,
                    'material': mat,
                    'beam_id': beam.id,
                    'capacity': cumulative_capacity,
                    'spacing': spacing
                })

    # Global State Tracking - T6: Store state per Gauss Point (List of 3 items per element)
    total_displacement = np.zeros(num_dof)
    element_stress_state = {ep['id']: [np.zeros(3) for _ in range(3)] for ep in elem_props_all}
    element_strain_state = {ep['id']: [np.zeros(3) for _ in range(3)] for ep in elem_props_all}
    element_yield_state = {ep['id']: [False for _ in range(3)] for ep in elem_props_all}
    element_pwp_excess_state = {ep['id']: [0.0 for _ in range(3)] for ep in elem_props_all}
    
    phase_results = []
    
    # Point Load Tracking (to calculate incremental Delta F)
    # Map node -> [fx, fy]
    active_point_loads = {} 

    # === STAGE 2: Topological Sort for Branching ===
    # Sort phases by dependency order (parents before children)
    phase_by_id = {p.id: p for p in request.phases}
    sorted_phases = []
    visited = set()
    
    def topo_visit(phase_id):
        if phase_id in visited:
            return
        visited.add(phase_id)
        ph = phase_by_id[phase_id]
        if ph.parent_id and ph.parent_id in phase_by_id:
            topo_visit(ph.parent_id)
        sorted_phases.append(ph)
    
    for p in request.phases:
        topo_visit(p.id)
    
    # State Snapshots: after each phase completes, save its full state
    # so child phases can restore from the correct baseline
    phase_snapshots = {}  # phase_id -> snapshot dict
    failed_phases = set()  # Track failed phases so we can skip their children
    
    # Save initial state as the "no parent" baseline
    import copy
    initial_snapshot = {
        'total_displacement': total_displacement.copy(),
        'element_stress_state': copy.deepcopy(element_stress_state),
        'element_strain_state': copy.deepcopy(element_strain_state),
        'element_yield_state': copy.deepcopy(element_yield_state),
        'element_pwp_excess_state': copy.deepcopy(element_pwp_excess_state),
        'current_water_level_data': copy.deepcopy(current_water_level_data),
        'current_water_level_id': current_water_level_id,
        'elem_materials': {ep['id']: (ep['material'], ep['K'].copy(), ep['F_grav'].copy(), ep['D'].copy(), copy.deepcopy(ep['gauss_points'])) for ep in elem_props_all},
        'beam_info': {bp['id']: (bp['material'], bp['K'].copy(), bp['F_grav'].copy()) for bp in beam_props_all},
    }

    # Initialize tracking sets for debug
    logged_zero_grav_polys = set()
    logged_silent_skip_polys = set()

    for phase_idx, phase in enumerate(sorted_phases):
        if should_stop and should_stop():
            log.append("Analysis cancelled by user.")
            yield {"type": "log", "content": "Analysis cancelled by user."}
            break
        
        # Skip children of failed phases
        if phase.parent_id and phase.parent_id in failed_phases:
            msg_skip = f"Skipping phase {phase.name} because parent phase failed."
            log.append(msg_skip)
            yield {"type": "log", "content": msg_skip}
            failed_phases.add(phase.id)
            continue
        
        # === RESTORE PARENT STATE ===
        # Before processing each phase, restore the parent's saved state
        if phase.parent_id and phase.parent_id in phase_snapshots:
            snapshot = phase_snapshots[phase.parent_id]
            total_displacement = snapshot['total_displacement'].copy()
            element_stress_state = copy.deepcopy(snapshot['element_stress_state'])
            element_strain_state = copy.deepcopy(snapshot['element_strain_state'])
            element_yield_state = copy.deepcopy(snapshot['element_yield_state'])
            element_pwp_excess_state = copy.deepcopy(snapshot['element_pwp_excess_state'])
            current_water_level_data = copy.deepcopy(snapshot['current_water_level_data'])
            current_water_level_id = snapshot['current_water_level_id']
            # Restore element materials from snapshot
            for ep in elem_props_all:
                eid = ep['id']
                if eid in snapshot['elem_materials']:
                    mat, K, F_grav, D, gps = snapshot['elem_materials'][eid]
                    ep['material'] = mat
                    ep['K'] = K.copy()
                    ep['F_grav'] = F_grav.copy()
                    ep['D'] = D.copy()
                    ep['gauss_points'] = copy.deepcopy(gps)
            # Restore beam materials from snapshot
            for bp in beam_props_all:
                bid = bp['id']
                if bid in snapshot['beam_info']:
                    mat, K, F_grav = snapshot['beam_info'][bid]
                    bp['material'] = mat
                    bp['K'] = K.copy()
                    bp['F_grav'] = F_grav.copy()
        elif not phase.parent_id:
            # First phase (no parent) — use initial state
            total_displacement = initial_snapshot['total_displacement'].copy()
            element_stress_state = copy.deepcopy(initial_snapshot['element_stress_state'])
            element_strain_state = copy.deepcopy(initial_snapshot['element_strain_state'])
            element_yield_state = copy.deepcopy(initial_snapshot['element_yield_state'])
            element_pwp_excess_state = copy.deepcopy(initial_snapshot['element_pwp_excess_state'])
            current_water_level_data = copy.deepcopy(initial_snapshot['current_water_level_data'])
            current_water_level_id = initial_snapshot['current_water_level_id']

        if phase.reset_displacements:
            total_displacement = np.zeros(num_dof)
            msg_reset = f"Displacements RESET for Phase: {phase.name}"
            log.append(msg_reset)
            yield {"type": "log", "content": msg_reset}

        msg_start = f"--- Starting Phase: {phase.name} ({phase.id}) [Type: {phase.phase_type or 'plastic'}] ---"
        log.append(msg_start)
        yield {"type": "log", "content": msg_start}
        print(msg_start)

        # 0.1 Determine Active Water Level for this Phase
        # Inheritance logic:
        # If Safety Analysis -> Must inherit from Parent Phase (unless we allow overriding? Usually safety uses same state)
        # Actually, PhaseRequest might have active_water_level_id.
        phase_water_level_data = current_water_level_data # Default to previous
        phase_water_level_id = current_water_level_id

        if phase.phase_type == PhaseType.SAFETY_ANALYSIS:
            # Safety analysis usually implies NO change in boundary conditions (loads, water) from parent.
            # So we keep `current_water_level_data` as is from the previous loop iteration (which was the parent).
            pass 
        else:
            # Check if this phase specifies a water level
            if phase.active_water_level_id:
                if phase.active_water_level_id in water_levels_map:
                    phase_water_level_data = water_levels_map[phase.active_water_level_id]
                    phase_water_level_id = phase.active_water_level_id
                else:
                    log.append(f"WARNING: Water Level ID '{phase.active_water_level_id}' not found. Using previous level.")
            else:
                # If None, what does it mean? "No Water" or "Keep Previous"?
                # Usually "Keep Previous" in staged construction unless explicitly set to "None" (which we might handle with special ID?)
                # For now, assume "Keep Previous"
                pass
        
        # Check for Water Level Change
        water_level_changed = (phase_water_level_id != current_water_level_id)
        if water_level_changed or phase_idx == 0: # Always set on first phase to be sure
             if water_level_changed:
                 msg_wl = f"Water Level changed to '{phase_water_level_id}'"
                 log.append(msg_wl)
                 yield {"type": "log", "content": msg_wl}
             current_water_level_data = phase_water_level_data
             current_water_level_id = phase_water_level_id

        # 0. MATERIAL DIFF: Compare current_material vs parent_material
        # For each polygon where material changed, rebuild element matrices.
        # Also compute incremental gravity load from unit weight difference.
        delta_F_grav_material = np.zeros(num_dof) # Incremental gravity from material changes
        material_map = {m.id: m for m in request.materials}
        
        if phase.phase_type != PhaseType.SAFETY_ANALYSIS:
            material_change_count = 0
            
            # Build maps: current_material and parent_material
            current_mat_map = phase.current_material or {}
            parent_mat_map = phase.parent_material or {}
            
            # Find all polygon indices that need material updates
            changed_polygons = {}  # poly_idx -> (new_mat, old_mat_id)
            
            for poly_idx_str, mat_id in current_mat_map.items():
                poly_idx = int(poly_idx_str)
                parent_mat_id = parent_mat_map.get(str(poly_idx)) or parent_mat_map.get(poly_idx)
                
                # Determine if this polygon's material changed from parent
                if parent_mat_id and str(mat_id) != str(parent_mat_id):
                    new_mat = material_map.get(mat_id)
                    if new_mat:
                        changed_polygons[poly_idx] = (new_mat, parent_mat_id)
            
            # Also check if water level changed (need to update all elements regardless)
            for ep in elem_props_all:
                poly_idx = ep['polygon_id']
                poly_idx_str = str(poly_idx)
                
                needs_update = False
                target_mat = ep['material']  # Default: keep current material
                old_mat = ep['material']
                
                # Check if this polygon has a material change from the diff
                if poly_idx in changed_polygons:
                    new_mat, old_mat_id = changed_polygons[poly_idx]
                    target_mat = new_mat
                    needs_update = True
                elif water_level_changed:
                    # Water level changed but material didn't — still need to recompute
                    # Use the current_material for this polygon to ensure right material
                    cur_mat_id = current_mat_map.get(poly_idx_str) or current_mat_map.get(poly_idx)
                    if cur_mat_id:
                        resolved_mat = material_map.get(str(cur_mat_id))
                        if resolved_mat:
                            target_mat = resolved_mat
                    needs_update = True
                else:
                    # Ensure element material matches current_material map (for first phase / state consistency)
                    cur_mat_id = current_mat_map.get(poly_idx_str) or current_mat_map.get(poly_idx)
                    if cur_mat_id and str(ep['material'].id) != str(cur_mat_id):
                        resolved_mat = material_map.get(str(cur_mat_id))
                        if resolved_mat:
                            target_mat = resolved_mat
                            needs_update = True
                
                if needs_update:
                    coords = np.array([nodes[n] for n in ep['nodes']])
                    
                    # Store old gravity force before recomputing
                    old_F_grav = ep['F_grav'].copy() if ep['F_grav'] is not None else np.zeros(12)
                    
                    K_el, F_grav, gauss_point_data, D = compute_element_matrices_t6(
                        coords, target_mat, water_level=current_water_level_data
                    )
                    
                    if K_el is not None:
                        # Compute incremental gravity from material change (unit weight diff)
                        if poly_idx in changed_polygons:
                            delta_F_grav_el = F_grav - old_F_grav
                            # Map element local DOFs to global DOFs
                            for local_idx, node_id in enumerate(ep['nodes']):
                                global_dof_x = node_id * 2
                                global_dof_y = node_id * 2 + 1
                                delta_F_grav_material[global_dof_x] += delta_F_grav_el[local_idx * 2]
                                delta_F_grav_material[global_dof_y] += delta_F_grav_el[local_idx * 2 + 1]
                        
                        ep['K'] = K_el
                        ep['F_grav'] = F_grav
                        ep['D'] = D
                        ep['material'] = target_mat
                        ep['gauss_points'] = gauss_point_data
                        material_change_count += 1
            
            if material_change_count > 0:
                msg_mat = f"Updated {material_change_count} elements (Material Diff / Water Level Update). Changed polygons: {list(changed_polygons.keys())}"
                log.append(msg_mat)
                yield {"type": "log", "content": msg_mat}
        
        # 1. Identify Active/Inactive Elements
        active_elem_props = [ep for ep in elem_props_all if ep['polygon_id'] in phase.active_polygon_indices]
        active_ids = {ep['id'] for ep in active_elem_props}
        
        # 2. Identify Active Nodes
        active_node_indices = set()
        for ep in active_elem_props:
            for n_idx in ep['nodes']:
                active_node_indices.add(n_idx)

        # 2.1 Identify Active Beams
        active_beam_props = []
        if phase.active_beam_ids:
            active_beam_ids_set = set(phase.active_beam_ids)
            active_beam_props = [bp for bp in beam_props_all if bp['beam_id'] in active_beam_ids_set]
            
            for bp in active_beam_props:
                for n_idx in bp['nodes']:
                    active_node_indices.add(n_idx)

        # Handle K0 Procedure
        if phase.phase_type == PhaseType.K0_PROCEDURE:
            msg_k0 = "Running K0 Procedure for stress initialization (T6)..."
            log.append(msg_k0)
            yield {"type": "log", "content": msg_k0}
            print(msg_k0)
            
            # T6 K0 Procedure returns stress per Gauss point
            k0_stresses = compute_vertical_stress_k0_t6(active_elem_props, nodes, current_water_level_data)
            
            # Update global state
            for eid, gp_stresses in k0_stresses.items():
                # gp_stresses is dict {'gp1': array, ...}
                # Store as list [gp1_stress, gp2_stress, gp3_stress]
                element_stress_state[eid] = [
                    gp_stresses[f'gp{i+1}'] for i in range(3)
                ]
                # Strain remains zero
                element_strain_state[eid] = [np.zeros(3) for _ in range(3)]
                element_yield_state[eid] = [False for _ in range(3)]
            
            # Reset Displacements (K0 procedure generates stress without deformation)
            total_displacement = np.zeros(num_dof)
            
            # Create Result Object
            p_displacements = [NodeResult(id=i+1, ux=0.0, uy=0.0) for i in range(num_nodes)]
            p_stresses = []
            
            for ep in active_elem_props:
                eid = ep['id']
                # Loop over Gauss points
                for i in range(3):
                    gp_data = ep['gauss_points'][i]
                    sig = element_stress_state[eid][i]
                    pwp_val = gp_data['pwp']
                    
                    sig_zz = sig[0] 
                    
                    p_stresses.append(StressResult(
                        element_id=eid, 
                        gp_id=i+1,
                        sig_xx=sig[0], sig_yy=sig[1], sig_xy=sig[2],
                        sig_zz=sig_zz, 
                        pwp_steady=pwp_val,
                        pwp_total=pwp_val,
                        is_yielded=False, m_stage=1.0
                    ))
            
            phase_results.append({
                'phase_id': phase.id,
                'success': True,
                'displacements': p_displacements,
                'stresses': p_stresses,
                'pwp': [], # Aggregate PWP? Maybe skip or average. For now empty is safe as StressResult has it.
                'reached_m_stage': 1.0,
                'step_failed_at': None,
                'error': None
            })
            msg_k0_done = "K0 Procedure completed."
            log.append(msg_k0_done)
            yield {"type": "log", "content": msg_k0_done}
            print(msg_k0_done)
            
            # Yield Phase Result immediately
            latest_phase_res = phase_results[-1]
            yield {"type": "phase_result", "content": latest_phase_res}
            continue # Skip to next phase
            
        # Standard FEA Steps (Plastic, Gravity Loading, Consolidation, etc.)
        # 3. Sparse Indices Pre-calculation
        rows = []
        cols = []
        for ep in active_elem_props:
            nodes_e = ep['nodes']
            dofs = []
            for n in nodes_e:
                dofs.extend([n*2, n*2+1])
            for r_dof in dofs:
                for c_dof in dofs:
                    rows.append(r_dof)
                    cols.append(c_dof)
        
        # Add Beam Indices
        for bp in active_beam_props:
            nodes_b = bp['nodes']
            dofs = []
            for n in nodes_b:
                dofs.extend([n*2, n*2+1])
            for r_dof in dofs:
                for c_dof in dofs:
                    rows.append(r_dof)
                    cols.append(c_dof)

        active_row_indices = np.array(rows, dtype=np.int32)
        active_col_indices = np.array(cols, dtype=np.int32)

        
        # === 3.5 Mesh Connectivity Check (Floating Element Detection) ===
        # Ensure all active elements are connected to at least one fixed node (Dirichlet BC).
        active_nodes_set = set(active_node_indices)
        if not active_nodes_set:
             # Look, no nodes! 
             pass
        else:
            # Build adjacency graph
            adj = {n: [] for n in active_nodes_set}
            for ep in active_elem_props:
                enodes = ep['nodes']
                for i in range(6):
                    u = enodes[i]
                    for j in range(i+1, 6):
                        v = enodes[j]
                        if u in adj and v in adj:
                            adj[u].append(v)
                            adj[v].append(u)
            
            # Identify BC nodes
            fixed_nodes = set()
            for bc in mesh.boundary_conditions.full_fixed:
                if bc.node in active_nodes_set: fixed_nodes.add(bc.node)
            for bc in mesh.boundary_conditions.normal_fixed:
                if bc.node in active_nodes_set: fixed_nodes.add(bc.node)
                
            # BFS from fixed nodes
            visited_nodes = set(fixed_nodes)
            import collections
            q = collections.deque(fixed_nodes)
            
            while q:
                u = q.popleft()
                for v in adj[u]:
                    if v not in visited_nodes:
                        visited_nodes.add(v)
                        q.append(v)
            
            # Check for unvisited active nodes
            unvisited = active_nodes_set - visited_nodes
            if unvisited:
                floating_polys = set()
                for ep in active_elem_props:
                    if any(n in unvisited for n in ep['nodes']):
                        floating_polys.add(ep['polygon_id'])
                
                msg = f"Phase '{phase.name}' FAILED: Floating elements detected in polygons {sorted(list(floating_polys))}. These elements are not connected to any boundary condition (mesh gap likely)."
                log.append(msg)
                yield {"type": "log", "content": msg}
                failed_phases.add(phase.id)
                continue

        # 4. Standard FEA Steps (Plastic, Gravity Loading, Consolidation, etc.)
        # Build initial stiffness (Linear Elastic)
        K_values = []
        for ep in active_elem_props:
            K_values.extend(ep['K'].flatten())
        
        for bp in active_beam_props:
            K_values.extend(bp['K'].flatten())
            
        K_global = sp.coo_matrix((K_values, (active_row_indices, active_col_indices)), shape=(num_dof, num_dof)).tocsr()
        
        # 4. Apply Boundary Conditions
        fixed_dofs = set()
        for bc in mesh.boundary_conditions.full_fixed:
            fixed_dofs.add(bc.node * 2)
            fixed_dofs.add(bc.node * 2 + 1)
        
        xs = [p[0] for p in nodes]; min_x, max_x = min(xs), max(xs)
        for bc in mesh.boundary_conditions.normal_fixed:
            nx = nodes[bc.node][0]
            if abs(nx - min_x) < 1e-3 or abs(nx - max_x) < 1e-3:
                fixed_dofs.add(bc.node * 2)
        
        free_dofs = []
        for d in range(num_dof):
            node_idx = d // 2
            if d not in fixed_dofs and node_idx in active_node_indices:
                free_dofs.append(d)
        free_dofs = np.array(free_dofs, dtype=np.int32)
        
        # Initial matrices will be sliced in the loop for efficiency if using direct solvers.
        # But slicing CSR is relatively fast.
        
        # 5. Calculate Incremental Forces (Delta F)
        delta_F_external = np.zeros(num_dof)
        
        # A. Gravity Changes (New activation minus Deactivation)
        parent_phase = next((p for p in request.phases if p.id == phase.parent_id), None) if phase.parent_id else None
        parent_active_indices = set(parent_phase.active_polygon_indices) if parent_phase else set()
        current_active_indices = set(phase.active_polygon_indices)

        for ep in elem_props_all:
            poly_id = ep['polygon_id']
            is_active_now = poly_id in current_active_indices
            was_active_before = poly_id in parent_active_indices
            
            if is_active_now and not was_active_before:
                # Newly activated -> Add full gravity
                for li in range(6):
                    gi = ep['nodes'][li]
                    delta_F_external[gi*2:gi*2+2] += ep['F_grav'][li*2:li*2+2]
                    
                # DEBUG: Check if gravity is non-zero
                if np.linalg.norm(ep['F_grav']) < 1e-9:
                     # Only log once per polygon to avoid spam
                     if poly_id not in logged_zero_grav_polys:
                         mat = ep['material']
                         rho = mat.unitWeightUnsaturated
                         log.append(f"WARNING: Polygon {poly_id} newly active but has ~0 gravity load. Mat: '{mat.name}', Rho: {rho}")
                         logged_zero_grav_polys.add(poly_id)
                         
            elif was_active_before and not is_active_now:
                # Deactivated -> Subtract its gravity (it's gone)
                for li in range(6):
                    gi = ep['nodes'][li]
                    delta_F_external[gi*2:gi*2+2] -= ep['F_grav'][li*2:li*2+2]
            elif is_active_now and was_active_before:
                 # Debug: Check for "Silent Skip" (Parent thought active, but no stress)
                 # Only if gravity is significant (non-zero density)
                 if np.linalg.norm(ep['F_grav']) > 1e-9:
                     stresses = element_stress_state.get(ep['id'], [])
                     has_stress = any(np.linalg.norm(s) > 1e-6 for s in stresses)
                     if not has_stress:
                         if poly_id not in logged_silent_skip_polys:
                             log.append(f"WARNING: Polygon {poly_id} treated as ALREADY ACTIVE in Phase '{phase.name}', but has ~0 stress. Gravity load skipped! Potential bug in parent_active_indices or snapshot restore.")
                             logged_silent_skip_polys.add(poly_id)
        
        # A.1 Beam Gravity Changes
        parent_active_beam_ids = set(parent_phase.active_beam_ids) if parent_phase and parent_phase.active_beam_ids else set()
        current_active_beam_ids = set(phase.active_beam_ids) if phase.active_beam_ids else set()

        for bp in beam_props_all:
            beam_id = bp['beam_id']
            is_active_now = beam_id in current_active_beam_ids
            was_active_before = beam_id in parent_active_beam_ids
            
            if is_active_now and not was_active_before:
                # Newly activated beam -> Add weight
                for li in range(2):
                    gi = bp['nodes'][li]
                    delta_F_external[gi*2:gi*2+2] += bp['F_grav'][li*2:li*2+2]

        # B. Stress Release from Deactivated Elements (Excavation)
        for ep in elem_props_all:
            poly_id = ep['polygon_id']
            if poly_id in parent_active_indices and poly_id not in current_active_indices:
                eid = ep['id']
                # Iterate over Gauss points to integrate internal force
                f_int_el = np.zeros(12)
                gp_stresses = element_stress_state[eid]
                
                for gp_idx in range(3):
                    sigma_gp = gp_stresses[gp_idx]
                    gp_data = ep['gauss_points'][gp_idx]
                    weight = gp_data['weight']
                    det_J = gp_data['det_J']
                    B_gp = gp_data['B']
                    
                    # f = B^T * sigma * detJ * weight * thickness
                    f_int_el += B_gp.T @ sigma_gp * det_J * weight * 1.0 # thickness=1
                
                for li in range(6):
                    gi = ep['nodes'][li]
                    # We ADD the release force because the boundary is now MISSING 
                    # the support from this element.
                    delta_F_external[gi*2:gi*2+2] += f_int_el[li*2:li*2+2]
        
        # C. Point/Line Load Changes
        current_load_vectors = np.zeros(num_dof)
        parent_load_vectors = np.zeros(num_dof)
        
        # Point Loads
        pl_map = {pl.id: pl for pl in (request.point_loads or [])}
        pl_assignment_map = {a.point_load_id: a.assigned_node_id - 1 for a in mesh.point_load_assignments}
        
        # Line Loads
        ll_map = {ll.id: ll for ll in (request.line_loads or [])}
        ll_assignment_map = {}
        for la in (mesh.line_load_assignments or []):
            if la.line_load_id not in ll_assignment_map:
                ll_assignment_map[la.line_load_id] = []
            ll_assignment_map[la.line_load_id].append(la)
            
        def apply_all_loads(active_ids, target_vector):
            # Apply Point Loads
            for lid in active_ids:
                if lid in pl_map and lid in pl_assignment_map:
                    pl = pl_map[lid]
                    n_idx = pl_assignment_map[lid]
                    target_vector[n_idx*2] += pl.fx
                    target_vector[n_idx*2+1] += pl.fy
                
                # Apply Line Loads
                if lid in ll_map and lid in ll_assignment_map:
                    ll = ll_map[lid]
                    for la in ll_assignment_map[lid]:
                        # edge_nodes: [n1, n2, n3] 1-based
                        n1, n2, n3 = la.edge_nodes[0]-1, la.edge_nodes[1]-1, la.edge_nodes[2]-1
                        p1, p2 = np.array(mesh.nodes[n1]), np.array(mesh.nodes[n2])
                        L = np.linalg.norm(p2 - p1)
                        # Quadratic edge distribution (parabolic): 1/6, 1/6, 2/3
                        f_total = np.array([ll.fx, ll.fy]) * L
                        target_vector[n1*2 : n1*2+2] += f_total / 6.0
                        target_vector[n2*2 : n2*2+2] += f_total / 6.0
                        target_vector[n3*2 : n3*2+2] += f_total * (2.0/3.0)

        # Calculate current and parent states
        apply_all_loads(phase.active_load_ids, current_load_vectors)
        if parent_phase:
            apply_all_loads(parent_phase.active_load_ids, parent_load_vectors)
        
        delta_F_external += (current_load_vectors - parent_load_vectors)
        
        # D. Incremental Gravity from Material Changes (unit weight difference)
        delta_F_external += delta_F_grav_material
        
        # 5. Out-of-Balance Forces (Internal Stress vs External Load) - Initial F_int
        F_int_initial = np.zeros(num_dof)
        for ep in active_elem_props:
            eid = ep['id']
            gp_stresses = element_stress_state[eid]
            f_int_el = np.zeros(12)
            
            for gp_idx in range(3):
                sigma_gp = gp_stresses[gp_idx]
                gp_data = ep['gauss_points'][gp_idx]
                weight = gp_data['weight']
                det_J = gp_data['det_J']
                B_gp = gp_data['B']
                f_int_el += B_gp.T @ sigma_gp * det_J * weight * 1.0
            
            for li in range(6):
                gi = ep['nodes'][li]
                F_int_initial[gi*2:gi*2+2] += f_int_el[li*2:li*2+2]
        
        # Add Beam Internal Forces (with yielding check)
        for bp in active_beam_props:
            # Extract u for this beam
            u_el_b = np.zeros(4)
            for li in range(2):
                gi = bp['nodes'][li]
                u_el_b[li*2] = total_displacement[gi*2]
                u_el_b[li*2+1] = total_displacement[gi*2+1]
                
            mat_b = bp['material']
            # Initial state matches parent (plastic/elastic), so is_srm=False for F_int_initial
            f_int_b, _ = compute_beam_internal_force_yield(
                bp['coords'], u_el_b, 
                mat_b.youngsModulus, mat_b.crossSectionArea, 
                bp['spacing'], bp['capacity'],
                False, 1.0
            )
            
            for li in range(2):
                gi = bp['nodes'][li]
                F_int_initial[gi*2:gi*2+2] += f_int_b[li*2:li*2+2]
        
        # Debug logging
        F_int_norm = np.linalg.norm(F_int_initial)
        delta_F_norm = np.linalg.norm(delta_F_external)
        msg_forces = f"Phase {phase.name} | F_int_initial norm: {F_int_norm:.2f} kN | delta_F_external norm: {delta_F_norm:.2f} kN | reset_disp: {phase.reset_displacements}"
        log.append(msg_forces)
        yield {"type": "log", "content": msg_forces}
        print(msg_forces)
        
        # Starting Residual (Out-of-balance)
        # R = F_ext_accumulated - F_int_initial
        # But we only APPLY delta_F_external in the MStage loop. 
        # So we start with current stress state, and add delta_F.
        
        # 6. MStage/SRM Loop for the Phase
        current_u_incremental = np.zeros(num_dof)
        
        is_srm = phase.phase_type == PhaseType.SAFETY_ANALYSIS
        if is_srm:
            current_m_stage = 1.0 # SigmaMSF starts at 1.0
            msg_srm = f"--- Phase {phase.name}: Starting Safety Analysis (SRM) ---"
            log.append(msg_srm)
            yield {"type": "log", "content": msg_srm}
        else:
            current_m_stage = 0.0
            
        step_size = settings.initial_step_size
        step_count = 0
        phase_step_points = [{"m_stage": float(current_m_stage), "max_disp": 0.0}]
        yield {"type": "step_point", "content": {"m_stage": float(current_m_stage), "max_disp": 0.0}}
        
        # Temporary history within phase (Step Start State)
        # Copy list of lists
        phase_stress_history = {eid: [s.copy() for s in ls] for eid, ls in element_stress_state.items()}
        phase_strain_history = {eid: [s.copy() for s in ls] for eid, ls in element_strain_state.items()}
        phase_yield_history = {eid: [y for y in ls] for eid, ls in element_yield_state.items()}
        phase_pwp_excess_history = {eid: [p for p in ls] for eid, ls in element_pwp_excess_state.items()}
        
        # Tangent Stiffness Matrix cache (List of 3 matrices per element)
        element_tangent_matrices = {}
        for ep in active_elem_props:
            D_init_gps = []
            mat = ep['material']
            for gp_idx in range(3):
                D_gp = ep['D'].copy()
                if mat.drainage_type in [DrainageType.UNDRAINED_A, DrainageType.UNDRAINED_B]:
                    # Add volumetric stiffening (Penalty Bulk Modulus of Water)
                    # For Undrained A/B using effective modulus, we stiffen the tangent
                    Kw = 2.2e6 # kPa
                    porosity = 0.3
                    penalty = Kw / porosity
                    E_skel = mat.effyoungsModulus or 10000.0
                    nu_skel = mat.poissonsRatio or 0.3
                    K_skel = E_skel / (3.0 * (1.0 - 2.0 * nu_skel))
                    if penalty > 10.0 * K_skel: penalty = 10.0 * K_skel # Safety limit
                    
                    D_gp[0,0] += penalty
                    D_gp[0,1] += penalty
                    D_gp[1,0] += penalty
                    D_gp[1,1] += penalty
                
                D_init_gps.append(D_gp)
            element_tangent_matrices[ep['id']] = D_init_gps
        
        log.append(f"Solving equilibrium for phase {phase.name}...")

        # Prepare Static Arrays for Numba Optimization
        num_active_phase = len(active_elem_props)
        elem_nodes_arr = np.array([ep['nodes'] for ep in active_elem_props], dtype=np.int32)
        B_matrices_arr = np.array([[gp['B'] for gp in ep['gauss_points']] for ep in active_elem_props])
        det_J_arr = np.array([[gp['det_J'] for gp in ep['gauss_points']] for ep in active_elem_props])
        pwp_static_arr = np.array([[gp['pwp'] or 0.0 for gp in ep['gauss_points']] for ep in active_elem_props])
        weights_arr = GAUSS_WEIGHTS
        D_elastic_arr = np.array([ep['D'] for ep in active_elem_props])
        
        # Drainage mapping: 0: DRAINED, 1: UNDRAINED_A, 2: UNDRAINED_B, 3: UNDRAINED_C, 4: NON_POROUS
        drainage_map = {
            DrainageType.DRAINED: 0,
            DrainageType.UNDRAINED_A: 1,
            DrainageType.UNDRAINED_B: 2,
            DrainageType.UNDRAINED_C: 3,
            DrainageType.NON_POROUS: 4
        }
        mat_drainage_arr = np.array([drainage_map.get(ep['material'].drainage_type, 0) for ep in active_elem_props], dtype=np.int32)
        mat_c_arr = np.array([ep['material'].cohesion or 0.0 for ep in active_elem_props])
        mat_phi_arr = np.array([ep['material'].frictionAngle or 0.0 for ep in active_elem_props])
        mat_su_arr = np.array([ep['material'].undrainedShearStrength or 0.0 for ep in active_elem_props])
        
        penalties_arr = []
        for ep in active_elem_props:
            mat = ep['material']
            penalty = 0.0
            if mat.drainage_type in [DrainageType.UNDRAINED_A, DrainageType.UNDRAINED_B]:
                # Penalty Value (Bulk Modulus Air)
                # Assume water bulk modulus Kw = 2.2e6 kPa and porosity = 0.3
                Kw = 2.2e6; porosity = 0.3; penalty = Kw / porosity
                E_skel = mat.effyoungsModulus or 10000.0
                nu_skel = mat.poissonsRatio or 0.3
                K_skel = E_skel / (3.0 * (1.0 - 2.0 * nu_skel))
                if penalty > 10.0 * K_skel: penalty = 10.0 * K_skel
            penalties_arr.append(penalty)
        penalties_arr = np.array(penalties_arr)

        # Material model mapping: 0: LINEAR_ELASTIC, 1: MOHR_COULOMB, 2: HOEK_BROWN
        model_map = {
            MaterialModel.LINEAR_ELASTIC: 0,
            MaterialModel.MOHR_COULOMB: 1,
            MaterialModel.HOEK_BROWN: 2
        }
        
        is_gravity_phase = phase.phase_type == PhaseType.GRAVITY_LOADING
        mat_model_arr = np.array([model_map.get(ep['material'].material_model, 0) for ep in active_elem_props], dtype=np.int32)
        
        if is_gravity_phase:
            msg_el = f"  > Elastic Gravity enabled (Yield check skipped for Drained materials) in phase '{phase.name}'"
            log.append(msg_el)
            print(msg_el)
            yield {"type": "log", "content": msg_el}

        # Hoek-Brown parameter preparation
        mat_sigma_ci_arr = []
        mat_gsi_arr = []
        mat_disturb_factor_arr = []
        mat_mb_arr = []
        mat_s_arr = []
        mat_a_arr = []

        for i, ep in enumerate(active_elem_props):
            mat = ep['material']
            
            # Validation Guard: Hoek-Brown + Undrained is not allowed
            if mat.material_model == MaterialModel.HOEK_BROWN:
                if mat.drainage_type in [DrainageType.UNDRAINED_A, DrainageType.UNDRAINED_B, DrainageType.UNDRAINED_C]:
                    msg_err = f"ERROR: Material '{mat.name}' uses Hoek-Brown with an Undrained drainage type. Rock models only support Drained or Non-Porous conditions."
                    log.append(msg_err)
                    yield {"type": "log", "content": msg_err}
                    failed_phases.add(phase.id)
            
            sig_ci = mat.sigma_ci or 0.0
            gsi = mat.gsi or 0.0 
            mi = mat.m_i or 5.0
            D_factor = mat.disturbFactor or 0.0
            
            if mat.m_b is None and mat.material_model == MaterialModel.HOEK_BROWN:
                m_b_calc = mi * np.exp((gsi - 100) / (28 - 14 * D_factor))
                s_calc = np.exp((gsi - 100) / (9 - 3 * D_factor))
                a_calc = 0.5 + (1/6) * (np.exp(-gsi/15) - np.exp(-20/3))
            else:
                m_b_calc = mat.m_b or 0.0
                s_calc = mat.s or 0.0
                a_calc = mat.a or 0.5
                
            mat_sigma_ci_arr.append(sig_ci)
            mat_gsi_arr.append(gsi)
            mat_disturb_factor_arr.append(D_factor)
            mat_mb_arr.append(m_b_calc)
            mat_s_arr.append(s_calc)
            mat_a_arr.append(a_calc)

        mat_sigma_ci_arr = np.array(mat_sigma_ci_arr)
        mat_gsi_arr = np.array(mat_gsi_arr)
        mat_disturb_factor_arr = np.array(mat_disturb_factor_arr)
        mat_mb_arr = np.array(mat_mb_arr)
        mat_s_arr = np.array(mat_s_arr)
        mat_a_arr = np.array(mat_a_arr)

        # Check if phase failed due to validation
        if phase.id in failed_phases:
            continue

        m_type = "MStage" if not is_srm else "Msf"
        while (not is_srm and current_m_stage < 1.0) or (is_srm and current_m_stage < 100.0): 
            if should_stop and should_stop():
                log.append("Analysis cancelled by user during MStage loop.")
                yield {"type": "log", "content": "Analysis cancelled by user."}
                break
            
            if step_count > settings.max_steps: 
                log.append(f"Max steps ({settings.max_steps}) reached. Terminating phase.")
                break
            
            if is_srm and step_size < 0.0001:
                log.append(f"SRM: Step size too small ({step_size:.5f}). Limit state reached.")
                break

            # Step Size Adaptation
            if not is_srm:
                if current_m_stage + step_size > 1.0: step_size = 1.0 - current_m_stage
                target_m_stage = current_m_stage + step_size
            else:
                target_m_stage = current_m_stage + step_size
            
            # Snapshot state at START of this step
            step_start_stress = {eid: [s.copy() for s in ls] for eid, ls in phase_stress_history.items()}
            step_start_strain = {eid: [s.copy() for s in ls] for eid, ls in phase_strain_history.items()}
            step_start_pwp = {eid: [p for p in ls] for eid, ls in phase_pwp_excess_history.items()}
            
            # Snapshot arrays for Numba
            step_start_stress_arr = np.array([step_start_stress[ep['id']] for ep in active_elem_props])
            step_start_strain_arr = np.array([step_start_strain[ep['id']] for ep in active_elem_props])
            step_start_pwp_arr = np.array([step_start_pwp[ep['id']] for ep in active_elem_props])

            # Newton-Raphson
            iteration = 0
            converged = False
            step_du = np.zeros(num_dof) 
            
            while iteration < settings.max_iterations:
                iteration += 1
                
                total_u_candidate = total_displacement + current_u_incremental + step_du
                
                # Call Numba Kernel for Internal Forces and Stress Update
                F_int, new_stresses_arr, new_yield_arr, new_strain_arr, new_pwp_excess_arr = compute_elements_stresses_numba(
                    elem_nodes_arr,
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
                )
                
                # Re-map collections for results consistency
                temp_phase_stress = {} 
                temp_phase_yield = {}
                temp_phase_strain = {}
                temp_phase_pwp_excess = {}
                for i, ep in enumerate(active_elem_props):
                    eid = ep['id']
                    temp_phase_stress[eid] = [new_stresses_arr[i, gp] for gp in range(3)]
                    temp_phase_yield[eid] = [new_yield_arr[i, gp] for gp in range(3)]
                    temp_phase_strain[eid] = [new_strain_arr[i, gp] for gp in range(3)]
                    temp_phase_pwp_excess[eid] = [new_pwp_excess_arr[i, gp] for gp in range(3)]
                
                # Add Beam Internal Forces to F_int (with yielding)
                for bp in active_beam_props:
                    u_el_b = np.zeros(4)
                    for li in range(2):
                        gi = bp['nodes'][li]
                        u_el_b[li*2] = total_u_candidate[gi*2]
                        u_el_b[li*2+1] = total_u_candidate[gi*2+1]
                    
                    mat_b = bp['material']
                    f_int_b, is_yielded_b = compute_beam_internal_force_yield(
                        bp['coords'], u_el_b, 
                        mat_b.youngsModulus, mat_b.crossSectionArea, 
                        bp['spacing'], bp['capacity'],
                        is_srm, target_m_stage
                    )
                    
                    for li in range(2):
                        gi = bp['nodes'][li]
                        F_int[gi*2] += f_int_b[li*2]
                        F_int[gi*2+1] += f_int_b[li*2+1]

                
                # Global Residual
                R = F_int_initial + (target_m_stage * delta_F_external) - F_int
                R_free = R[free_dofs]
                norm_R = np.linalg.norm(R_free)
                f_base = np.linalg.norm((F_int_initial + delta_F_external)[free_dofs])
                if f_base < 1.0: f_base = 1.0

                if norm_R / f_base < settings.tolerance and iteration > 1:
                    converged = True
                    break
                
                # Rebuild Stiffness Matrix (Sparse Assembly) - JIT Optimized
                # Using element_tangent_matrices (Modified Newton-Raphson) for stability
                active_elem_D_tangent_arr = np.array([element_tangent_matrices[ep['id']] for ep in active_elem_props])
                K_values = assemble_stiffness_values_numba(
                    active_elem_D_tangent_arr,
                    B_matrices_arr,
                    det_J_arr,
                    weights_arr
                )
                
                # Append Beam Stiffness
                if active_beam_props:
                    beam_k_vals = []
                    for bp in active_beam_props:
                        beam_k_vals.extend(bp['K'].flatten())
                    K_values = np.concatenate((K_values, np.array(beam_k_vals)))
                
                K_global = sp.coo_matrix((K_values, (active_row_indices, active_col_indices)), shape=(num_dof, num_dof)).tocsr()
                K_free = K_global[free_dofs, :][:, free_dofs]
                
                # === SOLVER STEP WITH DIAGNOSTICS ===
                # 1. Check for NaNs or Infs in R_free
                if not np.all(np.isfinite(R_free)):
                    msg = f"Solver Error: R_free vector contains NaNs or Infs at iteration {iteration}. Physics likely exploded."
                    log.append(msg)
                    print(msg)
                    yield {"type": "log", "content": msg}
                    converged = False
                    break

                try:
                    # 2. Solver Call
                    du_free = spsolve(K_free, R_free)
                    
                    if not np.all(np.isfinite(du_free)):
                        raise ValueError("Solver returned NaNs/Infs in displacement vector.")
                    
                    # Check for Explosion (Huge Displacement)
                    # Use a generous multiplier on the user limit (e.g. 100x) or a hard cap like 1e6 meters
                    limit_val = (settings.max_displacement_limit or 10.0) * 100.0
                    max_du = np.max(np.abs(du_free))
                    if max_du > limit_val:
                         raise ValueError(f"Solver instability detected: Incremental displacement {max_du:.2E} exceeds limit {limit_val:.2E}. Model is likely unstable/unconstrained.")

                    step_du[free_dofs] += du_free
                    
                except Exception as e:
                    msg_err = f"Solver Error at Iter {iteration}: {str(e)}"
                    print(f"DEBUG: {msg_err}")
                    log.append(msg_err)
                    yield {"type": "log", "content": msg_err}
                    
                    # === 3. SINGULARITY DIAGNOSTICS ===
                    # Analyze K_free for zero rows/cols (Unconstrained DOFs)
                    # This only catches unattached nodes. Rigid Body Motion (sliding) shows up as valid diagonals but singular matrix.
                    try:
                        # Check diagonal elements (detects disconnected nodes)
                        diag = K_free.diagonal()
                        near_zero_indices = np.where(np.abs(diag) < 1e-6)[0]
                        
                        diag_msg = ""
                        if len(near_zero_indices) > 0:
                            # Map back to Global Node IDs
                            bad_dofs_global = free_dofs[near_zero_indices]
                            
                            diagnostic_msgs = []
                            limit_reports = 5
                            for i, bad_dof in enumerate(bad_dofs_global):
                                if i >= limit_reports: 
                                    diagnostic_msgs.append(f"... and {len(bad_dofs_global) - limit_reports} more.")
                                    break
                                
                                node_id = bad_dof // 2
                                axis = "X" if bad_dof % 2 == 0 else "Y"
                                diagnostic_msgs.append(f"Node {node_id + 1} (DOF {axis}) has near-zero stiffness.")
                            
                            diag_msg = "Weak/Disconnect Nodes: " + "; ".join(diagnostic_msgs)
                        
                        full_msg = f"Analysis Failed. {diag_msg}"
                        if not diag_msg:
                            full_msg += " Possible Rigid Body Motion (Sliding/Rotation) due to missing boundary conditions."
                            
                        log.append(full_msg)
                        yield {"type": "log", "content": full_msg}
                        print(full_msg)
                            
                        # Update error message for UI
                        phase_results.append({
                            'phase_id': phase.id,
                            'success': False,
                            'displacements': [],
                            'stresses': [],
                            'error': f"{str(e)} \nDiagnosis: {full_msg}"
                        })
                    except Exception as diag_e:
                        print(f"Diagnostics failed: {diag_e}")

                    converged = False
                    break
            
            # Calculate displacement magnitudes for this step attempt (whether converged or not)
            trial_u = current_u_incremental + step_du
            trial_u_reshaped = trial_u.reshape(-1, 2)
            trial_magnitudes = np.sqrt(trial_u_reshaped[:,0]**2 + trial_u_reshaped[:,1]**2)
            max_disp = np.float64(np.max(trial_magnitudes))

            if converged:
                step_count += 1
                current_u_incremental = trial_u
                current_m_stage = target_m_stage
                
                for eid, stress in temp_phase_stress.items(): phase_stress_history[eid] = stress
                for eid, strain in temp_phase_strain.items(): phase_strain_history[eid] = strain
                for eid, yld in temp_phase_yield.items(): phase_yield_history[eid] = yld
                for eid, pexc in temp_phase_pwp_excess.items(): phase_pwp_excess_history[eid] = pexc
                
                msg = f"Phase {phase.name} | Step {step_count}: {m_type} {current_m_stage:.4f} | Max Incremental Disp: {max_disp:.6f} m | Iterations {iteration}"
                log.append(msg)
                yield {"type": "log", "content": msg}
                
                pt = {"m_stage": float(current_m_stage), "max_disp": float(max_disp)}
                phase_step_points.append(pt)
                yield {"type": "step_point", "content": pt}
                print(msg) 
                
                # Removed SF cap at 10.0 as per user request to see full collapse

                if iteration < settings.min_desired_iterations: step_size *= 1.5
                elif iteration > settings.max_desired_iterations: step_size *= 0.5

            else:
                # Failure Diagnostics before cutting step size
                msg_fail = f"Phase {phase.name} | Step {step_count+1} FAILED to converge after {iteration} iterations."
                log.append(msg_fail)
                print(msg_fail)
                
                # Identify worst node/DOF
                abs_R = np.abs(R_free)
                worst_idx = np.argmax(abs_R)
                worst_val = abs_R[worst_idx]
                global_dof = free_dofs[worst_idx]
                node_id = (global_dof // 2) + 1
                axis = "X" if global_dof % 2 == 0 else "Y"
                
                msg_detail = f"  > Final Residual Norm: {norm_R:.4f} | Max Displacement: {max_disp:.6f} m | (Rel: {norm_R/f_base:.6f} vs Tol: {settings.tolerance})"
                msg_worst = f"  > Largest Out-of-balance: {worst_val:.4f} kN at Node {node_id} (DOF {axis})"
                log.append(msg_detail)
                log.append(msg_worst)
                print(msg_detail)
                print(msg_worst)
                yield {"type": "log", "content": msg_detail}
                yield {"type": "log", "content": msg_worst}

                if step_size > (1e-4 if not is_srm else 0.001):
                     step_size *= 0.5
                     msg_retry = f"  > Retrying with smaller step size: {step_size:.5f}"
                     log.append(msg_retry)
                     print(msg_retry)
                     yield {"type": "log", "content": msg_retry}
                     continue
                else:
                    msg_abort = f"Step size too small ({step_size:.5f}). Aborting phase."
                    log.append(msg_abort)
                    print(msg_abort)
                    yield {"type": "log", "content": msg_abort}
                    break

        # End of Phase Result Gathering
        final_u_total = total_displacement + current_u_incremental
        p_displacements = []
        for i in range(num_nodes):
            p_displacements.append(NodeResult(id=i+1, ux=final_u_total[i*2], uy=final_u_total[i*2+1]))
        
        p_stresses = []
        for ep in active_elem_props:
            eid = ep['id']
            # Get list of Gauss point states
            sig_list = phase_stress_history.get(eid, element_stress_state.get(eid, [np.zeros(3)]*3))
            yld_list = phase_yield_history.get(eid, element_yield_state.get(eid, [False]*3))
            pwp_excess_list = phase_pwp_excess_history.get(eid, element_pwp_excess_state.get(eid, [0.0]*3))
            
            for gp_idx in range(3):
                gp_data = ep['gauss_points'][gp_idx]
                sig = sig_list[gp_idx]
                yld = yld_list[gp_idx]
                pwp_excess = pwp_excess_list[gp_idx]
                
                pwp_static = gp_data['pwp'] or 0.0
                pwp_total = pwp_static + pwp_excess
                
                sig_xx_total = sig[0]
                sig_yy_total = sig[1]
                nu = ep['material'].poissonsRatio
                
                dtype = ep['material'].drainage_type
                if dtype in [DrainageType.NON_POROUS, DrainageType.UNDRAINED_C]:
                     sig_zz_val = nu * (sig_xx_total + sig_yy_total)
                else:
                     sig_zz_val = nu * (sig_xx_total + sig_yy_total - 2*pwp_total) + pwp_total
    
                p_stresses.append(StressResult(
                    element_id=eid, 
                    gp_id=gp_idx+1,
                    sig_xx=sig[0], sig_yy=sig[1], sig_xy=sig[2],
                    sig_zz=sig_zz_val,
                    pwp_steady=pwp_static,
                    pwp_excess=pwp_excess,
                    pwp_total=pwp_total,
                    is_yielded=yld, m_stage=current_m_stage
                ))
        
        success = (not is_srm and current_m_stage >= 0.999) or (is_srm and current_m_stage > 1.0)
        error_msg = None
        if not success:
            error_msg = f"Phase failed at step {step_count}."

        phase_details = {
            'phase_id': phase.id,
            'success': success,
            'displacements': p_displacements,
            'stresses': p_stresses,
            'pwp': [], # Skipped for now
            'reached_m_stage': current_m_stage,
            'step_points': phase_step_points,
            'step_failed_at': step_count if not success else None,
            'error': error_msg
        }
        phase_results.append(phase_details)
        yield {"type": "phase_result", "content": phase_details}

        if success:
            if phase.reset_displacements:
                total_displacement = current_u_incremental
            else:
                total_displacement = final_u_total
            
            for eid in phase_stress_history: 
                element_stress_state[eid] = phase_stress_history[eid]
                element_strain_state[eid] = phase_strain_history[eid]
                element_yield_state[eid] = phase_yield_history[eid]
                if eid in phase_pwp_excess_history: element_pwp_excess_state[eid] = phase_pwp_excess_history[eid]
            log.append(f"Phase {phase.name} completed successfully.")
            
            # Save state snapshot for this phase so child phases can branch from it
            phase_snapshots[phase.id] = {
                'total_displacement': total_displacement.copy(),
                'element_stress_state': copy.deepcopy(element_stress_state),
                'element_strain_state': copy.deepcopy(element_strain_state),
                'element_yield_state': copy.deepcopy(element_yield_state),
                'element_pwp_excess_state': copy.deepcopy(element_pwp_excess_state),
                'current_water_level_data': copy.deepcopy(current_water_level_data),
                'current_water_level_id': current_water_level_id,
                'elem_materials': {ep['id']: (ep['material'], ep['K'].copy(), ep['F_grav'].copy(), ep['D'].copy(), copy.deepcopy(ep['gauss_points'])) for ep in elem_props_all},
                'beam_info': {bp['id']: (bp['material'], bp['K'].copy(), bp['F_grav'].copy()) for bp in beam_props_all},
            }
        else:
            log.append(f"Phase {phase.name} failed at step {step_count}.")
            failed_phases.add(phase.id)
            # Don't break — other branches may still succeed

    yield {"type": "final", "content": {
        "success": all(pr['success'] for pr in phase_results),
        "phases": phase_results,
        "log": log
    }}
