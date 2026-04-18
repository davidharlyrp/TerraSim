
import sys
import os
import numpy as np

# Mocking parts of engine to load mesh
sys.path.append(os.getcwd())
from engine.mesh_generator import generate_mesh
from engine.models import CalculationRequest, Polygon, Point, Material, SectionProperty, BoundaryConditions

# Create a mock request to see how many nodes on boundary for T15
mat = Material(id="m1", name="Soil", unitWeightUnsaturated=20, unitWeightSaturated=20, poissonsRatio=0.3, youngsModulus=1e4)
poly = Polygon(id=0, points=[Point(x=0, y=0), Point(x=10, y=0), Point(x=10, y=10), Point(x=0, y=10)], materialId="m1")
req = CalculationRequest(polygons=[poly], materials=[mat], mesh_size=2.0)

# Generate mesh
mesh = generate_mesh(req)

print(f"Total nodes: {len(mesh.nodes)}")
print(f"Total elements: {len(mesh.elements)}")
print(f"Full Fixed nodes count: {len(mesh.boundary_conditions.full_fixed)}")
print(f"Normal Fixed nodes count: {len(mesh.boundary_conditions.normal_fixed)}")

# Check if all boundary element edges have all their nodes pinned
bottom_nodes = [bc.node for bc in mesh.boundary_conditions.full_fixed]
side_nodes = [bc.node for bc in mesh.boundary_conditions.normal_fixed]

nodes_arr = np.array(mesh.nodes)
y_min = nodes_arr[:,1].min()
x_min = nodes_arr[:,0].min()
x_max = nodes_arr[:,0].max()

unpinned_bottom = []
for i, n in enumerate(mesh.nodes):
    if abs(n[1] - y_min) < 1e-3:
        if i not in bottom_nodes:
            unpinned_bottom.append(i)

unpinned_sides = []
for i, n in enumerate(mesh.nodes):
    if (abs(n[0] - x_min) < 1e-3 or abs(n[0] - x_max) < 1e-3) and abs(n[1] - y_min) > 1e-3:
        if i not in side_nodes:
            unpinned_sides.append(i)

print(f"Unpinned Bottom Nodes: {len(unpinned_bottom)}")
if unpinned_bottom:
    for i in unpinned_bottom:
        print(f"  - Node {i}: {mesh.nodes[i]}")

print(f"Unpinned Side Nodes: {len(unpinned_sides)}")
if unpinned_sides:
    for i in unpinned_sides:
        print(f"  - Node {i}: {mesh.nodes[i]}")

# Check connectivity of one T15 element
el0 = mesh.elements[0].nodes
print(f"Element 0 nodes: {el0}")
