import numpy as np
import triangle
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
        
        # To deduplicate vertices, we use a map and distance check
        # Previously used round(x,6) which is too strict for manual inputs.
        # Now using linear search with tolerance 1e-3 (1mm).
        # For typical boundary node counts (<1000), this is fast enough.
        vertex_indices: List[Tuple[float, float, int]] = [] 
        TOLERANCE = 1e-3 
        
        def get_vertex_index(x, y):
            # Check existing vertices
            for vx, vy, v_idx in vertex_indices:
                dist_sq = (x - vx)**2 + (y - vy)**2
                if dist_sq < TOLERANCE**2:
                    return v_idx
            
            # New vertex
            new_idx = len(all_vertices)
            all_vertices.append([x, y])
            vertex_indices.append((x, y, new_idx))
            return new_idx

        # Process each polygon
        material_id_map = {m.id: i for i, m in enumerate(request.materials)}
        
        # Global Mesh Settings (Fallback)
        global_mesh_size = request.mesh_settings.mesh_size if request.mesh_settings else 2.0
        global_refinement = request.mesh_settings.boundary_refinement_factor if request.mesh_settings else 1.0

        for poly_idx, poly in enumerate(request.polygons):
            # Calculate parameters: Use polygon-specific OR global fallback
            target_mesh_size = poly.mesh_size if poly.mesh_size else global_mesh_size
            refinement_factor = poly.boundary_refinement_factor if poly.boundary_refinement_factor else global_refinement
            
            # Target segment length for boundaries
            target_seg_len = target_mesh_size / max(refinement_factor, 0.1)
            # Max area for triangle (Area = sqrt(3)/4 * side^2 for equilateral)
            max_area = 0.5 * (target_mesh_size ** 2)
            
            poly_pts = poly.vertices
            num_pts = len(poly_pts)
            
            # 1. Add Vertices and Segments with Discretization
            for i in range(num_pts):
                p1 = poly_pts[i]
                p2 = poly_pts[(i + 1) % num_pts]
                
                # Calculate distance
                dx = p2.x - p1.x
                dy = p2.y - p1.y
                dist = np.sqrt(dx*dx + dy*dy)
                
                # Number of subdivisions
                n_segs = max(1, int(np.ceil(dist / target_seg_len)))
                
                # Generate points along the edge
                prev_idx = get_vertex_index(p1.x, p1.y)
                
                for j in range(1, n_segs + 1):
                    t = j / n_segs
                    # If it's the last point, it's p2
                    if j == n_segs:
                        curr_x, curr_y = p2.x, p2.y
                    else:
                        curr_x = p1.x + t * dx
                        curr_y = p1.y + t * dy
                    
                    curr_idx = get_vertex_index(curr_x, curr_y)
                    
                    # Add segment (order doesn't matter for undirected graph)
                    # Use frozenset or sorted tuple to deduplicate boundaries shared by polygons
                    # Actually triangle handles duplicate segments fine usually, or we can dedup.
                    # We'll just add them raw for now, triangle ignores dupes or we can cleaner approach.
                    # Better to dedup to avoid warnings.
                    seg = tuple(sorted((prev_idx, curr_idx)))
                    all_segments.append(seg)
                    
                    prev_idx = curr_idx

            # 2. Define Region Attribute (Material) and Area Constraint
            # Find a point inside the polygon
            shapely_poly = ShapelyPolygon([(p.x, p.y) for p in poly_pts])
            # representative_point is guaranteed to be within the polygon
            inner_pt = shapely_poly.representative_point()
            
            mat_idx = 0
            if poly.materialId in material_id_map:
                mat_idx = material_id_map[poly.materialId]
            
            # Attribute is float in triangle, we'll store poly_idx
            # Region: [x, y, attribute, max_area]
            regions.append([inner_pt.x, inner_pt.y, float(poly_idx), max_area])

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
            element_materials=[],
            error=f"{get_error_info(ErrorCode.SYS_INTERNAL_ERROR)} | Raw: {str(e)}"
        )
