/// 9-node quadrilateral element: B-matrix, shape functions, stiffness helpers.

pub const NUM_GAUSS: usize = 9;
pub const NUM_NODES: usize = 9;
pub const NUM_DOFS: usize = 18;

pub const GAUSS_POINTS_1D: [f64; 3] = [-0.7745966692414834, 0.0, 0.7745966692414834];

#[inline]
pub fn shape_functions_quad9(xi: f64, eta: f64) -> [f64; 9] {
    let lx = [
        0.5 * xi * (xi - 1.0),
        1.0 - xi * xi,
        0.5 * xi * (xi + 1.0),
    ];
    let ly = [
        0.5 * eta * (eta - 1.0),
        1.0 - eta * eta,
        0.5 * eta * (eta + 1.0),
    ];
    [
        lx[0] * ly[0],
        lx[2] * ly[0],
        lx[2] * ly[2],
        lx[0] * ly[2],
        lx[1] * ly[0],
        lx[2] * ly[1],
        lx[1] * ly[2],
        lx[0] * ly[1],
        lx[1] * ly[1],
    ]
}

#[inline]
pub fn shape_derivatives_quad9(xi: f64, eta: f64) -> ([f64; 9], [f64; 9]) {
    let lx = [
        0.5 * xi * (xi - 1.0),
        1.0 - xi * xi,
        0.5 * xi * (xi + 1.0),
    ];
    let ly = [
        0.5 * eta * (eta - 1.0),
        1.0 - eta * eta,
        0.5 * eta * (eta + 1.0),
    ];
    let dlx = [xi - 0.5, -2.0 * xi, xi + 0.5];
    let dly = [eta - 0.5, -2.0 * eta, eta + 0.5];
    let mut d_xi = [0.0; 9];
    let mut d_eta = [0.0; 9];
    d_xi[0] = dlx[0] * ly[0];
    d_eta[0] = lx[0] * dly[0];
    d_xi[1] = dlx[2] * ly[0];
    d_eta[1] = lx[2] * dly[0];
    d_xi[2] = dlx[2] * ly[2];
    d_eta[2] = lx[2] * dly[2];
    d_xi[3] = dlx[0] * ly[2];
    d_eta[3] = lx[0] * dly[2];
    d_xi[4] = dlx[1] * ly[0];
    d_eta[4] = lx[1] * dly[0];
    d_xi[5] = dlx[2] * ly[1];
    d_eta[5] = lx[2] * dly[1];
    d_xi[6] = dlx[1] * ly[2];
    d_eta[6] = lx[1] * dly[2];
    d_xi[7] = dlx[0] * ly[1];
    d_eta[7] = lx[0] * dly[1];
    d_xi[8] = dlx[1] * ly[1];
    d_eta[8] = lx[1] * dly[1];
    (d_xi, d_eta)
}

#[inline]
pub fn bt_times_sigma(b: &[f64; 54], sigma: &[f64; 3]) -> [f64; 18] {
    let mut result = [0.0f64; 18];
    for col in 0..18 {
        result[col] = b[col] * sigma[0] + b[18 + col] * sigma[1] + b[36 + col] * sigma[2];
    }
    result
}

#[inline]
pub fn b_times_u(b: &[f64; 54], u: &[f64; 18]) -> [f64; 3] {
    let mut eps = [0.0f64; 3];
    for row in 0..3 {
        for col in 0..18 {
            eps[row] += b[row * 18 + col] * u[col];
        }
    }
    eps
}

#[inline]
pub fn btdb_contribution(b: &[f64; 54], d: &[f64; 9], det_j: f64, weight: f64) -> [f64; 324] {
    let scale = det_j * weight;
    let mut db = [0.0f64; 54];
    for row in 0..3 {
        for col in 0..18 {
            db[row * 18 + col] = d[row * 3] * b[col]
                + d[row * 3 + 1] * b[18 + col]
                + d[row * 3 + 2] * b[36 + col];
        }
    }
    let mut k = [0.0f64; 324];
    for i in 0..18 {
        for j in 0..18 {
            let mut v = 0.0;
            for r in 0..3 {
                v += b[r * 18 + i] * db[r * 18 + j];
            }
            k[i * 18 + j] = v * scale;
        }
    }
    k
}
