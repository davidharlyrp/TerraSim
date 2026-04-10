from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import asyncio
from contextlib import asynccontextmanager

from backend.models import MeshRequest, MeshResponse, SolverRequest, SolverResponse, SolverSettings, MeshResponse, BoundaryConditionsResponse, BoundaryCondition, PointLoadAssignment, ElementMaterial, Material
from backend.mesh_generator import generate_mesh
from backend.solver import solve_phases
from backend.solver import solve_phases
from backend.legacy_models import LegacySequentialRequest, LegacySequentialResponse, LegacyStageResult
from backend.auth import verify_token, get_current_user, record_running_history
from backend.limiter import limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from fastapi import Depends

# Metadata
TAGS_METADATA = [
    {
        "name": "mesh",
        "description": "Mesh generation operations",
    },
    {
        "name": "solver",
        "description": "FEA Solver operations",
    },
    {
        "name": "legacy",
        "description": "Compatibility endpoints",
    },
]

app = FastAPI(
    title="TerraSim Backend",
    description="Geotechnical Analysis Backend using FEA 2D",
    version="0.5.1",
    openapi_tags=TAGS_METADATA,
    docs_url=None,
    redoc_url=None
)

# Initialize Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False, # Changed to False to allow wildcard origins in browsers
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "TerraSim Backend API v 0.5.1 - Active"}


@app.post("/api/mesh/generate", response_model=MeshResponse, tags=["mesh"])
@limiter.limit("5/minute")
async def create_mesh(mesh_req: MeshRequest, request: Request, user_payload: dict = Depends(verify_token)):
    """
    Generate a 2D triangular mesh based on provided polygons and settings.
    Runs in a thread pool to avoid blocking the event loop.
    """
    print(f"--- [START] Mesh Generation for {len(mesh_req.polygons)} polygons ---")
    try:
        loop = asyncio.get_event_loop()
        # 5-second timeout for mesh generation
        start_time = asyncio.get_event_loop().time()
        response = await asyncio.wait_for(
            loop.run_in_executor(None, generate_mesh, mesh_req),
            timeout=5.0
        )
        duration = asyncio.get_event_loop().time() - start_time
        print(f"--- [SUCCESS] Mesh Generation completed in {duration:.2f}s ---")
        return response
    except asyncio.TimeoutError:
        print("--- [TIMEOUT] Mesh Generation exceeded 5 seconds ---")
        return MeshResponse(
            success=False,
            nodes=[],
            elements=[],
            boundary_conditions=BoundaryConditionsResponse(full_fixed=[], normal_fixed=[]),
            point_load_assignments=[],
            line_load_assignments=[],
            element_materials=[],
            error="Mesh generation timed out. The geometry might be too complex or the mesh size too small."
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"--- [ERROR] Mesh Generation failed: {e} ---")
        return MeshResponse(
            success=False,
            nodes=[],
            elements=[],
            boundary_conditions=BoundaryConditionsResponse(full_fixed=[], normal_fixed=[]),
            point_load_assignments=[],
            line_load_assignments=[],
            element_materials=[],
            error=str(e)
        )

@app.post("/api/solver/calculate", tags=["solver"])
@limiter.limit("5/minute")
async def run_solver(solver_req: SolverRequest, request: Request, user_payload: dict = Depends(verify_token)):
    """
    Run Initial Phase FEA (Gravity Loading) using MStage load advancement.
    Returns a stream of progress logs and results.
    """
    print("Received streaming solver request.")
    
    # Record running history (Asynchronous)
    user_id = user_payload.get("id")
    auth_header = request.headers.get("Authorization")
    if auth_header and user_id:
        try:
            token = auth_header.split(" ")[1]
            asyncio.create_task(record_running_history(user_id, token))
        except Exception as e:
            print(f"Error starting usage history task: {e}")
    
    async def event_generator():
        stop_flag = [False]
        
        async def monitor_disconnect():
            while not stop_flag[0]:
                if await request.is_disconnected():
                    print("Client disconnected, stopping solver...")
                    stop_flag[0] = True
                    break
                await asyncio.sleep(0.5)
        
        monitor_task = asyncio.create_task(monitor_disconnect())
        
        try:
            loop = asyncio.get_event_loop()
            # Generator should check stop_flag via lambda
            gen = solve_phases(solver_req, should_stop=lambda: stop_flag[0])
            
            while True:
                try:
                    # Run iteration in thread pool to keep loop free
                    # Use None as sentinel to avoid StopIteration being raised into Future
                    item = await loop.run_in_executor(None, next, gen, None)
                    if item is None: break
                    yield json.dumps(jsonable_encoder(item)) + "\n"
                    if stop_flag[0]: break
                except StopIteration:
                    break
        except Exception as e:
            import traceback
            traceback.print_exc()
            from backend.error import ErrorCode, get_error_info
            msg = f"{get_error_info(ErrorCode.SYS_INTERNAL_ERROR)} | Raw: {str(e)}"
            yield json.dumps({"type": "log", "content": msg}) + "\n"
        finally:
            stop_flag[0] = True
            monitor_task.cancel()

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

@app.post("/api/sequential/analyze", response_model=LegacySequentialResponse, tags=["legacy"])
async def run_sequential_analysis(request: LegacySequentialRequest, user_payload: dict = Depends(verify_token)):
    """
    Adapter endpoint for Front-end compatibility.
    Only supports 'Initial Stage' currently by mapping to solve_initial_phase.
    """
    print(f"Received sequential analysis request with {len(request.stages)} stages.")
    
    stage_results = []
    
    # We only process the first stage for now as per instructions (Initial Phase focus)
    # or loop through them? The user said "initial phase" focus.
    # We'll try to process the first valid FEA stage.
    
    try:
        for stage in request.stages:
            print(f"Processing Stage: {stage.stage_name} ({stage.calculation_type})")
            
            # Map Legacy config to SolverRequest
            
            # Reconstruct Mesh Response Object from stage inputs
            # The frontend sends "nodes", "elements", "materials" per stage.
            
            # 1. Nodes (Convert dict to list)
            nodes_list = [[n['x'], n['y']] for n in stage.nodes]
            
            # 2. Elements (Convert dict to list [n1, n2, n3])
            # Frontend uses 1-based IDs for nodes in 'element.node1', etc.
            # Backend expects 0-based indices in 'elements' list.
            elements_list = []
            for el in stage.elements:
                # Node IDs are 1-based in FE. Need to map to 0-based index if IDs are sequential 1..N
                # Assuming standard sequential generation: ID 1 is index 0.
                elements_list.append([el['node1']-1, el['node2']-1, el['node3']-1])
            
            # 3. Materials
            # Map element_materials
            # Stage.materials is list of {element_id, material: {...}}
            elem_mats = []
            for item in stage.materials:
                # item is dict
                mat_data = item['material']
                # Create Pydantic Material
                mat = Material(
                    id=str(mat_data.get('id', 'unknown')),
                    name=mat_data.get('name', 'Material'),
                    color=mat_data.get('color', '#888888'),
                    youngsModulus=float(mat_data.get('youngsModulus', 0)),
                    effyoungsModulus=float(mat_data.get('effyoungsModulus', mat_data.get('youngsModulus', 0))),
                    poissonsRatio=float(mat_data.get('poissonsRatio', 0)),
                    unitWeightSaturated=float(mat_data.get('unitWeightSaturated', 0)),
                    unitWeightUnsaturated=float(mat_data.get('unitWeightUnsaturated', 0)),
                    cohesion=float(mat_data.get('cohesion', 0)),
                    frictionAngle=float(mat_data.get('frictionAngle', 0)),
                    undrainedShearStrength=float(mat_data.get('undrainedShearStrength', 0)),
                    dilationAngle=float(mat_data.get('dilationAngle', 0)),
                    sigma_ci=float(mat_data.get('sigma_ci', 0)),
                    gsi=float(mat_data.get('gsi', 0)),
                    mi=float(mat_data.get('mi', 0)),
                    disturbFactor=float(mat_data.get('disturbFactor', 0)),
                    k0_x=float(mat_data.get('k0_x', 0)),
                    thickness=float(mat_data.get('thickness', 1.0)),
                    permeability=float(mat_data.get('permeability', 0)),
                    voidRatio=float(mat_data.get('voidRatio', 0.5)),
                    specificGravity=float(mat_data.get('specificGravity', 2.65)),
                    # ✅ FIX: Map material_model and drainage_type from request
                    material_model=mat_data.get('material_model', 'linear_elastic'),
                    drainage_type=mat_data.get('drainage_type', 'drained')
                )
                elem_mats.append(ElementMaterial(
                    element_id=item['element_id'],
                    material=mat
                ))

            # 4. BCs
            full_fixed = [BoundaryCondition(node=bc['node']-1) for bc in stage.boundaryConditionsFullFixed]
            normal_fixed = [BoundaryCondition(node=bc['node']-1) for bc in stage.boundaryConditionsNormalFixed]

            # Construct partial MeshResponse required for solver
            mesh_proxy = MeshResponse(
                success=True,
                nodes=nodes_list,
                elements=elements_list,
                boundary_conditions=BoundaryConditionsResponse(full_fixed=full_fixed, normal_fixed=normal_fixed),
                point_load_assignments=[], # handled via loads?
                element_materials=elem_mats
            )
            
            # 5. Settings
            # Use defaults or infer from stage?
            settings = SolverSettings() # Default
            
            # 6. Point Loads (from stage.loads)
            # Frontend sends loads array with {node, fx, fy}
            # Node IDs in stage.loads are 1-based, convert to 0-based
            point_loads_data = []
            if hasattr(stage, 'loads') and stage.loads:
                from backend.models import PointLoadData
                for load in stage.loads:
                    point_loads_data.append(PointLoadData(
                        node=load['node'] - 1,  # Convert to 0-based
                        fx=load['fx'],
                        fy=load['fy']
                    ))
                print(f"Extracted {len(point_loads_data)} point loads from stage")
            
            solver_req = SolverRequest(
                mesh=mesh_proxy, 
                settings=settings,
                point_loads=point_loads_data
            )
            
            # RUN SOLVER
            # Only if it's "Initial" or "FEA"
            solver_res = solve_initial_phase(solver_req)
            
            # Format Result for Frontend
            # FE expects `stage_results` list.
            
            if solver_res.success:
                # 1. Displacements
                ux_vals = [d.ux for d in solver_res.displacements]
                uy_vals = [d.uy for d in solver_res.displacements]
                max_disp = max([max(abs(u), abs(v)) for u,v in zip(ux_vals, uy_vals)]) if ux_vals else 0
                max_settlement = min(uy_vals) if uy_vals else 0
                
                fe_displacements = []
                for d in solver_res.displacements:
                    fe_displacements.append({
                        "node_id": d.id - 1, # Convert to 0-based for Frontend Visualization
                        "u": d.ux,  # FE expects "u" not "ux"
                        "v": d.uy,  # FE expects "v" not "uy"
                        "magnitude": (d.ux**2 + d.uy**2)**0.5
                    })
                
                # 2. Element Stresses (Direct Map)
                fe_stresses = []
                # Map for averaging later
                elem_stress_map = {} # elem_id -> stress_obj
                
                for s in solver_res.stresses:
                    # Calculate Principal Stresses for Element (Mohr Circle)
                    # s1,2 = (sx+sy)/2 +/- sqrt(((sx-sy)/2)^2 + txy^2)
                    avg_s = (s.sig_xx + s.sig_yy) / 2.0
                    r = ((s.sig_xx - s.sig_yy)**2 / 4.0 + s.sig_xy**2)**0.5
                    s1 = avg_s + r
                    s3 = avg_s - r
                    
                    st_obj = {
                        "element_id": s.element_id, 
                        "sig_xx": s.sig_xx,
                        "sig_yy": s.sig_yy,
                        "sig_xy": s.sig_xy,
                        "sig_zz": s.sig_zz,
                        "principal_stress_1": s1,
                        "principal_stress_3": s3,
                         # Effective approx same as total if no pore pressure yet
                        "effective_stress_1": s1,
                        "effective_stress_3": s3,
                        # FIX: Pass plasticity flags
                        "is_yielded": s.is_yielded,
                        "yield_function": s.yield_function
                    }
                    fe_stresses.append(st_obj)
                    elem_stress_map[s.element_id] = st_obj

                # 3. Nodal Stress Smoothing (Averaging)
                # We need to know which elements wrap which node.
                # `elements_list` has 0-based indices.
                
                # Init accumulators
                node_stress_sum = {} # node_id (1-based) -> {sx, sy, sz, sxy, count}
                
                # Check 0-based to 1-based consistency
                # `elements_list` was built earlier in the loop (lines 144-150)
                
                for i, el_nodes_0 in enumerate(elements_list):
                    elem_id = i + 1
                    if elem_id not in elem_stress_map:
                        continue
                        
                    s_el = elem_stress_map[elem_id]
                    
                    for n_idx_0 in el_nodes_0:
                        n_id = n_idx_0 + 1
                        if n_id not in node_stress_sum:
                            node_stress_sum[n_id] = {'sx':0, 'sy':0, 'sz':0, 'sxy':0, 'count':0}
                            
                        node_stress_sum[n_id]['sx'] += s_el['sig_xx']
                        node_stress_sum[n_id]['sy'] += s_el['sig_yy']
                        node_stress_sum[n_id]['sz'] += s_el['sig_zz']
                        node_stress_sum[n_id]['sxy'] += s_el['sig_xy']
                        node_stress_sum[n_id]['count'] += 1
                
                fe_nodal_stresses = []
                for n_id, data in node_stress_sum.items():
                    c = data['count']
                    if c > 0:
                        sx = data['sx'] / c
                        sy = data['sy'] / c
                        sz = data['sz'] / c
                        sxy = data['sxy'] / c
                        
                        # Principals
                        avg_s = (sx + sy) / 2.0
                        r = ((sx - sy)**2 / 4.0 + sxy**2)**0.5
                        s1 = avg_s + r
                        s3 = avg_s - r
                        
                        fe_nodal_stresses.append({
                            "node_id": n_id - 1, # Convert to 0-based for Frontend Visualization
                            "total_stress_x": sx,
                            "total_stress_y": sy,
                            "effective_stress_x": sx, # No water yet
                            "effective_stress_y": sy,
                            "pore_water_pressure": 0.0,
                            "principal_stress_1": s1,
                            "principal_stress_3": s3,
                            "effective_principal_stress_1": s1,
                            "effective_principal_stress_3": s3
                        })

                
                result_payload = {
                    "summary": {
                        "max_displacement": max_disp,
                        "max_settlement": max_settlement,
                        "min_displacement": 0, 
                        "steps_taken": solver_res.steps_taken,
                        "final_m_stage": solver_res.final_m_stage
                    },
                    "nodal_displacements": fe_displacements,
                    "element_results": fe_stresses, 
                    "nodal_stress_strain": fe_nodal_stresses, 
                    "logs": solver_res.log,
                    # FE requires active_nodes indices to filter the node list.
                    "active_nodes": list(range(len(nodes_list))), 
                    # do NOT send active_elements, so FE falls back to full elementList with correct structure
                }
                
                # However, for `active_nodes`, we MUST send it because the filter Logic is:
                # `nodeList.filter((_, index) => results...active_nodes?.includes(index))`
                # If active_nodes is undefined, includes() crashes or filter gets nothing?
                # Actually `undefined?.includes()` returns undefined. Filter treats undefined as truthy??? No.
                # In JS, filter predicate must return truthy. Undefined is falsy.
                # So if active_nodes is missing, nodes=[]!
                
                # So we ADD active_nodes. 
                
                stage_results.append(LegacyStageResult(
                    stage_id=stage.stage_id,
                    stage_name=stage.stage_name,
                    success=True,
                    results=result_payload
                ))
            else:
                 stage_results.append(LegacyStageResult(
                    stage_id=stage.stage_id,
                    stage_name=stage.stage_name,
                    success=False,
                    results={"error": solver_res.error or "Unknown solver error"}
                ))
                
        return LegacySequentialResponse(
            success=True,
            stage_results=stage_results,
            results={"analysis_summary": {"status": "Complete"}}
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return LegacySequentialResponse(
            success=False,
            stage_results=[],
            error=str(e)
        )

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8010, reload=True)
