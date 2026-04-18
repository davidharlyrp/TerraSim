import numpy as np
import triangle
import math
from typing import List, Dict, Tuple, Optional
from shapely.geometry import Polygon as ShapelyPolygon, Point as ShapelyPoint
from scipy.spatial import cKDTree
from engine.models import MeshRequest, MeshResponse, BoundaryConditionsResponse, BoundaryCondition, PointLoadAssignment, ElementMaterial
from engine.error import ErrorCode, get_error_info


def _compute_local_size(dist_to_boundary: float, h_min: float, h_max: float, grading_distance: float) -> float:
    """
    Compute the desired local element size at a point based on its distance
    to the nearest boundary/structural line.
    
    Uses a smooth power-law grading function that transitions from h_min
    (at the boundary) to h_max (far from the boundary).
    
    Args:
        dist_to_boundary: Distance from the point to nearest boundary/EBR
        h_min: Target element size at boundaries (smallest)
        h_max: Target element size in the interior (largest)
        grading_distance: Distance over which the transition occurs
    """
    if grading_distance < 1e-9:
        return h_min
    t = min(1.0, dist_to_boundary / grading_distance)
    # Use sqrt for smoother grading (slightly slower growth near boundary)
    t_smooth = math.sqrt(t)
    return h_min + (h_max - h_min) * t_smooth


def _generate_graded_interior_points(
    polygon_geom: ShapelyPolygon,
    boundary_sample_pts: np.ndarray,
    h_min: float,
    h_max: float,
    grading_distance: float
) -> List[Tuple[float, float]]:
    """
    Generate interior Steiner points within a polygon sub-region.
    Points are spaced according to a distance-based size function,
    creating smooth gradual transitions from refined boundaries to
    coarser interiors (similar to Plaxis mesh generation).
    
    Uses a Poisson-disk-like sampling approach: candidate points on a
    fine grid are accepted only if they are far enough from all
    previously accepted points (with "far enough" determined by the
    local size function).
    """
    if polygon_geom.is_empty or polygon_geom.area < 1e-8:
        return []
    
    # Build a KD-tree of boundary sample points for fast distance queries
    if len(boundary_sample_pts) < 2:
        return []
    boundary_tree = cKDTree(boundary_sample_pts)
    
    # Get polygon bounding box
    minx, miny, maxx, maxy = polygon_geom.bounds
    
    # Generate candidate grid at spacing of h_min (finest resolution)
    # Use h_min * 0.7 for candidate spacing to ensure good coverage
    candidate_spacing = max(h_min * 0.7, 0.05)
    
    # Limit total candidates to prevent memory issues on very large models
    nx = int(math.ceil((maxx - minx) / candidate_spacing)) + 1
    ny = int(math.ceil((maxy - miny) / candidate_spacing)) + 1
    MAX_CANDIDATES = 200_000
    if nx * ny > MAX_CANDIDATES:
        # Scale up spacing to stay within budget
        scale = math.sqrt((nx * ny) / MAX_CANDIDATES)
        candidate_spacing *= scale
        nx = int(math.ceil((maxx - minx) / candidate_spacing)) + 1
        ny = int(math.ceil((maxy - miny) / candidate_spacing)) + 1
    
    accepted_points = []
    accepted_arr = []  # For building a KD-tree of accepted points
    acc_tree = None
    tree_dirty = True  # Flag to rebuild tree
    REBUILD_INTERVAL = 50  # Rebuild KD-tree every N new points
    points_since_rebuild = 0
    
    # Prepare shapely polygon for fast contains checks
    from shapely.prepared import prep
    prep_poly = prep(polygon_geom)
    
    # Scan grid with offset for even rows (hexagonal packing)
    for iy in range(ny):
        x_offset = (candidate_spacing * 0.5) if (iy % 2 == 1) else 0.0
        for ix in range(nx):
            cx = minx + ix * candidate_spacing + x_offset
            cy = miny + iy * candidate_spacing
            
            # Quick bounds check
            if cx < minx or cx > maxx or cy < miny or cy > maxy:
                continue
            
            # Check if inside polygon
            pt = ShapelyPoint(cx, cy)
            if not prep_poly.contains(pt):
                continue
            
            # Distance to nearest boundary
            dist_b, _ = boundary_tree.query([cx, cy])
            
            # Compute local desired size
            h_local = _compute_local_size(dist_b, h_min, h_max, grading_distance)
            
            # Skip if too close to boundary (boundary discretization handles that)
            if dist_b < h_min * 0.4:
                continue
            
            # Check distance to previously accepted interior points
            if accepted_arr:
                if tree_dirty:
                    acc_tree = cKDTree(np.array(accepted_arr))
                    tree_dirty = False
                dist_a, _ = acc_tree.query([cx, cy])
                if dist_a < h_local * 0.8:
                    continue
            
            accepted_points.append((cx, cy))
            accepted_arr.append([cx, cy])
            points_since_rebuild += 1
            if points_since_rebuild >= REBUILD_INTERVAL:
                tree_dirty = True
                points_since_rebuild = 0
    
    return accepted_points

def generate_mesh(request: MeshRequest) -> MeshResponse:
    try:
        # --- 0. Pre-flight Material Validation ---
        material_ids = {m.id for m in request.materials}
        
        # Check Polygons
        for i, poly in enumerate(request.polygons):
            if not poly.materialId or poly.materialId not in material_ids:
                return MeshResponse(
                    success=False, nodes=[], elements=[],
                    boundary_conditions=BoundaryConditionsResponse(full_fixed=[], normal_fixed=[]),
                    point_load_assignments=[], line_load_assignments=[],
                    embedded_beam_assignments=[], element_materials=[],
                    error=f"{get_error_info(ErrorCode.VAL_MISSING_MATERIAL)} (Polygon {i+1})"
                )
        
        # Check Embedded Beams
        if request.embedded_beams:
            beam_material_ids = {m.id for m in request.beam_materials}
            for i, beam in enumerate(request.embedded_beams):
                if not beam.materialId or beam.materialId not in beam_material_ids:
                    return MeshResponse(
                        success=False, nodes=[], elements=[],
                        boundary_conditions=BoundaryConditionsResponse(full_fixed=[], normal_fixed=[]),
                        point_load_assignments=[], line_load_assignments=[],
                        embedded_beam_assignments=[], element_materials=[],
                        error=f"{get_error_info(ErrorCode.VAL_MISSING_MATERIAL)} (Embedded Beam {i+1})"
                    )

        # --- 1. Geometry Preparation ---
        
        # We need to collect all vertices and segments.
        # We also need to identify regions (materials) and their intended mesh sizes.
        
        all_vertices = []
        all_segments = []
        regions = [] # [x, y, attribute, max_area]
        
        # to avoid O(N^2) linear search.
        # Configuration
        GRID_SIZE = 1e-3
        def snap(val):
            return round(val / GRID_SIZE) * GRID_SIZE

        # Global Mesh Settings
        global_mesh_size = request.mesh_settings.mesh_size if request.mesh_settings else 2.0
        global_refinement = request.mesh_settings.boundary_refinement_factor if request.mesh_settings else 1.0

        # To deduplicate vertices, we use a map with high precision rounding
        # This handles float noise from unary_union without breaking topology
        vertex_hash: Dict[Tuple[float, float], int] = {}
        def get_vertex_index(x, y):
            key = (round(x, 8), round(y, 8))
            if key in vertex_hash:
                return vertex_hash[key]
            new_idx = len(all_vertices)
            all_vertices.append([x, y])
            vertex_hash[key] = new_idx
            return new_idx

        # Process each polygon and snap vertices early to ensure perfect junctions
        material_id_map = {m.id: i for i, m in enumerate(request.materials)}
        
        # Collect all boundary lines (SNAPPED)
        from shapely.ops import unary_union
        from shapely.geometry import LineString, MultiLineString

        boundary_lines = []
        for poly in request.polygons:
            coords = []
            for p in poly.vertices:
                coords.append((snap(p.x), snap(p.y)))
            
            if len(coords) < 3: continue
            
            # Deduplicate sequential snapped points
            clean_coords = []
            for c in coords:
                if not clean_coords or c != clean_coords[-1]:
                    clean_coords.append(c)
            # Close it
            if clean_coords[0] != clean_coords[-1]:
                clean_coords.append(clean_coords[0])
            
            if len(clean_coords) < 4: continue 
            boundary_lines.append(LineString(clean_coords))

        # --- NEW: Include EBR lines in the geometric union ---
        if request.embedded_beams:
            for beam in request.embedded_beams:
                if len(beam.points) < 2: continue
                # Pass through snap() to ensure precision alignment with polygons
                snapped_beam = [(snap(p.x), snap(p.y)) for p in beam.points]
                boundary_lines.append(LineString(snapped_beam))
        
        print("Performing Unary Union (Cleaning boundaries)...", flush=True)
        # unary_union on snapped lines is much more robust
        clean_boundaries = unary_union(boundary_lines)
        print("Boundary cleaning done.", flush=True)
        
        # Flatten to list of LineStrings
        def flatten_geoms(geom):
            if geom.is_empty: return []
            if geom.geom_type in ['LineString', 'LinearRing']: return [geom]
            if hasattr(geom, 'geoms'):
                res = []
                for g in geom.geoms:
                    res.extend(flatten_geoms(g))
                return res
            return []
        
        unioned_lines = flatten_geoms(clean_boundaries)
        
        # Pre-calculate target segment lengths per polygon
        poly_target_lens = []
        MIN_SAFE_LEN = 1e-4
        target_global_len = max(global_mesh_size / max(global_refinement, 0.1), MIN_SAFE_LEN)
        for poly in request.polygons:
            target_ms = poly.mesh_size if poly.mesh_size else global_mesh_size
            ref_f = poly.boundary_refinement_factor if poly.boundary_refinement_factor else global_refinement
            poly_target_lens.append(max(target_ms / max(ref_f, 0.1), MIN_SAFE_LEN))

        # 1. Add Vertices and Segments with Discretization from Cleaned Boundaries
        print(f"Discretizing {len(unioned_lines)} boundary lines with localized refinement...", flush=True)
        
        # Prepare polygon boundaries for fast distance checks
        shapely_polys = [ShapelyPolygon([(snap(p.x), snap(p.y)) for p in poly.vertices]) for poly in request.polygons]
        
        # We need an index of all lines in unioned_lines for later reference
        unioned_segments_path = [] # For debugging
        
        for line in unioned_lines:
            coords = list(line.coords)
            
            # Find the local target length for this specific line
            # We check the midpoint of the entire line against original polygons
            mid_pt = line.interpolate(0.5, normalized=True)
            local_min_len = target_global_len
            
            for p_idx, s_poly in enumerate(shapely_polys):
                # distance to boundary is more robust for shared edges
                if s_poly.boundary.distance(mid_pt) < 1e-3:
                    local_min_len = min(local_min_len, poly_target_lens[p_idx])
            
            for i in range(len(coords) - 1):
                p1_c = coords[i]
                p2_c = coords[i+1]
                
                dx = p2_c[0] - p1_c[0]
                dy = p2_c[1] - p1_c[1]
                dist = np.sqrt(dx*dx + dy*dy)
                
                if dist < 1e-8: continue 
                
                # Use local_min_len for this specific boundary segment
                n_segs = min(max(1, int(np.ceil(dist / local_min_len))), 1000)
                
                prev_idx = get_vertex_index(p1_c[0], p1_c[1])
                for j in range(1, n_segs + 1):
                    t = j / n_segs
                    if j == n_segs:
                        curr_x, curr_y = p2_c[0], p2_c[1]
                    else:
                        curr_x = p1_c[0] + t * dx
                        curr_y = p1_c[1] + t * dy
                    
                    curr_idx = get_vertex_index(curr_x, curr_y)
                    if prev_idx != curr_idx:
                        seg = tuple(sorted((prev_idx, curr_idx)))
                        all_segments.append(seg)
                    prev_idx = curr_idx

        # 2. Define Regions (Materials) - Still using original polygons for point-in-poly
        print(f"Defining {len(request.polygons)} regions...", flush=True)
        from shapely.ops import split
        from shapely.geometry import LineString, MultiLineString

        # --- NEW: Aggressive Pre-splitting of Polygons by EBR lines ---
        # This ensuring the EBR becomes a physical edge of the soil layers.
        refined_polygons_geoms = [] # List of (ShapelyPolygon, original_metadata_dict)
        
        beam_geoms = []
        if request.embedded_beams:
            for beam in request.embedded_beams:
                if len(beam.points) < 2: continue
                # Snap beams to match polygon vertices
                coords = [(snap(p.x), snap(p.y)) for p in beam.points]
                beam_geoms.append(LineString(coords))
        
        # We need a union of all beams to split polygons in one go or sequentially
        merged_beams = MultiLineString(beam_geoms) if beam_geoms else None
        
        for p_idx, poly in enumerate(request.polygons):
            coords = [(snap(v.x), snap(v.y)) for v in poly.vertices]
            if not coords: continue
            if coords[0] != coords[-1]: coords.append(coords[0])
            s_poly = ShapelyPolygon(coords)
            
            meta = {
                "materialId": poly.materialId,
                "mesh_size": poly.mesh_size if poly.mesh_size else global_mesh_size,
                "refinement": poly.boundary_refinement_factor if poly.boundary_refinement_factor else global_refinement,
                "original_idx": p_idx
            }
            
            # Split this polygon by ALL beams
            parts = [s_poly]
            if merged_beams:
                try:
                    # split() returns a GeometryCollection
                    split_res = split(s_poly, merged_beams)
                    parts = [g for g in split_res.geoms if g.geom_type == 'Polygon']
                except:
                    parts = [s_poly]
            
            for part in parts:
                refined_polygons_geoms.append((part, meta))

        # Now redraw boundary_lines from these split polygons + structural lines
        boundary_lines = []
        for s_poly, meta in refined_polygons_geoms:
            # External boundary of the sub-polygon
            boundary_lines.append(s_poly.exterior)
            # Support internal holes if any
            for hole in s_poly.interiors:
                boundary_lines.append(hole)
        
        # Also include the beams themselves to ensure segments are added even if they don't split anything
        if beam_geoms:
            boundary_lines.extend(beam_geoms)

        print("Performing Unary Union (Cleaning boundaries)...", flush=True)
        # unary_union on snapped lines is much more robust
        clean_boundaries = unary_union(boundary_lines)
        print("Boundary cleaning done.", flush=True)

        unioned_lines = flatten_geoms(clean_boundaries)

        # 1. Add Vertices and Segments with Discretization
        for line in unioned_lines:
            coords = list(line.coords)
            mid_pt = line.interpolate(0.5, normalized=True)
            local_min_len = target_global_len
            
            # Find the local target length for this specific line from parent polygons
            for part, meta in refined_polygons_geoms:
                if part.boundary.distance(mid_pt) < 1e-3:
                    local_min_len = min(local_min_len, meta["mesh_size"] / max(meta["refinement"], 0.1))

            for i in range(len(coords) - 1):
                p1_c, p2_c = coords[i], coords[i+1]
                dx, dy = p2_c[0] - p1_c[0], p2_c[1] - p1_c[1]
                dist = math.sqrt(dx*dx + dy*dy)
                if dist < 1e-8: continue
                n_segs = max(1, int(math.ceil(dist / local_min_len)))
                
                prev_idx = get_vertex_index(p1_c[0], p1_c[1])
                for j in range(1, n_segs + 1):
                    t = j / n_segs
                    curr_x = p1_c[0] + t * dx if j < n_segs else p2_c[0]
                    curr_y = p1_c[1] + t * dy if j < n_segs else p2_c[1]
                    curr_idx = get_vertex_index(curr_x, curr_y)
                    if prev_idx != curr_idx:
                        all_segments.append(tuple(sorted((prev_idx, curr_idx))))
                    prev_idx = curr_idx

        # --- 2. Generate Graded Interior Steiner Points ---
        # This is the key improvement: instead of relying solely on max_area,
        # we seed the interior with points that follow a distance-based size
        # function, creating smooth Plaxis-like mesh transitions.
        print("Generating graded interior Steiner points...", flush=True)
        
        # Collect ALL boundary sample points (polygon edges + EBR + line loads)
        # for the global distance field
        all_boundary_sample_pts = []
        for v in all_vertices:
            all_boundary_sample_pts.append(v)
        
        # Also densely sample along EBR lines for better distance field
        if request.embedded_beams:
            for beam in request.embedded_beams:
                if len(beam.points) < 2: continue
                for i in range(len(beam.points) - 1):
                    p1 = beam.points[i]
                    p2 = beam.points[i + 1]
                    seg_len = math.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2)
                    n_samples = max(2, int(seg_len / 0.1))
                    for j in range(n_samples + 1):
                        t = j / n_samples
                        sx = p1.x + t * (p2.x - p1.x)
                        sy = p1.y + t * (p2.y - p1.y)
                        all_boundary_sample_pts.append([sx, sy])
        
        boundary_sample_arr = np.array(all_boundary_sample_pts)
        
        total_interior_pts = 0
        for part, meta in refined_polygons_geoms:
            h_min_local = meta["mesh_size"] / max(meta["refinement"], 0.1)
            h_max_local = meta["mesh_size"]
            
            # Grading distance: how far from boundary the transition takes
            # Use ~5x the mesh_size for a smooth transition
            grading_dist = meta["mesh_size"] * 5.0
            
            interior_pts = _generate_graded_interior_points(
                part, boundary_sample_arr,
                h_min_local, h_max_local, grading_dist
            )
            
            for px, py in interior_pts:
                get_vertex_index(px, py)
            
            total_interior_pts += len(interior_pts)
        
        print(f"  Added {total_interior_pts} graded interior points.", flush=True)

        # 3. Define Regions (Materials)
        for part, meta in refined_polygons_geoms:
            inner_pt = part.representative_point()
            rx, ry = round(inner_pt.x, 6), round(inner_pt.y, 6)
            # Use a generous max_area since Steiner points already control local sizing
            max_area = 0.5 * (meta["mesh_size"] ** 2)
            regions.append([rx, ry, float(meta["original_idx"]), max_area])

        # --- NEW: Add Point Load Coordinates to Vertices ---
        # This forces triangle to create a node at exactly these coordinates.
        if request.pointLoads:
            for pl in request.pointLoads:
                get_vertex_index(pl.x, pl.y)
        
        # --- NEW: Add Line Load Coordinates to Vertices and Segments ---
        if request.lineLoads:
            for ll in request.lineLoads:
                v1 = get_vertex_index(ll.x1, ll.y1)
                v2 = get_vertex_index(ll.x2, ll.y2)
                all_segments.append(tuple(sorted((v1, v2))))

        # --- NEW: Explicitly add EBR nodes to ensure they exist ---
        if request.embedded_beams:
            for beam in request.embedded_beams:
                if len(beam.points) < 2: continue
                # We add the vertices first to ensure get_vertex_index is consistent
                for p in beam.points:
                    get_vertex_index(snap(p.x), snap(p.y))

        # --- RE-DISCRETIZATION Check for EBR ---
        # To be absolutely sure, we can also add segments directly between these vertices
        # but ONLY if they don't already exist as part of unioned_lines.
        # Actually, if we use the same get_vertex_index, deduplication set(all_segments) handles it.
        # THE DANGER is overlapping segments (v1-v3) vs (v1-v2)-(v2-v3).
        # Triangle PSLG segments should be non-intersecting and non-overlapping.
        # Since we used unary_union, we should TRUST all_segments created from unioned_lines.

        # Deduplicate segments
        unique_segments = list(set(all_segments))
        
        # --- 2. Triangulation ---
        tri_input = {
            'vertices': np.array(all_vertices),
            'segments': np.array(unique_segments),
            'regions': np.array(regions)
        }
        
        # 'p' = PSLG
        # 'q30' = Quality mesh with min angle 30° (better shaped triangles)
        # 'a' = Area constraints (respect regions max_area)
        # 'A' = Assign attributes to triangles
        mesh_data = triangle.triangulate(tri_input, 'pq30aA')
        print("Triangulation done.", flush=True)
        
        nodes = mesh_data['vertices'].tolist()
        elements_linear = mesh_data['triangles'].tolist()
        
        # Handle empty mesh result
        if not elements_linear:
             return MeshResponse(
                success=False,
                nodes=[],
                elements=[],
                boundary_conditions=BoundaryConditionsResponse(full_fixed=[], normal_fixed=[]),
                point_load_assignments=[],
                line_load_assignments=[],
                element_materials=[],
                error=get_error_info(ErrorCode.VAL_EMPTY_MESH)
            )


        # Transform to 15-node quartic triangles (PLAXIS standard)
        # 1-2-3 Corners
        # 4,5,6 on edge 1-2
        # 7,8,9 on edge 2-3
        # 10,11,12 on edge 3-1
        # 13,14,15 interior
        
        # Track edge nodes to avoid duplicates: edge (min, max) -> [node_idx_a, node_idx_b, node_idx_c]
        # Always stored such that they are ordered from min_node to max_node.
        edge_nodes_map = {}
        current_node_idx = len(nodes)
        
        elements = []  
        
        for elem_linear in elements_linear:
            n1, n2, n3 = elem_linear
            
            def get_edge_nodes(ia, ib):
                nonlocal current_node_idx
                e_key = tuple(sorted([ia, ib]))
                if e_key not in edge_nodes_map:
                    # Always create nodes from min_node -> max_node (canonical direction)
                    pa_canon = np.array(nodes[e_key[0]])
                    pb_canon = np.array(nodes[e_key[1]])
                    # 3 points at 1/4, 2/4, 3/4 from pa_canon to pb_canon
                    p1 = (0.75 * pa_canon + 0.25 * pb_canon).tolist()
                    p2 = (0.50 * pa_canon + 0.50 * pb_canon).tolist()
                    p3 = (0.25 * pa_canon + 0.75 * pb_canon).tolist()
                    
                    indices = [current_node_idx, current_node_idx + 1, current_node_idx + 2]
                    nodes.extend([p1, p2, p3])
                    edge_nodes_map[e_key] = indices
                    current_node_idx += 3
                
                # Retrieve and Orient: stored nodes go from e_key[0] to e_key[1] (min to max)
                res = edge_nodes_map[e_key]
                if ia == e_key[0]:
                    # Requested direction matches canonical (min->max): no flip needed
                    return [res[0], res[1], res[2]]
                else:
                    # Requested direction is reversed (max->min): flip the edge nodes
                    return [res[2], res[1], res[0]]

            # 1. Edge Nodes
            e12 = get_edge_nodes(n1, n2) # nodes 4,5,6
            e23 = get_edge_nodes(n2, n3) # nodes 7,8,9
            e31 = get_edge_nodes(n3, n1) # nodes 10,11,12
            
            # 2. Interior Nodes (13, 14, 15)
            # Typically at (1/2, 1/4, 1/4), (1/4, 1/2, 1/4), (1/4, 1/4, 1/2)
            p1, p2, p3 = np.array(nodes[n1]), np.array(nodes[n2]), np.array(nodes[n3])
            i1 = (0.50 * p1 + 0.25 * p2 + 0.25 * p3).tolist()
            i2 = (0.25 * p1 + 0.50 * p2 + 0.25 * p3).tolist()
            i3 = (0.25 * p1 + 0.25 * p2 + 0.50 * p3).tolist()
            
            in13, in14, in15 = current_node_idx, current_node_idx+1, current_node_idx+2
            nodes.extend([i1, i2, i3])
            current_node_idx += 3
            
            # 3. Assemble Element (PLAXIS 15-node order)
            elements.append([
                n1, n2, n3,             # 1, 2, 3
                e12[0], e12[1], e12[2], # 4, 5, 6
                e23[0], e23[1], e23[2], # 7, 8, 9
                e31[0], e31[1], e31[2], # 10, 11, 12
                in13, in14, in15        # 13, 14, 15
            ])



        # Retrieve element attributes (material indices)
        # triangle returns shape (n, 1), flatten it
        elem_attrs = mesh_data['triangle_attributes'].flatten().tolist()
        
        # --- 3. Post-Processing ---
        
        # A. Element Materials
        element_materials = []
        
        # Build materials map for efficient lookup
        mat_map = {m.id: m for m in request.materials}
        
        for elem_idx, poly_idx_float in enumerate(elem_attrs):
            poly_idx = int(poly_idx_float)
            if 0 <= poly_idx < len(request.polygons):
                 poly = request.polygons[poly_idx]
                 element_materials.append(ElementMaterial(
                     element_id=elem_idx + 1,
                     material=mat_map[poly.materialId],
                     polygon_id=poly_idx
                 ))
        
        # B. Boundary Conditions
        # Detect bounding box
        xs = [n[0] for n in nodes]
        ys = [n[1] for n in nodes]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        tol = 1e-3
        print(f"[MESH] Identifying boundary nodes (tol={tol}). Model bounds: X=[{min_x}, {max_x}], Y=[{min_y}, {max_y}]")
        
        # Boundary Conditions - Hardcode removed. BCs are now dynamic in the Solver.
        full_fixed = []
        normal_fixed = []
        # C. Point Loads
        point_load_assigns = []
        if request.pointLoads and nodes:
            node_arr = np.array(nodes)
            tree = cKDTree(node_arr)
            
            for pl in request.pointLoads:
                # Query nearest node within reasonable distance
                dist, node_idx = tree.query([pl.x, pl.y])
                
                # Check for misalignment
                if dist > 0.1:
                    print(f"WARNING: Point load '{pl.id}' at ({pl.x}, {pl.y}) is {dist:.4f}m away from the nearest node!", flush=True)
                
                point_load_assigns.append(PointLoadAssignment(
                    point_load_id=pl.id,
                    assigned_node_id=int(node_idx) + 1 # FE uses 1-based IDs for nodes in this context
                ))

        # D. Line Loads
        line_load_assigns = []
        from engine.models import LineLoadAssignment
        if request.lineLoads and nodes:
            node_arr = np.array(nodes)
            for ll in request.lineLoads:
                # A line segment (x1,y1) to (x2,y2)
                p1 = np.array([ll.x1, ll.y1])
                p2 = np.array([ll.x2, ll.y2])
                line_vec = p2 - p1
                line_len = np.linalg.norm(line_vec)
                if line_len < 1e-9: continue
                line_unit = line_vec / line_len
                
                for el_idx, el in enumerate(elements):
                    # Check each of the 3 main edges for quadratic triangle: (n1-n2), (n2-n3), (n3-n1)
                    # Node indices are: n1=el[0], n2=el[1], n3=el[2], n12=el[3], n23=el[4], n31=el[5]
                    # T15 Elements have 5 nodes per edge: 2 corners + 3 midsides
                    edges = [
                        (el[0], el[1], [el[3], el[4], el[5]]), # Edge 1-2
                        (el[1], el[2], [el[6], el[7], el[8]]), # Edge 2-3
                        (el[2], el[0], [el[9], el[10], el[11]])# Edge 3-1
                    ]
                    
                    for na, nb, mids in edges:
                        pa, pb = node_arr[na], node_arr[nb]
                        pm_list = [node_arr[m] for m in mids]
                        
                        def is_on_segment(p, p1, p2, tol=1e-3):
                            v = p - p1
                            proj = np.dot(v, line_unit)
                            if proj < -tol or proj > line_len + tol: return False
                            dist = np.linalg.norm(v - proj * line_unit)
                            return dist < tol
                        
                        # Verify all 5 nodes are on segment
                        if is_on_segment(pa, p1, p2) and is_on_segment(pb, p1, p2) and all(is_on_segment(pm, p1, p2) for pm in pm_list):
                            edge_node_ids = [int(na)+1, int(nb)+1] + [int(m)+1 for m in mids]
                            line_load_assigns.append(LineLoadAssignment(
                                line_load_id=ll.id,
                                element_id=el_idx + 1,
                                edge_nodes=edge_node_ids
                            ))

        # E. Embedded Beams
        embedded_beam_assigns = []
        from engine.models import EmbeddedBeamAssignment
        if request.embedded_beams and nodes:
            node_arr = np.array(nodes)
            for beam in request.embedded_beams:
                beam_nodes = []
                if len(beam.points) < 2: continue
                
                # For each segment of the beam chain
                for i in range(len(beam.points) - 1):
                    p_start = np.array([beam.points[i].x, beam.points[i].y])
                    p_end = np.array([beam.points[i+1].x, beam.points[i+1].y])
                    
                    segment_vec = p_end - p_start
                    segment_len = np.linalg.norm(segment_vec)
                    if segment_len < 1e-9: continue
                    segment_unit = segment_vec / segment_len
                    
                    # Find all nodes lying on this segment
                    segment_node_indices = []
                    for n_idx, n_coords in enumerate(node_arr):
                        # Use is_on_segment logic
                        p = np.array(n_coords)
                        v = p - p_start
                        proj = np.dot(v, segment_unit)
                        if proj < -1e-4 or proj > segment_len + 1e-4: continue
                        dist = np.linalg.norm(v - proj * segment_unit)
                        if dist < 1e-4:
                            segment_node_indices.append((n_idx, proj))
                    
                    # Sort nodes by distance from start of segment
                    segment_node_indices.sort(key=lambda x: x[1])
                    
                    # Add to beam_nodes (deduplicating if needed, though sequential segments share end/start)
                    for n_idx, _ in segment_node_indices:
                        if not beam_nodes or beam_nodes[-1] != n_idx + 1:
                            beam_nodes.append(n_idx + 1) # 1-based
                
                if len(beam_nodes) > 1:
                    embedded_beam_assigns.append(EmbeddedBeamAssignment(
                        beam_id=beam.id,
                        nodes=beam_nodes
                    ))

        return MeshResponse(
            success=True,
            nodes=nodes,
            elements=elements,
            boundary_conditions=BoundaryConditionsResponse(
                full_fixed=full_fixed,
                normal_fixed=normal_fixed
            ),
            point_load_assignments=point_load_assigns,
            line_load_assignments=line_load_assigns,
            embedded_beam_assignments=embedded_beam_assigns,
            element_materials=element_materials
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return MeshResponse(
            success=False,
            nodes=[],
            elements=[],
            boundary_conditions=BoundaryConditionsResponse(full_fixed=[], normal_fixed=[]),
            point_load_assignments=[],
            line_load_assignments=[],
            embedded_beam_assignments=[],
            element_materials=[],
            error=f"{get_error_info(ErrorCode.SYS_INTERNAL_ERROR)} | Raw: {str(e)}"
        )
