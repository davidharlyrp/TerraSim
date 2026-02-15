
import numpy as np
import scipy.sparse as sp
import sys
import os

# Adjust path to allow imports from backend
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from backend.models import (
    SolverRequest, MeshResponse, BoundaryConditionsResponse, BoundaryCondition,
    Material, PhaseRequest, PhaseType, SolverSettings, ElementMaterial, PolygonData,
    PointLoad, LineLoad, WaterLevel, Point
)
from backend.solver.phase_solver import solve_phases
import asyncio

def create_mock_request():
    # 1. Define Nodes (2 triangles sharing a side)
    # T6 elements need 6 nodes per element.
    # High order (quadratic) mesh.
    
    # Quad 2x1 split into 2 triangles
    # Nodes:
    # 0,0  1,0  2,0
    # 0,1  1,1  2,1
    # Plus mid-nodes
    
    # Let's just make ONE T6 element for simplicity
    # Nodes: 
    # 0: (0,0), 1: (2,0), 2: (0,2)  (Corner nodes)
    # 3: (1,0), 4: (1,1), 5: (0,1)  (Mid nodes)
    
    nodes = [
        [0.0, 0.0], # 0
        [2.0, 0.0], # 1
        [0.0, 2.0], # 2
        [1.0, 0.0], # 3
        [1.0, 1.0], # 4
        [0.0, 1.0]  # 5
    ]
    
    elements = [
        [0, 1, 2, 3, 4, 5] 
    ]
    
    # Material
    mat = Material(
        id="mat1",
        name="Soft Clay",
        color="#ff0000",
        youngsModulus=1000.0,
        poissonsRatio=0.3, # Incompressible-ish? 
        unitWeightUnsaturated=18.0,
        cohesion=5.0,
        frictionAngle=25.0,
        material_model="mohr_coulomb",
        drainage_type="drained"
    )
    
    elem_materials = [
        ElementMaterial(element_id=1, material=mat, polygon_id=0)
    ]
    
    # Boundary Conditions
    # Fully constraint bottom left (Node 0)
    # But if we ONLY constraint Node 0, the element can rotate! -> Singular
    # Let's constraint Node 1 in Y only (Roller)
    
    # TO REPRODUCE SINGULARITY: 
    # Constraint only Y at bottom (Nodes 0, 1, 3). No X constraint.
    # System is free to slide in X.
    
    full_fixed = [] 
    normal_fixed = [
        BoundaryCondition(node=0), # Y fixed
        BoundaryCondition(node=1), # Y fixed
        BoundaryCondition(node=3)  # Y fixed
    ]
    
    mesh = MeshResponse(
        success=True,
        nodes=nodes,
        elements=elements,
        boundary_conditions=BoundaryConditionsResponse(
            full_fixed=full_fixed,
            normal_fixed=normal_fixed 
        ),
        point_load_assignments=[],
        line_load_assignments=[],
        element_materials=elem_materials
    )
    
    # Phase
    phase = PhaseRequest(
        id="phase1",
        name="Gravity Loading",
        phase_type=PhaseType.PLASTIC,
        active_polygon_indices=[0],
        active_load_ids=[],
        reset_displacements=False,
        current_material={0: "mat1"},
        parent_material={}
    )
    
    req = SolverRequest(
        mesh=mesh,
        phases=[phase],
        materials=[mat],
        settings=SolverSettings(max_iterations=10, initial_step_size=1.0)
    )
    
    return req

async def run_test():
    req = create_mock_request()
    print("Running solver with UNCONSTRAINED X (should be singular)...")
    
    try:
        gen = solve_phases(req)
        for item in gen:
            # print(item)
            if item['type'] == 'log':
                print(f"LOG: {item['content']}")
            elif item['type'] == 'phase_result':
                res = item['content']
                print(f"Phase Result: Success={res['success']}, Error={res['error']}")
    except Exception as e:
        print(f"Caught Exception: {e}")

if __name__ == "__main__":
    asyncio.run(run_test())
