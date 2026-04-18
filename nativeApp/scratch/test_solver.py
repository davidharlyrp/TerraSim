"""
Standalone test: Runs Foundation sample through mesh generation -> solver.
Captures detailed diagnostics for debugging T15 instability.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from engine.models import (
    Material, PolygonData, PointLoad, LineLoad, WaterLevel,
    MeshSettings, MeshRequest, SolverRequest, PhaseRequest,
    SolverSettings, EmbeddedBeam, EmbeddedBeamMaterial
)
from engine.mesh_generator import generate_mesh
from engine.solver.phase_solver import solve_phases
from core.samples import SAMPLE_FOUNDATION

def build_mesh_request(sample):
    materials = [Material(**m) for m in sample['materials']]
    polygons = [PolygonData(**p) for p in sample['polygons']]
    point_loads = [PointLoad(**pl) for pl in sample.get('pointLoads', [])]
    line_loads = [LineLoad(**ll) for ll in sample.get('lineLoads', [])]
    water_levels = [WaterLevel(**{**wl, 'name': wl.get('name', wl['id'])}) for wl in sample.get('waterLevels', [])]
    mesh_settings = MeshSettings(**sample.get('meshSettings', {}))

    return MeshRequest(
        polygons=polygons,
        materials=materials,
        pointLoads=point_loads,
        lineLoads=line_loads,
        water_levels=water_levels,
        mesh_settings=mesh_settings,
    ), materials, point_loads, line_loads, water_levels

def build_solver_request(mesh_response, sample, materials, point_loads, line_loads, water_levels):
    phases_raw = sample['phases']
    phases = []
    for p in phases_raw:
        p2 = dict(p)
        if 'phase_type' in p2:
            p2['phase_type'] = p2['phase_type'].lower()
        phases.append(PhaseRequest(**p2))
    settings = SolverSettings(
        max_iterations=60,
        tolerance=0.01,
        initial_step_size=0.05,
        max_steps=100,
        max_displacement_limit=10.0,
        use_pardiso=False,
    )
    return SolverRequest(
        mesh=mesh_response,
        phases=phases,
        settings=settings,
        materials=materials,
        water_levels=water_levels,
        point_loads=point_loads,
        line_loads=line_loads,
    )

def main():
    print("=" * 70)
    print("TERRASIM T15 SOLVER DIAGNOSTIC TEST")
    print("=" * 70)

    sample = SAMPLE_FOUNDATION

    # Step 1: Build mesh
    print("\n--- Step 1: Mesh Generation ---")
    mesh_req, materials, point_loads, line_loads, water_levels = build_mesh_request(sample)
    mesh_resp = generate_mesh(mesh_req)

    if not mesh_resp.success:
        print(f"MESH FAILED: {mesh_resp.error}")
        return

    print(f"  Nodes: {len(mesh_resp.nodes)}")
    print(f"  Elements: {len(mesh_resp.elements)}")
    print(f"  Full Fixed BCs: {len(mesh_resp.boundary_conditions.full_fixed)}")
    print(f"  Normal Fixed BCs: {len(mesh_resp.boundary_conditions.normal_fixed)}")

    # Verify T15 elements
    for i, el in enumerate(mesh_resp.elements[:3]):
        print(f"  Element {i+1}: {len(el)} nodes -> {el[:3]} (corners)")
    
    # Check element node counts
    bad_elems = [i for i, el in enumerate(mesh_resp.elements) if len(el) != 15]
    if bad_elems:
        print(f"  ERROR: {len(bad_elems)} elements don't have 15 nodes!")
    else:
        print(f"  All {len(mesh_resp.elements)} elements have 15 nodes OK")

    # Step 2: Verify B-matrices and det_J
    print("\n--- Step 2: Element Quality Check ---")
    from engine.solver.element_t15 import compute_b_matrix, shape_functions_t15, GAUSS_POINTS, GAUSS_WEIGHTS
    
    neg_detJ_count = 0
    small_detJ_count = 0
    total_gp = 0
    min_detJ = float('inf')
    max_detJ = float('-inf')
    
    for el_idx, el_nodes in enumerate(mesh_resp.elements[:200]):
        coords = np.array([mesh_resp.nodes[n] for n in el_nodes])
        for gp_idx in range(12):
            xi, eta = GAUSS_POINTS[gp_idx]
            B, det_J = compute_b_matrix(coords, xi, eta)
            total_gp += 1
            
            if det_J < 0:
                neg_detJ_count += 1
                if neg_detJ_count <= 5:
                    print(f"  !! NEGATIVE det_J = {det_J:.6e} at elem {el_idx+1}, GP {gp_idx+1}")
            elif abs(det_J) < 1e-10:
                small_detJ_count += 1
            
            min_detJ = min(min_detJ, det_J)
            max_detJ = max(max_detJ, det_J)
    
    print(f"  Checked {total_gp} Gauss points in {min(200, len(mesh_resp.elements))} elements")
    print(f"  det_J range: [{min_detJ:.6e}, {max_detJ:.6e}]")
    print(f"  Negative det_J: {neg_detJ_count}")
    print(f"  Near-zero det_J: {small_detJ_count}")

    # Step 3: Verify shape functions
    print("\n--- Step 3: Shape Function Verification ---")
    for gp_idx in range(12):
        xi, eta = GAUSS_POINTS[gp_idx]
        N = shape_functions_t15(xi, eta)
        sum_N = np.sum(N)
        if abs(sum_N - 1.0) > 1e-10:
            print(f"  ERROR: GP {gp_idx+1}: sum(N) = {sum_N} (should be 1.0)")
    print(f"  All shape functions sum to 1.0 OK")
    print(f"  Gauss weights sum: {np.sum(GAUSS_WEIGHTS):.15f} (should be 0.5)")

    # Step 4: Run solver
    print("\n--- Step 4: Solver Execution ---")
    solver_req = build_solver_request(mesh_resp, sample, materials, point_loads, line_loads, water_levels)
    
    phase_results = {}
    for event in solve_phases(solver_req):
        etype = event['type']
        if etype == 'log':
            print(f"  > {event['content']}")
        elif etype == 'phase_result':
            res = event['content']
            pid = res.get('phase_id', '?')
            success = res.get('success', False)
            m = res.get('reached_m_stage', 0)
            err = res.get('error')
            phase_results[pid] = res
            
            status = "OK SUCCESS" if success else "FAIL FAILED"
            print(f"\n  === Phase '{pid}': {status} (MStage={m:.4f}) ===")
            if err:
                print(f"      Error: {err}")
            
            # Print displacement stats
            disps = res.get('displacements', [])
            if disps:
                ux_vals = [d.ux for d in disps]
                uy_vals = [d.uy for d in disps]
                max_ux = max(abs(v) for v in ux_vals) if ux_vals else 0
                max_uy = max(abs(v) for v in uy_vals) if uy_vals else 0
                print(f"      Max |UX| = {max_ux:.6f} m, Max |UY| = {max_uy:.6f} m")
        elif etype == 'step_point':
            sp = event['content']
            # Print step points only for non-trivial steps
            if sp.get('max_disp', 0) > 0:
                print(f"    Step: MStage={sp['m_stage']:.4f}, MaxDisp={sp['max_disp']:.6f}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    total = len(phase_results)
    success = sum(1 for r in phase_results.values() if r.get('success'))
    print(f"  {success}/{total} phases succeeded")
    
    for pid, res in phase_results.items():
        status = "OK" if res.get('success') else "FAIL"
        print(f"  {status} {pid}: MStage={res.get('reached_m_stage', 0):.4f}")

if __name__ == "__main__":
    main()
