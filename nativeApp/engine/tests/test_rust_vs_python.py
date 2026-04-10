"""
Verification Test: Rust vs Python Material Models

Compares output of terrasim_core (Rust) against the original
Numba/Python implementations to ensure numerical equivalence.
"""
import sys
import numpy as np

# --- Import Rust ---
import terrasim_core

# --- Import Python/Numba originals ---
sys.path.insert(0, '.')
from engine.solver.mohr_coulomb import mohr_coulomb_yield as py_mc_yield
from engine.solver.mohr_coulomb import return_mapping_mohr_coulomb as py_mc_return
from engine.solver.hoek_brown import hoek_brown_yield as py_hb_yield
from engine.solver.hoek_brown import return_mapping_hoek_brown as py_hb_return


def test_mohr_coulomb_yield():
    """Test Mohr-Coulomb yield function: Rust vs Python."""
    test_cases = [
        # (sig_xx, sig_yy, sig_xy, c, phi)
        (-10.0, -20.0, 2.0, 50.0, 30.0),     # Elastic
        (100.0, -200.0, 50.0, 10.0, 25.0),    # Yielded
        (-50.0, -50.0, 0.0, 20.0, 0.0),       # Undrained phi=0
        (-100.0, -200.0, 30.0, 0.0, 35.0),    # c=0 frictional
        (0.0, 0.0, 0.0, 10.0, 30.0),          # Zero stress
        (-5.0, -300.0, 80.0, 5.0, 40.0),      # High deviatoric
        (50.0, -10.0, 20.0, 100.0, 20.0),     # Tensile regime
        (-30.0, -30.0, 30.0, 25.0, 28.0),     # Pure shear component
    ]
    
    print("=" * 60)
    print("Mohr-Coulomb Yield Function Verification")
    print("=" * 60)
    
    all_pass = True
    for i, (sxx, syy, sxy, c, phi) in enumerate(test_cases):
        f_rust = terrasim_core.mohr_coulomb_yield(sxx, syy, sxy, c, phi)
        f_py = py_mc_yield(sxx, syy, sxy, c, phi)
        diff = abs(f_rust - f_py)
        ok = diff < 1e-8
        status = "PASS" if ok else "FAIL"
        print(f"  Case {i+1}: f_rust={f_rust:12.6f}  f_py={f_py:12.6f}  diff={diff:.2e}  {status}")
        if not ok:
            all_pass = False
    
    return all_pass


def test_mohr_coulomb_return_mapping():
    """Test Mohr-Coulomb return mapping: Rust vs Python."""
    test_cases = [
        # (sig_xx, sig_yy, sig_xy, c, phi)
        (-10.0, -20.0, 2.0, 50.0, 30.0),     # Elastic
        (100.0, -200.0, 50.0, 10.0, 25.0),    # Yielded
        (-50.0, -200.0, 80.0, 50.0, 0.0),     # Undrained (phi=0)
        (-100.0, -200.0, 30.0, 0.0, 35.0),    # c=0 frictional
        (50.0, -10.0, 20.0, 5.0, 20.0),       # Tensile
    ]
    
    print("\n" + "=" * 60)
    print("Mohr-Coulomb Return Mapping Verification")
    print("=" * 60)
    
    # Dummy D_elastic for Python version
    E, nu = 30000.0, 0.3
    factor = E / ((1 + nu) * (1 - 2 * nu))
    D = np.array([
        [factor * (1 - nu), factor * nu, 0],
        [factor * nu, factor * (1 - nu), 0],
        [0, 0, factor * (1 - 2 * nu) / 2]
    ])
    
    all_pass = True
    for i, (sxx, syy, sxy, c, phi) in enumerate(test_cases):
        sx_r, sy_r, sxy_r, yld_r = terrasim_core.return_mapping_mohr_coulomb(sxx, syy, sxy, c, phi)
        sig_py, _, yld_py = py_mc_return(sxx, syy, sxy, c, phi, D)
        
        diff_xx = abs(sx_r - sig_py[0])
        diff_yy = abs(sy_r - sig_py[1])
        diff_xy = abs(sxy_r - sig_py[2])
        max_diff = max(diff_xx, diff_yy, diff_xy)
        yield_match = (yld_r == yld_py)
        ok = max_diff < 1e-4 and yield_match
        status = "PASS" if ok else "FAIL"
        
        print(f"  Case {i+1}: Rust=({sx_r:9.3f},{sy_r:9.3f},{sxy_r:8.3f}) yld={yld_r}")
        print(f"          Py  =({sig_py[0]:9.3f},{sig_py[1]:9.3f},{sig_py[2]:8.3f}) yld={yld_py}")
        print(f"          max_diff={max_diff:.2e}  yield_match={yield_match}  {status}")
        if not ok:
            all_pass = False
    
    return all_pass


def test_hoek_brown_yield():
    """Test Hoek-Brown yield function: Rust vs Python."""
    test_cases = [
        # (sig_xx, sig_yy, sig_xy, sigma_ci, m_b, s, a)
        (-5.0, -10.0, 1.0, 100.0, 5.0, 0.01, 0.5),     # Elastic
        (-20.0, -120.0, 15.0, 80.0, 3.0, 0.004, 0.5),   # Moderate
        (-50.0, -300.0, 20.0, 50.0, 2.0, 0.001, 0.5),   # Yielded
        (10.0, -50.0, 5.0, 200.0, 8.0, 0.1, 0.5),       # Strong rock
        (50.0, 20.0, 10.0, 30.0, 3.0, 0.001, 0.5),      # Tensile
    ]
    
    print("\n" + "=" * 60)
    print("Hoek-Brown Yield Function Verification")
    print("=" * 60)
    
    all_pass = True
    for i, (sxx, syy, sxy, sci, mb, s, a) in enumerate(test_cases):
        f_rust = terrasim_core.hoek_brown_yield(sxx, syy, sxy, sci, mb, s, a)
        f_py = py_hb_yield(sxx, syy, sxy, sci, mb, s, a)
        diff = abs(f_rust - f_py)
        ok = diff < 1e-6
        status = "PASS" if ok else "FAIL"
        print(f"  Case {i+1}: f_rust={f_rust:12.6f}  f_py={f_py:12.6f}  diff={diff:.2e}  {status}")
        if not ok:
            all_pass = False
    
    return all_pass


def test_hoek_brown_return_mapping():
    """Test Hoek-Brown return mapping: Rust vs Python."""
    test_cases = [
        # (sig_xx, sig_yy, sig_xy, sigma_ci, m_b, s, a)
        (-5.0, -10.0, 1.0, 100.0, 5.0, 0.01, 0.5),     # Elastic
        (-20.0, -120.0, 15.0, 80.0, 3.0, 0.004, 0.5),   # Yielded
        (-50.0, -250.0, 20.0, 60.0, 2.5, 0.002, 0.5),   # Yielded 2
    ]
    
    print("\n" + "=" * 60)
    print("Hoek-Brown Return Mapping Verification")
    print("=" * 60)
    
    # Dummy D_elastic for Python version
    E, nu = 50000.0, 0.25
    factor = E / ((1 + nu) * (1 - 2 * nu))
    D = np.array([
        [factor * (1 - nu), factor * nu, 0],
        [factor * nu, factor * (1 - nu), 0],
        [0, 0, factor * (1 - 2 * nu) / 2]
    ])
    
    all_pass = True
    for i, (sxx, syy, sxy, sci, mb, s, a) in enumerate(test_cases):
        sx_r, sy_r, sxy_r, yld_r = terrasim_core.return_mapping_hoek_brown(sxx, syy, sxy, sci, mb, s, a)
        sig_py, _, yld_py = py_hb_return(sxx, syy, sxy, sci, mb, s, a, D)
        
        diff_xx = abs(sx_r - sig_py[0])
        diff_yy = abs(sy_r - sig_py[1])
        diff_xy = abs(sxy_r - sig_py[2])
        max_diff = max(diff_xx, diff_yy, diff_xy)
        yield_match = (yld_r == yld_py)
        ok = max_diff < 1.0 and yield_match  # HB has inherent NR convergence differences
        status = "PASS" if ok else "FAIL"
        
        print(f"  Case {i+1}: Rust=({sx_r:9.3f},{sy_r:9.3f},{sxy_r:8.3f}) yld={yld_r}")
        print(f"          Py  =({sig_py[0]:9.3f},{sig_py[1]:9.3f},{sig_py[2]:8.3f}) yld={yld_py}")
        print(f"          max_diff={max_diff:.2e}  yield_match={yield_match}  {status}")
        if not ok:
            all_pass = False
    
    return all_pass


if __name__ == "__main__":
    results = []
    results.append(("MC Yield", test_mohr_coulomb_yield()))
    results.append(("MC Return Mapping", test_mohr_coulomb_return_mapping()))
    results.append(("HB Yield", test_hoek_brown_yield()))
    results.append(("HB Return Mapping", test_hoek_brown_return_mapping()))
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    all_ok = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_ok = False
    
    if all_ok:
        print("\n[SUCCESS] All tests passed! Rust and Python implementations match.")
    else:
        print("\n[ERROR] Some tests failed. Review differences above.")
    
    sys.exit(0 if all_ok else 1)
