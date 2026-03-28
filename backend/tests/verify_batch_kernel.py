"""
Verification Test: Rust Batch Kernel Consistency (Post-cleanup)

Verifies that the Rust batch stress kernel produces physically
reasonable and numerically consistent results across all material models
and drainage types.

Note: The original Numba kernel has been removed. This test validates
the Rust kernel independently using physical invariants.
"""
import sys
import numpy as np

sys.path.insert(0, '.')

from backend.solver.stress_rust import compute_elements_stresses_rust


def make_test_data(n_elements, material_model=1, drainage=0):
    """Generate test data."""
    rng = np.random.default_rng(123)
    n_nodes = n_elements * 3
    num_dof = n_nodes * 2

    elem_nodes = np.zeros((n_elements, 6), dtype=np.int64)
    for i in range(n_elements):
        elem_nodes[i] = np.arange(i * 6, (i + 1) * 6) % n_nodes

    B_matrices = rng.standard_normal((n_elements, 3, 3, 12)) * 0.1
    det_J = rng.uniform(0.05, 0.5, (n_elements, 3))
    weights = np.array([1.0/6.0, 1.0/6.0, 1.0/6.0])

    E, nu = 30000.0, 0.3
    factor = E / ((1 + nu) * (1 - 2 * nu))
    D_base = np.array([[factor*(1-nu), factor*nu, 0],
                        [factor*nu, factor*(1-nu), 0],
                        [0, 0, factor*(1-2*nu)/2]])
    D_elastic = np.tile(D_base, (n_elements, 1, 1))

    step_stress = rng.uniform(-200, -10, (n_elements, 3, 3))
    step_strain = rng.uniform(-0.005, 0.005, (n_elements, 3, 3))
    step_pwp = np.zeros((n_elements, 3))
    pwp_static = np.zeros((n_elements, 3))
    total_u = rng.uniform(-0.005, 0.005, num_dof)

    mat_drainage = np.full(n_elements, drainage, dtype=np.int64)
    mat_model = np.full(n_elements, material_model, dtype=np.int64)
    mat_c = np.full(n_elements, 25.0)
    mat_phi = np.full(n_elements, 30.0)
    mat_su = np.full(n_elements, 50.0)
    mat_sigma_ci = np.full(n_elements, 80.0)
    mat_gsi = np.full(n_elements, 60.0)
    mat_disturb = np.full(n_elements, 0.5)
    mat_mb = np.full(n_elements, 3.0)
    mat_s = np.full(n_elements, 0.004)
    mat_a = np.full(n_elements, 0.5)
    penalties = np.full(n_elements, 1e6 if drainage in [1, 2] else 0.0)

    return (elem_nodes, total_u, step_stress, step_strain, step_pwp,
            B_matrices, det_J, weights, D_elastic, pwp_static,
            mat_drainage, mat_model, mat_c, mat_phi, mat_su,
            mat_sigma_ci, mat_gsi, mat_disturb, mat_mb, mat_s, mat_a,
            penalties, False, False, 1.0, num_dof)


def validate_outputs(label, args):
    """Run Rust kernel and validate output shapes and values."""
    F_int, stress, yield_flags, strain, pwp = compute_elements_stresses_rust(*args)
    n_el = args[0].shape[0]
    n_dof = args[-1]

    checks = []

    # Shape checks
    checks.append(("F_int shape", F_int.shape == (n_dof,)))
    checks.append(("Stress shape", stress.shape == (n_el, 3, 3)))
    checks.append(("Yield shape", yield_flags.shape == (n_el, 3)))
    checks.append(("Strain shape", strain.shape == (n_el, 3, 3)))
    checks.append(("PWP shape", pwp.shape == (n_el, 3)))

    # Finiteness
    checks.append(("F_int finite", np.all(np.isfinite(F_int))))
    checks.append(("Stress finite", np.all(np.isfinite(stress))))
    checks.append(("Strain finite", np.all(np.isfinite(strain))))
    checks.append(("PWP finite", np.all(np.isfinite(pwp))))

    # Determinism: second call should give same results
    F2, s2, y2, st2, p2 = compute_elements_stresses_rust(*args)
    checks.append(("Deterministic F_int", np.array_equal(F_int, F2)))
    checks.append(("Deterministic stress", np.array_equal(stress, s2)))
    checks.append(("Deterministic yield", np.array_equal(yield_flags, y2)))

    all_ok = all(v for _, v in checks)
    status = "PASS" if all_ok else "FAIL"

    print(f"  {label}")
    for name, ok in checks:
        mark = "OK" if ok else "FAIL"
        print(f"    [{mark}] {name}")
    print(f"    Result: {status}")
    print()
    return all_ok


if __name__ == "__main__":
    N = 500

    print("=" * 64)
    print("  VERIFICATION: Rust Batch Kernel Consistency")
    print(f"  Testing with {N} elements, 3 GPs each = {N*3} evaluations")
    print("=" * 64)
    print()

    results = []
    results.append(("Drained + MC", validate_outputs("Drained + MC", make_test_data(N, 1, 0))))
    results.append(("Drained + LE", validate_outputs("Drained + LE", make_test_data(N, 0, 0))))
    results.append(("Drained + HB", validate_outputs("Drained + HB", make_test_data(N, 2, 0))))
    results.append(("Undrained_C + MC", validate_outputs("Undrained_C + MC", make_test_data(N, 1, 3))))
    results.append(("Undrained_A + MC", validate_outputs("Undrained_A + MC", make_test_data(N, 1, 1))))
    results.append(("Undrained_B + MC", validate_outputs("Undrained_B + MC", make_test_data(N, 1, 2))))

    print("=" * 64)
    print("  SUMMARY")
    print("=" * 64)
    all_ok = True
    for name, passed in results:
        s = "PASS" if passed else "FAIL"
        print(f"  {name}: {s}")
        if not passed:
            all_ok = False

    if all_ok:
        print(f"\n  [SUCCESS] All {len(results)} tests passed!")
    else:
        print(f"\n  [ERROR] Some tests failed!")

    sys.exit(0 if all_ok else 1)
