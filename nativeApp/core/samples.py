# nativeApp/core/samples.py

SAMPLE_FOUNDATION = {
    "name": "Shallow Foundation Sample",
    "materials": [
        {
            "id": "mat_sand",
            "name": "Dense Sand",
            "color": "#eab308",
            "effyoungsModulus": 50000.0,
            "poissonsRatio": 0.3,
            "unitWeightSaturated": 20.0,
            "unitWeightUnsaturated": 18.0,
            "cohesion": 0.0,
            "frictionAngle": 38.0,
            "material_model": "mohr_coulomb",
            "drainage_type": "drained",
        },
        {
            "id": "mat_undrained_a_clay",
            "name": "Stiff Clay (Undr A)",
            "color": "#12a41e",
            "effyoungsModulus": 9000.0,
            "poissonsRatio": 0.35,
            "unitWeightSaturated": 17.0,
            "unitWeightUnsaturated": 16.0,
            "cohesion": 8.0,
            "frictionAngle": 25.0,
            "material_model": "mohr_coulomb",
            "drainage_type": "undrained_a",
        },
        {
            "id": "mat_undrained_b_clay",
            "name": "Stiff Clay (Undr B)",
            "color": "#71717a",
            "effyoungsModulus": 9000.0,
            "poissonsRatio": 0.4,
            "unitWeightSaturated": 16.0,
            "unitWeightUnsaturated": 15.0,
            "undrainedShearStrength": 30.0,
            "material_model": "mohr_coulomb",
            "drainage_type": "undrained_b",
        },
        {
            "id": "mat_undrained_c_clay",
            "name": "Stiff Clay (Undr C)",
            "color": "#1b1ba0",
            "youngsModulus": 15000.0,
            "poissonsRatio": 0.49,
            "unitWeightSaturated": 15.0,
            "unitWeightUnsaturated": 15.0,
            "undrainedShearStrength": 50.0,
            "material_model": "mohr_coulomb",
            "drainage_type": "undrained_c",
        },
        {
            "id": "mat_non_porous",
            "name": "Concrete (Non-Porous)",
            "color": "#c16523",
            "youngsModulus": 21000000.0,
            "poissonsRatio": 0.25,
            "unitWeightUnsaturated": 24.0,
            "material_model": "linear_elastic",
            "drainage_type": "non_porous",
        },
    ],
    "polygons": [
        {"vertices": [{"x": -10, "y": -3}, {"x": 10, "y": -3}, {"x": 10, "y": 0}, {"x": -10, "y": 0}], "materialId": "mat_sand"},
        {"vertices": [{"x": -10, "y":  0}, {"x": 10, "y":  0}, {"x": 10, "y": 2}, {"x": -10, "y": 2}], "materialId": "mat_undrained_c_clay"},
        {"vertices": [{"x": -10, "y":  2}, {"x": -1, "y":  2}, {"x": -1, "y": 2.4}, {"x": -10, "y": 2.4}], "materialId": "mat_undrained_a_clay"},
        {"vertices": [{"x":  10, "y":  2}, {"x":  1, "y":  2}, {"x":  1, "y": 2.4}, {"x":  10, "y": 2.4}], "materialId": "mat_undrained_a_clay"},
        {"vertices": [{"x": -10, "y": 2.4}, {"x": -0.2, "y": 2.4}, {"x": -0.2, "y": 3.0}, {"x": -10, "y": 3.0}], "materialId": "mat_undrained_a_clay"},
        {"vertices": [{"x":  10, "y": 2.4}, {"x":  0.2, "y": 2.4}, {"x":  0.2, "y": 3.0}, {"x":  10, "y": 3.0}], "materialId": "mat_undrained_a_clay"},
        {"vertices": [{"x": -10, "y": 3.0}, {"x": -0.2, "y": 3.0}, {"x": -0.2, "y": 3.5}, {"x": -10, "y": 3.5}], "materialId": "mat_undrained_a_clay"},
        {"vertices": [{"x":  10, "y": 3.0}, {"x":  0.2, "y": 3.0}, {"x":  0.2, "y": 3.5}, {"x":  10, "y": 3.5}], "materialId": "mat_undrained_a_clay"},
        {"vertices": [{"x": -1, "y": 2}, {"x": -1, "y": 2.4}, {"x": -0.2, "y": 2.4}, {"x": -0.2, "y": 3.5}, {"x": 0.2, "y": 3.5}, {"x": 0.2, "y": 2.4}, {"x": 1, "y": 2.4}, {"x": 1, "y": 2}], "materialId": "mat_non_porous"},
    ],
    "pointLoads": [
        {"id": "load_1", "x": 0, "y": 3.5, "fx": 0.0, "fy": -200.0},
    ],
    "lineLoads": [],
    "waterLevels": [
        {"id": "wl_default", "name": "Initial Water Level", "points": [{"x": -10, "y": 2}, {"x": 10, "y": 2}]},
    ],
    "meshSettings": {"mesh_size": 0.5, "boundary_refinement_factor": 0.5},
    "phases": [
        {
            "id": "f_ph0", "name": "Initial (K0 Procedure)", "phase_type": "K0_PROCEDURE", "parent_id": None,
            "active_polygon_indices": [0, 1], "active_load_ids": [], "active_water_level_id": "wl_default",
            "current_material": {"0": "mat_sand", "1": "mat_undrained_c_clay"}, "parent_material": {}, "reset_displacements": False
        },
        {
            "id": "f_ph1", "name": "Fill 1", "phase_type": "PLASTIC", "parent_id": "f_ph0",
            "active_polygon_indices": [0, 1, 2, 3], "active_load_ids": [], "active_water_level_id": "wl_default",
            "current_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay"}, 
            "parent_material": {"0": "mat_sand", "1": "mat_undrained_c_clay"}, "reset_displacements": True
        },
        {
            "id": "f_ph2", "name": "Foundation", "phase_type": "PLASTIC", "parent_id": "f_ph1",
            "active_polygon_indices": [0, 1, 2, 3, 8], "active_load_ids": [], "active_water_level_id": "wl_default",
            "current_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "8": "mat_non_porous"},
            "parent_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay"}, "reset_displacements": False
        },
        {
            "id": "f_ph3", "name": "Fill 2", "phase_type": "PLASTIC", "parent_id": "f_ph2",
            "active_polygon_indices": [0, 1, 2, 3, 4, 5, 8], "active_load_ids": [], "active_water_level_id": "wl_default",
            "current_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "4": "mat_undrained_a_clay", "5": "mat_undrained_a_clay", "8": "mat_non_porous"},
            "parent_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "8": "mat_non_porous"}, "reset_displacements": False
        },
        {
            "id": "f_ph4", "name": "Fill 3", "phase_type": "PLASTIC", "parent_id": "f_ph3",
            "active_polygon_indices": [0, 1, 2, 3, 4, 5, 6, 7, 8], "active_load_ids": [], "active_water_level_id": "wl_default",
            "current_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "4": "mat_undrained_a_clay", "5": "mat_undrained_a_clay", "6": "mat_undrained_a_clay", "7": "mat_undrained_a_clay", "8": "mat_non_porous"},
            "parent_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "4": "mat_undrained_a_clay", "5": "mat_undrained_a_clay", "8": "mat_non_porous"}, "reset_displacements": False
        },
        {
            "id": "f_ph5", "name": "Load", "phase_type": "PLASTIC", "parent_id": "f_ph4",
            "active_polygon_indices": [0, 1, 2, 3, 4, 5, 6, 7, 8], "active_load_ids": ["load_1"], "active_water_level_id": "wl_default",
            "current_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "4": "mat_undrained_a_clay", "5": "mat_undrained_a_clay", "6": "mat_undrained_a_clay", "7": "mat_undrained_a_clay", "8": "mat_non_porous"},
            "parent_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "4": "mat_undrained_a_clay", "5": "mat_undrained_a_clay", "6": "mat_undrained_a_clay", "7": "mat_undrained_a_clay", "8": "mat_non_porous"}, "reset_displacements": False
        },
        {
            "id": "f_ph6", "name": "SF Analysis", "phase_type": "SAFETY_ANALYSIS", "parent_id": "f_ph5",
            "active_polygon_indices": [0, 1, 2, 3, 4, 5, 6, 7, 8], "active_load_ids": ["load_1"], "active_water_level_id": "wl_default",
            "current_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "4": "mat_undrained_a_clay", "5": "mat_undrained_a_clay", "6": "mat_undrained_a_clay", "7": "mat_undrained_a_clay", "8": "mat_non_porous"},
            "parent_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "4": "mat_undrained_a_clay", "5": "mat_undrained_a_clay", "6": "mat_undrained_a_clay", "7": "mat_undrained_a_clay", "8": "mat_non_porous"}, "reset_displacements": False
        }
    ],
}

SAMPLE_RETAINING_WALL = {
    "name": "Retaining Wall Embankment",
    "materials": [
        {"id": "mat_sand", "name": "Dense Sand", "color": "#eab308", "effyoungsModulus": 50000, "poissonsRatio": 0.3, "unitWeightSaturated": 20, "unitWeightUnsaturated": 18, "cohesion": 0, "frictionAngle": 38, "material_model": "mohr_coulomb", "drainage_type": "drained"},
        {"id": "mat_undrained_a_clay", "name": "Stiff Clay (Undr A)", "color": "#12a41e", "effyoungsModulus": 9000, "poissonsRatio": 0.35, "unitWeightSaturated": 17, "unitWeightUnsaturated": 16, "cohesion": 8, "frictionAngle": 25, "material_model": "mohr_coulomb", "drainage_type": "undrained_a"},
        {"id": "mat_undrained_b_clay", "name": "Stiff Clay (Undr B)", "color": "#71717a", "effyoungsModulus": 9000, "poissonsRatio": 0.4, "unitWeightSaturated": 16, "unitWeightUnsaturated": 15, "undrainedShearStrength": 30, "material_model": "mohr_coulomb", "drainage_type": "undrained_b"},
        {"id": "mat_undrained_c_clay", "name": "Stiff Clay (Undr C)", "color": "#1b1ba0", "youngsModulus": 15000, "poissonsRatio": 0.49, "unitWeightSaturated": 15, "unitWeightUnsaturated": 15, "undrainedShearStrength": 50, "material_model": "mohr_coulomb", "drainage_type": "undrained_c"},
        {"id": "mat_non_porous", "name": "Concrete (Non-Porous)", "color": "#c16523", "youngsModulus": 21000000, "poissonsRatio": 0.25, "unitWeightUnsaturated": 24, "material_model": "linear_elastic", "drainage_type": "non_porous"},
    ],
    "polygons": [
        {"materialId": "mat_sand", "vertices": [{"x": -35, "y": -2}, {"x": 35, "y": -2}, {"x": 35, "y": -10}, {"x": -35, "y": -10}]},
        {"materialId": "mat_undrained_c_clay", "vertices": [{"x": 20, "y": 7}, {"x": 19, "y": 8}, {"x": -20, "y": 8}, {"x": -21, "y": 7}]},
        {"materialId": "mat_undrained_a_clay", "vertices": [{"x": 20, "y": 7}, {"x": -20.5, "y": 7}, {"x": -20.5, "y": 6.5}, {"x": -22.5, "y": 6.5}, {"x": -22.5, "y": 7}, {"x": -35, "y": 7}, {"x": -35, "y": 2}, {"x": 35, "y": 2}, {"x": 35, "y": 7}]},
        {"materialId": "mat_non_porous", "vertices": [{"x": -22.5, "y": 7}, {"x": -20.5, "y": 7}, {"x": -20.5, "y": 6.5}, {"x": -22.5, "y": 6.5}]},
        {"materialId": "mat_non_porous", "vertices": [{"x": -21, "y": 7}, {"x": -21, "y": 9}, {"x": -21.5, "y": 9}, {"x": -22, "y": 7}]},
        {"materialId": "mat_undrained_b_clay", "vertices": [{"x": -20, "y": 8}, {"x": -21, "y": 8}, {"x": -21, "y": 7}]},
        {"materialId": "mat_undrained_c_clay", "vertices": [{"x": -20, "y": 8}, {"x": -19, "y": 9}, {"x": 18, "y": 9}, {"x": 19, "y": 8}]},
        {"materialId": "mat_undrained_c_clay", "vertices": [{"x": 18, "y": 9}, {"x": 17, "y": 10}, {"x": -18, "y": 10}, {"x": -19, "y": 9}]},
        {"materialId": "mat_undrained_c_clay", "vertices": [{"x": 17, "y": 10}, {"x": 16, "y": 11}, {"x": -17, "y": 11}, {"x": -18, "y": 10}]},
        {"materialId": "mat_undrained_c_clay", "vertices": [{"x": 16, "y": 11}, {"x": 15, "y": 12}, {"x": -16, "y": 12}, {"x": -17, "y": 11}]},
        {"materialId": "mat_undrained_b_clay", "vertices": [{"x": -21, "y": 9}, {"x": -19, "y": 9}, {"x": -20, "y": 8}, {"x": -21, "y": 8}]},
        {"materialId": "mat_undrained_b_clay", "vertices": [{"x": -21, "y": 9}, {"x": -20.5, "y": 10}, {"x": -18, "y": 10}, {"x": -19, "y": 9}]},
        {"materialId": "mat_undrained_b_clay", "vertices": [{"x": -20.5, "y": 10}, {"x": -20, "y": 11}, {"x": -17, "y": 11}, {"x": -18, "y": 10}]},
        {"materialId": "mat_undrained_b_clay", "vertices": [{"x": -20, "y": 11}, {"x": -19.5, "y": 12}, {"x": -16, "y": 12}, {"x": -17, "y": 11}]},
        {"materialId": "mat_undrained_b_clay", "vertices": [{"x": -35, "y": 2}, {"x": 35, "y": 2}, {"x": 35, "y": -2}, {"x": -35, "y": -2}]},
    ],
    "pointLoads": [],
    "lineLoads": [
        {"id": "line_load_1", "x1": 14, "y1": 12, "x2": -15, "y2": 12, "fx": 0, "fy": -15},
        {"id": "line_load_2", "x1": -15, "y1": 12, "x2": -18, "y2": 12, "fx": 0, "fy": -15},
    ],
    "waterLevels": [
        {"id": "wl_1", "name": "Phreatic Surface", "points": [{"x": -35, "y": 6}, {"x": -1, "y": 6}, {"x": 12, "y": -2}, {"x": 35, "y": -2.5}]},
    ],
    "meshSettings": {"mesh_size": 1.1, "boundary_refinement_factor": 1.0},
    "phases": [
        {
            "id": "rw_ph0", "name": "Initial (K0 Procedure)", "phase_type": "K0_PROCEDURE", "parent_id": None,
            "active_polygon_indices": [0, 2, 14, 3], "active_load_ids": [], "active_water_level_id": "wl_1",
            "current_material": {"0": "mat_sand", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "14": "mat_undrained_b_clay"}, 
            "parent_material": {}, "reset_displacements": False
        },
        {
            "id": "rw_ph1", "name": "Fill 1", "phase_type": "PLASTIC", "parent_id": "rw_ph0",
            "active_polygon_indices": [0, 2, 14, 3, 1], "active_load_ids": [], "active_water_level_id": "wl_1",
            "current_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "14": "mat_undrained_b_clay"}, 
            "parent_material": {"0": "mat_sand", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "14": "mat_undrained_b_clay"}, "reset_displacements": False
        },
        {
            "id": "rw_ph2", "name": "Fill 2", "phase_type": "PLASTIC", "parent_id": "rw_ph1",
            "active_polygon_indices": [0, 2, 14, 3, 1, 6], "active_load_ids": [], "active_water_level_id": "wl_1",
            "current_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "6": "mat_undrained_c_clay", "14": "mat_undrained_b_clay"}, 
            "parent_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "14": "mat_undrained_b_clay"}, "reset_displacements": False
        },
        {
            "id": "rw_ph3", "name": "Fill 3", "phase_type": "PLASTIC", "parent_id": "rw_ph2",
            "active_polygon_indices": [0, 2, 14, 3, 1, 6, 7], "active_load_ids": [], "active_water_level_id": "wl_1",
            "current_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "14": "mat_undrained_b_clay"}, 
            "parent_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "6": "mat_undrained_c_clay", "14": "mat_undrained_b_clay"}, "reset_displacements": False
        },
        {
            "id": "rw_ph4", "name": "Fill 4", "phase_type": "PLASTIC", "parent_id": "rw_ph3",
            "active_polygon_indices": [0, 2, 14, 3, 1, 6, 7, 8], "active_load_ids": [], "active_water_level_id": "wl_1",
            "current_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "14": "mat_undrained_b_clay"}, 
            "parent_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "14": "mat_undrained_b_clay"}, "reset_displacements": False
        },
        {
            "id": "rw_ph5", "name": "Fill 5", "phase_type": "PLASTIC", "parent_id": "rw_ph4",
            "active_polygon_indices": [0, 2, 14, 3, 1, 6, 7, 8, 9], "active_load_ids": [], "active_water_level_id": "wl_1",
            "current_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "14": "mat_undrained_b_clay"}, 
            "parent_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "14": "mat_undrained_b_clay"}, "reset_displacements": False
        },
        # --- Branch A (from Fill 5) ---
        {
            "id": "rw_ph5_load", "name": "Load 1", "phase_type": "PLASTIC", "parent_id": "rw_ph5",
            "active_polygon_indices": [0, 2, 14, 3, 1, 6, 7, 8, 9], "active_load_ids": ["line_load_1"], "active_water_level_id": "wl_1",
            "current_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "14": "mat_undrained_b_clay"}, 
            "parent_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "14": "mat_undrained_b_clay"}, "reset_displacements": False
        },
        {
            "id": "rw_ph5_sf", "name": "SF 1", "phase_type": "SAFETY_ANALYSIS", "parent_id": "rw_ph5_load",
            "active_polygon_indices": [0, 2, 14, 3, 1, 6, 7, 8, 9], "active_load_ids": ["line_load_1"], "active_water_level_id": "wl_1",
            "current_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "14": "mat_undrained_b_clay"}, 
            "parent_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "14": "mat_undrained_b_clay"}, "reset_displacements": False
        },
        # --- Branch B (from Fill 5) ---
        {
            "id": "rw_ph_dpt", "name": "DPT Construction", "phase_type": "PLASTIC", "parent_id": "rw_ph5",
            "active_polygon_indices": [0, 2, 14, 3, 1, 6, 7, 8, 9, 4], "active_load_ids": [], "active_water_level_id": "wl_1",
            "current_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_non_porous", "4": "mat_non_porous", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "14": "mat_undrained_b_clay"}, 
            "parent_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_undrained_a_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "14": "mat_undrained_b_clay"}, "reset_displacements": False
        },
        {
            "id": "rw_ph6", "name": "Fill 6", "phase_type": "PLASTIC", "parent_id": "rw_ph_dpt",
            "active_polygon_indices": [0, 2, 14, 3, 1, 6, 7, 8, 9, 4, 5], "active_load_ids": [], "active_water_level_id": "wl_1",
            "current_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_non_porous", "4": "mat_non_porous", "5": "mat_undrained_b_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "14": "mat_undrained_b_clay"}, 
            "parent_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_non_porous", "4": "mat_non_porous", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "14": "mat_undrained_b_clay"}, "reset_displacements": False
        },
        {
            "id": "rw_ph7", "name": "Fill 7", "phase_type": "PLASTIC", "parent_id": "rw_ph6",
            "active_polygon_indices": [0, 2, 14, 3, 1, 6, 7, 8, 9, 4, 5, 10], "active_load_ids": [], "active_water_level_id": "wl_1",
            "current_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_non_porous", "4": "mat_non_porous", "5": "mat_undrained_b_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "10": "mat_undrained_b_clay", "14": "mat_undrained_b_clay"}, 
            "parent_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_non_porous", "4": "mat_non_porous", "5": "mat_undrained_b_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "14": "mat_undrained_b_clay"}, "reset_displacements": False
        },
        {
            "id": "rw_ph8", "name": "Fill 8", "phase_type": "PLASTIC", "parent_id": "rw_ph7",
            "active_polygon_indices": [0, 2, 14, 3, 1, 6, 7, 8, 9, 4, 5, 10, 11], "active_load_ids": [], "active_water_level_id": "wl_1",
            "current_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_non_porous", "4": "mat_non_porous", "5": "mat_undrained_b_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "10": "mat_undrained_b_clay", "11": "mat_undrained_b_clay", "14": "mat_undrained_b_clay"}, 
            "parent_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_non_porous", "4": "mat_non_porous", "5": "mat_undrained_b_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "10": "mat_undrained_b_clay", "14": "mat_undrained_b_clay"}, "reset_displacements": False
        },
        {
            "id": "rw_ph9", "name": "Fill 9", "phase_type": "PLASTIC", "parent_id": "rw_ph8",
            "active_polygon_indices": [0, 2, 14, 3, 1, 6, 7, 8, 9, 4, 5, 10, 11, 12], "active_load_ids": [], "active_water_level_id": "wl_1",
            "current_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_non_porous", "4": "mat_non_porous", "5": "mat_undrained_b_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "10": "mat_undrained_b_clay", "11": "mat_undrained_b_clay", "12": "mat_undrained_b_clay", "14": "mat_undrained_b_clay"}, 
            "parent_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_non_porous", "4": "mat_non_porous", "5": "mat_undrained_b_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "10": "mat_undrained_b_clay", "11": "mat_undrained_b_clay", "14": "mat_undrained_b_clay"}, "reset_displacements": False
        },
        {
            "id": "rw_ph10", "name": "Fill 10", "phase_type": "PLASTIC", "parent_id": "rw_ph9",
            "active_polygon_indices": [0, 2, 14, 3, 1, 6, 7, 8, 9, 4, 5, 10, 11, 12, 13], "active_load_ids": [], "active_water_level_id": "wl_1",
            "current_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_non_porous", "4": "mat_non_porous", "5": "mat_undrained_b_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "10": "mat_undrained_b_clay", "11": "mat_undrained_b_clay", "12": "mat_undrained_b_clay", "13": "mat_undrained_b_clay", "14": "mat_undrained_b_clay"}, 
            "parent_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_non_porous", "4": "mat_non_porous", "5": "mat_undrained_b_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "10": "mat_undrained_b_clay", "11": "mat_undrained_b_clay", "12": "mat_undrained_b_clay", "14": "mat_undrained_b_clay"}, "reset_displacements": False
        },
        {
            "id": "rw_ph_final_load", "name": "Final Load", "phase_type": "PLASTIC", "parent_id": "rw_ph10",
            "active_polygon_indices": [0, 2, 14, 3, 1, 6, 7, 8, 9, 4, 5, 10, 11, 12, 13], "active_load_ids": ["line_load_1", "line_load_2"], "active_water_level_id": "wl_1",
            "current_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_non_porous", "4": "mat_non_porous", "5": "mat_undrained_b_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "10": "mat_undrained_b_clay", "11": "mat_undrained_b_clay", "12": "mat_undrained_b_clay", "13": "mat_undrained_b_clay", "14": "mat_undrained_b_clay"}, 
            "parent_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_non_porous", "4": "mat_non_porous", "5": "mat_undrained_b_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "10": "mat_undrained_b_clay", "11": "mat_undrained_b_clay", "12": "mat_undrained_b_clay", "13": "mat_undrained_b_clay", "14": "mat_undrained_b_clay"}, "reset_displacements": False
        },
        {
            "id": "rw_ph_final_sf", "name": "Final SF Analysis", "phase_type": "SAFETY_ANALYSIS", "parent_id": "rw_ph_final_load",
            "active_polygon_indices": [0, 2, 14, 3, 1, 6, 7, 8, 9, 4, 5, 10, 11, 12, 13], "active_load_ids": ["line_load_1", "line_load_2"], "active_water_level_id": "wl_1",
            "current_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_non_porous", "4": "mat_non_porous", "5": "mat_undrained_b_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "10": "mat_undrained_b_clay", "11": "mat_undrained_b_clay", "12": "mat_undrained_b_clay", "13": "mat_undrained_b_clay", "14": "mat_undrained_b_clay"}, 
            "parent_material": {"0": "mat_sand", "1": "mat_undrained_c_clay", "2": "mat_undrained_a_clay", "3": "mat_non_porous", "4": "mat_non_porous", "5": "mat_undrained_b_clay", "6": "mat_undrained_c_clay", "7": "mat_undrained_c_clay", "8": "mat_undrained_c_clay", "9": "mat_undrained_c_clay", "10": "mat_undrained_b_clay", "11": "mat_undrained_b_clay", "12": "mat_undrained_b_clay", "13": "mat_undrained_b_clay", "14": "mat_undrained_b_clay"}, "reset_displacements": False
        }
    ],
}
