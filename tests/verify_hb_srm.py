import numpy as np
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.solver.hoek_brown import hoek_brown_yield, return_mapping_hoek_brown

def test_hb_yield():
    print("Testing Hoek-Brown Yield Function...")
    sig_ci = 30000.0 # kPa (30 MPa) intact rock
    m_b = 2.0
    s = 0.01
    a = 0.5
    
    # sig_1_c = -sig_min, sig_3_c = -sig_max
    # Pure compression: sig_xx=-1000, sig_yy=-1000 -> sig_1_c=1000, sig_3_c=1000
    f = hoek_brown_yield(-1000, -1000, 0, sig_ci, m_b, s, a)
    print(f"Yield f at -1000 kPa (comp): {f:.2f} (Should be negative/elastic)")
    
    # Significant compression: sig_1_c=50000, sig_3_c=0
    f_yield = hoek_brown_yield(-50000, 0, 0, sig_ci, m_b, s, a)
    print(f"Yield f at -50000 kPa (failure): {f_yield:.2f} (Should be positive/yielded)")
    
    assert f < 0
    assert f_yield > 0
    print("Yield test PASSED.")

def test_hb_return_mapping():
    print("\nTesting Hoek-Brown Return Mapping...")
    sig_ci = 20000.0
    m_b = 1.6
    s = 0.004
    a = 0.51
    D_el = np.eye(3) * 1e6 # Mock D matrix
    
    # Trial stress that clearly yields: sig_1_c=40000, sig_3_c=0
    sig_xx_trial = -40000.0
    sig_yy_trial = 0.0
    sig_xy_trial = 0.0
    
    sig_corr, _, yld = return_mapping_hoek_brown(
        sig_xx_trial, sig_yy_trial, sig_xy_trial,
        sig_ci, m_b, s, a, D_el
    )
    
    print(f"Yielded: {yld}")
    print(f"Corrected Stress: {sig_corr}")
    
    # Verify new stress is on or inside the yield surface
    f_new = hoek_brown_yield(sig_corr[0], sig_corr[1], sig_corr[2], sig_ci, m_b, s, a)
    print(f"New Yield f: {f_new:.6f} (Should be close to 0)")
    
    assert yld == True
    assert abs(f_new) < 1e-3
    print("Return mapping test PASSED.")

def test_hb_srm_logic():
    print("\nTesting SRM Reduction Logic simulation...")
    sig_ci = 20000.0
    m_b = 2.0
    s = 0.01
    a = 0.5
    D_el = np.eye(3) * 1e6
    
    # Static stress state sig_1_c=1000, sig_3_c=0 (Elastic at SF=1)
    sig_xx = -1000.0
    f_orig = hoek_brown_yield(sig_xx, 0, 0, sig_ci, m_b, s, a)
    print(f"Original f at {sig_xx}: {f_orig:.2f} (Elastic)")
    
    # Apply SF = 10 (Target M-Stage)
    SF = 10.0
    sig_ci_f = sig_ci / SF
    m_b_f = m_b / SF
    s_f = s / SF
    # Strength becomes 2000/sqrt(10) * sqrt(0.01/10) ... wait
    # sig_ci_f = 2000, term = 0.001 -> f = 1000 - 2000*sqrt(0.001) = 1000 - 63 = 937 > 0
    
    f_srm = hoek_brown_yield(sig_xx, 0, 0, sig_ci_f, m_b_f, s_f, a)
    print(f"SRM f at SF={SF}: {f_srm:.2f} (Should be yielded)")
    
    assert f_orig < 0
    assert f_srm > 0
    print("SRM logic test PASSED.")

if __name__ == "__main__":
    try:
        test_hb_yield()
        test_hb_return_mapping()
        test_hb_srm_logic()
        print("\nAll Hoek-Brown verification tests PASSED!")
    except Exception as e:
        print(f"\nTest FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
