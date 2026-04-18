import numpy as np
import scipy.sparse as sp
import sys
import os
from pathlib import Path

# Adjust path to allow imports from engine
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from engine.models import (
    SolverRequest, MeshResponse, BoundaryConditionsResponse, BoundaryCondition,
    Material, PhaseRequest, PhaseType, SolverSettings, ElementMaterial, PolygonData,
    PointLoad, LineLoad, WaterLevel, Point
)
from engine.solver.phase_solver import solve_phases
import asyncio

def create_mock_request():
    # 1. Define Nodes for ONE T15 Triangle (Quartic)
    # Corners: 0,0  2,0  0,2
    # Edge 12 (at 0.25, 0.5, 0.75): (0.5, 0), (1, 0), (1.5, 0)
    # Edge 23: (1.5, 0.5), (1, 1), (0.5, 1.5)
    # Edge 31: (0, 1.5), (0, 1), (0, 0.5)
    # Interiors: (0.5, 0.5), (1, 0.5), (0.5, 1)
    
    nodes = [
        [0.0, 0.0], [2.0, 0.0], [0.0, 2.0], # 0,1,2 (Corners)
        [0.5, 0.0], [1.0, 0.0], [1.5, 0.0], # 3,4,5 (Edge 12)
        [1.5, 0.5], [1.0, 1.0], [0.5, 1.5], # 6,7,8 (Edge 23)
        [0.0, 1.5], [0.0, 1.0], [0.0, 0.5], # 9,10,11 (Edge 31)
        [0.5, 0.5], [1.0, 0.5], [0.5, 1.0]  # 12,13,14 (Interiors)
    ]
    
    elements = [
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14] 
    ]
    
    # Material
    mat = Material(
        id="mat1",
        name="Soft Clay",
        color="#ff0000",
        youngsModulus=10000.0, # Stiffer for test
        effyoungsModulus=10000.0,
        poissonsRatio=0.3, 
        unitWeightUnsaturated=18.0,
        cohesion=5.0,
        frictionAngle=25.0,
        material_model="mohr_coulomb",
        drainage_type="drained"
    )
    
    elem_materials = [
        ElementMaterial(element_id=1, material=mat, polygon_id=0)
    ]
    
    # Boundary Conditions: Fully fix the bottom edge (0-1: 0, 1, 3, 4, 5)
    full_fixed = [
        BoundaryCondition(node=0), BoundaryCondition(node=1),
        BoundaryCondition(node=3), BoundaryCondition(node=4), BoundaryCondition(node=5)
    ]
    normal_fixed = []
    
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
        embedded_beam_assignments=[],
        element_materials=elem_materials
    )
    
    # Phase
    phase = PhaseRequest(
        id="phase1",
        name="Plastic Step",
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
        beam_materials=[],
        embedded_beams=[],
        point_loads=[],
        line_loads=[],
        water_levels=[],
        settings=SolverSettings(max_iterations=15, initial_step_size=0.1)
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
