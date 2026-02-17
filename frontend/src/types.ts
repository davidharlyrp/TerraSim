export interface Point {
    x: number;
    y: number;
}

export interface WaterLevel {
    id: string;
    name: string;
    points: Point[];
}

export interface PolygonData {
    vertices: Point[];
    mesh_size?: number;
    boundary_refinement_factor?: number;
    materialId: string;
}

export enum MaterialModel {
    LINEAR_ELASTIC = "linear_elastic",
    MOHR_COULOMB = "mohr_coulomb",
    HOEK_BROWN = "hoek_brown"
}

export enum DrainageType {
    DRAINED = "drained",
    UNDRAINED_A = "undrained_a",
    UNDRAINED_B = "undrained_b",
    UNDRAINED_C = "undrained_c",
    NON_POROUS = "non_porous",
}

export enum PhaseType {
    PLASTIC = "plastic",
    K0_PROCEDURE = "k0_procedure",
    GRAVITY_LOADING = "gravity_loading",
    FLOW = "flow",
    SAFETY_ANALYSIS = "safety_analysis"
}

export interface Material {
    id: string;
    name: string;
    color: string;
    youngsModulus?: number;
    effyoungsModulus?: number;
    poissonsRatio: number;
    unitWeightUnsaturated: number;
    unitWeightSaturated?: number;
    cohesion?: number;
    frictionAngle?: number;
    undrainedShearStrength?: number;
    dilationAngle?: number;
    thickness?: number;
    permeability?: number;
    voidRatio?: number;
    specificGravity?: number;
    material_model?: MaterialModel;
    drainage_type?: DrainageType;
    // Hoek-Brown parameters
    sigma_ci?: number;
    gsi?: number;
    mi?: number;
    disturbFactor?: number;
    m_b?: number;
    s?: number;
    a?: number;
    k0_x?: number;
    k0_z?: number;
}

export interface EmbeddedBeamMaterial {
    id: string;
    name: string;
    color: string;
    youngsModulus: number; // E
    crossSectionArea: number; // A
    momentOfInertia: number; // I
    unitWeight: number; // w
    spacing: number; // L_spacing
    skinFrictionMax: number; // T_max
    tipResistanceMax: number; // F_max
    shape: string;
    thickness?: number;
    width?: number;
    diameter?: number;
}

export interface EmbeddedBeam {
    id: string;
    points: Point[];
    materialId: string;
}

export interface PointLoad {
    id: string;
    x: number;
    y: number;
    fx: number;
    fy: number;
    node?: number; // Backend assigned node index (0-based usually, check MeshResponse)
}

export interface LineLoad {
    id: string;
    x1: number;
    y1: number;
    x2: number;
    y2: number;
    fx: number;
    fy: number;
}

export interface MeshSettings {
    mesh_size: number;
    boundary_refinement_factor: number;
}

export interface MeshRequest {
    polygons: PolygonData[];
    materials: Material[];
    pointLoads: PointLoad[];
    lineLoads?: LineLoad[];
    // water_level removed
    water_levels?: WaterLevel[]; // NEW
    mesh_settings?: MeshSettings; // NEW: Global mesh settings
    embedded_beams?: EmbeddedBeam[]; // NEW
    beam_materials?: EmbeddedBeamMaterial[]; // NEW
}

// --- Project Management ---
export interface ProjectMetadata {
    lastEdited: string; // ISO Date string
    authorName?: string;
    authorEmail?: string;
}

export interface ProjectFile {
    version: string;
    projectName: string;
    metadata: ProjectMetadata;
    materials: Material[];
    polygons: PolygonData[];
    pointLoads: PointLoad[];
    lineLoads: LineLoad[];
    waterLevel: { x: number, y: number }[]; // Deprecated, keep for old file compat loading
    waterLevels: WaterLevel[]; // NEW
    embeddedBeams: EmbeddedBeam[]; // NEW
    beamMaterials: EmbeddedBeamMaterial[]; // NEW
    phases: PhaseRequest[];
    generalSettings: GeneralSettings;
    solverSettings: SolverSettings;
    meshSettings: MeshSettings;
    meshResponse: MeshResponse | null;
    solverResponse?: SolverResponse | null;  // Optional - excluded from saves
}

export interface BoundaryCondition {
    node: number; // 0-based index from backend
}

export interface BoundaryConditionsResponse {
    full_fixed: BoundaryCondition[];
    normal_fixed: BoundaryCondition[];
}

export interface PointLoadAssignment {
    point_load_id: string;
    assigned_node_id: number; // 0-based index
}

export interface LineLoadAssignment {
    line_load_id: string;
    element_id: number;
    edge_nodes: number[]; // 1-based node IDs
}

export interface EmbeddedBeamAssignment {
    beam_id: string;
    nodes: number[]; // 1-based node IDs
}

export interface ElementMaterial {
    element_id: number; // 1-based index (check backend usage, usually elements are 0-based in array but IDs might be 1-based)
    material: Material;
    polygon_id?: number; // NEW: 0-based index of polygon
}

export interface MeshResponse {
    success: boolean;
    nodes: [number, number][]; // [[x, y], ...]
    elements: number[][]; // [[n1, n2, n3, n4, n5, n6], ...] 0-based indices, 6-node quadratic triangles
    boundary_conditions: BoundaryConditionsResponse;
    point_load_assignments: PointLoadAssignment[];
    line_load_assignments: LineLoadAssignment[];
    embedded_beam_assignments: EmbeddedBeamAssignment[]; // NEW
    element_materials: ElementMaterial[];
    error?: string;
}

export interface SolverSettings {
    max_iterations?: number;
    min_desired_iterations?: number;
    max_desired_iterations?: number;
    initial_step_size?: number;
    tolerance?: number;
    max_load_fraction?: number;
    unloading_max_retries?: number;
    max_steps?: number;
}

export interface PointLoadData {
    node: number; // 0-based
    fx: number;
    fy: number;
}

export interface PhaseRequest {
    id: string;
    name: string;
    phase_type?: PhaseType;
    parent_id?: string;
    active_polygon_indices: number[];
    active_load_ids: string[];
    reset_displacements?: boolean;
    // NEW: Full material state for this phase
    current_material: Record<number, string>; // poly_idx -> material_id
    parent_material: Record<number, string>; // poly_idx -> material_id (snapshot of parent)
    active_water_level_id?: string; // NEW
    active_beam_ids?: string[]; // IDs of active beams
}

export interface SolverRequest {
    mesh: MeshResponse;
    phases: PhaseRequest[]; // Sequence of phases
    settings?: SolverSettings;
    // water_level removed
    water_levels?: WaterLevel[]; // NEW
    point_loads?: PointLoad[]; // Definitions
    line_loads?: LineLoad[];
    materials?: Material[]; // NEW: Material library for overrides
    embedded_beams?: EmbeddedBeam[]; // NEW
    beam_materials?: EmbeddedBeamMaterial[]; // NEW
}

export interface NodeResult {
    id: number; // matches node index? backend says 1-based ID in example, need to verify
    ux: number;
    uy: number;
}

export interface StressResult {
    element_id: number; // 1-based
    gp_id?: number; // 1-based index for Gauss point
    sig_xx: number;
    sig_yy: number;
    sig_xy: number;
    sig_zz: number;
    m_stage: number;
    is_yielded?: boolean;
    yield_function?: number;
    pwp_steady?: number;
    pwp_excess?: number;
    pwp_total?: number;
}

export interface StepPoint {
    m_stage: number;
    max_disp: number;
}

export interface PhaseResult {
    phase_id: string;
    success: boolean;
    displacements: NodeResult[];
    stresses: StressResult[];
    pwp: number[];
    reached_m_stage?: number;
    step_points?: StepPoint[];
    step_failed_at?: number;
    error?: string;
}

export interface SolverResponse {
    success: boolean;
    phases: PhaseResult[];
    log: string[];
    error?: string;
}

export enum OutputType {
    DEFORMED_MESH = "deformed_mesh",
    DEFORMED_CONTOUR = "deformed_contour",
    SIGMA_1 = "sigma_1",
    SIGMA_3 = "sigma_3",
    SIGMA_1_EFF = "sigma_1_eff",
    SIGMA_3_EFF = "sigma_3_eff",
    YIELD_STATUS = "yield_status",
    PWP_STEADY = "pwp_steady",
    PWP_EXCESS = "pwp_excess",
    PWP_TOTAL = "pwp_total"
}

export interface GeneralSettings {
    snapToGrid: boolean;
    snapSpacing: number;
    hideGrid: boolean;
    hideRuler: boolean;
}
