"""
Mohr-Coulomb Module
Implements yield function and return mapping algorithm for elasto-plastic analysis
"""
import numpy as np
from typing import Tuple

from numba import njit

@njit
def mohr_coulomb_yield(sig_xx: float, sig_yy: float, sig_xy: float, 
                       c: float, phi: float) -> float:
    """
    Calculate Mohr-Coulomb yield function value.
    """
    # Convert phi to radians
    phi_rad = np.deg2rad(phi)
    sin_phi = np.sin(phi_rad)
    cos_phi = np.cos(phi_rad)
    
    s_avg = (sig_xx + sig_yy) / 2.0
    radius = np.sqrt(((sig_xx - sig_yy) / 2.0)**2 + sig_xy**2)
    
    sig_math_max = s_avg + radius
    sig_math_min = s_avg - radius
    
    f = (sig_math_max - sig_math_min) + (sig_math_max + sig_math_min) * sin_phi - 2.0 * c * cos_phi
    
    return f


@njit
def return_mapping_mohr_coulomb(
    sig_xx_trial: float, 
    sig_yy_trial: float, 
    sig_xy_trial: float,
    c: float, 
    phi: float,
    D_elastic: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, bool]:
    """
    Return mapping algorithm for Mohr-Coulomb plasticity (radial return method).
    """
    # Check yield
    f_trial = mohr_coulomb_yield(sig_xx_trial, sig_yy_trial, sig_xy_trial, c, phi)
    
    if f_trial <= 1e-6:
        return np.array([sig_xx_trial, sig_yy_trial, sig_xy_trial]), D_elastic, False
    
    phi_rad = np.deg2rad(phi)
    sin_phi = np.sin(phi_rad)
    cos_phi = np.cos(phi_rad)
    
    # Principal stresses of trial
    s_avg_trial = (sig_xx_trial + sig_yy_trial) / 2.0
    radius_trial = np.sqrt(((sig_xx_trial - sig_yy_trial) / 2.0)**2 + sig_xy_trial**2)
    
    p_trial = s_avg_trial
    q_target = 2.0 * c * cos_phi - 2.0 * p_trial * sin_phi
    
    if q_target < 0:
        q_target = 0.0
        # Tension Cut-off cap
        limit_p = 1e9
        if sin_phi > 0:
            limit_p = c * cos_phi / sin_phi
        if s_avg_trial > limit_p:
            s_avg_trial = limit_p

    # Scale down radius
    if radius_trial > 1e-9:
        scale_factor = q_target / (2.0 * radius_trial)
        if scale_factor < 0: scale_factor = 0.0
        if scale_factor > 1.0: scale_factor = 1.0
    else:
        scale_factor = 0.0
    
    radius_corrected = radius_trial * scale_factor
    
    # Reconstruct stresses
    if radius_trial > 1e-9:
        cos_2theta = (sig_xx_trial - sig_yy_trial) / (2.0 * radius_trial)
        sin_2theta = sig_xy_trial / radius_trial
    else:
        cos_2theta = 1.0
        sin_2theta = 0.0
    
    sig_xx_corrected = s_avg_trial + radius_corrected * cos_2theta
    sig_yy_corrected = s_avg_trial - radius_corrected * cos_2theta
    sig_xy_corrected = radius_corrected * sin_2theta
    
    sigma_corrected = np.array([sig_xx_corrected, sig_yy_corrected, sig_xy_corrected])
    D_tangent = D_elastic
    
    return sigma_corrected, D_tangent, True
