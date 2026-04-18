
import sys
import os
import numpy as np

# Mocking parts of engine to load mesh
sys.path.append(os.getcwd())
from engine.mesh_generator import generate_mesh
from engine.models import MeshSettings, PolygonData, Point, Material, MeshRequest

# Create a mock request same as the log ( mesh_size=0.5 )
mat = Material(id="m1", name="Soil", color="red", unitWeightUnsaturated=20, poissonsRatio=0.3, youngsModulus=1e4)
poly = PolygonData(vertices=[Point(x=0, y=0), Point(x=30, y=0), Point(x=30, y=20), Point(x=0, y=20)], materialId="m1")
req = MeshRequest(polygons=[poly], materials=[mat], pointLoads=[], mesh_settings=MeshSettings(mesh_size=0.5))

# Generate mesh
mesh = generate_mesh(req)

print(f"Total nodes: {len(mesh.nodes)}")
if len(mesh.nodes) > 5065:
    p = mesh.nodes[5065]
    print(f"Node 5065 coordinates: {p}")
    # check if it's on boundary
    nodes_arr = np.array(mesh.nodes)
    y_min = nodes_arr[:,1].min()
    y_max = nodes_arr[:,1].max()
    x_min = nodes_arr[:,0].min()
    x_max = nodes_arr[:,0].max()
    
    print(f"Mesh Bounds: X[{x_min}, {x_max}], Y[{y_min}, {y_max}]")
    is_bc = abs(p[1]-y_min)<1e-3 or abs(p[0]-x_min)<1e-3 or abs(p[0]-x_max)<1e-3
    print(f"Node 5065 is on boundary? {is_bc}")
