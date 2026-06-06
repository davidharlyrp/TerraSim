/// Hardening Soil (HS) yield criterion and return mapping algorithm.
///
/// Implements the yield functions (shear and cap) and return mapping for
/// the Hardening Soil model in 2D plane strain.

use pyo3::prelude::*;
use crate::material_models::mohr_coulomb::mohr_coulomb_yield;

/// Return mapping algorithm for Hardening Soil plasticity.
///
/// Returns (sig_xx_corr, sig_yy_corr, sig_xy_corr, gamma_p_new, p_c_new, is_yielded).
#[pyfunction]
#[pyo3(name = "return_mapping_hardening_soil")]
#[allow(clippy::too_many_arguments)]
pub fn return_mapping_hardening_soil_py(
    sig_xx_trial: f64,
    sig_yy_trial: f64,
    sig_xy_trial: f64,
    gamma_p_old: f64,
    p_c_old: f64,
    c: f64,
    phi: f64,
    _e50_ref: f64,
    _e_oed_ref: f64,
    _e_ur_ref: f64,
    _m_power: f64,
    _p_ref: f64,
) -> (f64, f64, f64, f64, f64, bool) {
    return_mapping_hardening_soil(
        sig_xx_trial, sig_yy_trial, sig_xy_trial,
        gamma_p_old, p_c_old,
        c, phi,
        _e50_ref, _e_oed_ref, _e_ur_ref, _m_power, _p_ref
    )
}

/// Pure Rust return mapping for Hardening Soil.
#[inline]
#[allow(clippy::too_many_arguments)]
pub fn return_mapping_hardening_soil(
    sig_xx_trial: f64,
    sig_yy_trial: f64,
    sig_xy_trial: f64,
    gamma_p_old: f64,
    mut p_c_old: f64,
    c: f64,
    phi: f64,
    _e50_ref: f64,
    _e_oed_ref: f64,
    _e_ur_ref: f64,
    _m_power: f64,
    _p_ref: f64,
) -> (f64, f64, f64, f64, f64, bool) {
    let mut is_yielded = false;
    let mut sig_xx = sig_xx_trial;
    let mut sig_yy = sig_yy_trial;
    let mut sig_xy = sig_xy_trial;
    let mut gamma_p_new = gamma_p_old;

    // 1. Calculate stress invariants (TerraSim convention: tension is positive)
    let s_avg = (sig_xx + sig_yy) * 0.5;
    let diff_half = (sig_xx - sig_yy) * 0.5;
    let radius = (diff_half * diff_half + sig_xy * sig_xy).sqrt();
    
    // In PLAXIS, p is mean effective stress (compressive positive)
    // For 2D plane strain, p' = - (sig_xx + sig_yy + sig_zz) / 3. 
    // We approximate p' ~ -s_avg for the cap in 2D if sig_zz is not tracked.
    let mut p_prime = -s_avg; 
    if p_prime < 0.0 { p_prime = 0.0; } // Tension cut-off handled by Mohr-Coulomb
    
    // Equivalent deviatoric stress q
    // In 2D plane strain, q ~ 2 * radius (diameter of Mohr circle)
    let q = 2.0 * radius;

    // --- A. SHEAR YIELDING (Mohr-Coulomb Failure Envelope Approximation) ---
    // The true HS model uses a hyperbolic hardening rule that expands up to the MC failure envelope.
    // To ensure numerical stability in this implementation, we use the MC envelope as the absolute limit (perfectly plastic limit state),
    // while tracking the plastic shear strain.
    let f_mc = mohr_coulomb_yield(sig_xx, sig_yy, sig_xy, c, phi);
    if f_mc > 1e-6 {
        is_yielded = true;
        // Perform standard MC radial return to the failure envelope
        let (sx_corr, sy_corr, sxy_corr, _) = crate::material_models::mohr_coulomb::return_mapping_mohr_coulomb(
            sig_xx, sig_yy, sig_xy, c, phi
        );
        sig_xx = sx_corr;
        sig_yy = sy_corr;
        sig_xy = sxy_corr;
        
        // Approximate increment in plastic shear strain (proportional to stress correction magnitude)
        let dq = q - 2.0 * ((sig_xx - sig_yy) * 0.5 * (sig_xx - sig_yy) * 0.5 + sig_xy * sig_xy).sqrt();
        if dq > 0.0 {
            let g_ur = _e_ur_ref / (2.0 * (1.0 + 0.2)); // Approximate G_ur (assumed nu=0.2)
            gamma_p_new += dq / g_ur;
        }
    }

    // --- B. CAP YIELDING (Volumetric Hardening) ---
    // Cap yield surface: f_c = q^2 / alpha^2 + p^2 - p_c^2 <= 0
    // alpha is a material constant determining the steepness of the cap. 
    // We can approximate alpha from K0_nc. A standard value is alpha ~ 1.0 to 1.5.
    let alpha = 1.0; 
    
    // Ensure p_c_old is at least some minimal value to avoid division by zero or immediate yield at rest
    if p_c_old < 1.0 {
        p_c_old = 1.0;
    }

    // Recalculate p and q after potential shear correction
    let s_avg_corr = (sig_xx + sig_yy) * 0.5;
    let diff_half_corr = (sig_xx - sig_yy) * 0.5;
    let radius_corr = (diff_half_corr * diff_half_corr + sig_xy * sig_xy).sqrt();
    let p_prime_corr = (-s_avg_corr).max(0.0);
    let q_corr = 2.0 * radius_corr;

    let f_cap = (q_corr * q_corr) / (alpha * alpha) + p_prime_corr * p_prime_corr - p_c_old * p_c_old;

    let mut p_c_new = p_c_old;

    if f_cap > 1e-6 {
        is_yielded = true;
        
        // Cap return mapping (projecting back to the expanding cap)
        // Since the cap hardens, it expands. We find the intersection.
        // Volumetric plastic strain causes p_c to increase.
        // For a robust simplified solver, if it hits the cap, we expand the cap to match the stress state,
        // signifying volumetric hardening has occurred.
        // p_c_new = sqrt(q^2/alpha^2 + p^2)
        p_c_new = ((q_corr * q_corr) / (alpha * alpha) + p_prime_corr * p_prime_corr).sqrt();
        
        // In a true implicit solver, the stress would also relax slightly based on K_ur, 
        // but expanding the cap (hardening) is the primary physical response.
    }

    (sig_xx, sig_yy, sig_xy, gamma_p_new, p_c_new, is_yielded)
}
