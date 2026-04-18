/// Embedded beam element computations (Bernoulli-Euler 6-DOF Frame).

use numpy::{PyArray1, PyArray2};
use numpy::{PyReadonlyArray1, PyReadonlyArray2};
use pyo3::prelude::*;

/// Compute 6x6 stiffness matrix and gravity vector for a 2D Bernoulli beam.
#[pyfunction]
#[pyo3(name = "compute_beam_element_matrix")]
pub fn compute_beam_element_matrix_py<'py>(
    py: Python<'py>,
    node_coords: PyReadonlyArray2<'py, f64>,
    e: f64,
    a: f64,
    i_inertia: f64,
    spacing: f64,
    unit_weight: f64,
    kh: f64,
    kv: f64,
) -> PyResult<(Bound<'py, PyArray2<f64>>, Bound<'py, PyArray1<f64>>)> {
    let coords = node_coords.as_array();
    let x1 = coords[[0, 0]];
    let y1 = coords[[0, 1]];
    let x2 = coords[[1, 0]];
    let y2 = coords[[1, 1]];

    let dx = x2 - x1;
    let dy = y2 - y1;
    let l_span = (dx * dx + dy * dy).sqrt();

    if l_span < 1e-9 {
        return Ok((
            PyArray2::zeros(py, [6, 6], false),
            PyArray1::zeros(py, [6], false),
        ));
    }

    let c = dx / l_span;
    let s = dy / l_span;
    let inv_spacing = if spacing > 1e-9 { 1.0 / spacing } else { 1.0 };

    let k_axial = (e * a / l_span) * inv_spacing;
    let k_bend = (e * i_inertia / l_span.powi(3)) * inv_spacing;

    // Local stiffness matrix (6x6)
    let mut k_local = [[0.0f64; 6]; 6];
    k_local[0][0] = k_axial;
    k_local[0][3] = -k_axial;
    k_local[3][0] = -k_axial;
    k_local[3][3] = k_axial;

    k_local[1][1] = 12.0 * k_bend;
    k_local[1][2] = 6.0 * k_bend * l_span;
    k_local[1][4] = -12.0 * k_bend;
    k_local[1][5] = 6.0 * k_bend * l_span;

    k_local[2][1] = 6.0 * k_bend * l_span;
    k_local[2][2] = 4.0 * k_bend * l_span * l_span;
    k_local[2][4] = -6.0 * k_bend * l_span;
    k_local[2][5] = 2.0 * k_bend * l_span * l_span;

    k_local[4][1] = -12.0 * k_bend;
    k_local[4][2] = -6.0 * k_bend * l_span;
    k_local[4][4] = 12.0 * k_bend;
    k_local[4][5] = -6.0 * k_bend * l_span;

    k_local[5][1] = 6.0 * k_bend * l_span;
    k_local[5][2] = 2.0 * k_bend * l_span * l_span;
    k_local[5][4] = -6.0 * k_bend * l_span;
    k_local[5][5] = 4.0 * k_bend * l_span * l_span;

    // Transformation Matrix T (6x6)
    // T = [c s 0 0 0 0; -s c 0 0 0 0; 0 0 1 0 0 0; ...]
    let mut k_global = [[0.0f64; 6]; 6];
    // K_global = T.T @ k_local @ T
    // Hand-unrolled for performance without full matrix library
    let t = [
        [c, s, 0.0, 0.0, 0.0, 0.0],
        [-s, c, 0.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, c, s, 0.0],
        [0.0, 0.0, 0.0, -s, c, 0.0],
        [0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
    ];

    for r in 0..6 {
        for c_idx in 0..6 {
            let mut val = 0.0;
            for i in 0..6 {
                for j in 0..6 {
                    val += t[i][r] * k_local[i][j] * t[j][c_idx];
                }
            }
            k_global[r][c_idx] = val;
        }
    }

    let total_w = (unit_weight * l_span) * inv_spacing;
    let fx = kh * total_w / 2.0;
    let fy = -(1.0 + kv) * total_w / 2.0;
    let f_grav = [fx, fy, 0.0, fx, fy, 0.0];

    Ok((
        PyArray2::from_owned_array(py, numpy::ndarray::Array2::from_shape_vec((6, 6), k_global.flatten().to_vec()).unwrap()),
        PyArray1::from_owned_array(py, numpy::ndarray::Array1::from_vec(f_grav.to_vec())),
    ))
}

/// Compute internal forces with axial yielding (Bernoulli EB-Row).
#[pyfunction]
#[pyo3(name = "compute_beam_internal_force_yield")]
pub fn compute_beam_internal_force_yield_py<'py>(
    _py: Python<'py>,
    node_coords: PyReadonlyArray2<'py, f64>,
    u_el: PyReadonlyArray1<'py, f64>,
    u_ref: PyReadonlyArray1<'py, f64>,
    e: f64,
    a: f64,
    i_inertia: f64,
    spacing: f64,
    capacity: f64,
    is_srm: bool,
    target_m_stage: f64,
) -> PyResult<(Bound<'py, PyArray1<f64>>, bool)> {
    let coords = node_coords.as_array();
    let x1 = coords[[0, 0]];
    let y1 = coords[[0, 1]];
    let x2 = coords[[1, 0]];
    let y2 = coords[[1, 1]];

    let dx = x2 - x1;
    let dy = y2 - y1;
    let l_span = (dx * dx + dy * dy).sqrt();
    if l_span < 1e-9 {
        return Ok((PyArray1::zeros(_py, [6], false), false));
    }

    let c = dx / l_span;
    let s = dy / l_span;
    let u_el_arr = u_el.as_array();
    let u_ref_arr = u_ref.as_array();

    let mut u_diff = [0.0f64; 6];
    for k in 0..6 {
        u_diff[k] = u_el_arr[k] - u_ref_arr[k];
    }

    // T @ u_diff
    let u_local = [
        c * u_diff[0] + s * u_diff[1],
        -s * u_diff[0] + c * u_diff[1],
        u_diff[2],
        c * u_diff[3] + s * u_diff[4],
        -s * u_diff[3] + c * u_diff[4],
        u_diff[5],
    ];

    let inv_spacing = if spacing > 1e-9 { 1.0 / spacing } else { 1.0 };
    let k_axial = (e * a / l_span) * inv_spacing;
    let k_bend = (e * i_inertia / l_span.powi(3)) * inv_spacing;

    // k_local @ u_local manually
    let mut f_local_trial = [0.0f64; 6];
    f_local_trial[0] = k_axial * u_local[0] - k_axial * u_local[3];
    f_local_trial[3] = -k_axial * u_local[0] + k_axial * u_local[3];

    f_local_trial[1] = 12.0 * k_bend * u_local[1] + 6.0 * k_bend * l_span * u_local[2] - 12.0 * k_bend * u_local[4] + 6.0 * k_bend * l_span * u_local[5];
    f_local_trial[2] = 6.0 * k_bend * l_span * u_local[1] + 4.0 * k_bend * l_span * l_span * u_local[2] - 6.0 * k_bend * l_span * u_local[4] + 2.0 * k_bend * l_span * l_span * u_local[5];
    f_local_trial[4] = -12.0 * k_bend * u_local[1] - 6.0 * k_bend * l_span * u_local[2] + 12.0 * k_bend * u_local[4] - 6.0 * k_bend * l_span * u_local[5];
    f_local_trial[5] = 6.0 * k_bend * l_span * u_local[1] + 2.0 * k_bend * l_span * l_span * u_local[2] - 6.0 * k_bend * l_span * u_local[4] + 4.0 * k_bend * l_span * l_span * u_local[5];

    let mut eff_capacity = capacity * inv_spacing;
    if is_srm && target_m_stage > 0.0 {
        eff_capacity /= target_m_stage;
    }

    let mut f_axial = f_local_trial[3];
    let mut is_yielded = false;
    if capacity > 0.0 {
        if f_axial > eff_capacity {
            f_axial = eff_capacity;
            is_yielded = true;
        } else if f_axial < -eff_capacity {
            f_axial = -eff_capacity;
            is_yielded = true;
        }
    }

    let mut f_local = f_local_trial;
    f_local[3] = f_axial;
    f_local[0] = -f_axial;

    // T.T @ f_local
    let f_global = [
        c * f_local[0] - s * f_local[1],
        s * f_local[0] + c * f_local[1],
        f_local[2],
        c * f_local[3] - s * f_local[4],
        s * f_local[3] + c * f_local[4],
        f_local[5],
    ];

    Ok((
        PyArray1::from_owned_array(_py, numpy::ndarray::Array1::from_vec(f_global.to_vec())),
        is_yielded,
    ))
}

/// Compute local forces [N, V1, M1, V2, M2].
#[pyfunction]
#[pyo3(name = "compute_beam_forces_local")]
pub fn compute_beam_forces_local_py<'py>(
    _py: Python<'py>,
    node_coords: PyReadonlyArray2<'py, f64>,
    u_el: PyReadonlyArray1<'py, f64>,
    u_ref: PyReadonlyArray1<'py, f64>,
    e: f64,
    a: f64,
    i_inertia: f64,
    spacing: f64,
) -> PyResult<Bound<'py, PyArray1<f64>>> {
    let coords = node_coords.as_array();
    let x1 = coords[[0, 0]];
    let y1 = coords[[0, 1]];
    let x2 = coords[[1, 0]];
    let y2 = coords[[1, 1]];

    let dx = x2 - x1;
    let dy = y2 - y1;
    let l_span = (dx * dx + dy * dy).sqrt();
    if l_span < 1e-9 {
        return Ok(PyArray1::zeros(_py, [5], false));
    }

    let c = dx / l_span;
    let s = dy / l_span;
    let u_el_arr = u_el.as_array();
    let u_ref_arr = u_ref.as_array();

    let mut u_diff = [0.0f64; 6];
    for k in 0..6 {
        u_diff[k] = u_el_arr[k] - u_ref_arr[k];
    }

    let u_local = [
        c * u_diff[0] + s * u_diff[1],
        -s * u_diff[0] + c * u_diff[1],
        u_diff[2],
        c * u_diff[3] + s * u_diff[4],
        -s * u_diff[3] + c * u_diff[4],
        u_diff[5],
    ];

    let inv_spacing = if spacing > 1e-9 { 1.0 / spacing } else { 1.0 };
    let k_axial = (e * a / l_span) * inv_spacing;
    let k_bend = (e * i_inertia / l_span.powi(3)) * inv_spacing;

    let mut f_local = [0.0f64; 6];
    f_local[0] = k_axial * u_local[0] - k_axial * u_local[3];
    f_local[3] = -k_axial * u_local[0] + k_axial * u_local[3];
    f_local[1] = 12.0 * k_bend * u_local[1] + 6.0 * k_bend * l_span * u_local[2] - 12.0 * k_bend * u_local[4] + 6.0 * k_bend * l_span * u_local[5];
    f_local[2] = 6.0 * k_bend * l_span * u_local[1] + 4.0 * k_bend * l_span * l_span * u_local[2] - 6.0 * k_bend * l_span * u_local[4] + 2.0 * k_bend * l_span * l_span * u_local[5];
    f_local[4] = -12.0 * k_bend * u_local[1] - 6.0 * k_bend * l_span * u_local[2] + 12.0 * k_bend * u_local[4] - 6.0 * k_bend * l_span * u_local[5];
    f_local[5] = 6.0 * k_bend * l_span * u_local[1] + 2.0 * k_bend * l_span * l_span * u_local[2] - 6.0 * k_bend * l_span * u_local[4] + 4.0 * k_bend * l_span * l_span * u_local[5];

    let mut res = [0.0f64; 5];
    res[0] = f_local[3];  // N
    res[1] = -f_local[1]; // V1
    res[2] = -f_local[2]; // M1
    res[3] = f_local[4];  // V2
    res[4] = f_local[5];  // M2

    Ok(PyArray1::from_owned_array(_py, numpy::ndarray::Array1::from_vec(res.to_vec())))
}

trait Flatten {
    fn flatten(&self) -> Vec<f64>;
}

impl Flatten for [[f64; 6]; 6] {
    fn flatten(&self) -> Vec<f64> {
        self.iter().flat_map(|row| row.iter()).copied().collect()
    }
}
