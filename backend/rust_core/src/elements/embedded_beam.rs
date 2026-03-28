/// Embedded beam element computations.
///
/// 2D truss element with axial-only stiffness, yielding, and gravity load.

/// Compute beam element stiffness matrix (4x4) and gravity load vector.
///
/// Returns (K_global_flat[16], F_grav[4]).
#[inline]
pub fn compute_beam_element_matrix(
    x1: f64, y1: f64,
    x2: f64, y2: f64,
    e: f64,
    a: f64,
    spacing: f64,
    unit_weight: f64,
) -> ([f64; 16], [f64; 4]) {
    let dx = x2 - x1;
    let dy = y2 - y1;
    let l = (dx * dx + dy * dy).sqrt();

    if l < 1e-9 {
        return ([0.0; 16], [0.0; 4]);
    }

    let c = dx / l;
    let s = dy / l;
    let inv_spacing = if spacing > 1e-9 { 1.0 / spacing } else { 1.0 };
    let k = (e * a / l) * inv_spacing;

    let cc = c * c * k;
    let ss = s * s * k;
    let cs = c * s * k;

    #[rustfmt::skip]
    let k_mat = [
         cc,  cs, -cc, -cs,
         cs,  ss, -cs, -ss,
        -cc, -cs,  cc,  cs,
        -cs, -ss,  cs,  ss,
    ];

    let total_w = (unit_weight * l) * inv_spacing;
    let f_grav = [0.0, -total_w / 2.0, 0.0, -total_w / 2.0];

    (k_mat, f_grav)
}

/// Compute beam internal force with axial yielding.
///
/// Returns (f_int[4], is_yielded).
#[inline]
pub fn compute_beam_internal_force_yield(
    x1: f64, y1: f64,
    x2: f64, y2: f64,
    u_el: &[f64; 4],
    e: f64,
    a: f64,
    spacing: f64,
    capacity: f64,
    is_srm: bool,
    target_m_stage: f64,
) -> ([f64; 4], bool) {
    let dx = x2 - x1;
    let dy = y2 - y1;
    let l = (dx * dx + dy * dy).sqrt();
    if l < 1e-9 {
        return ([0.0; 4], false);
    }

    let c = dx / l;
    let s = dy / l;

    let u1_local = u_el[0] * c + u_el[1] * s;
    let u2_local = u_el[2] * c + u_el[3] * s;
    let du_local = u2_local - u1_local;

    let inv_spacing = if spacing > 1e-9 { 1.0 / spacing } else { 1.0 };
    let k_axial = (e * a / l) * inv_spacing;
    let f_axial_trial = k_axial * du_local;

    let eff_capacity = if is_srm && target_m_stage > 0.0 {
        capacity / target_m_stage
    } else {
        capacity
    };

    let (f_axial, is_yielded) = if f_axial_trial.abs() > eff_capacity {
        (f_axial_trial.signum() * eff_capacity, true)
    } else {
        (f_axial_trial, false)
    };

    let f_int = [
        -f_axial * c,
        -f_axial * s,
        f_axial * c,
        f_axial * s,
    ];

    (f_int, is_yielded)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_vertical_beam() {
        let (k, f) = compute_beam_element_matrix(0.0, 0.0, 0.0, 5.0, 200e6, 0.01, 1.0, 10.0);
        // Vertical beam: c=0, s=1; only ss entries should be nonzero
        assert!(k[0].abs() < 1e-6, "K[0,0] should be ~0 for vertical beam");
        assert!(k[5] > 0.0, "K[1,1] should be positive for vertical beam");
        assert!(f[1] < 0.0, "F_grav should be negative (downward)");
    }

    #[test]
    fn test_yield_check() {
        let u_el = [0.0, 0.0, 0.1, 0.0]; // horizontal extension
        let (f_int, yld) = compute_beam_internal_force_yield(
            0.0, 0.0, 5.0, 0.0, &u_el, 200e6, 0.01, 1.0, 100.0, false, 1.0,
        );
        // Very large displacement should yield
        assert!(yld, "Should yield with large displacement");
        assert!(f_int[2] > 0.0, "Positive axial force at node 2");
    }
}
