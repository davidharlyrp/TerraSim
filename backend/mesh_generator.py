import numpy as np
import triangle
import math
from typing import List, Dict, Tuple, Optional
from shapely.geometry import Polygon as ShapelyPolygon, Point as ShapelyPoint
from scipy.spatial import cKDTree
from backend.models import MeshRequest, MeshResponse, BoundaryConditionsResponse, BoundaryCondition, PointLoadAssignment, ElementMaterial
from backend.error import ErrorCode, get_error_info

def generate_mesh(request: MeshRequest) -> MeshResponse:
    try:
        # --- 1. Geometry Preparation ---
        
        # We need to collect all vertices and segments.
        # We also need to identify regions (materials) and their intended mesh sizes.
        
        # Global collections
        all_vertices = []
        all_segments = []
        regions = [] # [x, y, attribute, max_area]
        
        # To deduplicate vertices, we use a spatial hash (grid-based dictionary)
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
        
        print("Performing Unary Union (Cleaning boundaries)...", flush=True)
        # unary_union on snapped lines is much more robust
        clean_boundaries = unary_union(boundary_lines)
        print("Boundary cleaning done.", flush=True)
        
        # Flatten to list of LineStrings
        def flatten_geoms(geom):
            if geom.is_empty: return []
            if geom.geom_type == 'LineString': return [geom]
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

        # Collect EBR lines for splitting polygons
        beam_geoms = []
        if request.embedded_beams:
            for beam in request.embedded_beams:
                if len(beam.points) < 2: continue
                for i in range(len(beam.points) - 1):
                    p1, p2 = beam.points[i], beam.points[i+1]
                    beam_geoms.append(LineString([(p1.x, p1.y), (p2.x, p2.y)]))
        
        merged_beams = MultiLineString(beam_geoms) if beam_geoms else None

        for poly_idx, poly in enumerate(request.polygons):
            coords = [(v.x, v.y) for v in poly.vertices]
            if not coords: continue
            if coords[0] != coords[-1]: coords.append(coords[0])
            shapely_poly = ShapelyPolygon(coords)
            if shapely_poly.is_empty: continue
            
            target_mesh_size = poly.mesh_size if poly.mesh_size else global_mesh_size
            max_area = 0.5 * (target_mesh_size ** 2)
            MIN_AREA = 1e-4 
            if max_area < MIN_AREA:
                max_area = MIN_AREA

            # If beams exist, split the polygon to ensure every "part" gets a region point
            parts = [shapely_poly]
            if merged_beams:
                try:
                    split_result = split(shapely_poly, merged_beams)
                    parts = [g for g in split_result.geoms if g.geom_type == 'Polygon']
                    if not parts: parts = [shapely_poly]
                except Exception as e:
                    print(f"Warning: split failed for poly {poly_idx}: {e}", flush=True)
                    parts = [shapely_poly]

            for part in parts:
                inner_pt = part.representative_point()
                # Round to improve symmetry
                rx, ry = round(inner_pt.x, 6), round(inner_pt.y, 6)
                regions.append([rx, ry, float(poly_idx), max_area])
                print(f"  Region {poly_idx} part: at ({rx:.2f}, {ry:.2f}), max_area={max_area:.4f}", flush=True)

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
        
        # --- NEW: Add Embedded Beam Segments to Vertices and Segments ---
        if request.embedded_beams:
            for beam in request.embedded_beams:
                if len(beam.points) < 2: continue
                for i in range(len(beam.points) - 1):
                    p1, p2 = beam.points[i], beam.points[i+1]
                    
                    dx = p2.x - p1.x
                    dy = p2.y - p1.y
                    dist = math.sqrt(dx*dx + dy*dy)
                    
                    num_sub = 1
                    if global_mesh_size > 0:
                        num_sub = max(1, math.ceil(dist / global_mesh_size))
                    
                    last_v = get_vertex_index(p1.x, p1.y)
                    for s in range(1, num_sub + 1):
                        px = p1.x + dx * (s / num_sub)
                        py = p1.y + dy * (s / num_sub)
                        curr_v = get_vertex_index(px, py)
                        all_segments.append(tuple(sorted((last_v, curr_v))))
                        last_v = curr_v

        # Deduplicate segments
        unique_segments = list(set(all_segments))
        
        # --- 2. Triangulation ---
        tri_input = {
            'vertices': np.array(all_vertices),
            'segments': np.array(unique_segments),
            'regions': np.array(regions)
        }
        
        # 'p' = PSLG
        # 'q' = Quality mesh (min angle 20)
        # 'a' = Area constraints (respect regions max_area)
        # 'A' = Assign attributes to triangles
        mesh_data = triangle.triangulate(tri_input, 'pqaA')
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


        # Transform to 6-node quadratic triangles
        # Standard ordering: [n1, n2, n3, n12, n23, n31]
        # where n12 = midpoint of edge 1-2, n23 = midpoint of edge 2-3, n31 = midpoint of edge 3-1
        # This corresponds to standard numbering: [1, 2, 3, 6, 4, 5]
        
        # Track edge midpoints to avoid duplicates: edge (min, max) -> midpoint_node_index
        edge_midpoint_map = {}
        current_node_idx = len(nodes)
        
        elements = []  # Will store 6-node elements
        
        for elem_linear in elements_linear:
            n1, n2, n3 = elem_linear
            
            # Get or create midpoint nodes for each edge
            # IMPORTANT: We need to get the midpoint index regardless of sort order
            
            # Edge 1-2 (midpoint goes to position 3 in the 6-node element)
            edge_12 = tuple(sorted([n1, n2]))
            if edge_12 not in edge_midpoint_map:
                p1, p2 = nodes[n1], nodes[n2]
                mid_12 = [(p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0]
                nodes.append(mid_12)
                edge_midpoint_map[edge_12] = current_node_idx
                current_node_idx += 1
            n12 = edge_midpoint_map[edge_12]
            
            # Edge 2-3 (midpoint goes to position 4 in the 6-node element)
            edge_23 = tuple(sorted([n2, n3]))
            if edge_23 not in edge_midpoint_map:
                p2, p3 = nodes[n2], nodes[n3]
                mid_23 = [(p2[0] + p3[0]) / 2.0, (p2[1] + p3[1]) / 2.0]
                nodes.append(mid_23)
                edge_midpoint_map[edge_23] = current_node_idx
                current_node_idx += 1
            n23 = edge_midpoint_map[edge_23]
            
            # Edge 3-1 (midpoint goes to position 5 in the 6-node element)
            edge_31 = tuple(sorted([n3, n1]))
            if edge_31 not in edge_midpoint_map:
                p3, p1 = nodes[n3], nodes[n1]
                mid_31 = [(p3[0] + p1[0]) / 2.0, (p3[1] + p1[1]) / 2.0]
                nodes.append(mid_31)
                edge_midpoint_map[edge_31] = current_node_idx
                current_node_idx += 1
            n31 = edge_midpoint_map[edge_31]
            
            # Create 6-node element with standard ordering: [n1, n2, n3, n12, n23, n31]
            elements.append([n1, n2, n3, n12, n23, n31])



        # Retrieve element attributes (material indices)
        # triangle returns shape (n, 1), flatten it
        elem_attrs = mesh_data['triangle_attributes'].flatten().tolist()
        
        # --- 3. Post-Processing ---
        
        # A. Element Materials
        element_materials = []
        # Reverse map for materials
        materials_list = request.materials
        
        for elem_idx, poly_idx_float in enumerate(elem_attrs):
            poly_idx = int(poly_idx_float)
            if 0 <= poly_idx < len(request.polygons):
                 poly = request.polygons[poly_idx]
                 element_materials.append(ElementMaterial(
                     element_id=elem_idx + 1, # FE expects 1-based
                     material=next(m for m in materials_list if m.id == poly.materialId),
                     polygon_id=poly_idx
                 ))
        
        # B. Boundary Conditions
        # Detect bounding box
        xs = [n[0] for n in nodes]
        ys = [n[1] for n in nodes]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        tol = 1e-3
        
        full_fixed = []
        normal_fixed = []
        
        for i, node in enumerate(nodes):
            nx, ny = node[0], node[1]
            
            is_min_y = abs(ny - min_y) < tol
            is_min_x = abs(nx - min_x) < tol
            is_max_x = abs(nx - max_x) < tol
            
            # Bottom -> Full Fixed
            if is_min_y:
                full_fixed.append(BoundaryCondition(node=i)) # Send 0-based
            # Sides -> Normal Fixed (Roller)
            elif is_min_x or is_max_x:
                normal_fixed.append(BoundaryCondition(node=i)) # Send 0-based
        
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
        from backend.models import LineLoadAssignment
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
                    edges = [
                        (el[0], el[1], el[3]), # Edge 1-2, midpoint n12
                        (el[1], el[2], el[4]), # Edge 2-3, midpoint n23
                        (el[2], el[0], el[5])  # Edge 3-1, midpoint n31
                    ]
                    
                    for na, nb, nm in edges:
                        pa, pb, pm = node_arr[na], node_arr[nb], node_arr[nm]
                        
                        # Check if both endpoints and midpoint lie on the line segment
                        def is_on_segment(p, p1, p2, tol=1e-3):
                            v = p - p1
                            proj = np.dot(v, line_unit)
                            if proj < -tol or proj > line_len + tol: return False
                            dist = np.linalg.norm(v - proj * line_unit)
                            return dist < tol
                        
                        if is_on_segment(pa, p1, p2) and is_on_segment(pb, p1, p2) and is_on_segment(pm, p1, p2):
                            line_load_assigns.append(LineLoadAssignment(
                                line_load_id=ll.id,
                                element_id=el_idx + 1,
                                edge_nodes=[int(na)+1, int(nb)+1, int(nm)+1]
                            ))

        # E. Embedded Beams
        embedded_beam_assigns = []
        from backend.models import EmbeddedBeamAssignment
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
