import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from engine.models import *
from engine.mesh_generator import generate_mesh
from engine.solver.element_t15 import compute_b_matrix, GAUSS_POINTS
from core.samples import SAMPLE_FOUNDATION

sample = SAMPLE_FOUNDATION
materials = [Material(**m) for m in sample['materials']]
polygons = [PolygonData(**p) for p in sample['polygons']]
point_loads = [PointLoad(**pl) for pl in sample.get('pointLoads', [])]
line_loads = [LineLoad(**ll) for ll in sample.get('lineLoads', [])]
water_levels = [WaterLevel(**{**wl, 'name': wl.get('name', wl['id'])}) for wl in sample.get('waterLevels', [])]
mesh_settings = MeshSettings(**sample.get('meshSettings', {}))

mesh_req = MeshRequest(polygons=polygons, materials=materials, pointLoads=point_loads,
    lineLoads=line_loads, water_levels=water_levels, mesh_settings=mesh_settings)
mesh_resp = generate_mesh(mesh_req)

# Check FIRST few elements with negative det_J
neg_count = 0
total_neg_gp = 0
total_gp = 0
bad_elements = []

for el_idx, el in enumerate(mesh_resp.elements):
    coords = np.array([mesh_resp.nodes[n] for n in el])
    elem_neg = 0
    for gp_idx in range(12):
        xi, eta = GAUSS_POINTS[gp_idx]
        B, det_J = compute_b_matrix(coords, xi, eta)
        total_gp += 1
        if det_J < 0:
            total_neg_gp += 1
            elem_neg += 1
    if elem_neg > 0:
        neg_count += 1
        if len(bad_elements) < 5:
            bad_elements.append(el_idx)

print(f"Total elements: {len(mesh_resp.elements)}")
print(f"Elements with neg det_J: {neg_count}")
print(f"Total neg GPs: {total_neg_gp} / {total_gp}")

# Detailed check of first bad element
if bad_elements:
    el_idx = bad_elements[0]
    el = mesh_resp.elements[el_idx]
    coords = np.array([mesh_resp.nodes[n] for n in el])
    
    print(f"\n--- Element {el_idx+1} (first bad element) ---")
    for i, (nid, c) in enumerate(zip(el, coords)):
        print(f"  Local {i} (Global {nid}): ({c[0]:.6f}, {c[1]:.6f})")
    
    # Check corners
    c0, c1, c2 = coords[0], coords[1], coords[2]
    cross = (c1[0]-c0[0])*(c2[1]-c0[1]) - (c1[1]-c0[1])*(c2[0]-c0[0])
    orient = "CCW" if cross > 0 else "CW"
    print(f"\n  Corner cross product: {cross:.6f} ({orient})")
    print(f"  Linear area: {abs(cross/2):.6f}")
    
    # Check expected vs actual positions of edge/interior nodes
    # Edge 1-2: from n1(corners[0]) to n2(corners[1]) at 1/4, 1/2, 3/4
    p = coords
    print(f"\n  Edge 0-1 (nodes 3,4,5):")
    for i, frac in enumerate([0.25, 0.50, 0.75]):
        expected = (1-frac)*c0 + frac*c1
        actual = coords[3+i]
        diff = np.linalg.norm(actual - expected)
        print(f"    Node {3+i}: expected ({expected[0]:.4f},{expected[1]:.4f}), actual ({actual[0]:.4f},{actual[1]:.4f}), diff={diff:.6f}")
    
    print(f"\n  Edge 1-2 (nodes 6,7,8):")
    for i, frac in enumerate([0.25, 0.50, 0.75]):
        expected = (1-frac)*c1 + frac*c2
        actual = coords[6+i]
        diff = np.linalg.norm(actual - expected)
        print(f"    Node {6+i}: expected ({expected[0]:.4f},{expected[1]:.4f}), actual ({actual[0]:.4f},{actual[1]:.4f}), diff={diff:.6f}")
    
    print(f"\n  Edge 2-0 (nodes 9,10,11):")
    for i, frac in enumerate([0.25, 0.50, 0.75]):
        expected = (1-frac)*c2 + frac*c0
        actual = coords[9+i]
        diff = np.linalg.norm(actual - expected)
        print(f"    Node {9+i}: expected ({expected[0]:.4f},{expected[1]:.4f}), actual ({actual[0]:.4f},{actual[1]:.4f}), diff={diff:.6f}")
    
    print(f"\n  All det_J:")
    for gp_idx in range(12):
        xi, eta = GAUSS_POINTS[gp_idx]
        B, det_J = compute_b_matrix(coords, xi, eta)
        print(f"    GP {gp_idx+1}: det_J={det_J:.8f}")
