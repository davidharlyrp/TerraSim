
import { DrainageType, MaterialModel, PhaseRequest, PhaseType, PointLoad, PolygonData, Material, WaterLevel, GeneralSettings, MeshSettings, EmbeddedBeamMaterial } from '../../types';

// Sample Materials
export const SAMPLE_MATERIALS: Material[] = [
    {
        id: 'mat_sand',
        name: 'Dense Sand',
        color: '#eab308', // yellow-500
        effyoungsModulus: 50000.0, // kPa
        poissonsRatio: 0.3,
        unitWeightSaturated: 20.0, // kN/m3
        unitWeightUnsaturated: 18.0,
        cohesion: 0.0, // kPa
        frictionAngle: 38.0, // degrees
        material_model: MaterialModel.MOHR_COULOMB,
        drainage_type: DrainageType.DRAINED,
    },
    {
        id: 'mat_undrained_a_clay',
        name: 'Stiff Clay (Undr A)',
        color: '#12a41e', // stone-400
        effyoungsModulus: 9000.0, // kPa
        poissonsRatio: 0.35,
        unitWeightSaturated: 17.0,
        unitWeightUnsaturated: 16.0,
        cohesion: 8.0,
        frictionAngle: 25.0,
        material_model: MaterialModel.MOHR_COULOMB,
        drainage_type: DrainageType.UNDRAINED_A,
    },
    {
        id: 'mat_undrained_b_clay',
        name: 'Stiff Clay (Undr B)',
        color: '#71717a', // zinc-500
        effyoungsModulus: 9000.0,
        poissonsRatio: 0.4,
        unitWeightSaturated: 16.0,
        unitWeightUnsaturated: 15.0,
        undrainedShearStrength: 30.0, // Su used instead of c, phi
        material_model: MaterialModel.MOHR_COULOMB,
        drainage_type: DrainageType.UNDRAINED_B,
    },
    {
        id: 'mat_undrained_c_clay',
        name: 'Stiff Clay (Undr C)',
        color: '#1b1ba0', // zinc-500
        youngsModulus: 15000.0,
        poissonsRatio: 0.49,
        unitWeightSaturated: 15.0,
        unitWeightUnsaturated: 15.0,
        undrainedShearStrength: 50.0, // Su used instead of c, phi
        material_model: MaterialModel.MOHR_COULOMB,
        drainage_type: DrainageType.UNDRAINED_C,
    },
    {
        id: 'mat_non_porous',
        name: 'Concrete (Non-Porous)',
        color: '#c16523', // zinc-500
        youngsModulus: 21000000.0,
        poissonsRatio: 0.25,
        unitWeightUnsaturated: 24.0,
        material_model: MaterialModel.LINEAR_ELASTIC,
        drainage_type: DrainageType.NON_POROUS,
    },
];

export const SAMPLE_POLYGONS: PolygonData[] = [
    // Bottom Layer (Sand)
    {
        vertices: [
            { x: -10, y: -3 },
            { x: 10, y: -3 },
            { x: 10, y: 0 },
            { x: -10, y: 0 },
        ],
        materialId: 'mat_sand',
    },
    // Top Layer (Clay)
    {
        vertices: [
            { x: -10, y: 0 },
            { x: 10, y: 0 },
            { x: 10, y: 2 },
            { x: -10, y: 2 },
        ],
        materialId: 'mat_undrained_c_clay',
    },
    // Top Layer (Clay)
    {
        vertices: [
            { x: -10, y: 2 },
            { x: -1, y: 2 },
            { x: -1, y: 2.4 },
            { x: -10, y: 2.4 },
        ],
        materialId: 'mat_undrained_a_clay',
    },
    // Top Layer (Clay)
    {
        vertices: [
            { x: 10, y: 2 },
            { x: 1, y: 2 },
            { x: 1, y: 2.4 },
            { x: 10, y: 2.4 },
        ],
        materialId: 'mat_undrained_a_clay',
    },
    // Top Layer (Clay)
    {
        vertices: [
            { x: -10, y: 2.4 },
            { x: -0.2, y: 2.4 },
            { x: -0.2, y: 3.0 },
            { x: -10, y: 3.0 },
        ],
        materialId: 'mat_undrained_a_clay',
    },
    // Top Layer (Clay)
    {
        vertices: [
            { x: 10, y: 2.4 },
            { x: 0.2, y: 2.4 },
            { x: 0.2, y: 3.0 },
            { x: 10, y: 3.0 },
        ],
        materialId: 'mat_undrained_a_clay',
    },
    // Top Layer (Clay)
    {
        vertices: [
            { x: -10, y: 3.0 },
            { x: -0.2, y: 3.0 },
            { x: -0.2, y: 3.5 },
            { x: -10, y: 3.5 },
        ],
        materialId: 'mat_undrained_a_clay',
    },
    {
        vertices: [
            { x: 10, y: 3.0 },
            { x: 0.2, y: 3.0 },
            { x: 0.2, y: 3.5 },
            { x: 10, y: 3.5 },
        ],
        materialId: 'mat_undrained_a_clay',
    },
    // Foundation
    {
        vertices: [
            { x: -1, y: 2 },
            { x: -1, y: 2.4 },
            { x: -0.2, y: 2.4 },
            { x: -0.2, y: 3.5 },
            { x: 0.2, y: 3.5 },
            { x: 0.2, y: 2.4 },
            { x: 1, y: 2.4 },
            { x: 1, y: 2 },
        ],
        materialId: 'mat_non_porous',
    },
];

export const SAMPLE_POINT_LOADS: PointLoad[] = [
    {
        id: 'load_1',
        x: 0,
        y: 3.5,
        fx: 0.0,
        fy: -200.0, // 100 kN downward
    },
];

export const DEFAULT_BEAM_MATERIALS: EmbeddedBeamMaterial[] = [
    {
        id: 'bmat_default',
        name: 'Standard Pile',
        color: '#f59e0b', // amber-500
        youngsModulus: 30000000,
        crossSectionArea: 0.2,
        momentOfInertia: 0.005,
        unitWeight: 7.85,
        spacing: 2.0,
        skinFrictionMax: 100,
        tipResistanceMax: 500,
        shape: 'user_defined',
    }
];

export const SAMPLE_WATER_LEVELS: WaterLevel[] = [
    {
        id: 'wl_default',
        name: 'Initial Water Level',
        points: [
            { x: -10, y: 2 },
            { x: 10, y: 2 }
        ]
    }
];

// Helper: build polygon->material map from polygons
const buildMaterialMap = (): Record<number, string> => {
    const map: Record<number, string> = {};
    SAMPLE_POLYGONS.forEach((poly, i) => {
        map[i] = poly.materialId;
    });
    return map;
};

const BASE_MATERIAL_MAP = buildMaterialMap();

export const SAMPLE_PHASES: PhaseRequest[] = [
    {
        id: 'phase_0',
        name: 'Initial (K0 Procedure)',
        phase_type: PhaseType.K0_PROCEDURE,
        active_polygon_indices: [0, 1], // Bottom soil and structures
        active_load_ids: [],
        active_water_level_id: 'wl_default',
        reset_displacements: false,
        current_material: { ...BASE_MATERIAL_MAP },
        parent_material: {},  // No parent
    },
    {
        id: 'phase_1',
        name: 'Fill 1',
        phase_type: PhaseType.PLASTIC,
        parent_id: 'phase_0',
        active_polygon_indices: [0, 1, 2, 3], // Add another layer
        active_load_ids: [],
        active_water_level_id: 'wl_default',
        reset_displacements: true,
        current_material: { ...BASE_MATERIAL_MAP },
        parent_material: { ...BASE_MATERIAL_MAP },
    },
    {
        id: 'phase_2',
        name: 'Foundation',
        phase_type: PhaseType.PLASTIC,
        parent_id: 'phase_1',
        active_polygon_indices: [0, 1, 2, 3, 8],
        active_load_ids: [''], // Assuming some load ID exists
        active_water_level_id: 'wl_default',
        reset_displacements: false,
        current_material: { ...BASE_MATERIAL_MAP },
        parent_material: { ...BASE_MATERIAL_MAP },
    },
    {
        id: 'phase_3',
        name: 'Fill 2',
        phase_type: PhaseType.PLASTIC,
        parent_id: 'phase_2',
        active_polygon_indices: [0, 1, 2, 3, 4, 5, 8],
        active_load_ids: [''], // Assuming some load ID exists
        active_water_level_id: 'wl_default',
        reset_displacements: false,
        current_material: { ...BASE_MATERIAL_MAP },
        parent_material: { ...BASE_MATERIAL_MAP },
    },
    {
        id: 'phase_4',
        name: 'Fill 3',
        phase_type: PhaseType.PLASTIC,
        parent_id: 'phase_3',
        active_polygon_indices: [0, 1, 2, 3, 4, 5, 6, 7, 8],
        active_load_ids: [''], // Assuming some load ID exists
        active_water_level_id: 'wl_default',
        reset_displacements: false,
        current_material: { ...BASE_MATERIAL_MAP },
        parent_material: { ...BASE_MATERIAL_MAP },
    },
    {
        id: 'phase_5',
        name: 'Load',
        phase_type: PhaseType.PLASTIC,
        parent_id: 'phase_4',
        active_polygon_indices: [0, 1, 2, 3, 4, 5, 6, 7, 8],
        active_load_ids: ['load_1'], // Assuming some load ID exists
        active_water_level_id: 'wl_default',
        reset_displacements: false,
        current_material: { ...BASE_MATERIAL_MAP },
        parent_material: { ...BASE_MATERIAL_MAP },
    },
    {
        id: 'phase_6',
        name: 'SF',
        phase_type: PhaseType.SAFETY_ANALYSIS,
        parent_id: 'phase_5',
        active_polygon_indices: [0, 1, 2, 3, 4, 5, 6, 7, 8],
        active_load_ids: ['load_1'], // Assuming some load ID exists
        active_water_level_id: 'wl_default',
        reset_displacements: false,
        current_material: { ...BASE_MATERIAL_MAP },
        parent_material: { ...BASE_MATERIAL_MAP },
    }
];

export const SAMPLE_GENERAL_SETTINGS: GeneralSettings = {
    snapSpacing: 0.5,
    snapToGrid: true,
    hideGrid: false,
    hideRuler: false,
};

export const SAMPLE_MESH_SETTINGS: MeshSettings = {
    mesh_size: 0.5,
    boundary_refinement_factor: 0.5,
};

export const SAMPLE_FOUNDATION = {
    name: "Foundation Sample",
    materials: SAMPLE_MATERIALS,
    polygons: SAMPLE_POLYGONS,
    pointLoads: SAMPLE_POINT_LOADS,
    beamMaterials: DEFAULT_BEAM_MATERIALS,
    phases: SAMPLE_PHASES,
    waterLevels: SAMPLE_WATER_LEVELS,
    lineLoads: [],
    meshSettings: SAMPLE_MESH_SETTINGS,
};
