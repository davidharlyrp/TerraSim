/// Element T15 computations: B-matrix, shape functions, stiffness assembly.
///
/// Implements 15-node quartic triangle element operations for professional FEA.
/// Node ordering follows PLAXIS standard.

/// Gauss quadrature points for triangles (9-point symmetrical rule).
/// Natural coordinates [xi, eta].
pub const GAUSS_POINTS: [[f64; 2]; 12] = [
    // (L2, L3) barycentric. L1 = 1 - L2 - L3.
    // Group 1: 3 points
    [0.063089014576192, 0.063089014576192],
    [0.063089014576192, 0.873821970847616],
    [0.873821970847616, 0.063089014576192],
    // Group 2: 3 points
    [0.24928674517091, 0.24928674517091],
    [0.24928674517091, 0.501426509658179],
    [0.501426509658179, 0.24928674517091],
    // Group 3: 6 points
    [0.310352451033784, 0.053145049344120],
    [0.053145049344120, 0.636502499622095],
    [0.636502499622095, 0.310352451033784],
    [0.053145049344120, 0.310352451033784],
    [0.310352451033784, 0.636502499622095],
    [0.636502499622095, 0.053145049344120],
];

pub const GAUSS_WEIGHTS: [f64; 12] = [
    0.02517361530155050, 0.02517361530155050, 0.02517361530155050,
    0.05839313786335150, 0.05839313786335150, 0.05839313786335150,
    0.04142553780918917, 0.04142553780918917, 0.04142553780918917,
    0.04142553780918917, 0.04142553780918917, 0.04142553780918917,
];

/// Compute T15 shape functions at natural coordinates (xi, eta).
/// Returns [N1..N15].
#[inline]
fn lagrange_tri_basis(l1: f64, l2: f64, l3: f64, i: i32, j: i32, k: i32) -> f64 {
    let mut val = 1.0;
    for p in 0..i {
        val *= (4.0 * l1 - p as f64) / (p as f64 + 1.0);
    }
    for p in 0..j {
        val *= (4.0 * l2 - p as f64) / (p as f64 + 1.0);
    }
    for p in 0..k {
        val *= (4.0 * l3 - p as f64) / (p as f64 + 1.0);
    }
    val
}

#[inline]
pub fn shape_functions_t15(xi: f64, eta: f64) -> [f64; 15] {
    let l2 = xi;
    let l3 = eta;
    let l1 = 1.0 - xi - eta;

    let triplets: [(i32, i32, i32); 15] = [
        (4, 0, 0), (0, 4, 0), (0, 0, 4), // Corners
        (3, 1, 0), (2, 2, 0), (1, 3, 0), // Edge 1-2
        (0, 3, 1), (0, 2, 2), (0, 1, 3), // Edge 2-3
        (1, 0, 3), (2, 0, 2), (3, 0, 1), // Edge 3-1
        (2, 1, 1), (1, 2, 1), (1, 1, 2), // Interiors
    ];

    let mut n = [0.0; 15];
    for idx in 0..15 {
        let (i, j, k) = triplets[idx];
        n[idx] = lagrange_tri_basis(l1, l2, l3, i, j, k);
    }
    n
}

#[inline]
pub fn shape_function_derivatives(xi: f64, eta: f64) -> [[f64; 15]; 2] {
    let l2 = xi;
    let l3 = eta;
    let l1 = 1.0 - xi - eta;

    let triplets: [(i32, i32, i32); 15] = [
        (4, 0, 0), (0, 4, 0), (0, 0, 4),
        (3, 1, 0), (2, 2, 0), (1, 3, 0),
        (0, 3, 1), (0, 2, 2), (0, 1, 3),
        (1, 0, 3), (2, 0, 2), (3, 0, 1),
        (2, 1, 1), (1, 2, 1), (1, 1, 2),
    ];

    let l_val = |l: f64, m: i32| -> f64 {
        let mut v = 1.0;
        for p in 0..m { v *= (4.0 * l - p as f64) / (p as f64 + 1.0); }
        v
    };
    
    let l_deriv = |l: f64, m: i32| -> f64 {
        if m == 0 { return 0.0; }
        let mut total = 0.0;
        for q in 0..m {
            let mut term = 4.0 / (q as f64 + 1.0);
            for p in 0..m {
                if p != q { term *= (4.0 * l - p as f64) / (p as f64 + 1.0); }
            }
            total += term;
        }
        total
    };

    let mut d_xi = [0.0; 15];
    let mut d_eta = [0.0; 15];

    for idx in 0..15 {
        let (i, j, k) = triplets[idx];
        
        let dn_dl1 = l_deriv(l1, i) * l_val(l2, j) * l_val(l3, k);
        let dn_dl2 = l_val(l1, i) * l_deriv(l2, j) * l_val(l3, k);
        let dn_dl3 = l_val(l1, i) * l_val(l2, j) * l_deriv(l3, k);

        // Chain rule for Barycentric -> Natural
        // L2=xi, L3=eta, L1=1-xi-eta
        d_xi[idx] = dn_dl2 - dn_dl1;
        d_eta[idx] = dn_dl3 - dn_dl1;
    }

    [d_xi, d_eta]
}

/// Compute B-matrix (3x30) and det(J) at a Gauss point.
/// node_coords: flattened [x1,y1, ..., x15,y15] (30 values)
#[inline]
pub fn compute_b_matrix(node_coords: &[f64; 30], xi: f64, eta: f64) -> ([f64; 90], f64) {
    let dn = shape_function_derivatives(xi, eta);

    let mut j00 = 0.0;
    let mut j01 = 0.0;
    let mut j10 = 0.0;
    let mut j11 = 0.0;
    for i in 0..15 {
        let x_i = node_coords[2 * i];
        let y_i = node_coords[2 * i + 1];
        j00 += dn[0][i] * x_i;
        j01 += dn[0][i] * y_i;
        j10 += dn[1][i] * x_i;
        j11 += dn[1][i] * y_i;
    }

    let det_j = j00 * j11 - j01 * j10;
    if det_j.abs() < 1e-12 {
        return ([0.0; 90], 0.0);
    }

    let inv_det = 1.0 / det_j;
    let ji00 = j11 * inv_det;
    let ji01 = -j01 * inv_det;
    let ji10 = -j10 * inv_det;
    let ji11 = j00 * inv_det;

    let mut dn_phys = [[0.0f64; 15]; 2];
    for i in 0..15 {
        dn_phys[0][i] = ji00 * dn[0][i] + ji01 * dn[1][i];
        dn_phys[1][i] = ji10 * dn[0][i] + ji11 * dn[1][i];
    }

    let mut b = [0.0f64; 90];
    for i in 0..15 {
        b[0 * 30 + 2 * i] = dn_phys[0][i];
        b[1 * 30 + 2 * i + 1] = dn_phys[1][i];
        b[2 * 30 + 2 * i] = dn_phys[1][i];
        b[2 * 30 + 2 * i + 1] = dn_phys[0][i];
    }

    (b, det_j)
}

/// Multiply B^T (30x3) @ sigma (3,) -> result (30,)
#[inline]
pub fn bt_times_sigma(b: &[f64; 90], sigma: &[f64; 3]) -> [f64; 30] {
    let mut result = [0.0f64; 30];
    for col in 0..30 {
        result[col] = b[0 * 30 + col] * sigma[0]
            + b[1 * 30 + col] * sigma[1]
            + b[2 * 30 + col] * sigma[2];
    }
    result
}

/// Multiply B (3x30) @ u (30,) -> strain (3,)
#[inline]
pub fn b_times_u(b: &[f64; 90], u: &[f64; 30]) -> [f64; 3] {
    let mut eps = [0.0f64; 3];
    for row in 0..3 {
        for col in 0..30 {
            eps[row] += b[row * 30 + col] * u[col];
        }
    }
    eps
}

/// Compute B^T @ D @ B * det_J * weight. Returns 900 values (30x30).
#[inline]
pub fn btdb_contribution(b: &[f64; 90], d: &[f64; 9], det_j: f64, weight: f64) -> [f64; 900] {
    let scale = det_j * weight;
    let mut db = [0.0f64; 90]; // 3x30
    for row in 0..3 {
        for col in 0..30 {
            db[row * 30 + col] = d[row * 3] * b[col]
                + d[row * 3 + 1] * b[30 + col]
                + d[row * 3 + 2] * b[60 + col];
        }
    }
    let mut k = [0.0f64; 900];
    for i in 0..30 {
        for j in 0..30 {
            let mut v = 0.0;
            for r in 0..3 {
                v += b[r * 30 + i] * db[r * 30 + j];
            }
            k[i * 30 + j] = v * scale;
        }
    }
    k
}
