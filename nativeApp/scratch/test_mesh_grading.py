"""Quick integration test for the improved graded mesh generation."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.mesh_generator import generate_mesh
from engine.models import (
    MeshRequest, MeshSettings, PolygonData, Point, Material,
    EmbeddedBeam, EmbeddedBeamMaterial
)

# Create a simple 2-layer model with an EBR
materials = [
    Material(id="m1", name="Clay", color="#88cc88", youngsModulus=10000,
             poissonsRatio=0.3, unitWeightUnsaturated=18),
    Material(id="m2", name="Sand", color="#cccc88", youngsModulus=30000,
             poissonsRatio=0.25, unitWeightUnsaturated=20),
]

beam_materials = [
    EmbeddedBeamMaterial(id="bm1", name="Pile", color="#333333",
                         youngsModulus=2e7, crossSectionArea=0.1,
                         momentOfInertia=0.001, unitWeight=5,
                         spacing=2.0, skinFrictionMax=100, tipResistanceMax=500)
]

polygons = [
    PolygonData(
        vertices=[Point(x=0, y=0), Point(x=20, y=0), Point(x=20, y=5), Point(x=0, y=5)],
        materialId="m1", mesh_size=2.0, boundary_refinement_factor=2.0
    ),
    PolygonData(
        vertices=[Point(x=0, y=-5), Point(x=20, y=-5), Point(x=20, y=0), Point(x=0, y=0)],
        materialId="m2", mesh_size=2.0, boundary_refinement_factor=1.5
    ),
]

embedded_beams = [
    EmbeddedBeam(
        id="eb1",
        points=[Point(x=10, y=5), Point(x=10, y=-3)],
        materialId="bm1"
    )
]

request = MeshRequest(
    polygons=polygons,
    materials=materials,
    pointLoads=[],
    lineLoads=[],
    mesh_settings=MeshSettings(mesh_size=2.0, boundary_refinement_factor=2.0),
    embedded_beams=embedded_beams,
    beam_materials=beam_materials
)

print("Running mesh generation...")
response = generate_mesh(request)

if response.success:
    print(f"SUCCESS: {len(response.nodes)} nodes, {len(response.elements)} elements")
    print(f"  Element materials: {len(response.element_materials)}")
    print(f"  EBR assignments: {len(response.embedded_beam_assignments)}")
    for ba in response.embedded_beam_assignments:
        print(f"    Beam {ba.beam_id}: {len(ba.nodes)} nodes")
else:
    print(f"FAILED: {response.error}")
    sys.exit(1)

print("\nDone!")
