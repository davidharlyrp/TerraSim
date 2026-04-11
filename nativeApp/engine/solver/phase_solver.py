"""
Phase Solver Module
Main FEA solver loop implementing M-Stage load advancement and Newton-Raphson iteration.
Handles multiple analysis phases including K0 procedure, plastic analysis, and safety analysis.
"""
import numpy as np
import time
from typing import List, Dict, Optional
from engine.models import (
    SolverRequest, SolverResponse, NodeResult, StressResult, MaterialModel, DrainageType, Point,
    MeshResponse, Material, PhaseType, SolverSettings, PhaseResult, BeamResult
)
try:
    from engine.error import ErrorCode, get_error_info
except ImportError:
    # Fallback if not yet fully integrated
    ErrorCode = None
    get_error_info = lambda x: str(x)

import scipy.sparse as sp
# new solver
from scipy.sparse.linalg import spsolve as scipy_spsolve

try:
    from pypardiso import spsolve as pardiso_spsolve
    HAS_PARDISO = True
except ImportError:
    pardiso_spsolve = scipy_spsolve
    HAS_PARDISO = False
# old solver
# from scipy.sparse.linalg import spsolve

from numba import njit
from .element_t6 import compute_element_matrices_t6, GAUSS_WEIGHTS
from .k0_procedure import compute_vertical_stress_k0_t6
from .element_embedded_beam import (
    compute_beam_element_matrix, 
    compute_beam_internal_force_yield,
    compute_beam_forces_local
)
from .arc_length import run_arc_length_step, compute_initial_arc_length
from .stress_rust import compute_elements_stresses_rust


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

def format_duration(seconds: float) -> str:
    """Helper to format duration as 'Xm Y.Ys' or 'Y.Ys'."""
    m = int(seconds // 60)
    s = seconds % 60
    if m > 0:
        return f"{m}m {s:.2f}s"
    else:
        return f"{s:.2f}s"


def solve_phases(request: SolverRequest, should_stop=None):
    total_start_time = time.time()
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
    # if len(mesh.elements) > 10000:
    #     validation_errors.append(get_error_info(ErrorCode.VAL_OVER_ELEMENT_LIMIT))

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
    num_dof = num_nodes * 3
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
        # Use initial/default water level for first pass. kh/kv default to 0.0 for initial setup.
        K_el, F_grav, gauss_point_data, D = compute_element_matrices_t6(
            coords, mat, water_level=default_water_level, kh=0.0, kv=0.0
        )
        
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

            # Ensure consistent orientation (Y-first then X)
            # This prevents sawtooth in slanted beams due to inconsistent T-matrices.
            if len(b_nodes) >= 2:
                n1_coord = nodes[b_nodes[0]]
                n2_coord = nodes[b_nodes[-1]]
                # Standardize: n1 should be higher (larger Y)
                if n1_coord[1] < n2_coord[1] or (n1_coord[1] == n2_coord[1] and n1_coord[0] > n2_coord[0]):
                    b_nodes.reverse()

            mat = beam_mat_map.get(beam.materialId)
            if not mat: continue

            # First pass: compute lengths and basic properties
            segments = []
            for i in range(len(b_nodes) - 1):
                n1 = b_nodes[i]
                n2 = b_nodes[i+1]
                coords = np.array([nodes[n1], nodes[n2]])
                L = np.linalg.norm(coords[1] - coords[0])
                if L < 1e-9: continue # Skip zero-length segments
                segments.append({'nodes': [n1, n2], 'coords': coords, 'L': L})
            
            # Second pass: calculate capacities 
            # (Capacities are cumulative from tip resistance at the bottom)
            t_max = mat.skinFrictionMax
            f_tip = mat.tipResistanceMax
            spacing = mat.spacing
            inv_spacing = 1.0 / spacing if spacing > 1e-9 else 1.0
            
            # Pre-calculate capacities for each segment to allow forward iteration
            seg_capacities = [0.0] * len(segments)
            curr_cap = f_tip * inv_spacing
            for i in range(len(segments) - 1, -1, -1):
                seg = segments[i]
                curr_cap += (t_max * seg['L']) * inv_spacing
                seg_capacities[i] = curr_cap

            # Resolve global head node for this beam (Head-to-Tip ordering)
            h_idx = beam.head_point_index or 0 # 0=P1, 1=P2
            global_head_gi = b_nodes[0] if h_idx == 0 else b_nodes[-1]
            head_conn_type = str(beam.head_connection_type).upper()

            # Iterate segments from Head to Tip (0 to N) to ensure correct result ordering
            for i in range(len(segments)):
                seg = segments[i]
                
                # Compute K_frame and F_grav
                E = mat.youngsModulus
                A = mat.crossSectionArea
                I = getattr(mat, 'momentOfInertia', 1e-6)
                unit_weight = mat.unitWeight
                
                K_b, F_grav_b = compute_beam_element_matrix(seg['coords'], E, A, I, spacing, unit_weight, kh=0.0, kv=0.0)
                
                beam_props_all.append({
                    'id': f"{beam.id}_seg_{i}",
                    'beam_index': b_idx,
                    'nodes': seg['nodes'],
                    'coords': seg['coords'],
                    'L': seg['L'],
                    'K': K_b,
                    'F_grav': F_grav_b,
                    'material': mat,
                    'beam_id': beam.id,
                    'capacity': seg_capacities[i],
                    'spacing': spacing,
                    'global_head_gi': global_head_gi,
                    'head_connection_type': head_conn_type
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
        
        print(f"Executing Phase {phase_idx + 1}: {phase.name} (type: {phase.phase_type})")
        
        # Initialize tracking data for this phase
        phase_start_time = time.time()
        phase_track_data = {tp.id: [] for tp in getattr(request, 'track_points', [])}

        # Skip children of failed phases
        if phase.parent_id and phase.parent_id in failed_phases:
            msg_skip = f"Skipping phase {phase.name} because parent phase failed."
            log.append(msg_skip)
            yield {"type": "log", "content": msg_skip}
            
            # Formally report as failed to UI so counters update
            skipped_details = {
                'phase_id': phase.id,
                'success': False,
                'error': "Parent phase failed. Calculation skipped.",
                'reached_m_stage': 0.0,
                'step_points': [],
                'displacements': [],
                'stresses': [],
                'track_data': {}
            }
            phase_results.append(skipped_details)
            yield {"type": "phase_result", "content": skipped_details}
            
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
            snapshot = initial_snapshot
            total_displacement = snapshot['total_displacement'].copy()
            element_stress_state = copy.deepcopy(snapshot['element_stress_state'])
            element_strain_state = copy.deepcopy(snapshot['element_strain_state'])
            element_yield_state = copy.deepcopy(snapshot['element_yield_state'])
            element_pwp_excess_state = copy.deepcopy(snapshot['element_pwp_excess_state'])
            current_water_level_data = copy.deepcopy(snapshot['current_water_level_data'])
            current_water_level_id = snapshot['current_water_level_id']

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
        # Also compute incremental gravity from unit weight difference.
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
                                global_dof_x = node_id * 3
                                global_dof_y = node_id * 3 + 1
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

        # 2.1 Identify Active Beams and their Activation Reference (u_ref)
        active_beam_props = []
        active_beam_ids_set = set()
        beam_u_ref_map = {} # Maps segment_id -> u_ref (6-dof)
        
        parent_beam_u_ref = snapshot.get('beam_u_ref', {})

        if phase.active_beam_ids:
            active_beam_ids_set = set(phase.active_beam_ids)
            active_beam_props = [bp for bp in beam_props_all if bp['beam_id'] in active_beam_ids_set]
            
            for bp in active_beam_props:
                seg_id = bp['id']
                for n_idx in bp['nodes']:
                    active_node_indices.add(n_idx)
                
                # Check if this beam was already active in the parent phase
                if seg_id in parent_beam_u_ref:
                    beam_u_ref_map[seg_id] = parent_beam_u_ref[seg_id]
                else:
                    # NEWLY ACTIVATED: Capture current total_displacement as its zero reference
                    u_ref_b = np.zeros(6)
                    for li in range(2):
                        gi = bp['nodes'][li]
                        u_ref_b[li*3] = total_displacement[gi*3]
                        u_ref_b[li*3+1] = total_displacement[gi*3+1]
                        u_ref_b[li*3+2] = total_displacement[gi*3+2]
                    beam_u_ref_map[seg_id] = u_ref_b

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
                # Soil Elements only use u, v (3n, 3n+1)
                dofs.extend([n*3, n*3+1])
            for r_dof in dofs:
                for c_dof in dofs:
                    rows.append(r_dof)
                    cols.append(c_dof)
        
        # Add Beam Indices
        for bp in active_beam_props:
            nodes_b = bp['nodes']
            dofs = []
            for n in nodes_b:
                # Beam Elements use u, v, theta (3n, 3n+1, 3n+2)
                dofs.extend([n*3, n*3+1, n*3+2])
            for r_dof in dofs:
                for c_dof in dofs:
                    rows.append(r_dof)
                    cols.append(c_dof)
                    
        # Add Stabilization terms (small base stiffness for ALL DOFs)
        for i in range(num_nodes):
            for d in range(3):
                dof = i*3 + d
                rows.append(dof)
                cols.append(dof)

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
            
            # Add Soil Element Connectivity
            for ep in active_elem_props:
                enodes = ep['nodes']
                for i in range(6):
                    u = enodes[i]
                    for j in range(i+1, 6):
                        v = enodes[j]
                        if u in adj and v in adj:
                            adj[u].append(v)
                            adj[v].append(u)
            
            # Add Beam Connectivity
            for bp in active_beam_props:
                bnodes = bp['nodes']
                # Iterate over all nodes in the segment to build connectivity
                n_count = len(bnodes)
                for i in range(n_count):
                    u = bnodes[i]
                    for j in range(i+1, n_count):
                        v = bnodes[j]
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
            
        # Add stabilization values to match the indices added in Step 3
        for _ in range(num_nodes * 3):
            K_values.append(1e-9)
            
        K_global = sp.coo_matrix((K_values, (active_row_indices, active_col_indices)), shape=(num_dof, num_dof)).tocsr()
        
        # 4. Apply Boundary Conditions
        fixed_dofs = set()
        for bc in mesh.boundary_conditions.full_fixed:
            fixed_dofs.add(bc.node * 3)
            fixed_dofs.add(bc.node * 3 + 1)
            # Don't manually fix rotation (+2) here; let beams and stabilizers handle it.
        
        xs = [p[0] for p in nodes]; min_x, max_x = min(xs), max(xs)
        for bc in mesh.boundary_conditions.normal_fixed:
            nx = nodes[bc.node][0]
            if abs(nx - min_x) < 1e-3 or abs(nx - max_x) < 1e-3:
                fixed_dofs.add(bc.node * 3)
        
        # Add beam head rotation constraints (ONLY once per beam)
        processed_heads = set()
        for bp in active_beam_props:
            bid = bp['beam_id']
            if bid in processed_heads: continue
            
            # Use standardized string comparison for PIN vs FIXED
            conn_type = str(bp.get('head_connection_type', 'FIXED')).upper()
            gi_head = bp.get('global_head_gi')
            
            if gi_head is not None:
                # Get head coordinates for verification
                hx, hy = nodes[gi_head]
                
                # Use print() to force terminal output (UI yield logs might be buffered or missing)
                print(f"  - Head Point: Node {gi_head} at (x={hx:.3f}, y={hy:.3f})")
                print(f"  - Head Type: {conn_type}")
                
                # Check for Global BC Override
                is_globally_fixed = gi_head in [bc.node for bc in mesh.boundary_conditions.full_fixed]
                if is_globally_fixed:
                    print(f"  ! WARNING: Node {gi_head} is part of a FULL FIXED boundary. Fixed setting will override PINNED.")

                # Apply fixity
                if conn_type in ["FIXED", "FIX"]:
                    fixed_dofs.add(gi_head * 3 + 2)
                    print(f"  ---> [ACTION] Constraint applied: Fixed Rotation (DOF {gi_head * 3 + 2})")
                    yield {"type": "log", "content": f"  - Beam '{bid}': Head Node {gi_head} set to FIXED"}
                else:
                    print(f"  ---> [ACTION] No constraint: Rotation remains FREE (PINNED)")
                    yield {"type": "log", "content": f"  - Beam '{bid}': Head Node {gi_head} set to PINNED"}
                
                processed_heads.add(bid)
        
        free_dofs = []
        for d in range(num_dof):
            node_idx = d // 3
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
                    delta_F_external[gi*3] += ep['F_grav'][li*2]
                    delta_F_external[gi*3+1] += ep['F_grav'][li*2+1]
                    
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
                    delta_F_external[gi*3] -= ep['F_grav'][li*2]
                    delta_F_external[gi*3+1] -= ep['F_grav'][li*2+1]
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
                    delta_F_external[gi*3] += bp['F_grav'][li*3]
                    delta_F_external[gi*3+1] += bp['F_grav'][li*3+1]
                    delta_F_external[gi*3+2] += bp['F_grav'][li*3+2]

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
                    delta_F_external[gi*3] += f_int_el[li*2]
                    delta_F_external[gi*3+1] += f_int_el[li*2+1]
        
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
                    target_vector[n_idx*3] += pl.fx
                    target_vector[n_idx*3+1] += pl.fy
                
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
                        target_vector[n1*3] += f_total[0] / 6.0
                        target_vector[n1*3+1] += f_total[1] / 6.0
                        target_vector[n2*3] += f_total[0] / 6.0
                        target_vector[n2*3+1] += f_total[1] / 6.0
                        target_vector[n3*3] += f_total[0] * (2.0/3.0)
                        target_vector[n3*3+1] += f_total[1] * (2.0/3.0)

        # Calculate current and parent states
        apply_all_loads(phase.active_load_ids, current_load_vectors)
        if parent_phase:
            apply_all_loads(parent_phase.active_load_ids, parent_load_vectors)
        
        delta_F_external += (current_load_vectors - parent_load_vectors)
        
        # D. Incremental Gravity from Material Changes (unit weight difference)
        delta_F_external += delta_F_grav_material
        
        # D.1 Pseudo-static Force Adjustment (Handling changes in kh/kv for already active elements)
        kh_curr = getattr(phase, "kh", 0.0)
        kv_curr = getattr(phase, "kv", 0.0)
        kh_prev = getattr(parent_phase, "kh", 0.0) if parent_phase else 0.0
        kv_prev = getattr(parent_phase, "kv", 0.0) if parent_phase else 0.0
        
        if (abs(kh_curr - kh_prev) > 1e-9 or abs(kv_curr - kv_prev) > 1e-9):
            msg_ps = f"Applying pseudo-static increment: kh({kh_prev}->{kh_curr}), kv({kv_prev}->{kv_curr})"
            log.append(msg_ps); yield {"type": "log", "content": msg_ps}
            
            # Update gravity for all elements to match current phase coeffs
            for ep in elem_props_all:
                poly_id = ep['polygon_id']
                # If it was already active, we must apply the LOAD DIFFERENCE.
                # If it's newly active, its ep['F_grav'] is already correct from rebuild OR 
                # we need to ensure it uses current kh/kv.
                
                # Re-calculate current target F_grav
                coords = np.array([nodes[n] for n in ep['nodes']])
                _, F_grav_curr, _, _ = compute_element_matrices_t6(
                    coords, ep['material'], water_level=current_water_level_data,
                    kh=kh_curr, kv=kv_curr
                )
                
                if poly_id in parent_active_indices and poly_id in current_active_indices:
                    # Remaining active -> Apply increment
                    for li in range(6):
                        gi = ep['nodes'][li]
                        delta_F_external[gi*3] += (F_grav_curr[li*2] - ep['F_grav'][li*2])
                        delta_F_external[gi*3+1] += (F_grav_curr[li*2+1] - ep['F_grav'][li*2+1])
                
                # Update ep['F_grav'] to the new values for future phases
                ep['F_grav'] = F_grav_curr

            # Beam adjustment
            for bp in beam_props_all:
                beam_id = bp['beam_id']
                _, F_grav_b_curr = compute_beam_element_matrix(
                    bp['coords'], bp['material'].youngsModulus, bp['material'].crossSectionArea, 
                    getattr(bp['material'], 'momentOfInertia', 1e-6),
                    bp['spacing'], bp['material'].unitWeight, kh=kh_curr, kv=kv_curr
                )
                if beam_id in parent_active_beam_ids and beam_id in current_active_beam_ids:
                    for li in range(2):
                        gi = bp['nodes'][li]
                        delta_F_external[gi*3] += (F_grav_b_curr[li*3] - bp['F_grav'][li*3])
                        delta_F_external[gi*3+1] += (F_grav_b_curr[li*3+1] - bp['F_grav'][li*3+1])
                        delta_F_external[gi*3+2] += (F_grav_b_curr[li*3+2] - bp['F_grav'][li*3+2])
                bp['F_grav'] = F_grav_b_curr
        
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
                F_int_initial[gi*3] += f_int_el[li*2]
                F_int_initial[gi*3+1] += f_int_el[li*2+1]
        
        # Add Beam internal forces to F_int_initial based on parent state
        # This prevents "ghost" jumps when starting a new phase with already stressed beams
        is_srm = (phase.phase_type == PhaseType.SAFETY_ANALYSIS)
        for bp in active_beam_props:
            u_el_b = np.zeros(6)
            for li in range(2):
                gi = bp['nodes'][li]
                u_el_b[li*3] = total_displacement[gi*3]
                u_el_b[li*3+1] = total_displacement[gi*3+1]
                u_el_b[li*3+2] = total_displacement[gi*3+2]
            
            mat_b = bp['material']
            beam_was_active = (bp['beam_id'] in parent_active_beam_ids)
            # If beam was active in parent, its gravity is already in Dead Load, so it must be in F_int_initial
            # If Ph 2 (activation) finished at m=1.0, and Ph 3 starts at m=0.0, we use 1.0 here 
            # to match the parent's final state internal force.
            m_init = 1.0 if beam_was_active else 0.0
            
            u_ref_b = beam_u_ref_map.get(bp['id'], np.zeros(6))
            
            f_int_b_start, _ = compute_beam_internal_force_yield(
                bp['coords'], u_el_b, u_ref_b,
                mat_b.youngsModulus, mat_b.crossSectionArea,
                getattr(mat_b, 'momentOfInertia', 1e-6),
                bp['spacing'], bp['capacity'],
                is_srm, m_init
            )
            for li in range(2):
                gi = bp['nodes'][li]
                F_int_initial[gi*3] += f_int_b_start[li*3]
                F_int_initial[gi*3+1] += f_int_b_start[li*3+1]
                F_int_initial[gi*3+2] += f_int_b_start[li*3+2]
                
                # Stabilization Reaction: Matches the 1.0 penalty in stiffness
                F_int_initial[gi*3+2] += 1.0 * total_displacement[gi*3+2]
        
        # Notify UI that a new phase is starting
        is_srm = (phase.phase_type == PhaseType.SAFETY_ANALYSIS)
        yield {"type": "phase_start", "content": {"phase_id": phase.id, "phase_name": phase.name, "is_safety": is_srm}}
        
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

        # === ARC LENGTH INITIALIZATION ===
        use_arc_length = getattr(settings, 'use_arc_length', False)
        arc_length_radius = 0.0
        sign_lambda = 1.0
        F_ref_srm = None  # Perturbation-based reference load for SRM
        prev_delta_u_free = None  # Track previous displacement for limit point detection
        if use_arc_length:
            msg_al = f"Arc Length Method ENABLED for phase '{phase.name}'"
            if is_srm:
                msg_al += " (SRM: using perturbation-based reference load)"
            log.append(msg_al)
            yield {"type": "log", "content": msg_al}
            print(msg_al)

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

            if use_arc_length:
                # ==========================================
                # ARC LENGTH METHOD BRANCH
                # ==========================================
                
                # Helper: Assemble stiffness matrix (returns K_free sparse)
                def _assemble_stiffness():
                    _active_elem_D_tangent_arr = np.array([element_tangent_matrices[ep['id']] for ep in active_elem_props])
                    _K_values = assemble_stiffness_values_numba(
                        _active_elem_D_tangent_arr,
                        B_matrices_arr,
                        det_J_arr,
                        weights_arr
                    )
                    if active_beam_props:
                        _beam_k_vals = []
                        for bp in active_beam_props:
                            _beam_k_vals.extend(bp['K'].flatten())
                        _K_values = np.concatenate((_K_values, np.array(_beam_k_vals, dtype=np.float64)))
                    
                    # Standard Stabilization (Global)
                    _stab_vals = np.full(num_nodes * 3, 1e-9, dtype=np.float64)
                    
                    # ENHANCED STABILIZATION for EBR Nodes (prevent rotation jitter)
                    # EBR nodes only have rotational stiffness from the beam itself.
                    # Soil (T6) has 0 rotational stiffness, which can lead to poorly conditioned 
                    # beam rotations in slanted configurations.
                    for bid in active_beam_ids_set:
                        assign = beam_assign_map.get(bid)
                        if assign:
                            for nid in assign.nodes:
                                _stab_vals[(nid-1)*3 + 2] = 1.0

                    _K_values = np.concatenate((_K_values, _stab_vals))
                    
                    _K_global = sp.coo_matrix((_K_values, (active_row_indices, active_col_indices)), shape=(num_dof, num_dof)).tocsr()
                    return _K_global[free_dofs, :][:, free_dofs]
                
                # Helper: Compute stresses via Rust kernel
                def _compute_stresses(total_u_cand, tgt_m):
                    return compute_elements_stresses_rust(
                        elem_nodes_arr, total_u_cand,
                        step_start_stress_arr, step_start_strain_arr, step_start_pwp_arr,
                        B_matrices_arr, det_J_arr, weights_arr, D_elastic_arr, pwp_static_arr,
                        mat_drainage_arr, mat_model_arr, mat_c_arr, mat_phi_arr, mat_su_arr,
                        mat_sigma_ci_arr, mat_gsi_arr, mat_disturb_factor_arr,
                        mat_mb_arr, mat_s_arr, mat_a_arr, penalties_arr,
                        is_srm, is_gravity_phase, tgt_m, num_dof
                    )
                
                # Helper: Compute beam internal forces
                def _compute_beam_forces(total_u_cand, tgt_m):
                    F_int_b = np.zeros(num_dof)
                    for bp in active_beam_props:
                        u_el_b = np.zeros(6)
                        for li in range(2):
                            gi = bp['nodes'][li]
                            u_el_b[li*3] = total_u_cand[gi*3]
                            u_el_b[li*3+1] = total_u_cand[gi*3+1]
                            u_el_b[li*3+2] = total_u_cand[gi*3+2]
                        mat_b = bp['material']
                        u_ref_b = beam_u_ref_map.get(bp['id'], np.zeros(6))
                        f_int_b, _ = compute_beam_internal_force_yield(
                            bp['coords'], u_el_b, u_ref_b,
                            mat_b.youngsModulus, mat_b.crossSectionArea,
                            getattr(mat_b, 'momentOfInertia', 1e-6),
                            bp['spacing'], bp['capacity'],
                            is_srm, tgt_m
                        )
                        for li in range(2):
                            gi = bp['nodes'][li]
                            F_int_b[gi*3] += f_int_b[li*3]
                            F_int_b[gi*3+1] += f_int_b[li*3+1]
                            F_int_b[gi*3+2] += f_int_b[li*3+2]
                            
                            # Stabilization Reaction: Matches the 1.0 penalty in stiffness
                            F_int_b[gi*3+2] += 1.0 * total_u_cand[gi*3+2]
                    return F_int_b
                
                # Compute initial arc-length radius on first step
                if step_count == 0:
                    # For SRM: compute F_ref by perturbation of Msf
                    if is_srm:
                        epsilon_msf = 0.01
                        total_u_current = total_displacement + current_u_incremental
                        F_int_base = _compute_stresses(total_u_current, current_m_stage)[0]
                        F_int_base = F_int_base + _compute_beam_forces(total_u_current, current_m_stage)
                        F_int_pert = _compute_stresses(total_u_current, current_m_stage + epsilon_msf)[0]
                        F_int_pert = F_int_pert + _compute_beam_forces(total_u_current, current_m_stage + epsilon_msf)
                        # Negative because increasing Msf reduces strength -> increases out-of-balance
                        F_ref_srm = -(F_int_pert - F_int_base) / epsilon_msf
                        f_ref_for_init = F_ref_srm[free_dofs]
                        msg_fref = f"  > SRM F_ref computed by perturbation (norm: {np.linalg.norm(f_ref_for_init):.4f})"
                        log.append(msg_fref)
                        yield {"type": "log", "content": msg_fref}
                    else:
                        f_ref_for_init = delta_F_external[free_dofs]
                    
                    K_free_init = _assemble_stiffness()
                    arc_length_radius, _ = compute_initial_arc_length(
                        step_size, f_ref_for_init, K_free_init
                    )
                    msg_al_r = f"  > Arc-length radius (Δl): {arc_length_radius:.6f}"
                    log.append(msg_al_r)
                    yield {"type": "log", "content": msg_al_r}
                
                al_result = run_arc_length_step(
                    assemble_stiffness_fn=_assemble_stiffness,
                    compute_stresses_fn=_compute_stresses,
                    compute_beam_forces_fn=_compute_beam_forces,
                    free_dofs=free_dofs,
                    num_dof=num_dof,
                    F_int_initial=F_int_initial,
                    delta_F_external=delta_F_external,
                    total_displacement=total_displacement,
                    current_u_incremental=current_u_incremental,
                    max_iterations=settings.max_iterations,
                    tolerance=settings.tolerance,
                    arc_length_radius=arc_length_radius,
                    sign_lambda=sign_lambda,
                    current_m_stage=current_m_stage,
                    is_srm=is_srm,
                    F_ref_direction=F_ref_srm,  # None for regular phases, perturbation-based for SRM
                    prev_delta_u_free=prev_delta_u_free  # For limit point detection
                )
                
                converged = bool(al_result['converged'])
                step_du = al_result['step_du']
                iteration = int(al_result['iterations'])
                delta_lambda = float(al_result['delta_lambda'])
                norm_R = float(al_result['norm_R'])
                f_base = float(al_result['f_base'])
                R_free = al_result['R_free']
                
                # Re-map stress data from arc-length result
                temp_phase_stress = {}
                temp_phase_yield = {}
                temp_phase_strain = {}
                temp_phase_pwp_excess = {}
                if al_result['stress_data'] is not None:
                    new_stresses_arr, new_yield_arr, new_strain_arr, new_pwp_excess_arr = al_result['stress_data']
                    for i, ep in enumerate(active_elem_props):
                        eid = ep['id']
                        temp_phase_stress[eid] = [new_stresses_arr[i, gp] for gp in range(3)]
                        temp_phase_yield[eid] = [new_yield_arr[i, gp] for gp in range(3)]
                        temp_phase_strain[eid] = [new_strain_arr[i, gp] for gp in range(3)]
                        temp_phase_pwp_excess[eid] = [new_pwp_excess_arr[i, gp] for gp in range(3)]
                
                # For arc-length, target_m_stage is determined by delta_lambda
                target_m_stage = current_m_stage + delta_lambda
                if not is_srm:
                    target_m_stage = min(target_m_stage, 1.0)
                
                if al_result['error']:
                    msg_al_err = f"Arc-Length: {al_result['error']}"
                    log.append(msg_al_err)
                    yield {"type": "log", "content": msg_al_err}
                    print(msg_al_err)

            else:
                # ==========================================
                # STANDARD NEWTON-RAPHSON BRANCH (unchanged)
                # ==========================================
                iteration = 0
                converged = False
                step_du = np.zeros(num_dof) 
                
                while iteration < settings.max_iterations:
                    iteration += 1
                    
                    total_u_candidate = total_displacement + current_u_incremental + step_du
                    
                    # Compute Internal Forces and Stress Update (Rust Kernel)
                    F_int, new_stresses_arr, new_yield_arr, new_strain_arr, new_pwp_excess_arr = compute_elements_stresses_rust(
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
                    
                    # (Moved collections re-mapping outside iteration loop for performance)
                    
                    # Add Beam Internal Forces to F_int (with yielding)
                    for bp in active_beam_props:
                        u_el_b = np.zeros(6)
                        for li in range(2):
                            gi = bp['nodes'][li]
                            u_el_b[li*3] = total_u_candidate[gi*3]
                            u_el_b[li*3+1] = total_u_candidate[gi*3+1]
                            u_el_b[li*3+2] = total_u_candidate[gi*3+2]
                        
                        mat_b = bp['material']
                        u_ref_b = beam_u_ref_map.get(bp['id'], np.zeros(6))
                        f_int_b, is_yielded_b = compute_beam_internal_force_yield(
                            bp['coords'], u_el_b, u_ref_b,
                            mat_b.youngsModulus, mat_b.crossSectionArea, 
                            getattr(mat_b, 'momentOfInertia', 1e-6),
                            bp['spacing'], bp['capacity'],
                            is_srm, target_m_stage
                        )
                        
                        for li in range(2):
                            gi = bp['nodes'][li]
                            F_int[gi*3] += f_int_b[li*3]
                            F_int[gi*3+1] += f_int_b[li*3+1]
                            F_int[gi*3+2] += f_int_b[li*3+2]
                            
                            # Stabilization Reaction: Matches the 1.0 penalty and prevents drift
                            F_int[gi*3+2] += 1.0 * total_u_candidate[gi*3+2]

                    
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
                        K_values = np.concatenate((K_values, np.array(beam_k_vals, dtype=np.float64)))
                    
                    # Standard Stabilization (Global)
                    _stab_vals = np.full(num_nodes * 3, 1e-9, dtype=np.float64)
                    
                    # ENHANCED STABILIZATION for EBR Nodes (prevent rotation jitter)
                    for bid in active_beam_ids_set:
                        assign = beam_assign_map.get(bid)
                        if assign:
                            for nid in assign.nodes:
                                _stab_vals[(nid-1)*3 + 2] = 1.0

                    K_values = np.concatenate((K_values, _stab_vals))
                    
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
                        # 2. Solver Call (Prefer Multi-threaded Pardiso if enabled)
                        if HAS_PARDISO and settings.use_pardiso:
                            du_free = pardiso_spsolve(K_free, R_free)
                        else:
                            du_free = scipy_spsolve(K_free, R_free)
                        
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
                                    
                                    node_id = bad_dof // 3
                                    axis_id = bad_dof % 3
                                    axis = "X" if axis_id == 0 else ("Y" if axis_id == 1 else "Rotation")
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
            trial_u_reshaped = trial_u.reshape(-1, 3)
            trial_magnitudes = np.sqrt(trial_u_reshaped[:,0]**2 + trial_u_reshaped[:,1]**2)
            max_disp = np.float64(np.max(trial_magnitudes))

            if converged:
                # Optimized: Build result dictionaries ONLY on convergence
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

                step_count += 1
                current_u_incremental = trial_u
                if use_arc_length:
                    current_m_stage = target_m_stage  # target_m_stage already set from delta_lambda
                else:
                    current_m_stage = target_m_stage
                
                for eid, stress in temp_phase_stress.items(): phase_stress_history[eid] = stress
                for eid, strain in temp_phase_strain.items(): phase_strain_history[eid] = strain
                for eid, yld in temp_phase_yield.items(): phase_yield_history[eid] = yld
                for eid, pexc in temp_phase_pwp_excess.items(): phase_pwp_excess_history[eid] = pexc
                
                method_label = "(Arc-Length)" if use_arc_length else ""
                msg = f"Phase {phase.name} | Step {step_count}: {m_type} {current_m_stage:.4f} | Max Incr. Disp: {max_disp:.6f} m | Iterations {iteration} {method_label}"
                log.append(msg)
                if getattr(settings, 'realtime_logging', True):
                    yield {"type": "log", "content": msg}
                
                pt = {"m_stage": float(current_m_stage), "max_disp": float(max_disp)}
                phase_step_points.append(pt)
                
                # --- Termination Check: Displacement Limit (Collapse Detection) ---
                if max_disp > settings.max_displacement_limit:
                    msg_coll = f"Displacement limit ({settings.max_displacement_limit:.2f} m) exceeded. Terminating phase due to excessive deformation."
                    log.append(msg_coll)
                    yield {"type": "log", "content": msg_coll}
                    print(msg_coll)
                    break

                if getattr(settings, 'realtime_logging', True):
                    yield {"type": "step_point", "content": pt}
                print(msg)
                
                # --- Record Track Point Data ---
                for tp in getattr(request, 'track_points', []):
                    # Find tracking data for Newton iteration step completion
                    entry = {"step": step_count, "m_stage": float(current_m_stage)}
                    if tp.type == "node":
                        n_idx = tp.index
                        dof_x, dof_y = n_idx * 3, n_idx * 3 + 1
                        if n_idx < len(nodes):
                            entry["ux"] = float(trial_u[dof_x])
                            entry["uy"] = float(trial_u[dof_y])
                            entry["total_ux"] = float(total_displacement[dof_x] + trial_u[dof_x])
                            entry["total_uy"] = float(total_displacement[dof_y] + trial_u[dof_y])
                    elif tp.type == "gp":
                        e_idx = tp.index
                        gp_idx = tp.gp_index if tp.gp_index is not None else 0
                        # Try to get from temp updated state, fallback to prev state
                        st = temp_phase_stress.get(e_idx + 1)
                        pexc = temp_phase_pwp_excess.get(e_idx + 1)
                        if not st: 
                            st = element_stress_state.get(e_idx + 1)
                            pexc = element_pwp_excess_state.get(e_idx + 1)
                        
                        if st and gp_idx < len(st):
                            sig = st[gp_idx]
                            entry["sig_xx"] = float(sig[0])
                            entry["sig_yy"] = float(sig[1])
                            entry["sig_xy"] = float(sig[2])
                            entry["sig_zz"] = float(sig[3]) if len(sig) > 3 else float(0.3 * (sig[0] + sig[1]))
                            # PWP approximation
                            px = pexc[gp_idx] if pexc and hasattr(pexc, '__len__') and gp_idx < len(pexc) else 0.0
                            entry["pwp_excess"] = float(px)
                            
                            # Steady PWP from initial state
                            ep = active_elem_props[e_idx]
                            p_steady = ep['gauss_points'][gp_idx]['pwp'] or 0.0
                            entry["pwp_steady"] = float(p_steady)
                            entry["pwp_total"] = float(px + p_steady)
                            
                        # Strain
                        sr = temp_phase_strain.get(e_idx + 1)
                        if not sr: sr = element_strain_state.get(e_idx + 1)
                        if sr and gp_idx < len(sr):
                            eps = sr[gp_idx]
                            entry["eps_xx"] = float(eps[0])
                            entry["eps_yy"] = float(eps[1])
                            entry["eps_xy"] = float(eps[2])
                    
                    phase_track_data[tp.id].append(entry)
                # -------------------------------
                
                # Removed SF cap at 10.0 as per user request to see full collapse

                if use_arc_length:
                    # Arc-length step size adaptation based on iteration count
                    if iteration < settings.min_desired_iterations:
                        arc_length_radius *= 1.5
                    elif iteration > settings.max_desired_iterations:
                        arc_length_radius *= 0.5
                    # Also scale the nominal step_size for the m_stage capping logic
                    step_size = abs(delta_lambda) if abs(delta_lambda) > 1e-8 else step_size
                    
                    # Update sign_lambda and prev_delta_u for limit point detection
                    new_sign = al_result.get('sign_lambda_next', sign_lambda)
                    if new_sign != sign_lambda:
                        msg_sign = f"  > Limit point detected! sign_lambda flipped: {sign_lambda:+.0f} -> {new_sign:+.0f} (load parameter now {'decreasing' if new_sign < 0 else 'increasing'})"
                        log.append(msg_sign)
                        yield {"type": "log", "content": msg_sign}
                        print(msg_sign)
                        sign_lambda = new_sign
                    
                    conv_du = al_result.get('delta_u_free_converged')
                    if conv_du is not None:
                        prev_delta_u_free = conv_du
                else:
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
                node_id = (global_dof // 3) + 1
                axis_id = global_dof % 3
                axis = "X" if axis_id == 0 else ("Y" if axis_id == 1 else "Rotation")
                
                msg_detail = f"  > Final Residual Norm: {norm_R:.4f} | Max Displacement: {max_disp:.6f} m | (Rel: {norm_R/f_base:.6f} vs Tol: {settings.tolerance})"
                msg_worst = f"  > Largest Out-of-balance: {worst_val:.4f} kN at Node {node_id} (DOF {axis})"
                log.append(msg_detail)
                log.append(msg_worst)
                print(msg_detail)
                print(msg_worst)
                yield {"type": "log", "content": msg_detail}
                yield {"type": "log", "content": msg_worst}

                if use_arc_length:
                    if arc_length_radius > 1e-6:
                        arc_length_radius *= 0.5
                        step_size *= 0.5
                        msg_retry = f"  > Arc-Length: Retrying with smaller radius: {arc_length_radius:.6f}"
                        log.append(msg_retry)
                        print(msg_retry)
                        yield {"type": "log", "content": msg_retry}
                        continue
                    else:
                        msg_abort = f"Arc-length radius too small ({arc_length_radius:.6f}). Aborting phase."
                        log.append(msg_abort)
                        print(msg_abort)
                        yield {"type": "log", "content": msg_abort}
                        break
                else:
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
            p_displacements.append(NodeResult(
                id=i+1, 
                ux=final_u_total[i*3], 
                uy=final_u_total[i*3+1], 
                rot=final_u_total[i*3+2]
            ))
        
        # Post-Process Beam Forces
        p_beam_results = []
        for bp in active_beam_props:
            bm = bp['material']
            u_el_b = np.zeros(6)
            for li in range(2):
                gi = bp['nodes'][li]
                u_el_b[li*3] = final_u_total[gi*3]
                u_el_b[li*3+1] = final_u_total[gi*3+1]
                u_el_b[li*3+2] = final_u_total[gi*3+2]
            
            u_ref_b = beam_u_ref_map.get(bp['id'], np.zeros(6))
            forces = compute_beam_forces_local(
                bp['coords'], u_el_b, u_ref_b,
                bm.youngsModulus, bm.crossSectionArea, 
                getattr(bm, 'momentOfInertia', 1e-6),
                bp['spacing']
            )
            # forces: [N, V1, M1, V2, M2]
            # relative displacements
            u_rel = u_el_b - u_ref_b
            
            p_beam_results.append(BeamResult(
                beam_id=bp['beam_id'],
                segment_index=int(bp['id'].split("_seg_")[-1]),
                n=float(forces[0]),
                v1=float(forces[1]),
                m1=float(forces[2]),
                v2=float(forces[3]),
                m2=float(forces[4]),
                # Total displacements
                ux1=float(u_el_b[0]), uy1=float(u_el_b[1]),
                ux2=float(u_el_b[3]), uy2=float(u_el_b[4]),
                # Relative displacements
                urx1=float(u_rel[0]), ury1=float(u_rel[1]),
                urx2=float(u_rel[3]), ury2=float(u_rel[4])
            ))

        # --- DIAGNOSTIC: Check beam continuity at shared nodes ---
        if p_beam_results:
            # Group by beam_id
            from collections import defaultdict
            beam_groups = defaultdict(list)
            for res in p_beam_results:
                beam_groups[res.beam_id].append(res)
            
            for bid, segments in beam_groups.items():
                segments.sort(key=lambda x: x.segment_index)
                for i in range(len(segments) - 1):
                    s1 = segments[i]
                    s2 = segments[i+1]
                    diff_m = abs(s1.m2 - s2.m1)
                    diff_v = abs(s1.v2 - s2.v1)
                    
                    if diff_m > 1e-2 or diff_v > 1e-2:
                        msg_disco = f"  [DIAGNOSTIC] EBR '{bid}' Discontinuity at Seg {i}-{i+1}: dM={diff_m:.4f}, dV={diff_v:.4f}"
                        print(msg_disco)
                        log.append(msg_disco)
                        
                        # DEEP DIAGNOSTIC for slanted beams
                        # Grab original element props for these segments to see their forces
                        bp1 = next((p for p in beam_props_all if p['id'] == f"{bid}_seg_{i}"), None)
                        bp2 = next((p for p in beam_props_all if p['id'] == f"{bid}_seg_{i+1}"), None)
                        
                        if bp1 and bp2:
                            def get_forces_for_bp(bp):
                                u_el_b = np.zeros(6)
                                for li in range(2):
                                    gi = bp['nodes'][li]
                                    u_el_b[li*3] = final_u_total[gi*3]
                                    u_el_b[li*3+1] = final_u_total[gi*3+1]
                                    u_el_b[li*3+2] = final_u_total[gi*3+2]
                                    
                                u_ref_b = beam_u_ref_map.get(bp['id'], np.zeros(6))
                                return compute_beam_forces_local(
                                    bp['coords'], u_el_b, u_ref_b,
                                    bp['material'].youngsModulus, bp['material'].crossSectionArea, 
                                    getattr(bp['material'], 'momentOfInertia', 1e-6),
                                    bp['spacing']
                                )
                            
                            f1 = get_forces_for_bp(bp1)
                            f2 = get_forces_for_bp(bp2)
                            print(f"    - Seg {i}   Ends: M2={f1[4]:.4f}, V2={f1[3]:.4f}")
                            print(f"    - Seg {i+1} Starts: M1={f2[2]:.4f}, V1={f2[1]:.4f}")
                            print(f"    - Seg {i}   f_loc: {f1}")
                            print(f"    - Seg {i+1} f_loc: {f2}")
        
        p_stresses = []
        for ep in active_elem_props:
            eid = ep['id']
            # Get list of Gauss point states
            sig_list = phase_stress_history.get(eid, element_stress_state.get(eid, [np.zeros(3)]*3))
            yld_list = phase_yield_history.get(eid, element_yield_state.get(eid, [False]*3))
            strain_list = phase_strain_history.get(eid, element_strain_state.get(eid, [np.zeros(3)]*3))
            pwp_excess_list = phase_pwp_excess_history.get(eid, element_pwp_excess_state.get(eid, [0.0]*3))
            
            for gp_idx in range(3):
                gp_data = ep['gauss_points'][gp_idx]
                sig = sig_list[gp_idx]
                eps = strain_list[gp_idx]
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
                    pwp_excess=float(pwp_excess),
                    pwp_total=float(pwp_total),
                    eps_xx=float(eps[0]), eps_yy=float(eps[1]), eps_xy=float(eps[2]), eps_zz=0.0,
                    is_yielded=bool(yld), m_stage=float(current_m_stage)
                ))
        
        # success = (not is_srm and current_m_stage >= 0.999) or (is_srm and current_m_stage > 1.0)
        success = (not is_srm and current_m_stage >= 0.999) or (is_srm)
        error_msg = None
        if not success:
            error_msg = f"Phase failed at step {step_count}."

        phase_details = {
            'phase_id': phase.id,
            'success': success,
            'displacements': p_displacements,
            'stresses': p_stresses,
            'beam_results': p_beam_results,
            'pwp': [], # Skipped for now
            'reached_m_stage': current_m_stage,
            'step_points': phase_step_points,
            'step_failed_at': step_count if not success else None,
            'error': error_msg,
            'track_data': phase_track_data
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
                'beam_u_ref': copy.deepcopy(beam_u_ref_map),
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
        
        # Log Phase Duration
        phase_duration = time.time() - phase_start_time
        msg_phase_done = f"Phase \"{phase.name}\" finished in {format_duration(phase_duration)}."
        log.append(msg_phase_done)
        yield {"type": "log", "content": msg_phase_done}
        print(msg_phase_done)

    # Final Summary
    total_duration = time.time() - total_start_time
    msg_total = f"--- Calculation Completed. Total Time: {format_duration(total_duration)} for {len(request.phases)} phases ---"
    log.append(msg_total)
    yield {"type": "log", "content": msg_total}
    print(msg_total)

    yield {"type": "final", "content": {
        "success": all(pr['success'] for pr in phase_results),
        "phases": phase_results,
        "log": log
    }}
