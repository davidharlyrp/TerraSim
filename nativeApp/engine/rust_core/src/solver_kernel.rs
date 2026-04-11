/// Full stress computation loop — the performance-critical kernel.
///
/// This replaces the entire `compute_elements_stresses_numba` Python/Numba function
/// with a single Rust call, eliminating all Python-Rust FFI overhead per element.
///
/// The loop iterates over all active elements and their 3 Gauss points,
/// computing strain, trial stress, return mapping, and internal forces.

use numpy::ndarray::{Array1, Array2, Array3};
use numpy::{PyArray1, PyArray2, PyArray3, PyReadonlyArray1, PyReadonlyArray2, PyReadonlyArray3};
use pyo3::prelude::*;

use crate::elements::t6;
use crate::material_models::hoek_brown;
use crate::material_models::mohr_coulomb;

/// Full stress computation loop exposed to Python via PyO3.
///
/// This is a drop-in replacement for `compute_elements_stresses_numba`.
/// All array shapes match the Python/Numba version exactly.
#[pyfunction]
#[pyo3(name = "compute_stresses_loop")]
pub fn compute_stresses_loop_py<'py>(
    py: Python<'py>,
    element_nodes: PyReadonlyArray2<'py, i64>,      // (N, 6)
    total_u: PyReadonlyArray1<'py, f64>,             // (num_dof,)
    step_start_stress: PyReadonlyArray3<'py, f64>,   // (N, 3, 3)
    step_start_strain: PyReadonlyArray3<'py, f64>,   // (N, 3, 3)
    step_start_pwp: PyReadonlyArray2<'py, f64>,      // (N, 3)
    b_matrices: PyReadonlyArray2<'py, f64>,          // (N*3, 36) flattened B per GP
    det_j: PyReadonlyArray2<'py, f64>,               // (N, 3)
    weights: PyReadonlyArray1<'py, f64>,             // (3,)
    d_elastic: PyReadonlyArray3<'py, f64>,           // (N, 3, 3)
    pwp_static: PyReadonlyArray2<'py, f64>,          // (N, 3)
    mat_drainage: PyReadonlyArray1<'py, i64>,        // (N,)
    mat_model: PyReadonlyArray1<'py, i64>,           // (N,)
    mat_c: PyReadonlyArray1<'py, f64>,               // (N,)
    mat_phi: PyReadonlyArray1<'py, f64>,             // (N,)
    mat_su: PyReadonlyArray1<'py, f64>,              // (N,)
    mat_sigma_ci: PyReadonlyArray1<'py, f64>,        // (N,)
    mat_gsi: PyReadonlyArray1<'py, f64>,             // (N,)
    mat_disturb_factor: PyReadonlyArray1<'py, f64>,  // (N,)
    mat_mb: PyReadonlyArray1<'py, f64>,              // (N,)
    mat_s: PyReadonlyArray1<'py, f64>,               // (N,)
    mat_a: PyReadonlyArray1<'py, f64>,               // (N,)
    penalties: PyReadonlyArray1<'py, f64>,            // (N,)
    is_srm: bool,
    is_gravity_phase: bool,
    target_m_stage: f64,
    num_dof: usize,
) -> PyResult<(
    Bound<'py, PyArray1<f64>>,
    Bound<'py, PyArray3<f64>>,
    Bound<'py, PyArray2<bool>>,
    Bound<'py, PyArray3<f64>>,
    Bound<'py, PyArray2<f64>>,
)> {
    let elem_nodes = element_nodes.as_array();
    let u = total_u.as_array();
    let start_stress = step_start_stress.as_array();
    let start_strain = step_start_strain.as_array();
    let start_pwp = step_start_pwp.as_array();
    let b_mats_flat = b_matrices.as_array();
    let det_j_arr = det_j.as_array();
    let w_arr = weights.as_array();
    let d_el_arr = d_elastic.as_array();
    let pwp_s_arr = pwp_static.as_array();
    let drainage = mat_drainage.as_array();
    let model = mat_model.as_array();
    let c_arr = mat_c.as_array();
    let phi_arr = mat_phi.as_array();
    let su_arr = mat_su.as_array();
    let sci_arr = mat_sigma_ci.as_array();
    let gsi_arr = mat_gsi.as_array();
    let df_arr = mat_disturb_factor.as_array();
    let mb_arr = mat_mb.as_array();
    let s_arr = mat_s.as_array();
    let a_arr = mat_a.as_array();
    let pen_arr = penalties.as_array();

    let num_active = elem_nodes.shape()[0];

    let mut f_int = Array1::<f64>::zeros(num_dof);
    let mut new_stresses = Array3::<f64>::zeros((num_active, 3, 3));
    let mut new_yield = Array2::<bool>::default((num_active, 3));
    let mut new_strain = Array3::<f64>::zeros((num_active, 3, 3));
    let mut new_pwp_excess = Array2::<f64>::zeros((num_active, 3));

    for i in 0..num_active {
        // Gather element DOFs
        let mut u_el = [0.0f64; 12];
        for li in 0..6 {
            let n_idx = elem_nodes[[i, li]] as usize;
            u_el[li * 2] = u[n_idx * 3];
            u_el[li * 2 + 1] = u[n_idx * 3 + 1];
        }

        let mut f_int_el = [0.0f64; 12];
        let dtype = drainage[i];
        let mmodel = model[i];

        // D_elastic for this element (row-major flat)
        let mut d_flat = [0.0f64; 9];
        for r in 0..3 {
            for c in 0..3 {
                d_flat[r * 3 + c] = d_el_arr[[i, r, c]];
            }
        }

        let c_val = c_arr[i];
        let phi_val = phi_arr[i];
        let su_val = su_arr[i];
        let sci_val = sci_arr[i];
        let gsi_val = gsi_arr[i];
        let df_val = df_arr[i];
        let mb_val = mb_arr[i];
        let s_val = s_arr[i];
        let a_val = a_arr[i];
        let penalty = pen_arr[i];

        for gp_idx in 0..3usize {
            // B matrix for this GP (stored in flat array)
            let b_row = i * 3 + gp_idx;
            let mut b_gp = [0.0f64; 36];
            for k in 0..36 {
                b_gp[k] = b_mats_flat[[b_row, k]];
            }

            let det_j_val = det_j_arr[[i, gp_idx]];
            let weight = w_arr[gp_idx];
            let p_static = pwp_s_arr[[i, gp_idx]];

            // epsilon_total = B @ u_el
            let epsilon_total = t6::b_times_u(&b_gp, &u_el);
            let start_str = [
                start_strain[[i, gp_idx, 0]],
                start_strain[[i, gp_idx, 1]],
                start_strain[[i, gp_idx, 2]],
            ];
            let d_eps = [
                epsilon_total[0] - start_str[0],
                epsilon_total[1] - start_str[1],
                epsilon_total[2] - start_str[2],
            ];

            let sigma_start = [
                start_stress[[i, gp_idx, 0]],
                start_stress[[i, gp_idx, 1]],
                start_stress[[i, gp_idx, 2]],
            ];
            let pwp_excess_start = start_pwp[[i, gp_idx]];

            let (sig_new, yld, p_exc_new);

            if dtype == 3 {
                // UNDRAINED_C
                let d_sig = d_times_eps_fn(&d_flat, &d_eps);
                let trial = [
                    sigma_start[0] + d_sig[0],
                    sigma_start[1] + d_sig[1],
                    sigma_start[2] + d_sig[2],
                ];
                let mut su_eff = su_val;
                if is_srm {
                    su_eff /= target_m_stage;
                }
                if mmodel == 1 {
                    let (sx, sy, sxy, y) =
                        mohr_coulomb::return_mapping_mohr_coulomb(trial[0], trial[1], trial[2], su_eff, 0.0);
                    sig_new = [sx, sy, sxy];
                    yld = y;
                } else {
                    sig_new = trial;
                    yld = false;
                }
                p_exc_new = 0.0;
            } else if dtype == 1 || dtype == 2 {
                // UNDRAINED_A or B
                let mut d_total = d_flat;
                d_total[0] += penalty;
                d_total[1] += penalty;
                d_total[3] += penalty;
                d_total[4] += penalty;

                let d_sig = d_times_eps_fn(&d_total, &d_eps);
                let trial_total = [
                    sigma_start[0] + d_sig[0],
                    sigma_start[1] + d_sig[1],
                    sigma_start[2] + d_sig[2],
                ];
                let d_vol = d_eps[0] + d_eps[1];
                p_exc_new = pwp_excess_start + penalty * d_vol;
                let p_total = p_static + p_exc_new;

                let eff_trial = [
                    trial_total[0] - p_total,
                    trial_total[1] - p_total,
                    trial_total[2],
                ];

                if mmodel == 1 {
                    let (mut c_eff, mut phi_eff) = (c_val, phi_val);
                    if dtype == 2 {
                        c_eff = su_val;
                        phi_eff = 0.0;
                    }
                    if is_srm {
                        c_eff /= target_m_stage;
                        if phi_eff > 0.0 {
                            phi_eff = (phi_eff.to_radians().tan() / target_m_stage)
                                .atan()
                                .to_degrees();
                        }
                    }
                    let (sx, sy, sxy, y) = mohr_coulomb::return_mapping_mohr_coulomb(
                        eff_trial[0],
                        eff_trial[1],
                        eff_trial[2],
                        c_eff,
                        phi_eff,
                    );
                    sig_new = [sx + p_total, sy + p_total, sxy];
                    yld = y;
                } else {
                    sig_new = trial_total;
                    yld = false;
                }
            } else {
                // DRAINED or NON_POROUS
                let eff_start = [
                    sigma_start[0] - p_static,
                    sigma_start[1] - p_static,
                    sigma_start[2],
                ];
                let d_sig = d_times_eps_fn(&d_flat, &d_eps);
                let eff_trial = [
                    eff_start[0] + d_sig[0],
                    eff_start[1] + d_sig[1],
                    eff_start[2] + d_sig[2],
                ];

                let skip_yield = is_gravity_phase && (dtype == 0);

                if mmodel == 1 && !skip_yield {
                    let (mut c_eff, mut phi_eff) = (c_val, phi_val);
                    if is_srm {
                        c_eff /= target_m_stage;
                        if phi_eff > 0.0 {
                            phi_eff = (phi_eff.to_radians().tan() / target_m_stage)
                                .atan()
                                .to_degrees();
                        }
                    }
                    let (sx, sy, sxy, y) = mohr_coulomb::return_mapping_mohr_coulomb(
                        eff_trial[0],
                        eff_trial[1],
                        eff_trial[2],
                        c_eff,
                        phi_eff,
                    );
                    sig_new = [sx + p_static, sy + p_static, sxy];
                    yld = y;
                } else if mmodel == 2 && !skip_yield {
                    // Hoek-Brown
                    let (mut sci_f, mut mb_f, mut s_f, mut a_f) =
                        (sci_val, mb_val, s_val, a_val);
                    if is_srm {
                        sci_f /= target_m_stage;
                        mb_f /= target_m_stage;
                        let gsi_n = gsi_val / target_m_stage;
                        let mut dn = df_val * target_m_stage;
                        if dn > 1.0 {
                            dn = 1.0;
                        }
                        s_f = ((gsi_n - 100.0) / (9.0 - 3.0 * dn)).exp();
                        a_f = 0.5 + ((-gsi_n / 15.0_f64).exp() - (-20.0_f64 / 3.0_f64).exp()) / 6.0;
                    }
                    let (sx, sy, sxy, y) = hoek_brown::return_mapping_hoek_brown(
                        eff_trial[0],
                        eff_trial[1],
                        eff_trial[2],
                        sci_f,
                        mb_f,
                        s_f,
                        a_f,
                    );
                    sig_new = [sx + p_static, sy + p_static, sxy];
                    yld = y;
                } else {
                    sig_new = [eff_trial[0] + p_static, eff_trial[1] + p_static, eff_trial[2]];
                    yld = false;
                }
                p_exc_new = 0.0;
            }

            new_stresses[[i, gp_idx, 0]] = sig_new[0];
            new_stresses[[i, gp_idx, 1]] = sig_new[1];
            new_stresses[[i, gp_idx, 2]] = sig_new[2];
            new_yield[[i, gp_idx]] = yld;
            new_strain[[i, gp_idx, 0]] = epsilon_total[0];
            new_strain[[i, gp_idx, 1]] = epsilon_total[1];
            new_strain[[i, gp_idx, 2]] = epsilon_total[2];
            new_pwp_excess[[i, gp_idx]] = p_exc_new;

            // f_int_el += B^T @ sig_new * det_J * weight
            let bt_sig = t6::bt_times_sigma(&b_gp, &sig_new);
            let scale = det_j_val * weight;
            for k in 0..12 {
                f_int_el[k] += bt_sig[k] * scale;
            }
        }

        // Scatter to global F_int
        for li in 0..6 {
            let gi = elem_nodes[[i, li]] as usize;
            f_int[gi * 3] += f_int_el[li * 2];
            f_int[gi * 3 + 1] += f_int_el[li * 2 + 1];
        }
    }

    Ok((
        PyArray1::from_owned_array(py, f_int),
        PyArray3::from_owned_array(py, new_stresses),
        PyArray2::from_owned_array(py, new_yield),
        PyArray3::from_owned_array(py, new_strain),
        PyArray2::from_owned_array(py, new_pwp_excess),
    ))
}

/// Stiffness assembly kernel — computes K_values for all elements.
///
/// Returns flattened array of length N*144.
#[pyfunction]
#[pyo3(name = "assemble_stiffness_loop")]
pub fn assemble_stiffness_loop_py<'py>(
    py: Python<'py>,
    d_tangent: PyReadonlyArray2<'py, f64>,  // (N*3, 9) flattened D per GP
    b_matrices: PyReadonlyArray2<'py, f64>, // (N*3, 36) flattened B per GP
    det_j: PyReadonlyArray2<'py, f64>,      // (N, 3)
    weights: PyReadonlyArray1<'py, f64>,    // (3,)
) -> PyResult<Bound<'py, PyArray1<f64>>> {
    let d_arr = d_tangent.as_array();
    let b_arr = b_matrices.as_array();
    let det_j_arr = det_j.as_array();
    let w_arr = weights.as_array();

    let num_active = det_j_arr.shape()[0];
    let mut k_values = Array1::<f64>::zeros(num_active * 144);

    for i in 0..num_active {
        let mut k_el = [0.0f64; 144];
        for gp_idx in 0..3usize {
            let row = i * 3 + gp_idx;

            let mut b = [0.0f64; 36];
            for k in 0..36 {
                b[k] = b_arr[[row, k]];
            }
            let mut d = [0.0f64; 9];
            for k in 0..9 {
                d[k] = d_arr[[row, k]];
            }

            let contrib = t6::btdb_contribution(&b, &d, det_j_arr[[i, gp_idx]], w_arr[gp_idx]);
            for k in 0..144 {
                k_el[k] += contrib[k];
            }
        }

        let offset = i * 144;
        for k in 0..144 {
            k_values[offset + k] = k_el[k];
        }
    }

    Ok(PyArray1::from_owned_array(py, k_values))
}

/// D @ eps helper (3x3 matrix times 3-vector)
#[inline]
fn d_times_eps_fn(d: &[f64; 9], eps: &[f64; 3]) -> [f64; 3] {
    [
        d[0] * eps[0] + d[1] * eps[1] + d[2] * eps[2],
        d[3] * eps[0] + d[4] * eps[1] + d[5] * eps[2],
        d[6] * eps[0] + d[7] * eps[1] + d[8] * eps[2],
    ]
}
