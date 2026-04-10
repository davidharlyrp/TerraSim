# Mesh Generator Documentation

## Overview
The Mesh Generator in `DaharTerraSim` is a robust 2D unstructured triangular mesh generator designed for geotechnical finite element analysis (FEA). It produces high-quality meshes similar to Plaxis, supporting:
- Complex polygonal geometries (soil layers, structures).
- Multiple materials.
- Automatic boundary refinement (densification near edges).
- Point loads and boundary condition mapping.

It is built on top of the **Triangle** library (Jonathan Shewchuk), which is the industry standard for Constrained Delaunay Triangulation (CDT).

## Core Technologies
- **Python**: Core language.
- **Triangle**: Efficient C-based library for generating quality meshes.
- **Shapely**: Geometric operations (point-in-polygon checks).
- **NumPy/SciPy**: efficient numerical arrays and spatial querying (KDTree).

## Algorithm Pipeline

The generation process in `mesh_generator.py` follows these steps:

### 1. Geometry Preparation
The input consists of multiple `Polygon` objects. The generator:
- **Flattens Vertices**: Collects all unique vertices from all polygons.
- **Discretizes Segments (Boundary Refinement)**:
    - Instead of just connecting vertices A and B, the system subdivides the edge A-B into smaller segments based on the `mesh_size` and `boundary_refinement_factor`.
    - **Formula**: $TargetSegmentLength = \frac{MeshSize}{\max(RefinementFactor, 0.1)}$
    - This ensures that mesh elements near boundaries are smaller and higher quality, capturing stress concentrations better.

### 2. Region Definition
For each input polygon, the system identifies a "Region" marker:
- It calculates a point inside the polygon (representative point).
- It assigns a **Maximum Area Constraint** to that region: $MaxArea \approx 0.5 \times MeshSize^2$.
- This forces the triangulator to fill the interior of the polygon with triangles no larger than the specified size.

### 3. Triangulation (CDT)
The system calls `triangle.triangulate` with the following flags (`pqaA`):
- **p (Planar Straight Line Graph)**: Respects the input segments (boundaries).
- **q (Quality)**: Enforces a minimum angle check (typically 20-30 degrees) to avoid "sliver" triangles which are bad for FEA.
- **a (Area)**: Enforces the maximum area constraints defined in step 2.
- **A (Attributes)**: Propagates the region attributes (Material IDs) to the generated triangles.

### 4. Post-Processing
After raw triangles are generated:
- **Element Logic**: 3-node triangles are converted to the API format.
- **Material Assignment**: Each element identifies which material it belongs to based on the region attribute.
- **Nodes**: Coordinates are formatted for the Frontend (0-based or 1-based as required).

### 5. Boundary Conditions & Loads
- **Automatic BCs**: The system detects the bounding box of the mesh.
    - **Bottom Edge**: Assigned **Full Fixed** ($U_x=0, U_y=0$).
    - **Left/Right Edges**: Assigned **Normal Fixed** (Roller, $U_x=0$, free vertical settlement).
    - **Top Edge**: Free (no constraints).
- **Point Loads**: The system uses a `KDTree` (spatial search) to find the nearest mesh node to the user's defined point load coordinates ($x, y$).
    - Point loads are assigned to the **nearest node** automatically.
    - Assignment stored in `point_load_assignments` with mapping `{point_load_id → node_id}`.

## Mesh Quality Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `mesh_size` | 1.0 | Target element size (m) |
| `boundary_refinement_factor` | 1.0 | Refinement multiplier for boundaries |
| Min angle | 20° | Enforced by Triangle library |
| Max area | 0.5 × mesh_size² | Per region constraint |

**Quality Metrics**:
- **Aspect Ratio**: Maintained by minimum angle constraint
- **Boundary Refinement**: Smaller elements near edges = better stress capture
- **Element Count**: Approximately $\frac{Area}{0.5 \times mesh\_size^2}$ elements

## API Data Structure

### Input (`MeshRequest`)
```json
{
  "polygons": [
    {
      "vertices": [{"x": 0, "y": 0}, ...],
      "mesh_size": 1.0, 
      "boundary_refinement_factor": 1.0,
      "materialId": "material_1"
    }
  ],
  "materials": [...],
  "pointLoads": [...]
}
```

### Output (`MeshResponse`)
```json
{
  "success": true,
  "nodes": [[x1, y1], [x2, y2], ...],
  "elements": [[n1, n2, n3], ...],
  "element_materials": [
    {"element_id": 1, "material": {...}}
  ],
  "boundary_conditions": {
    "full_fixed": [{"node": 0}, ...],
    "normal_fixed": [{"node": 5}, ...]
  },
  "point_load_assignments": [
    {"point_load_id": "pl1", "assigned_node_id": 12}
  ]
}
```

## Running the mesh generator

### Validation
You can run the included test script to verify the generator without the Frontend:
```bash
python backend/test_mesh.py
```

### Starting the Server
To use it with the Frontend, start the FastAPI server from the **root directory**:
```bash
# Correct command (run from D:\Program\Dahar Engineer\daharterrasim)
python -m backend.main
```
*Note: Do not run `python main.py` inside the backend folder, as this breaks package imports.*

## Integration with Solver

The mesh output is directly compatible with `fea_solver.py`:
1. **Nodes**: 0-based indexing used consistently
2. **Elements**: Triangle node indices (0-based)
3. **Materials**: Mapped to elements via `element_materials`
4. **BCs**: Automatically applied in solver
5. **Point Loads**: Node assignments used in force vector assembly

For solver documentation, see [SOLVER_DOCUMENTATION.md](SOLVER_DOCUMENTATION.md).
