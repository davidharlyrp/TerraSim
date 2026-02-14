
import { DrainageType, MaterialModel, PhaseRequest, PhaseType, PointLoad, PolygonData, Material, WaterLevel, LineLoad, GeneralSettings, SolverSettings, MeshSettings } from '../../types';

export const SAMPLE_MATERIALS: Material[] = [
    {
        cohesion: 0,
        color: "#eab308",
        drainage_type: DrainageType.DRAINED,
        effyoungsModulus: 50000,
        frictionAngle: 38,
        id: "mat_sand",
        material_model: MaterialModel.MOHR_COULOMB,
        name: "Dense Sand",
        poissonsRatio: 0.3,
        unitWeightSaturated: 20,
        unitWeightUnsaturated: 18
    },
    {
        cohesion: 8,
        color: "#12a41e",
        drainage_type: DrainageType.UNDRAINED_A,
        effyoungsModulus: 9000,
        frictionAngle: 25,
        id: "mat_undrained_a_clay",
        material_model: MaterialModel.MOHR_COULOMB,
        name: "Stiff Clay (Undr A)",
        poissonsRatio: 0.35,
        unitWeightSaturated: 17,
        unitWeightUnsaturated: 16
    },
    {
        color: "#71717a",
        drainage_type: DrainageType.UNDRAINED_B,
        effyoungsModulus: 9000,
        id: "mat_undrained_b_clay",
        material_model: MaterialModel.MOHR_COULOMB,
        name: "Stiff Clay (Undr B)",
        poissonsRatio: 0.4,
        undrainedShearStrength: 30,
        unitWeightSaturated: 16,
        unitWeightUnsaturated: 15
    },
    {
        color: "#1b1ba0",
        drainage_type: DrainageType.UNDRAINED_C,
        id: "mat_undrained_c_clay",
        material_model: MaterialModel.MOHR_COULOMB,
        name: "Stiff Clay (Undr C)",
        poissonsRatio: 0.49,
        undrainedShearStrength: 50,
        unitWeightSaturated: 15,
        unitWeightUnsaturated: 15,
        youngsModulus: 15000
    },
    {
        color: "#c16523",
        drainage_type: DrainageType.NON_POROUS,
        id: "mat_non_porous",
        material_model: MaterialModel.LINEAR_ELASTIC,
        name: "Concrete (Non-Porous)",
        poissonsRatio: 0.25,
        unitWeightUnsaturated: 24,
        youngsModulus: 21000000
    }
];

export const SAMPLE_POLYGONS: PolygonData[] = [
    {
        materialId: "mat_sand",
        vertices: [{ x: -35, y: -2 }, { x: 35, y: -2 }, { x: 35, y: -10 }, { x: -35, y: -10 }]
    },
    {
        materialId: "mat_undrained_c_clay",
        vertices: [{ x: 20, y: 7 }, { x: 19, y: 8 }, { x: -20, y: 8 }, { x: -21, y: 7 }]
    },
    {
        materialId: "mat_undrained_a_clay",
        vertices: [{ x: 20, y: 7 }, { x: -20.5, y: 7 }, { x: -20.5, y: 6.5 }, { x: -22.5, y: 6.5 }, { x: -22.5, y: 7 }, { x: -35, y: 7 }, { x: -35, y: 2 }, { x: 35, y: 2 }, { x: 35, y: 7 }]
    },
    {
        materialId: "mat_non_porous",
        vertices: [{ x: -22.5, y: 7 }, { x: -20.5, y: 7 }, { x: -20.5, y: 6.5 }, { x: -22.5, y: 6.5 }]
    },
    {
        materialId: "mat_non_porous",
        vertices: [{ x: -21, y: 7 }, { x: -21, y: 9 }, { x: -21.5, y: 9 }, { x: -22, y: 7 }]
    },
    {
        materialId: "mat_undrained_b_clay",
        vertices: [{ x: -20, y: 8 }, { x: -21, y: 8 }, { x: -21, y: 7 }]
    },
    {
        materialId: "mat_undrained_c_clay",
        vertices: [{ x: -20, y: 8 }, { x: -19, y: 9 }, { x: 18, y: 9 }, { x: 19, y: 8 }]
    },
    {
        materialId: "mat_undrained_c_clay",
        vertices: [{ x: 18, y: 9 }, { x: 17, y: 10 }, { x: -18, y: 10 }, { x: -19, y: 9 }]
    },
    {
        materialId: "mat_undrained_c_clay",
        vertices: [{ x: 17, y: 10 }, { x: 16, y: 11 }, { x: -17, y: 11 }, { x: -18, y: 10 }]
    },
    {
        materialId: "mat_undrained_c_clay",
        vertices: [{ x: 16, y: 11 }, { x: 15, y: 12 }, { x: -16, y: 12 }, { x: -17, y: 11 }]
    },
    {
        materialId: "mat_undrained_b_clay",
        vertices: [{ x: -21, y: 9 }, { x: -19, y: 9 }, { x: -20, y: 8 }, { x: -21, y: 8 }]
    },
    {
        materialId: "mat_undrained_b_clay",
        vertices: [{ x: -21, y: 9 }, { x: -20.5, y: 10 }, { x: -18, y: 10 }, { x: -19, y: 9 }]
    },
    {
        materialId: "mat_undrained_b_clay",
        vertices: [{ x: -20.5, y: 10 }, { x: -20, y: 11 }, { x: -17, y: 11 }, { x: -18, y: 10 }]
    },
    {
        materialId: "mat_undrained_b_clay",
        vertices: [{ x: -20, y: 11 }, { x: -19.5, y: 12 }, { x: -16, y: 12 }, { x: -17, y: 11 }]
    },
    {
        materialId: "mat_undrained_b_clay",
        vertices: [{ x: -35, y: 2 }, { x: 35, y: 2 }, { x: 35, y: -2 }, { x: -35, y: -2 }]
    }
];

export const SAMPLE_LINE_LOADS: LineLoad[] = [
    {
        fx: 0,
        fy: -15,
        id: "line_load_1770979537515",
        x1: 14,
        x2: -15,
        y1: 12,
        y2: 12
    },
    {
        fx: 0,
        fy: -15,
        id: "line_load_1770979541044",
        x1: -15,
        x2: -18,
        y1: 12,
        y2: 12
    }
];

export const SAMPLE_POINT_LOADS: PointLoad[] = [];

export const SAMPLE_WATER_LEVELS: WaterLevel[] = [
    {
        id: "wl_1770979395644",
        name: "Water Level 2",
        points: [{ x: -35, y: 6 }, { x: -1, y: 6 }, { x: 12, y: -2 }, { x: 35, y: -2.5 }]
    }
];

export const SAMPLE_PHASES: PhaseRequest[] = [
    {
        active_load_ids: [],
        active_polygon_indices: [0, 2, 14, 3],
        active_water_level_id: "wl_1770979395644",
        current_material: { "0": "mat_sand", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "14": "mat_undrained_b_clay" },
        id: "phase_0",
        name: "Initial (K0 Procedure)",
        parent_material: {},
        phase_type: PhaseType.K0_PROCEDURE,
        reset_displacements: false
    },
    {
        active_load_ids: [],
        active_polygon_indices: [0, 2, 14, 3, 1],
        active_water_level_id: "wl_1770979395644",
        current_material: { "0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "14": "mat_undrained_b_clay" },
        id: "phase_1771084929350",
        name: "Fill 1",
        parent_id: "phase_0",
        parent_material: { "0": "mat_sand", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "14": "mat_undrained_b_clay" },
        phase_type: PhaseType.PLASTIC,
        reset_displacements: false
    },
    {
        active_load_ids: [],
        active_polygon_indices: [0, 2, 14, 3, 1, 6],
        active_water_level_id: "wl_1770979395644",
        current_material: { "0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "6": "mat_undrained_c_clay", "14": "mat_undrained_b_clay" },
        id: "phase_1771085317662",
        name: "Fill 2",
        parent_id: "phase_1771084929350",
        parent_material: { "0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "14": "mat_undrained_b_clay" },
        phase_type: PhaseType.PLASTIC,
        reset_displacements: false
    },
    {
        active_load_ids: [],
        active_polygon_indices: [0, 2, 14, 3, 1, 6, 7],
        active_water_level_id: "wl_1770979395644",
        current_material: { "0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "14": "mat_undrained_b_clay" },
        id: "phase_1771085837826",
        name: "Fill 3",
        parent_id: "phase_1771085317662",
        parent_material: { "0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "6": "mat_undrained_c_clay", "14": "mat_undrained_b_clay" },
        phase_type: PhaseType.PLASTIC,
        reset_displacements: false
    },
    {
        active_load_ids: [],
        active_polygon_indices: [0, 2, 14, 3, 1, 6, 7, 8],
        active_water_level_id: "wl_1770979395644",
        current_material: { "0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "14": "mat_undrained_b_clay" },
        id: "phase_1771085853714",
        name: "Fill 4",
        parent_id: "phase_1771085837826",
        parent_material: { "0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "14": "mat_undrained_b_clay" },
        phase_type: PhaseType.PLASTIC,
        reset_displacements: false
    },
    {
        active_load_ids: [],
        active_polygon_indices: [0, 2, 14, 3, 1, 6, 7, 8, 9],
        active_water_level_id: "wl_1770979395644",
        current_material: { "0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "14": "mat_undrained_b_clay" },
        id: "phase_1771086262027",
        name: "Fill 5",
        parent_id: "phase_1771085853714",
        parent_material: { "0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "14": "mat_undrained_b_clay" },
        phase_type: PhaseType.PLASTIC,
        reset_displacements: false
    },
    {
        active_load_ids: ["line_load_1770979537515"],
        active_polygon_indices: [0, 2, 14, 3, 1, 6, 7, 8, 9],
        active_water_level_id: "wl_1770979395644",
        current_material: { "0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "14": "mat_undrained_b_clay" },
        id: "phase_1771086372337",
        name: "Load",
        parent_id: "phase_1771086262027",
        parent_material: { "0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "14": "mat_undrained_b_clay" },
        phase_type: PhaseType.PLASTIC,
        reset_displacements: false
    },
    {
        active_load_ids: ["line_load_1770979537515"],
        active_polygon_indices: [0, 2, 14, 3, 1, 6, 7, 8, 9],
        active_water_level_id: "wl_1770979395644",
        current_material: { "0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "14": "mat_undrained_b_clay" },
        id: "phase_1771086386492",
        name: "SF",
        parent_id: "phase_1771086372337",
        parent_material: { "0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "14": "mat_undrained_b_clay" },
        phase_type: PhaseType.SAFETY_ANALYSIS,
        reset_displacements: false
    },
    {
        active_load_ids: ["line_load_1770979537515"],
        active_polygon_indices: [0, 2, 14, 3, 1, 6, 7, 8, 9, 4],
        active_water_level_id: "wl_1770979395644",
        current_material: { "0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_non_porous", "4": "mat_non_porous", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "14": "mat_undrained_b_clay" },
        id: "phase_1771086481217",
        name: "DPT",
        parent_id: "phase_1771086262027",
        parent_material: { "0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "14": "mat_undrained_b_clay" },
        phase_type: PhaseType.PLASTIC,
        reset_displacements: false
    },
    {
        active_load_ids: ["line_load_1770979537515"],
        active_polygon_indices: [0, 2, 14, 3, 1, 6, 7, 8, 9, 4, 5],
        active_water_level_id: "wl_1770979395644",
        current_material: { "0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_non_porous", "4": "mat_non_porous", "5": "mat_undrained_b_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "14": "mat_undrained_b_clay" },
        id: "phase_1771086766783",
        name: "Fill 6",
        parent_id: "phase_1771086481217",
        parent_material: { "0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_non_porous", "4": "mat_non_porous", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "14": "mat_undrained_b_clay" },
        phase_type: PhaseType.PLASTIC,
        reset_displacements: false
    },
    {
        active_load_ids: ["line_load_1770979537515"],
        active_polygon_indices: [0, 2, 14, 3, 1, 6, 7, 8, 9, 4, 5, 10],
        active_water_level_id: "wl_1770979395644",
        current_material: { "0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_non_porous", "4": "mat_non_porous", "5": "mat_undrained_b_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "10": "mat_undrained_b_clay", "14": "mat_undrained_b_clay" },
        id: "phase_1771089144181",
        name: "Fill 7",
        parent_id: "phase_1771086766783",
        parent_material: { "0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_non_porous", "4": "mat_non_porous", "5": "mat_undrained_b_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "14": "mat_undrained_b_clay" },
        phase_type: PhaseType.PLASTIC,
        reset_displacements: false
    },
    {
        active_load_ids: ["line_load_1770979537515"],
        active_polygon_indices: [0, 2, 14, 3, 1, 6, 7, 8, 9, 4, 5, 10, 11],
        active_water_level_id: "wl_1770979395644",
        current_material: { "0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_non_porous", "4": "mat_non_porous", "5": "mat_undrained_b_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "10": "mat_undrained_b_clay", "11": "mat_undrained_b_clay", "14": "mat_undrained_b_clay" },
        id: "phase_1771089153741",
        name: "Fill 8",
        parent_id: "phase_1771089144181",
        parent_material: { "0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_non_porous", "4": "mat_non_porous", "5": "mat_undrained_b_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "10": "mat_undrained_b_clay", "14": "mat_undrained_b_clay" },
        phase_type: PhaseType.PLASTIC,
        reset_displacements: false
    },
    {
        active_load_ids: ["line_load_1770979537515"],
        active_polygon_indices: [0, 2, 14, 3, 1, 6, 7, 8, 9, 4, 5, 10, 11, 12],
        active_water_level_id: "wl_1770979395644",
        current_material: { "0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_non_porous", "4": "mat_non_porous", "5": "mat_undrained_b_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "10": "mat_undrained_b_clay", "11": "mat_undrained_b_clay", "12": "mat_undrained_b_clay", "14": "mat_undrained_b_clay" },
        id: "phase_1771089526803",
        name: "Fill 9",
        parent_id: "phase_1771089153741",
        parent_material: { "0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_non_porous", "4": "mat_non_porous", "5": "mat_undrained_b_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "10": "mat_undrained_b_clay", "11": "mat_undrained_b_clay", "14": "mat_undrained_b_clay" },
        phase_type: PhaseType.PLASTIC,
        reset_displacements: false
    },
    {
        active_load_ids: ["line_load_1770979537515"],
        active_polygon_indices: [0, 2, 14, 3, 1, 6, 7, 8, 9, 4, 5, 10, 11, 12, 13],
        active_water_level_id: "wl_1770979395644",
        current_material: { "0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_non_porous", "4": "mat_non_porous", "5": "mat_undrained_b_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "10": "mat_undrained_b_clay", "11": "mat_undrained_b_clay", "12": "mat_undrained_b_clay", "13": "mat_undrained_b_clay", "14": "mat_undrained_b_clay" },
        id: "phase_1771090689663",
        name: "Fill 10",
        parent_id: "phase_1771089526803",
        parent_material: { "0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_non_porous", "4": "mat_non_porous", "5": "mat_undrained_b_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "10": "mat_undrained_b_clay", "11": "mat_undrained_b_clay", "12": "mat_undrained_b_clay", "14": "mat_undrained_b_clay" },
        phase_type: PhaseType.PLASTIC,
        reset_displacements: false
    },
    {
        active_load_ids: ["line_load_1770979537515", "line_load_1770979541044"],
        active_polygon_indices: [0, 2, 14, 3, 1, 6, 7, 8, 9, 4, 5, 10, 11, 12, 13],
        active_water_level_id: "wl_1770979395644",
        current_material: { "0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_non_porous", "4": "mat_non_porous", "5": "mat_undrained_b_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "10": "mat_undrained_b_clay", "11": "mat_undrained_b_clay", "12": "mat_undrained_b_clay", "13": "mat_undrained_b_clay", "14": "mat_undrained_b_clay" },
        id: "phase_1771090939946",
        name: "Load",
        parent_id: "phase_1771090689663",
        parent_material: { "0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_non_porous", "4": "mat_non_porous", "5": "mat_undrained_b_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "10": "mat_undrained_b_clay", "11": "mat_undrained_b_clay", "12": "mat_undrained_b_clay", "13": "mat_undrained_b_clay", "14": "mat_undrained_b_clay" },
        phase_type: PhaseType.PLASTIC,
        reset_displacements: false
    },
    {
        active_load_ids: ["line_load_1770979537515", "line_load_1770979541044"],
        active_polygon_indices: [0, 2, 14, 3, 1, 6, 7, 8, 9, 4, 5, 10, 11, 12, 13],
        active_water_level_id: "wl_1770979395644",
        current_material: { "0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_non_porous", "4": "mat_non_porous", "5": "mat_undrained_b_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "10": "mat_undrained_b_clay", "11": "mat_undrained_b_clay", "12": "mat_undrained_b_clay", "13": "mat_undrained_b_clay", "14": "mat_undrained_b_clay" },
        id: "phase_1771090946451",
        name: "SF",
        parent_id: "phase_1771090939946",
        parent_material: { "0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_non_porous", "4": "mat_non_porous", "5": "mat_undrained_b_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "10": "mat_undrained_b_clay", "11": "mat_undrained_b_clay", "12": "mat_undrained_b_clay", "13": "mat_undrained_b_clay", "14": "mat_undrained_b_clay" },
        phase_type: PhaseType.SAFETY_ANALYSIS,
        reset_displacements: false
    }
];

export const SAMPLE_GENERAL_SETTINGS: GeneralSettings = {
    snapSpacing: 0.5,
    snapToGrid: true
};

export const SAMPLE_SOLVER_SETTINGS: SolverSettings = {
    initial_step_size: 0.05,
    max_desired_iterations: 15,
    max_iterations: 60,
    max_load_fraction: 0.5,
    max_steps: 100,
    min_desired_iterations: 3,
    tolerance: 0.01
};

export const SAMPLE_MESH_SETTINGS: MeshSettings = {
    boundary_refinement_factor: 1,
    mesh_size: 1.1
};

export const SAMPLE_RETAINING_WALL = {
    name: "Retaining Wall Embankment",
    materials: SAMPLE_MATERIALS,
    polygons: SAMPLE_POLYGONS,
    pointLoads: SAMPLE_POINT_LOADS,
    lineLoads: SAMPLE_LINE_LOADS,
    phases: SAMPLE_PHASES,
    waterLevels: SAMPLE_WATER_LEVELS,
    generalSettings: SAMPLE_GENERAL_SETTINGS,
    solverSettings: SAMPLE_SOLVER_SETTINGS,
    meshSettings: SAMPLE_MESH_SETTINGS
};
