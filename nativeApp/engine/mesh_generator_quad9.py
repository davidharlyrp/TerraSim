"""
Gmsh-based Quad9 mesh generator for TerraSim nativeApp.

Produces 9-node quadrilateral elements (Gmsh type 10) with optional:
- custom_overrides (transfinite boundary progression)
- adaptive refinement toward point/line loads (Distance + Threshold fields)
- refinement toward embedded beam (EBR) lines
"""
from __future__ import annotations

import math
import threading
from typing import Dict, List, Optional, Tuple

import gmsh
import numpy as np
from matplotlib.path import Path as MplPath
from scipy.spatial import cKDTree
from shapely.geometry import LineString, MultiLineString, Polygon as ShapelyPolygon
from shapely.ops import split

from engine.error import ErrorCode, get_error_info
from engine.models import (
    BoundaryMeshOverride,
    ElementMaterial,
    EmbeddedBeamAssignment,
    LineLoadAssignment,
    MeshElementType,
    MeshRequest,
    MeshResponse,
    PointLoadAssignment,
    BoundaryConditionsResponse,
)
from engine.solver.element_quad9 import compute_b_matrix

# Permutation to reverse Quad9 winding when det(J) < 0 (Gmsh can emit either orientation).
_QUAD9_FLIP_PERM = (0, 3, 2, 1, 7, 6, 5, 4, 8)


GRID_SIZE = 1e-3
_gmsh_lock = threading.Lock()


def _gmsh_init() -> None:
    """Initialize Gmsh without SIGINT handler (safe inside QThread workers)."""
    if gmsh.isInitialized():
        return
    gmsh.initialize([], readConfigFiles=False, run=False, interruptible=False)


def _gmsh_shutdown() -> None:
    if gmsh.isInitialized():
        gmsh.finalize()


def _snap(val: float) -> float:
    return round(val / GRID_SIZE) * GRID_SIZE


def _orient_quad9_indices(nodes: List[List[float]], indices: List[int]) -> List[int]:
    """Ensure counter-clockwise Quad9 connectivity (positive det(J) at element center)."""
    coords = np.array([nodes[i] for i in indices], dtype=float)
    _, det_j = compute_b_matrix(coords, 0.0, 0.0)
    if det_j < 0.0:
        return [indices[i] for i in _QUAD9_FLIP_PERM]
    return indices


def _split_polygons_by_ebr(request: MeshRequest) -> List[Tuple[ShapelyPolygon, dict]]:
    """Split polygons along embedded beams; return (geometry, metadata) parts."""
    global_mesh_size = request.mesh_settings.mesh_size if request.mesh_settings else 2.0
    global_refinement = (
        request.mesh_settings.boundary_refinement_factor if request.mesh_settings else 1.0
    )

    beam_geoms = []
    if request.embedded_beams:
        for beam in request.embedded_beams:
            if len(beam.points) < 2:
                continue
            coords = [(_snap(p.x), _snap(p.y)) for p in beam.points]
            beam_geoms.append(LineString(coords))
    merged_beams = MultiLineString(beam_geoms) if beam_geoms else None

    refined: List[Tuple[ShapelyPolygon, dict]] = []
    for p_idx, poly in enumerate(request.polygons):
        coords = [(_snap(v.x), _snap(v.y)) for v in poly.vertices]
        if len(coords) < 3:
            continue
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        s_poly = ShapelyPolygon(coords)
        meta = {
            "materialId": poly.materialId,
            "mesh_size": poly.mesh_size if poly.mesh_size else global_mesh_size,
            "refinement": (
                poly.boundary_refinement_factor
                if poly.boundary_refinement_factor
                else global_refinement
            ),
            "original_idx": p_idx,
        }
        parts = [s_poly]
        if merged_beams:
            try:
                split_res = split(s_poly, merged_beams)
                parts = [g for g in split_res.geoms if g.geom_type == "Polygon"]
            except Exception:
                parts = [s_poly]
        for part in parts:
            refined.append((part, meta))
    return refined


def _build_boundary_adjustments(
    request: MeshRequest,
) -> Dict[str, dict]:
    """Convert BoundaryMeshOverride list to {name: {point_start, point_end, num_elements, bias}}."""
    adjustments: Dict[str, dict] = {}
    if not request.custom_overrides:
        return adjustments

    for i, ov in enumerate(request.custom_overrides):
        if ov.polygon_index < 0 or ov.polygon_index >= len(request.polygons):
            continue
        poly = request.polygons[ov.polygon_index]
        verts = poly.vertices
        n = len(verts)
        if n < 2:
            continue
        vs = ov.vertex_start % n
        ve = ov.vertex_end % n
        p_start = verts[vs]
        p_end = verts[ve]
        adjustments[f"override_{i}"] = {
            "point_start": [p_start.x, p_start.y],
            "point_end": [p_end.x, p_end.y],
            "num_elements": ov.num_elements,
            "bias": ov.bias,
        }
    return adjustments


def _curve_length(line_tag: int) -> float:
    try:
        return float(gmsh.model.occ.getMass(1, line_tag))
    except Exception:
        return 0.0


def _even_element_count(length: float, mesh_size: float, minimum: int = 2) -> int:
    """Quad9 needs an even number of 1D elements on every curve (for order-2 nodes)."""
    h = max(mesh_size, 1e-6)
    n_elem = max(minimum, int(math.ceil(length / h)))
    if n_elem % 2 != 0:
        n_elem += 1
    return n_elem


def _apply_transfinite_overrides(
    all_lines, boundary_adjustments: Dict[str, dict]
) -> set[int]:
    """Apply custom edge sizing; return set of curve tags already configured."""
    configured: set[int] = set()
    for adj in boundary_adjustments.values():
        p_start = np.array(adj["point_start"])
        p_end = np.array(adj["point_end"])
        n_elements = int(adj["num_elements"])
        if n_elements % 2 != 0:
            n_elements += 1
        n_points = n_elements + 1  # odd node count on edge (required for Quad9)
        bias = float(adj["bias"])

        for _dim, line_tag in all_lines:
            bnd_nodes = gmsh.model.getBoundary([(1, line_tag)], combined=False, oriented=False)
            c1 = np.array(gmsh.model.getValue(0, bnd_nodes[0][1], [])[:2])
            c2 = np.array(gmsh.model.getValue(0, bnd_nodes[1][1], [])[:2])
            if (
                (np.allclose(c1, p_start, atol=1e-3) and np.allclose(c2, p_end, atol=1e-3))
                or (np.allclose(c2, p_start, atol=1e-3) and np.allclose(c1, p_end, atol=1e-3))
            ):
                gmsh.model.mesh.setTransfiniteCurve(
                    line_tag, n_points, meshType="Progression", coef=bias
                )
                configured.add(line_tag)
                break
    return configured


def _apply_even_transfinite_all_curves(
    all_lines, mesh_size: float, skip_tags: set[int] | None = None
) -> None:
    """
    Force an even 1D element count on every curve so Quad9 (order 2) can be built.
    Skips curves already set via custom_overrides.
    """
    skip = skip_tags or set()
    for _dim, line_tag in all_lines:
        if line_tag in skip:
            continue
        length = _curve_length(line_tag)
        if length < 1e-9:
            continue
        n_elem = _even_element_count(length, mesh_size)
        n_points = n_elem + 1
        try:
            gmsh.model.mesh.setTransfiniteCurve(line_tag, n_points)
        except Exception:
            pass


def _setup_attractor_field(
    layers_coords: List[List[List[float]]],
    max_element_size: float,
    attractor_point_tags: List[int],
    attractor_curve_tags: List[int],
    dist_min: float = 0.3,
    dist_max_ratio: float = 0.6,
    h_min_ratio: float = 0.25,
) -> None:
    if not attractor_point_tags and not attractor_curve_tags:
        return

    all_coords = []
    for coords in layers_coords:
        all_coords.extend(coords)
    arr = np.array(all_coords)
    domain_diag = float(np.linalg.norm(arr.max(axis=0) - arr.min(axis=0)))
    if domain_diag < 1e-6:
        domain_diag = max_element_size * 10.0

    f_dist = gmsh.model.mesh.field.add("Distance")
    if attractor_point_tags:
        gmsh.model.mesh.field.setNumbers(f_dist, "PointsList", attractor_point_tags)
    if attractor_curve_tags:
        gmsh.model.mesh.field.setNumbers(f_dist, "CurvesList", attractor_curve_tags)

    h_min = max_element_size * h_min_ratio
    h_max = max_element_size
    dist_max = domain_diag * dist_max_ratio

    f_thresh = gmsh.model.mesh.field.add("Threshold")
    gmsh.model.mesh.field.setNumber(f_thresh, "InField", f_dist)
    gmsh.model.mesh.field.setNumber(f_thresh, "SizeMin", h_min)
    gmsh.model.mesh.field.setNumber(f_thresh, "SizeMax", h_max)
    gmsh.model.mesh.field.setNumber(f_thresh, "DistMin", dist_min)
    gmsh.model.mesh.field.setNumber(f_thresh, "DistMax", dist_max)
    gmsh.model.mesh.field.setAsBackgroundMesh(f_thresh)

    gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)


def _find_point_tags(target_coords: List[List[float]], atol: float = 1e-3) -> List[int]:
    point_tags: List[int] = []
    for lc in target_coords:
        target = np.array(lc)
        for _dim, pt_tag in gmsh.model.getEntities(0):
            coord = np.array(gmsh.model.getValue(0, pt_tag, [])[:2])
            if np.allclose(coord, target, atol=atol) and pt_tag not in point_tags:
                point_tags.append(pt_tag)
                break
    return point_tags


def _find_curve_tags_on_segments(
    segments: List[Tuple[List[float], List[float]]], atol: float = 1e-3
) -> List[int]:
    curve_tags: List[int] = []
    all_lines = gmsh.model.getEntities(1)

    def _on_segment(p, a, b, tol=atol):
        v = b - a
        seg_len = np.linalg.norm(v)
        if seg_len < 1e-10:
            return np.linalg.norm(p - a) < tol
        d = v / seg_len
        t = float(np.dot(p - a, d))
        if t < -tol or t > seg_len + tol:
            return False
        return np.linalg.norm(p - (a + t * d)) < tol

    for start, end in segments:
        a = np.array(start)
        b = np.array(end)
        for _dim, l_tag in all_lines:
            bnd = gmsh.model.getBoundary([(1, l_tag)], combined=False, oriented=False)
            if len(bnd) != 2:
                continue
            c1 = np.array(gmsh.model.getValue(0, bnd[0][1], [])[:2])
            c2 = np.array(gmsh.model.getValue(0, bnd[1][1], [])[:2])
            if _on_segment(c1, a, b) and _on_segment(c2, a, b):
                if l_tag not in curve_tags:
                    curve_tags.append(l_tag)
    return curve_tags


def _run_gmsh_quad9(
    layers_data: List[dict],
    boundary_adjustments: Dict[str, dict],
    nodal_forces: List[dict],
    line_loads_gmsh: List[dict],
    request: MeshRequest,
    global_mesh_size: float,
    load_refine: bool,
    ebr_refine: bool,
) -> Tuple[Dict, Dict[int, List[List[int]]], set]:
    """
    Run full Gmsh pipeline. Must be called under _gmsh_lock (MeshWorker thread-safe).
    Returns (all_nodes_dict, elements_by_part, active_node_tags).
    """
    _gmsh_init()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("TerraSim_Quad9")
        factory = gmsh.model.occ

        surface_tags = []
        layers_coords_for_field: List[List[List[float]]] = []
        for layer in layers_data:
            coords = layer["coords"]
            layers_coords_for_field.append(coords)
            point_tags = []
            for pt in coords:
                point_tags.append(factory.addPoint(pt[0], pt[1], 0.0))
            line_tags = []
            num_pts = len(point_tags)
            for i in range(num_pts):
                line_tags.append(
                    factory.addLine(point_tags[i], point_tags[(i + 1) % num_pts])
                )
            cl_tag = factory.addCurveLoop(line_tags)
            s_tag = factory.addPlaneSurface([cl_tag])
            surface_tags.append((2, s_tag))

        factory.fragment(surface_tags, [])
        factory.synchronize()

        embed_tools = []
        load_point_coords: List[List[float]] = []
        load_line_segments: List[Tuple[List[float], List[float]]] = []

        for force in nodal_forces:
            coord = force["coord"]
            p_tag = factory.addPoint(coord[0], coord[1], 0.0)
            embed_tools.append((0, p_tag))
            load_point_coords.append(coord)

        for ll in line_loads_gmsh:
            # Embed endpoints only — embedding the 1D line often creates a single
            # segment edge that cannot be promoted to Quad9 (order 2).
            p1 = factory.addPoint(ll["start"][0], ll["start"][1], 0.0)
            p2 = factory.addPoint(ll["end"][0], ll["end"][1], 0.0)
            embed_tools.append((0, p1))
            embed_tools.append((0, p2))
            load_point_coords.append(ll["start"])
            load_point_coords.append(ll["end"])
            load_line_segments.append((ll["start"], ll["end"]))

        ebr_line_segments: List[Tuple[List[float], List[float]]] = []
        if request.embedded_beams:
            for beam in request.embedded_beams:
                if len(beam.points) < 2:
                    continue
                for i in range(len(beam.points) - 1):
                    a = [_snap(beam.points[i].x), _snap(beam.points[i].y)]
                    b = [_snap(beam.points[i + 1].x), _snap(beam.points[i + 1].y)]
                    p1 = factory.addPoint(a[0], a[1], 0.0)
                    p2 = factory.addPoint(b[0], b[1], 0.0)
                    embed_tools.append((0, p1))
                    embed_tools.append((0, p2))
                    ebr_line_segments.append((a, b))

        if embed_tools:
            current_surfaces = gmsh.model.getEntities(2)
            factory.fragment(current_surfaces, embed_tools)
            factory.synchronize()

        all_surfaces = gmsh.model.getEntities(2)
        all_lines = gmsh.model.getEntities(1)

        configured_curves: set[int] = set()
        if boundary_adjustments:
            configured_curves = _apply_transfinite_overrides(all_lines, boundary_adjustments)
            factory.synchronize()

        # All remaining 1D curves must have an even division count for Quad9
        _apply_even_transfinite_all_curves(
            all_lines, global_mesh_size, skip_tags=configured_curves
        )

        has_loads = load_refine and (nodal_forces or line_loads_gmsh)
        has_ebr = ebr_refine and bool(ebr_line_segments)

        if has_loads or has_ebr:
            pt_coords = list(load_point_coords)
            seg_list = list(load_line_segments)
            for seg in ebr_line_segments:
                pt_coords.extend([seg[0], seg[1]])
                seg_list.append(seg)
            attractor_pts = _find_point_tags(pt_coords)
            attractor_curves = _find_curve_tags_on_segments(seg_list)
            _setup_attractor_field(
                layers_coords_for_field,
                global_mesh_size,
                attractor_pts,
                attractor_curves,
            )

        for dim, s_tag in all_surfaces:
            gmsh.model.mesh.setRecombine(dim, s_tag)

        gmsh.option.setNumber("Mesh.Algorithm", 8)
        gmsh.option.setNumber("Mesh.RecombineAll", 1)
        gmsh.option.setNumber("Mesh.RecombinationAlgorithm", 3)
        gmsh.option.setNumber("Mesh.RecombineMinimumQuality", 0.0)
        gmsh.option.setNumber("Mesh.SubdivisionAlgorithm", 0)
        gmsh.option.setNumber("Mesh.Smoothing", 40)
        gmsh.option.setNumber("Mesh.MeshSizeMax", global_mesh_size)
        # Generate Quad9 directly (order 2). Avoid setOrder(2) after the fact —
        # it fails when any 1D edge has an odd number of linear segments.
        gmsh.option.setNumber("Mesh.ElementOrder", 2)
        gmsh.option.setNumber("Mesh.SecondOrderLinear", 0)
        gmsh.option.setNumber("Mesh.HighOrderOptimize", 0)
        gmsh.model.mesh.generate(2)

        node_tags, node_coords, _ = gmsh.model.mesh.getNodes()
        all_nodes_dict = {
            tag: [node_coords[3 * i], node_coords[3 * i + 1]]
            for i, tag in enumerate(node_tags)
        }

        elements_by_part: Dict[int, List[List[int]]] = {
            layer["id"]: [] for layer in layers_data
        }
        active_node_tags: set = set()

        for dim, s_tag in all_surfaces:
            elem_types, _elem_tags, elem_node_tags = gmsh.model.mesh.getElements(2, s_tag)
            try:
                mass_center = gmsh.model.occ.getCenterOfMass(2, s_tag)
                cx, cy = mass_center[0], mass_center[1]
            except Exception:
                cx, cy = 0.0, 0.0

            target_part_id = layers_data[0]["id"]
            for layer in layers_data:
                poly_path = MplPath(layer["coords"])
                if poly_path.contains_point((cx, cy)) or poly_path.contains_point(
                    (cx, cy), radius=1e-2
                ):
                    target_part_id = layer["id"]
                    break

            for e_type, e_node_tags in zip(elem_types, elem_node_tags):
                if e_type != 10:
                    continue
                num_elems = len(e_node_tags) // 9
                for e in range(num_elems):
                    tags_of_elem = e_node_tags[e * 9 : (e + 1) * 9]
                    elements_by_part[target_part_id].append(tags_of_elem)
                    active_node_tags.update(tags_of_elem)

        return all_nodes_dict, elements_by_part, active_node_tags
    finally:
        _gmsh_shutdown()


def generate_mesh_quad9(request: MeshRequest) -> MeshResponse:
    """Generate a Quad9 mesh via Gmsh from a MeshRequest."""
    try:
        material_ids = {m.id for m in request.materials}
        for i, poly in enumerate(request.polygons):
            if not poly.materialId or poly.materialId not in material_ids:
                return _fail(
                    f"{get_error_info(ErrorCode.VAL_MISSING_MATERIAL)} (Polygon {i + 1})"
                )

        if request.embedded_beams:
            beam_material_ids = {m.id for m in request.beam_materials}
            for i, beam in enumerate(request.embedded_beams):
                if not beam.materialId or beam.materialId not in beam_material_ids:
                    return _fail(
                        f"{get_error_info(ErrorCode.VAL_MISSING_MATERIAL)} (Embedded Beam {i + 1})"
                    )

        global_mesh_size = request.mesh_settings.mesh_size if request.mesh_settings else 2.0
        ms = request.mesh_settings
        load_refine = ms.load_refinement_enabled if ms else True
        ebr_refine = ms.ebr_refinement_enabled if ms else True

        refined_parts = _split_polygons_by_ebr(request)
        if not refined_parts:
            return _fail(get_error_info(ErrorCode.VAL_EMPTY_MESH))

        layers_data = []
        for part_idx, (geom, meta) in enumerate(refined_parts):
            coords = [[float(x), float(y)] for x, y in geom.exterior.coords[:-1]]
            if len(coords) < 3:
                continue
            layers_data.append(
                {
                    "id": part_idx,
                    "coords": coords,
                    "materialId": meta["materialId"],
                    "original_idx": meta["original_idx"],
                }
            )

        if not layers_data:
            return _fail(get_error_info(ErrorCode.VAL_EMPTY_MESH))

        boundary_adjustments = _build_boundary_adjustments(request)

        nodal_forces = [
            {"coord": [pl.x, pl.y], "id": pl.id} for pl in (request.pointLoads or [])
        ]
        line_loads_gmsh = [
            {"start": [ll.x1, ll.y1], "end": [ll.x2, ll.y2], "id": ll.id}
            for ll in (request.lineLoads or [])
        ]

        with _gmsh_lock:
            all_nodes_dict, elements_by_part, active_node_tags = _run_gmsh_quad9(
                layers_data=layers_data,
                boundary_adjustments=boundary_adjustments,
                nodal_forces=nodal_forces,
                line_loads_gmsh=line_loads_gmsh,
                request=request,
                global_mesh_size=global_mesh_size,
                load_refine=load_refine,
                ebr_refine=ebr_refine,
            )

        active_node_tags_sorted = sorted(active_node_tags)
        node_tag_to_idx = {tag: idx for idx, tag in enumerate(active_node_tags_sorted)}
        nodes = [
            all_nodes_dict[tag]
            for tag in active_node_tags_sorted
            if tag in all_nodes_dict
        ]

        elements: List[List[int]] = []
        element_materials: List[ElementMaterial] = []
        mat_map = {m.id: m for m in request.materials}
        elem_id = 0

        for layer in layers_data:
            part_id = layer["id"]
            orig_idx = layer["original_idx"]
            poly = request.polygons[orig_idx]
            mat = mat_map.get(poly.materialId)
            if not mat:
                continue
            for tags_of_elem in elements_by_part.get(part_id, []):
                indices = [node_tag_to_idx[t] for t in tags_of_elem]
                indices = _orient_quad9_indices(nodes, indices)
                elements.append(indices)
                elem_id += 1
                element_materials.append(
                    ElementMaterial(
                        element_id=elem_id,
                        material=mat,
                        polygon_id=orig_idx,
                    )
                )

        if not elements:
            return _fail(get_error_info(ErrorCode.VAL_EMPTY_MESH))

        point_load_assigns = _assign_point_loads(request, nodes)
        line_load_assigns = _assign_line_loads(request, nodes, elements)
        ebr_assigns = _assign_embedded_beams(request, nodes)

        return MeshResponse(
            success=True,
            nodes=nodes,
            elements=elements,
            element_type=MeshElementType.QUAD9,
            boundary_conditions=BoundaryConditionsResponse(
                full_fixed=[], normal_fixed=[]
            ),
            point_load_assignments=point_load_assigns,
            line_load_assignments=line_load_assigns,
            embedded_beam_assignments=ebr_assigns,
            element_materials=element_materials,
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        return _fail(f"{get_error_info(ErrorCode.SYS_INTERNAL_ERROR)} | Raw: {str(e)}")


def _fail(error: str) -> MeshResponse:
    return MeshResponse(
        success=False,
        nodes=[],
        elements=[],
        element_type=MeshElementType.QUAD9,
        boundary_conditions=BoundaryConditionsResponse(full_fixed=[], normal_fixed=[]),
        point_load_assignments=[],
        line_load_assignments=[],
        embedded_beam_assignments=[],
        element_materials=[],
        error=error,
    )


def _assign_point_loads(request: MeshRequest, nodes: List[List[float]]) -> List[PointLoadAssignment]:
    if not request.pointLoads or not nodes:
        return []
    node_arr = np.array(nodes)
    tree = cKDTree(node_arr)
    assigns = []
    for pl in request.pointLoads:
        dist, node_idx = tree.query([pl.x, pl.y])
        if dist > 0.1:
            print(
                f"WARNING: Point load '{pl.id}' at ({pl.x}, {pl.y}) is {dist:.4f}m from nearest node.",
                flush=True,
            )
        assigns.append(
            PointLoadAssignment(point_load_id=pl.id, assigned_node_id=int(node_idx) + 1)
        )
    return assigns


def _assign_line_loads(
    request: MeshRequest, nodes: List[List[float]], elements: List[List[int]]
) -> List[LineLoadAssignment]:
    if not request.lineLoads or not nodes:
        return []
    node_arr = np.array(nodes)
    assigns: List[LineLoadAssignment] = []

    # Quad9 edges: (corner_a, mid, corner_b) for each side
    quad_edges = [
        (0, 4, 1),
        (1, 5, 2),
        (2, 6, 3),
        (3, 7, 0),
    ]

    for ll in request.lineLoads:
        p1 = np.array([ll.x1, ll.y1])
        p2 = np.array([ll.x2, ll.y2])
        line_vec = p2 - p1
        line_len = np.linalg.norm(line_vec)
        if line_len < 1e-9:
            continue
        line_unit = line_vec / line_len

        def is_on_segment(p, tol=1e-3):
            v = p - p1
            proj = float(np.dot(v, line_unit))
            if proj < -tol or proj > line_len + tol:
                return False
            return np.linalg.norm(v - proj * line_unit) < tol

        for el_idx, el in enumerate(elements):
            if len(el) < 9:
                continue
            for na, nm, nb in quad_edges:
                pa, pm, pb = node_arr[el[na]], node_arr[el[nm]], node_arr[el[nb]]
                if is_on_segment(pa) and is_on_segment(pb) and is_on_segment(pm):
                    edge_node_ids = [el[na] + 1, el[nm] + 1, el[nb] + 1]
                    assigns.append(
                        LineLoadAssignment(
                            line_load_id=ll.id,
                            element_id=el_idx + 1,
                            edge_nodes=edge_node_ids,
                        )
                    )
    return assigns


def _assign_embedded_beams(
    request: MeshRequest, nodes: List[List[float]]
) -> List[EmbeddedBeamAssignment]:
    if not request.embedded_beams or not nodes:
        return []
    node_arr = np.array(nodes)
    assigns: List[EmbeddedBeamAssignment] = []

    for beam in request.embedded_beams:
        if len(beam.points) < 2:
            continue
        beam_nodes: List[int] = []
        for i in range(len(beam.points) - 1):
            p_start = np.array([beam.points[i].x, beam.points[i].y])
            p_end = np.array([beam.points[i + 1].x, beam.points[i + 1].y])
            segment_vec = p_end - p_start
            segment_len = np.linalg.norm(segment_vec)
            if segment_len < 1e-9:
                continue
            segment_unit = segment_vec / segment_len
            segment_node_indices = []
            for n_idx, n_coords in enumerate(node_arr):
                p = np.array(n_coords)
                v = p - p_start
                proj = float(np.dot(v, segment_unit))
                if proj < -1e-4 or proj > segment_len + 1e-4:
                    continue
                dist = np.linalg.norm(v - proj * segment_unit)
                if dist < 1e-4:
                    segment_node_indices.append((n_idx, proj))
            segment_node_indices.sort(key=lambda x: x[1])
            for n_idx, _ in segment_node_indices:
                nid = n_idx + 1
                if not beam_nodes or beam_nodes[-1] != nid:
                    beam_nodes.append(nid)
        if len(beam_nodes) > 1:
            assigns.append(EmbeddedBeamAssignment(beam_id=beam.id, nodes=beam_nodes))
    return assigns
