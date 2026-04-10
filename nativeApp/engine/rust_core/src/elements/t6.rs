/// Element T6 computations: B-matrix, shape functions, stiffness assembly.
///
/// Implements 6-node quadratic triangle element operations for 2D plane strain FEA.

/// Gauss quadrature points for triangles (3-point rule).
pub const GAUSS_POINTS: [[f64; 2]; 3] = [
    [1.0 / 6.0, 1.0 / 6.0],
    [2.0 / 3.0, 1.0 / 6.0],
    [1.0 / 6.0, 2.0 / 3.0],
];

pub const GAUSS_WEIGHTS: [f64; 3] = [1.0 / 6.0, 1.0 / 6.0, 1.0 / 6.0];

/// Compute T6 shape functions at natural coordinates (xi, eta).
/// Returns [N1, N2, N3, N4, N5, N6].
#[inline]
pub fn shape_functions_t6(xi: f64, eta: f64) -> [f64; 6] {
    let zeta = 1.0 - xi - eta;
    [
        zeta * (2.0 * zeta - 1.0),        // N1 corner
        xi * (2.0 * xi - 1.0),            // N2 corner
        eta * (2.0 * eta - 1.0),           // N3 corner
        4.0 * zeta * xi,                   // N4 midpoint 1-2
        4.0 * xi * eta,                    // N5 midpoint 2-3
        4.0 * eta * zeta,                  // N6 midpoint 3-1
    ]
}

/// Compute derivatives of T6 shape functions w.r.t. natural coordinates.
/// Returns [[dN/dxi x6], [dN/deta x6]].
#[inline]
pub fn shape_function_derivatives(xi: f64, eta: f64) -> [[f64; 6]; 2] {
    let zeta = 1.0 - xi - eta;
    [
        // dN/dxi
        [
            -4.0 * zeta + 1.0,
            4.0 * xi - 1.0,
            0.0,
            4.0 * (zeta - xi),
            4.0 * eta,
            -4.0 * eta,
        ],
        // dN/deta
        [
            -4.0 * zeta + 1.0,
            0.0,
            4.0 * eta - 1.0,
            -4.0 * xi,
            4.0 * xi,
            4.0 * (zeta - eta),
        ],
    ]
}

/// Compute B-matrix (3x12) and det(J) at a Gauss point.
///
/// node_coords: flattened [x1,y1, x2,y2, ..., x6,y6] (12 values)
#[inline]
pub fn compute_b_matrix(node_coords: &[f64; 12], xi: f64, eta: f64) -> ([f64; 36], f64) {
    let dn = shape_function_derivatives(xi, eta);

    // Jacobian J = dN_natural @ node_coords
    // J is 2x2: J[r][c] = sum_i dn[r][i] * node_coords_2d[i][c]
    let mut j00 = 0.0;
    let mut j01 = 0.0;
    let mut j10 = 0.0;
    let mut j11 = 0.0;
    for i in 0..6 {
        let x_i = node_coords[2 * i];
        let y_i = node_coords[2 * i + 1];
        j00 += dn[0][i] * x_i;
        j01 += dn[0][i] * y_i;
        j10 += dn[1][i] * x_i;
        j11 += dn[1][i] * y_i;
    }

    let det_j = j00 * j11 - j01 * j10;
    if det_j.abs() < 1e-10 {
        return ([0.0; 36], 0.0);
    }

    let inv_det = 1.0 / det_j;
    // J_inv = [[j11, -j01], [-j10, j00]] / det_j
    let ji00 = j11 * inv_det;
    let ji01 = -j01 * inv_det;
    let ji10 = -j10 * inv_det;
    let ji11 = j00 * inv_det;

    // dN_physical = J_inv @ dN_natural
    let mut dn_phys = [[0.0f64; 6]; 2];
    for i in 0..6 {
        dn_phys[0][i] = ji00 * dn[0][i] + ji01 * dn[1][i]; // dN/dx
        dn_phys[1][i] = ji10 * dn[0][i] + ji11 * dn[1][i]; // dN/dy
    }

    // B matrix (3x12), stored row-major
    let mut b = [0.0f64; 36];
    for i in 0..6 {
        b[0 * 12 + 2 * i] = dn_phys[0][i]; // B[0, 2i] = dNi/dx (exx)
        b[1 * 12 + 2 * i + 1] = dn_phys[1][i]; // B[1, 2i+1] = dNi/dy (eyy)
        b[2 * 12 + 2 * i] = dn_phys[1][i]; // B[2, 2i] = dNi/dy (gxy)
        b[2 * 12 + 2 * i + 1] = dn_phys[0][i]; // B[2, 2i+1] = dNi/dx (gxy)
    }

    (b, det_j)
}

/// Multiply B^T (12x3) @ sigma (3,) -> result (12,)
/// B is stored as 3x12 row-major (36 values).
#[inline]
pub fn bt_times_sigma(b: &[f64; 36], sigma: &[f64; 3]) -> [f64; 12] {
    let mut result = [0.0f64; 12];
    for col in 0..12 {
        // B^T[col, row] = B[row, col]
        result[col] = b[0 * 12 + col] * sigma[0]
            + b[1 * 12 + col] * sigma[1]
            + b[2 * 12 + col] * sigma[2];
    }
    result
}

/// Multiply B (3x12) @ u (12,) -> strain (3,)
#[inline]
pub fn b_times_u(b: &[f64; 36], u: &[f64; 12]) -> [f64; 3] {
    let mut eps = [0.0f64; 3];
    for row in 0..3 {
        for col in 0..12 {
            eps[row] += b[row * 12 + col] * u[col];
        }
    }
    eps
}

/// Multiply D (3x3) @ strain (3,) -> stress (3,)
/// D is stored row-major (9 values).
#[inline]
pub fn d_times_eps(d: &[f64; 9], eps: &[f64; 3]) -> [f64; 3] {
    [
        d[0] * eps[0] + d[1] * eps[1] + d[2] * eps[2],
        d[3] * eps[0] + d[4] * eps[1] + d[5] * eps[2],
        d[6] * eps[0] + d[7] * eps[1] + d[8] * eps[2],
    ]
}

/// Compute B^T @ D @ B * det_J * weight (contribution to element stiffness).
/// Returns 144 values (12x12 row-major).
#[inline]
pub fn btdb_contribution(b: &[f64; 36], d: &[f64; 9], det_j: f64, weight: f64) -> [f64; 144] {
    let scale = det_j * weight;
    // DB = D @ B (3x12)
    let mut db = [0.0f64; 36];
    for row in 0..3 {
        for col in 0..12 {
            db[row * 12 + col] = d[row * 3] * b[col]
                + d[row * 3 + 1] * b[12 + col]
                + d[row * 3 + 2] * b[24 + col];
        }
    }
    // K = B^T @ DB (12x12)
    let mut k = [0.0f64; 144];
    for i in 0..12 {
        for j in 0..12 {
            let mut v = 0.0;
            for r in 0..3 {
                v += b[r * 12 + i] * db[r * 12 + j];
            }
            k[i * 12 + j] = v * scale;
        }
    }
    k
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_shape_functions_sum_to_one() {
        for gp in &GAUSS_POINTS {
            let n = shape_functions_t6(gp[0], gp[1]);
            let sum: f64 = n.iter().sum();
            assert!(
                (sum - 1.0).abs() < 1e-14,
                "Shape functions should sum to 1, got {sum}"
            );
        }
    }

    #[test]
    fn test_b_matrix_simple_triangle() {
        // Simple right triangle with midpoints
        let coords: [f64; 12] = [
            0.0, 0.0, // n1
            2.0, 0.0, // n2
            0.0, 2.0, // n3
            1.0, 0.0, // n4 mid 1-2
            1.0, 1.0, // n5 mid 2-3
            0.0, 1.0, // n6 mid 3-1
        ];
        let (b, det_j) = compute_b_matrix(&coords, 1.0 / 6.0, 1.0 / 6.0);
        assert!(det_j > 0.0, "det_J should be positive for CCW triangle");
        // B should have non-zero entries
        let b_norm: f64 = b.iter().map(|v| v * v).sum();
        assert!(b_norm > 0.0, "B matrix should be non-zero");
    }
}
