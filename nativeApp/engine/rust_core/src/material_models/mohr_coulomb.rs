/// Mohr-Coulomb yield criterion and return mapping algorithm.
///
/// Implements the yield function and radial return mapping for
/// elasto-plastic analysis in 2D plane strain.

use pyo3::prelude::*;

/// Calculate Mohr-Coulomb yield function value.
///
/// Returns f > 0 if stress state violates the yield surface.
#[pyfunction]
#[pyo3(name = "mohr_coulomb_yield")]
pub fn mohr_coulomb_yield_py(
    sig_xx: f64,
    sig_yy: f64,
    sig_xy: f64,
    c: f64,
    phi: f64,
) -> f64 {
    mohr_coulomb_yield(sig_xx, sig_yy, sig_xy, c, phi)
}

/// Pure Rust implementation (no Python overhead, callable from other Rust code).
#[inline]
pub fn mohr_coulomb_yield(
    sig_xx: f64,
    sig_yy: f64,
    sig_xy: f64,
    c: f64,
    phi: f64,
) -> f64 {
    let phi_rad = phi.to_radians();
    let sin_phi = phi_rad.sin();
    let cos_phi = phi_rad.cos();

    let s_avg = (sig_xx + sig_yy) * 0.5;
    let diff_half = (sig_xx - sig_yy) * 0.5;
    let radius = (diff_half * diff_half + sig_xy * sig_xy).sqrt();

    let sig_max = s_avg + radius;
    let sig_min = s_avg - radius;

    (sig_max - sig_min) + (sig_max + sig_min) * sin_phi - 2.0 * c * cos_phi
}

/// Return mapping algorithm for Mohr-Coulomb plasticity (radial return).
///
/// Returns (sig_xx_corr, sig_yy_corr, sig_xy_corr, is_yielded).
#[pyfunction]
#[pyo3(name = "return_mapping_mohr_coulomb")]
pub fn return_mapping_mohr_coulomb_py(
    sig_xx_trial: f64,
    sig_yy_trial: f64,
    sig_xy_trial: f64,
    c: f64,
    phi: f64,
) -> (f64, f64, f64, bool) {
    return_mapping_mohr_coulomb(sig_xx_trial, sig_yy_trial, sig_xy_trial, c, phi)
}

/// Pure Rust return mapping (callable from other Rust modules).
#[inline]
pub fn return_mapping_mohr_coulomb(
    sig_xx_trial: f64,
    sig_yy_trial: f64,
    sig_xy_trial: f64,
    c: f64,
    phi: f64,
) -> (f64, f64, f64, bool) {
    let f_trial = mohr_coulomb_yield(sig_xx_trial, sig_yy_trial, sig_xy_trial, c, phi);

    if f_trial <= 1e-6 {
        return (sig_xx_trial, sig_yy_trial, sig_xy_trial, false);
    }

    let phi_rad = phi.to_radians();
    let sin_phi = phi_rad.sin();
    let cos_phi = phi_rad.cos();

    let mut s_avg_trial = (sig_xx_trial + sig_yy_trial) * 0.5;
    let diff_half = (sig_xx_trial - sig_yy_trial) * 0.5;
    let radius_trial = (diff_half * diff_half + sig_xy_trial * sig_xy_trial).sqrt();

    let mut q_target = 2.0 * c * cos_phi - 2.0 * s_avg_trial * sin_phi;

    if q_target < 0.0 {
        q_target = 0.0;
        // Tension cut-off cap
        if sin_phi > 0.0 {
            let limit_p = c * cos_phi / sin_phi;
            if s_avg_trial > limit_p {
                s_avg_trial = limit_p;
            }
        }
    }

    // Scale down radius
    let scale_factor = if radius_trial > 1e-9 {
        let sf = q_target / (2.0 * radius_trial);
        sf.clamp(0.0, 1.0)
    } else {
        0.0
    };

    let radius_corrected = radius_trial * scale_factor;

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
    fn test_elastic_state_not_yielded() {
        // Small stress — should remain elastic
        let f = mohr_coulomb_yield(-10.0, -20.0, 2.0, 50.0, 30.0);
        assert!(f < 0.0, "Expected elastic state, got f={f}");
    }

    #[test]
    fn test_yielded_state() {
        // Large deviatoric stress — should yield
        let f = mohr_coulomb_yield(100.0, -200.0, 50.0, 10.0, 25.0);
        assert!(f > 0.0, "Expected yielded state, got f={f}");
    }

    #[test]
    fn test_return_mapping_elastic() {
        let (sx, sy, sxy, yld) =
            return_mapping_mohr_coulomb(-10.0, -20.0, 2.0, 50.0, 30.0);
        assert!(!yld);
        assert!((sx - (-10.0)).abs() < 1e-10);
        assert!((sy - (-20.0)).abs() < 1e-10);
        assert!((sxy - 2.0).abs() < 1e-10);
    }

    #[test]
    fn test_return_mapping_plastic() {
        let (sx, sy, sxy, yld) =
            return_mapping_mohr_coulomb(100.0, -200.0, 50.0, 10.0, 25.0);
        assert!(yld);
        // After return mapping, the corrected stress should satisfy yield = 0
        let f_corr = mohr_coulomb_yield(sx, sy, sxy, 10.0, 25.0);
        assert!(
            f_corr.abs() < 1.0,
            "Corrected stress should be near yield surface, got f={f_corr}"
        );
    }

    #[test]
    fn test_undrained_c_mode() {
        // Su = 50 kPa, phi = 0 (undrained)
        let (sx, sy, sxy, yld) =
            return_mapping_mohr_coulomb(-50.0, -200.0, 80.0, 50.0, 0.0);
        assert!(yld);
        let f_corr = mohr_coulomb_yield(sx, sy, sxy, 50.0, 0.0);
        assert!(
            f_corr.abs() < 1.0,
            "Undrained corrected stress should be near yield surface, got f={f_corr}"
        );
    }
}
