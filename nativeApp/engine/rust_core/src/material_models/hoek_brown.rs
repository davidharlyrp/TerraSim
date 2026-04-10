/// Hoek-Brown yield criterion and return mapping algorithm.
///
/// Implements the generalized Hoek-Brown failure criterion for rock masses
/// with Newton-Raphson return mapping in 2D plane strain.

use pyo3::prelude::*;

/// Calculate Hoek-Brown yield function value.
///
/// Uses compressive-positive convention internally:
///   sig_1_c = -sig_math_min (most compressive)
///   sig_3_c = -sig_math_max (least compressive)
///
/// Returns f > 0 if stress state violates the yield surface.
#[pyfunction]
#[pyo3(name = "hoek_brown_yield")]
pub fn hoek_brown_yield_py(
    sig_xx: f64,
    sig_yy: f64,
    sig_xy: f64,
    sigma_ci: f64,
    m_b: f64,
    s: f64,
    a: f64,
) -> f64 {
    hoek_brown_yield(sig_xx, sig_yy, sig_xy, sigma_ci, m_b, s, a)
}

/// Pure Rust implementation.
#[inline]
pub fn hoek_brown_yield(
    sig_xx: f64,
    sig_yy: f64,
    sig_xy: f64,
    sigma_ci: f64,
    m_b: f64,
    s: f64,
    a: f64,
) -> f64 {
    let s_avg = (sig_xx + sig_yy) * 0.5;
    let diff_half = (sig_xx - sig_yy) * 0.5;
    let radius = (diff_half * diff_half + sig_xy * sig_xy).sqrt();

    let sig_math_max = s_avg + radius;
    let sig_math_min = s_avg - radius;

    // Convert to compressive-positive
    let sig_1_c = -sig_math_min;
    let sig_3_c = -sig_math_max;

    // Check tension cap: term must be >= 0
    let term = m_b * sig_3_c / sigma_ci + s;
    if term < 0.0 {
        return sig_1_c - sig_3_c; // Yielded in pure tension
    }

    (sig_1_c - sig_3_c) - sigma_ci * term.powf(a)
}

/// Return mapping algorithm for Hoek-Brown plasticity using Newton-Raphson.
///
/// Finds corrected Mohr circle radius R such that the yield function f(s_avg, R) = 0.
///
/// Returns (sig_xx_corr, sig_yy_corr, sig_xy_corr, is_yielded).
#[pyfunction]
#[pyo3(name = "return_mapping_hoek_brown")]
pub fn return_mapping_hoek_brown_py(
    sig_xx_trial: f64,
    sig_yy_trial: f64,
    sig_xy_trial: f64,
    sigma_ci: f64,
    m_b: f64,
    s: f64,
    a: f64,
) -> (f64, f64, f64, bool) {
    return_mapping_hoek_brown(
        sig_xx_trial,
        sig_yy_trial,
        sig_xy_trial,
        sigma_ci,
        m_b,
        s,
        a,
    )
}

/// Pure Rust return mapping.
#[inline]
pub fn return_mapping_hoek_brown(
    sig_xx_trial: f64,
    sig_yy_trial: f64,
    sig_xy_trial: f64,
    sigma_ci: f64,
    m_b: f64,
    s: f64,
    a: f64,
) -> (f64, f64, f64, bool) {
    let f_trial =
        hoek_brown_yield(sig_xx_trial, sig_yy_trial, sig_xy_trial, sigma_ci, m_b, s, a);

    if f_trial <= 1e-6 {
        return (sig_xx_trial, sig_yy_trial, sig_xy_trial, false);
    }

    let s_avg_trial = (sig_xx_trial + sig_yy_trial) * 0.5;
    let diff_half = (sig_xx_trial - sig_yy_trial) * 0.5;
    let radius_trial = (diff_half * diff_half + sig_xy_trial * sig_xy_trial).sqrt();

    // Solve: 2R - sigma_ci * (m_b * (-s_avg - R) / sigma_ci + s)^a = 0
    // Newton-Raphson on g(R) = 2R - sigma_ci * term^a
    let mut r = radius_trial;

    let mut converged = false;
    for _ in 0..20 {
        let term = m_b * (-s_avg_trial - r) / sigma_ci + s;

        if term < 0.0 {
            // Tension cap
            r = -s_avg_trial + s * sigma_ci / m_b;
            converged = true;
            break;
        }

        let g = 2.0 * r - sigma_ci * term.powf(a);
        // g'(R) = 2 + a * m_b * term^(a-1)
        let g_prime = 2.0 + a * m_b * term.powf(a - 1.0);

        let dr = g / g_prime;
        r -= dr;

        if dr.abs() < 1e-7 * radius_trial {
            converged = true;
            break;
        }
    }

    let _ = converged; // Proceed with best estimate even if not fully converged

    let radius_corrected = r.max(0.0);

    // Reconstruct stresses preserving orientation
    let (cos_2theta, sin_2theta) = if radius_trial > 1e-9 {
        (
            (sig_xx_trial - sig_yy_trial) / (2.0 * radius_trial),
            sig_xy_trial / radius_trial,
        )
    } else {
        (1.0, 0.0)
    };

    let sig_xx_corr = s_avg_trial + radius_corrected * cos_2theta;
    let sig_yy_corr = s_avg_trial - radius_corrected * cos_2theta;
    let sig_xy_corr = radius_corrected * sin_2theta;

    (sig_xx_corr, sig_yy_corr, sig_xy_corr, true)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_elastic_rock() {
        // Low stress in strong rock — elastic
        let f = hoek_brown_yield(-5.0, -10.0, 1.0, 100.0, 5.0, 0.01, 0.5);
        assert!(f < 0.0, "Expected elastic state in rock, got f={f}");
    }

    #[test]
    fn test_yielded_rock() {
        // High deviatoric stress — should yield
        let f = hoek_brown_yield(50.0, -300.0, 20.0, 50.0, 2.0, 0.001, 0.5);
        assert!(f > 0.0, "Expected yielded rock, got f={f}");
    }

    #[test]
    fn test_return_mapping_elastic() {
        let (sx, sy, sxy, yld) =
            return_mapping_hoek_brown(-5.0, -10.0, 1.0, 100.0, 5.0, 0.01, 0.5);
        assert!(!yld);
        assert!((sx - (-5.0)).abs() < 1e-10);
        assert!((sy - (-10.0)).abs() < 1e-10);
        assert!((sxy - 1.0).abs() < 1e-10);
    }

    #[test]
    fn test_return_mapping_plastic() {
        // Use realistic rock stress state (moderate deviatoric stress in compressive regime)
        let (sx, sy, sxy, yld) =
            return_mapping_hoek_brown(-20.0, -120.0, 15.0, 80.0, 3.0, 0.004, 0.5);
        assert!(yld);
        // After return mapping, corrected stress should be significantly closer to yield surface
        let f_trial = hoek_brown_yield(-20.0, -120.0, 15.0, 80.0, 3.0, 0.004, 0.5);
        let f_corr = hoek_brown_yield(sx, sy, sxy, 80.0, 3.0, 0.004, 0.5);
        assert!(
            f_corr.abs() < f_trial.abs() * 0.5,
            "Corrected stress f={f_corr:.4} should be much smaller than trial f={f_trial:.4}"
        );
    }

    #[test]
    fn test_tension_cap() {
        // Tensile state — should trigger tension cap
        let (_, _, _, yld) =
            return_mapping_hoek_brown(100.0, 50.0, 10.0, 30.0, 3.0, 0.001, 0.5);
        assert!(yld, "Tensile state should be yielded");
    }
}
