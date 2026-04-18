/// K0 Procedure — Initial stress computation for geostatic conditions.
///
/// Computes vertical/horizontal effective and total stresses at all 12 Gauss points
/// for T15 high-order elements. Includes O(N) surface detection and water level interpolation.

use numpy::ndarray::{Array2, Array3};
use numpy::{PyArray2, PyArray3, PyReadonlyArray1, PyReadonlyArray2, PyReadonlyArray3};
use pyo3::prelude::*;

#[inline]
fn is_point_in_triangle(
    v1x: f64, v1y: f64,
    v2x: f64, v2y: f64,
    v3x: f64, v3y: f64,
    px: f64, py: f64,
) -> bool {
    let denom = (v2y - v3y) * (v1x - v3x) + (v3x - v2x) * (v1y - v3y);
    if denom.abs() < 1e-12 {
        return false;
    }
    let a = ((v2y - v3y) * (px - v3x) + (v3x - v2x) * (py - v3y)) / denom;
    let b = ((v3y - v1y) * (px - v3x) + (v1x - v3x) * (py - v3y)) / denom;
    let c = 1.0 - a - b;
    a >= -1e-9 && b >= -1e-9 && c >= -1e-9
}

#[inline]
fn get_water_y(x: f64, water_pts: &[[f64; 2]]) -> f64 {
    if water_pts.is_empty() {
        return -1e15;
    }
    if x <= water_pts[0][0] {
        return water_pts[0][1];
    }
    if x >= water_pts[water_pts.len() - 1][0] {
        return water_pts[water_pts.len() - 1][1];
    }
    for i in 0..water_pts.len() - 1 {
        let (x1, y1) = (water_pts[i][0], water_pts[i][1]);
        let (x2, y2) = (water_pts[i + 1][0], water_pts[i + 1][1]);
        if x1 <= x && x <= x2 {
            let t = (x - x1) / (x2 - x1);
            return y1 + t * (y2 - y1);
        }
    }
    -1e15
}

/// K0 initial stress computation kernel for T15 high-order mesh.
#[pyfunction]
#[pyo3(name = "compute_k0_stresses")]
pub fn compute_k0_stresses_py<'py>(
    py: Python<'py>,
    gp_coords_all: PyReadonlyArray3<'py, f64>,    // (N, 12, 2)
    node_coords: PyReadonlyArray2<'py, f64>,       // (num_nodes, 2)
    elem_nodes_corner: PyReadonlyArray2<'py, i32>, // (N, 3)
    elem_bboxes: PyReadonlyArray2<'py, f64>,       // (N, 4)
    rho_unsat: PyReadonlyArray1<'py, f64>,         // (N,)
    rho_sat: PyReadonlyArray1<'py, f64>,           // (N,)
    mat_k0: PyReadonlyArray1<'py, f64>,            // (N,)
    mat_phi: PyReadonlyArray1<'py, f64>,           // (N,)
    mat_nu: PyReadonlyArray1<'py, f64>,            // (N,)
    mat_drainage: PyReadonlyArray1<'py, i32>,      // (N,)
    water_pts_flat: PyReadonlyArray2<'py, f64>,    // (M, 2)
) -> PyResult<(
    pyo3::Bound<'py, PyArray3<f64>>,
    pyo3::Bound<'py, PyArray2<f64>>,
)> {
    let gp = gp_coords_all.as_array();
    let nodes = node_coords.as_array();
    let corners = elem_nodes_corner.as_array();
    let bboxes = elem_bboxes.as_array();
    let rho_u = rho_unsat.as_array();
    let rho_s = rho_sat.as_array();
    let k0_arr = mat_k0.as_array();
    let phi_arr = mat_phi.as_array();
    let nu_arr = mat_nu.as_array();
    let drain_arr = mat_drainage.as_array();
    let wp_flat = water_pts_flat.as_array();

    let num_active = gp.shape()[0];
    let gamma_w: f64 = 9.81;

    let n_wp = wp_flat.shape()[0];
    let mut water_pts: Vec<[f64; 2]> = Vec::with_capacity(n_wp);
    for i in 0..n_wp {
        water_pts.push([wp_flat[[i, 0]], wp_flat[[i, 1]]]);
    }

    let mut results = Array3::<f64>::zeros((num_active, 12, 3));
    let mut pwp_results = Array2::<f64>::zeros((num_active, 12));

    for i in 0..num_active {
        for gp_idx in 0..12usize {
            let x_gp = gp[[i, gp_idx, 0]];
            let y_gp = gp[[i, gp_idx, 1]];

            let water_y = get_water_y(x_gp, &water_pts);
            let mut pwp = 0.0;
            let dtype = drain_arr[i];
            if dtype != 3 && dtype != 4 {
                if water_y > -1e14 && y_gp < water_y {
                    pwp = -gamma_w * (water_y - y_gp);
                }
            }
            pwp_results[[i, gp_idx]] = pwp;

            let mut y_surf = -1e9_f64;
            for j in 0..num_active {
                if bboxes[[j, 0]] <= x_gp && x_gp <= bboxes[[j, 1]] {
                    if bboxes[[j, 3]] > y_surf {
                        y_surf = bboxes[[j, 3]];
                    }
                }
            }
            if y_surf < -1e8 {
                y_surf = y_gp;
            }

            let steps = 20;
            let dy = (y_surf - y_gp) / steps as f64;
            let mut sigma_accum = 0.0_f64;
            if dy > 0.0 {
                for s in 0..steps {
                    let y_sample = y_gp + (s as f64 + 0.5) * dy;
                    let mut gamma_sample = rho_u[i];
                    for j in 0..num_active {
                        if bboxes[[j, 0]] <= x_gp && x_gp <= bboxes[[j, 1]]
                            && bboxes[[j, 2]] <= y_sample && y_sample <= bboxes[[j, 3]]
                        {
                            let n1 = corners[[j, 0]] as usize;
                            let n2 = corners[[j, 1]] as usize;
                            let n3 = corners[[j, 2]] as usize;
                            if is_point_in_triangle(
                                nodes[[n1, 0]], nodes[[n1, 1]],
                                nodes[[n2, 0]], nodes[[n2, 1]],
                                nodes[[n3, 0]], nodes[[n3, 1]],
                                x_gp, y_sample,
                            ) {
                                let wy = get_water_y(x_gp, &water_pts);
                                if wy > -1e14 && y_sample < wy {
                                    gamma_sample = if rho_s[j] > 0.0 { rho_s[j] } else { rho_u[j] };
                                } else {
                                    gamma_sample = rho_u[j];
                                }
                                break;
                            }
                        }
                    }
                    sigma_accum += gamma_sample * dy;
                }
            }

            let sigma_v_total = -sigma_accum;
            let sigma_v_eff = sigma_v_total - pwp;

            let mut k0 = k0_arr[i];
            if k0 < 0.0 {
                let phi = phi_arr[i];
                if phi > 0.0 {
                    k0 = 1.0 - (phi.to_radians()).sin();
                } else {
                    let nu = nu_arr[i];
                    if nu > 0.0 {
                        let nu_eff = nu.min(0.499);
                        k0 = nu_eff / (1.0 - nu_eff);
                    } else {
                        k0 = 0.5;
                    }
                }
            }

            let sigma_h_eff = k0 * sigma_v_eff;
            let sigma_h_total = sigma_h_eff + pwp;

            results[[i, gp_idx, 0]] = sigma_h_total;
            results[[i, gp_idx, 1]] = sigma_v_total;
            results[[i, gp_idx, 2]] = 0.0;
        }
    }

    Ok((
        PyArray3::from_owned_array(py, results),
        PyArray2::from_owned_array(py, pwp_results),
    ))
}
