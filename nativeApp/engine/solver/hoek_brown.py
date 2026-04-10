"""
Hoek-Brown Module
Implements yield function and return mapping algorithm for elasto-plastic analysis
"""
import numpy as np
from typing import Tuple

from numba import njit

@njit
def hoek_brown_yield(
    sig_xx: float, 
    sig_yy: float, 
    sig_xy: float, 
    sigma_ci: float, # Unconfined compressive strength
    m_b: float, #
    s: float, #
    a: float #
) -> float:
    """
    Calculate Hoek-Brown yield function value.
    Tension positive: sig_math_max is least compressive (sigma_3 in HB), 
    sig_math_min is most compressive (sigma_1 in HB).
    HB: sig_1_c - sig_3_c - sig_ci * (m_b * sig_3_c / sig_ci + s)^a = 0
    where sig_1_c = -sig_math_min, sig_3_c = -sig_math_max
    """
    s_avg = (sig_xx + sig_yy) / 2.0
    radius = np.sqrt(((sig_xx - sig_yy) / 2.0)**2 + sig_xy**2)
    
    sig_math_max = s_avg + radius
    sig_math_min = s_avg - radius
    
    # Compressive stresses (positive)
    sig_1_c = -sig_math_min
    sig_3_c = -sig_math_max
    
    # Check for tension cap (m_b * sig_3_c / sig_ci + s must be >= 0)
    term = m_b * sig_3_c / sigma_ci + s
    if term < 0:
        return sig_1_c - sig_3_c # Yielded in pure tension
        
    f = (sig_1_c - sig_3_c) - (sigma_ci * (term ** a))
    return f


@njit
def return_mapping_hoek_brown(
    sig_xx_trial: float, 
    sig_yy_trial: float, 
    sig_xy_trial: float,
    sigma_ci: float,
    m_b: float,
    s: float,
    a: float,
    D_elastic: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, bool]:
    """
    Return mapping algorithm for Hoek-Brown plasticity using Newton-Raphson.
    Finds R such that f(s_avg, R) = 0.
    """
    # Check yield
    f_trial = hoek_brown_yield(sig_xx_trial, sig_yy_trial, sig_xy_trial, sigma_ci, m_b, s, a)
    
    if f_trial <= 1e-6:
        return np.array([sig_xx_trial, sig_yy_trial, sig_xy_trial]), D_elastic, False
    
    s_avg_trial = (sig_xx_trial + sig_yy_trial) / 2.0
    radius_trial = np.sqrt(((sig_xx_trial - sig_yy_trial) / 2.0)**2 + sig_xy_trial**2)
    
    # Solve 2R - sigma_ci * (m_b * (-s_avg - R) / sigma_ci + s)^a = 0 for R
    # Let g(R) = 2R - sigma_ci * (term)^a
    # term = (m_b * (-s_avg - R) / sigma_ci + s)
    
    R = radius_trial
    converged = False
    for _ in range(20): # Newton-Raphson loop
        term = (m_b * (-s_avg_trial - R) / sigma_ci + s)
        
        # Handle tension cap
        if term < 0:
            R = -s_avg_trial + (s * sigma_ci / m_b)
            converged = True
            break
            
        g = 2.0 * R - sigma_ci * (term ** a)
        # g'(R) = 2 + a * m_b * (term)^(a-1)
        g_prime = 2.0 + a * m_b * (term ** (a - 1.0))
        
        dR = g / g_prime
        R -= dR
        
        if abs(dR) < 1e-7 * radius_trial:
            converged = True
            break
            
    radius_corrected = R
    if radius_corrected < 0: radius_corrected = 0.0
    
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
