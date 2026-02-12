import { DrainageType, MaterialModel, MeshRequest, SolverSettings, PhaseRequest, PhaseType, MeshSettings } from './types';

// Sample Materials
export const SAMPLE_MATERIALS = [
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

// Sample Geometry (Polygons)
// export const SAMPLE_POLYGONS = [
// Bottom Layer (Sand)
// {
//     vertices: [
//         { x: -25, y: -10 },
//         { x: 25, y: -10 },
//         { x: 25, y: 0 },
//         { x: -25, y: 0 },
//     ],
//     materialId: 'mat_sand',
// },
// // Top Layer (Clay)
// {
//     vertices: [
//         { x: -25, y: 0 },
//         { x: 25, y: 0 },
//         { x: 25, y: 10 },
//         { x: -25, y: 10 },
//     ],
//     materialId: 'mat_undrained_c_clay',
// },
// // Top Layer (Clay)
// {
//     vertices: [
//         { x: -5, y: 10 },
//         { x: 25, y: 10 },
//         { x: 25, y: 15 },
//         { x: 0, y: 15 },
//     ],
//     materialId: 'mat_undrained_b_clay',
// },
// // Top Layer (Clay)
// {
//     vertices: [
//         { x: -25, y: 10 },
//         { x: -5, y: 10 },
//         { x: 0, y: 15 },
//         { x: -25, y: 15 },
//     ],
//     materialId: 'mat_undrained_a_clay',
// },
// ];


export const SAMPLE_POLYGONS = [
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

// Sample Point Loads
export const SAMPLE_POINT_LOADS = [
    {
        id: 'load_1',
        x: 0,
        y: 3.5,
        fx: 0.0,
        fy: -200.0, // 100 kN downward
    },
];

export const SAMPLE_MESH_SETTINGS: MeshSettings = {
    mesh_size: 0.5,
    boundary_refinement_factor: 1,
};

// Composed Mesh Request
export const SAMPLE_MESH_REQUEST: MeshRequest = {
    polygons: SAMPLE_POLYGONS,
    materials: SAMPLE_MATERIALS,
    pointLoads: SAMPLE_POINT_LOADS,
    // water_level: [
    //     { x: -25, y: 3 },
    //     { x: 0, y: 5 },
    //     { x: 25, y: 10 },
    // ],
    water_level: [
        { x: -10, y: 2 },
        { x: 10, y: 2 }
    ],
    water_levels: [
        {
            id: 'wl_default',
            name: 'Initial Water Level',
            points: [
                { x: -10, y: 2 },
                { x: 10, y: 2 }
            ]
        }
    ],
    mesh_settings: SAMPLE_MESH_SETTINGS
};

// Sample Phases for Embankment Model
// export const SAMPLE_PHASES: PhaseRequest[] = [
// {
//     id: 'phase_0',
//     name: 'Initial (K0 Procedure)',
//     phase_type: PhaseType.K0_PROCEDURE,
//     active_polygon_indices: [0, 1], // Bottom soil and structures
//     active_load_ids: [],
//     reset_displacements: false
// },
// {
//     id: 'phase_1',
//     name: 'Embankment',
//     phase_type: PhaseType.PLASTIC,
//     parent_id: 'phase_0',
//     active_polygon_indices: [0, 1, 2, 3], // Add another layer
//     active_load_ids: [],
//     reset_displacements: true
// },
// {
//     id: 'phase_2',
//     name: 'Cut',
//     phase_type: PhaseType.PLASTIC,
//     parent_id: 'phase_1',
//     active_polygon_indices: [0, 1, 2],
//     active_load_ids: [], // Assuming some load ID exists
//     reset_displacements: false
// },
// {
//     id: 'phase_3',
//     name: 'SF',
//     phase_type: PhaseType.SAFETY_ANALYSIS,
//     parent_id: 'phase_2',
//     active_polygon_indices: [0, 1, 2],
//     active_load_ids: [], // Assuming some load ID exists
//     reset_displacements: false
// }
// ];


// Sample Phases for Foundation Model
export const SAMPLE_PHASES: PhaseRequest[] = [
    {
        id: 'phase_0',
        name: 'Initial (K0 Procedure)',
        phase_type: PhaseType.K0_PROCEDURE,
        active_polygon_indices: [0, 1], // Bottom soil and structures
        active_load_ids: [],
        active_water_level_id: 'wl_default',
        reset_displacements: false
    },
    {
        id: 'phase_1',
        name: 'Fill 1',
        phase_type: PhaseType.PLASTIC,
        parent_id: 'phase_0',
        active_polygon_indices: [0, 1, 2, 3], // Add another layer
        active_load_ids: [],
        reset_displacements: true
    },
    {
        id: 'phase_2',
        name: 'Foundation',
        phase_type: PhaseType.PLASTIC,
        parent_id: 'phase_1',
        active_polygon_indices: [0, 1, 2, 3, 8],
        active_load_ids: [''], // Assuming some load ID exists
        reset_displacements: false
    },
    {
        id: 'phase_3',
        name: 'Fill 2',
        phase_type: PhaseType.PLASTIC,
        parent_id: 'phase_2',
        active_polygon_indices: [0, 1, 2, 3, 4, 5, 8],
        active_load_ids: [''], // Assuming some load ID exists
        reset_displacements: false
    },
    {
        id: 'phase_4',
        name: 'Fill 3',
        phase_type: PhaseType.PLASTIC,
        parent_id: 'phase_3',
        active_polygon_indices: [0, 1, 2, 3, 4, 5, 6, 7, 8],
        active_load_ids: [''], // Assuming some load ID exists
        reset_displacements: false
    },
    {
        id: 'phase_5',
        name: 'Load',
        phase_type: PhaseType.PLASTIC,
        parent_id: 'phase_4',
        active_polygon_indices: [0, 1, 2, 3, 4, 5, 6, 7, 8],
        active_load_ids: ['load_1'], // Assuming some load ID exists
        reset_displacements: false
    },
    {
        id: 'phase_6',
        name: 'SF',
        phase_type: PhaseType.SAFETY_ANALYSIS,
        parent_id: 'phase_5',
        active_polygon_indices: [0, 1, 2, 3, 4, 5, 6, 7, 8],
        active_load_ids: ['load_1'], // Assuming some load ID exists
        reset_displacements: false
    }
];

// Sample Solver Settings
export const SAMPLE_SOLVER_SETTINGS: SolverSettings = {
    max_iterations: 60,
    min_desired_iterations: 3,
    max_desired_iterations: 15,
    initial_step_size: 0.05,
    tolerance: 0.01,
    max_load_fraction: 0.5,
    max_steps: 100,
};

// General Settings
export const SAMPLE_GENERAL_SETTINGS = {
    snapToGrid: true,
    snapSpacing: 0.5,
};
