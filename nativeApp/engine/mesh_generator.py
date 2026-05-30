"""
Mesh generation entry point — Quad9 elements via Gmsh.
"""
from engine.mesh_generator_quad9 import generate_mesh_quad9
from engine.models import MeshRequest, MeshResponse


def generate_mesh(request: MeshRequest) -> MeshResponse:
    return generate_mesh_quad9(request)
