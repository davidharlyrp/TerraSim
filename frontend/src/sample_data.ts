
import { DrainageType, MaterialModel, PhaseRequest, PhaseType, MeshSettings, Material, SolverSettings } from './types';

// Default Data for New Project
export const DEFAULT_MATERIALS: Material[] = [
    {
        id: 'mat_default',
        name: 'Soil 1',
        color: '#94a3b8', // slate-400
        effyoungsModulus: 10000,
        poissonsRatio: 0.3,
        unitWeightUnsaturated: 18,
        material_model: MaterialModel.MOHR_COULOMB,
        drainage_type: DrainageType.DRAINED
    }
];

export const DEFAULT_PHASES: PhaseRequest[] = [
    {
        id: 'phase_initial',
        name: 'Initial Phase',
        phase_type: PhaseType.K0_PROCEDURE,
        active_polygon_indices: [],
        active_load_ids: [],
        reset_displacements: false,
        current_material: {},
        parent_material: {}
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

export const SAMPLE_MESH_SETTINGS: MeshSettings = {
    mesh_size: 0.5,
    boundary_refinement_factor: 1,
};
