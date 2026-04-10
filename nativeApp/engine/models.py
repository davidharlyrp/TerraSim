from typing import List, Optional, Dict
from pydantic import BaseModel
from enum import Enum

class Point(BaseModel):
    x: float
    y: float

class WaterLevel(BaseModel):
    id: str
    name: str
    points: List[Point]

class PolygonData(BaseModel):
    vertices: List[Point]
    mesh_size: Optional[float] = None
    boundary_refinement_factor: Optional[float] = None
    materialId: str

class MaterialModel(str, Enum):
    # """Material constitutive model types"""
    LINEAR_ELASTIC = "linear_elastic"
    MOHR_COULOMB = "mohr_coulomb"
    HOEK_BROWN = "hoek_brown"
    # Future: HARDENING_SOIL, CAM_CLAY, etc.

class DrainageType(str, Enum):
    DRAINED = "drained"
    UNDRAINED_A = "undrained_a"
    UNDRAINED_B = "undrained_b"
    UNDRAINED_C = "undrained_c"
    NON_POROUS = "non_porous"

class PhaseType(str, Enum):
    # """Type of analysis phase"""
    PLASTIC = "plastic"               # Standard elastoplastic deformation
    K0_PROCEDURE = "k0_procedure"     # Initial stress generation (no deformation)
    GRAVITY_LOADING = "gravity_loading" # Legacy deformation-based gravity (not recommended)
    FLOW = "flow"                     # Groundwater flow only
    SAFETY_ANALYSIS = "safety_analysis" # Strength Reduction Method

class Material(BaseModel):
    id: str
    name: str
    color: str
    youngsModulus: Optional[float] = 0.0
    effyoungsModulus: Optional[float] = 0.0
    poissonsRatio: float
    unitWeightUnsaturated: float
    unitWeightSaturated: Optional[float] = None
    cohesion: Optional[float] = None
    frictionAngle: Optional[float] = None
    undrainedShearStrength: Optional[float] = None
    # Hoek-Brown parameters
    sigma_ci: Optional[float] = None
    gsi: Optional[float] = None
    disturbFactor: Optional[float] = None
    m_i: Optional[float] = None
    m_b: Optional[float] = None
    s: Optional[float] = None
    a: Optional[float] = None
    dilationAngle: Optional[float] = 0.0
    thickness: Optional[float] = 1.0
    permeability: Optional[float] = 0.0
    voidRatio: Optional[float] = 0.5
    specificGravity: Optional[float] = 2.65
    material_model: Optional[MaterialModel] = MaterialModel.LINEAR_ELASTIC
    drainage_type: Optional[DrainageType] = DrainageType.DRAINED
    k0_x: Optional[float] = None  # Coefficient of lateral earth pressure (auto-calculated if None)
    k0_z: Optional[float] = None  # Often same as k0_x, but can be different for anisotropy

class EmbeddedBeamMaterial(BaseModel):
    id: str
    name: str
    color: str
    youngsModulus: float # E (kN/m2)
    crossSectionArea: float # A (m2)
    momentOfInertia: float # I (m4)
    unitWeight: float # w (kN/m/m) -> actually usually kN/m per beam. But for 2D we need to know.
                      # Let's stick to Plaxis style: w is weight per unit length of the beam (kN/m).
    spacing: float # L_spacing (m) - out of plane spacing
    skinFrictionMax: float # T_max (kN/m) - limit shear force per unit length of beam
    tipResistanceMax: float # F_max (kN) - limit compressive force at the tip
    # Connection logic (top/bottom) could be here or in the beam instance. 
    # Usually connection type is a property of the beam instance's node, but material property is E, A, I.
    shape: Optional[str] = "user_defined"
    thickness: Optional[float] = None
    width: Optional[float] = None
    diameter: Optional[float] = None

class PointLoad(BaseModel):
    id: str
    x: float
    y: float
    fx: float
    fy: float
    node: Optional[int] = None

class LineLoad(BaseModel):
    id: str
    x1: float
    y1: float
    x2: float
    y2: float
    fx: float # (kN/m)
    fy: float

class EmbeddedBeam(BaseModel):
    id: str
    points: List[Point] # Usually 2 points for a line segment [start, end]
    materialId: str

class MeshSettings(BaseModel):
    mesh_size: float = 2.0
    boundary_refinement_factor: float = 1.0

class MeshRequest(BaseModel):
    polygons: List[PolygonData]
    materials: List[Material]
    pointLoads: List[PointLoad]
    lineLoads: Optional[List[LineLoad]] = []
    mesh_settings: Optional[MeshSettings] = MeshSettings()
    # water_level removed. Use water_levels.
    water_levels: Optional[List[WaterLevel]] = [] # NEW
    embedded_beams: Optional[List[EmbeddedBeam]] = [] # NEW
    beam_materials: Optional[List[EmbeddedBeamMaterial]] = [] # NEW

class BoundaryCondition(BaseModel):
    node: int  # 1-based index usually for FE, but typically backend sends 0-based for arrays. 
               # However, FE code: `bc.node + 1`. So backend sends 0-based.
class BoundaryConditionsResponse(BaseModel):
    full_fixed: List[BoundaryCondition]
    normal_fixed: List[BoundaryCondition]

class PointLoadAssignment(BaseModel):
    point_load_id: str
    assigned_node_id: int # FE expects this to be ready-to-use ID (1-based).

class LineLoadAssignment(BaseModel):
    line_load_id: str
    element_id: int 
    edge_nodes: List[int] # 1-based node IDs [n1, n2, n3]

class ElementMaterial(BaseModel):
    element_id: int # 1-based ID
    material: Material
    polygon_id: Optional[int] = None # NEW: 0-based index of polygon in MeshRequest

class EmbeddedBeamAssignment(BaseModel):
    beam_id: str
    nodes: List[int] # Ordered list of node IDs (1-based) defining the beam chain



class MeshResponse(BaseModel):
    success: bool
    nodes: List[List[float]] # [[x, y], ...]
    elements: List[List[int]] # [[n1, n2, n3, n4, n5, n6], ...] 0-based, 6-node quadratic triangles
    boundary_conditions: BoundaryConditionsResponse
    point_load_assignments: List[PointLoadAssignment]
    line_load_assignments: List[LineLoadAssignment]
    embedded_beam_assignments: List[EmbeddedBeamAssignment] # NEW
    element_materials: List[ElementMaterial]
    error: Optional[str] = None

# --- Solver Models ---

class SolverSettings(BaseModel):
    max_iterations: Optional[int] = 60
    min_desired_iterations: Optional[int] = 3
    max_desired_iterations: Optional[int] = 15
    initial_step_size: Optional[float] = 0.05
    tolerance: Optional[float] = 0.01
    max_load_fraction: Optional[float] = 0.5
    unloading_max_retries: Optional[int] = 5
    realtime_logging: Optional[bool] = True
    max_steps: Optional[int] = 100  # Maximum MStage steps allowed
    max_displacement_limit: Optional[float] = 10.0 # Define "collapse" if disp > 10m
    use_arc_length: Optional[bool] = False # Use Crisfield arc-length method instead of Newton-Raphson
    use_pardiso: Optional[bool] = True    # Use multi-threaded Pardiso solver if available

class PointLoadData(BaseModel):
    node: int  # 0-based node index
    fx: float
    fy: float

class PhaseRequest(BaseModel):
    id: str
    name: str
    phase_type: Optional[PhaseType] = PhaseType.PLASTIC
    parent_id: Optional[str] = None # Continues from this phase
    active_polygon_indices: List[int] # Indices of polygons in original MeshRequest
    active_load_ids: List[str] # IDs of point/line loads to activate
    reset_displacements: bool = False # If true, reset total displacement visualization
    current_material: Dict[int, str] = {} # Map polygon_index -> material_id (full state for this phase)
    parent_material: Dict[int, str] = {} # Map polygon_index -> material_id (inherited from parent)
    active_water_level_id: Optional[str] = None # NEW
    active_beam_ids: Optional[List[str]] = [] # IDs of active beams

class TrackPoint(BaseModel):
    id: str  # e.g., "node_14" or "gp_10_0" (element 10, gp 0)
    type: str  # "node" or "gp"
    index: int  # node index (0-based) or element index (0-based)
    gp_index: Optional[int] = None # 0, 1, or 2 for element GPs
    label: str  # "A", "B", etc.

class SolverRequest(BaseModel):
    mesh: MeshResponse
    phases: List[PhaseRequest] # Sequence of phases
    settings: Optional[SolverSettings] = SolverSettings()
    # water_level removed. Use water_levels + active_water_level_id
    water_levels: Optional[List[WaterLevel]] = [] # NEW
    point_loads: Optional[List[PointLoad]] = [] # Definitions of load vectors
    line_loads: Optional[List[LineLoad]] = []
    embedded_beams: Optional[List[EmbeddedBeam]] = [] # NEW
    materials: List[Material] = [] # NEW: Library of all available materials
    beam_materials: List[EmbeddedBeamMaterial] = [] # NEW
    track_points: Optional[List[TrackPoint]] = [] # Points to track exactly at every Newton step

class NodeResult(BaseModel):
    id: int # 1-based
    ux: float
    uy: float

class StressResult(BaseModel):
    element_id: int # 1-based
    gp_id: Optional[int] = 1
    sig_xx: float
    sig_yy: float
    sig_xy: float
    sig_zz: float # Out of plane
    m_stage: float
    is_yielded: Optional[bool] = False  # NEW: Plasticity flag
    yield_function: Optional[float] = None  # NEW: f value (f<0 elastic, f=0 yield surface)
    pwp_steady: Optional[float] = 0.0
    pwp_excess: Optional[float] = 0.0
    pwp_total: Optional[float] = 0.0
    eps_xx: Optional[float] = 0.0
    eps_yy: Optional[float] = 0.0
    eps_xy: Optional[float] = 0.0
    eps_zz: Optional[float] = 0.0

class PhaseResult(BaseModel):
    phase_id: str
    success: bool
    displacements: List[NodeResult] # Incremental or Total? Usually incremental is sent, then summed.
    stresses: List[StressResult]
    pwp: List[float] = []
    reached_m_stage: Optional[float] = 1.0 # default to 1.0 if successful
    step_failed_at: Optional[int] = None
    error: Optional[str] = None
    track_data: Optional[dict] = {} # Dict mapping track_point_id to list of step data dicts

class SolverResponse(BaseModel):
    success: bool
    phases: List[PhaseResult]
    log: List[str]
    error: Optional[str] = None
