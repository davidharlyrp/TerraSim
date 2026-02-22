"""
Arc Length Method Module
Implements the Crisfield Cylindrical Arc-Length Method for nonlinear FEA.

This method replaces standard Newton-Raphson iteration when enabled,
allowing the solver to trace load-displacement paths through limit points
(snap-through / snap-back behavior common in softening materials and collapse).

Reference:
  Crisfield, M.A. (1981). "A fast incremental/iterative solution procedure
  that handles snap-through." Computers & Structures, 13, 55-62.
"""
import numpy as np
from scipy.sparse.linalg import spsolve


def compute_initial_arc_length(step_size, delta_F_external_free, K_free):
    """
    Compute the initial arc-length radius (Δl) for the first predictor step.
    
    Uses the tangent predictor: Δl = step_size * ||K⁻¹ · F_ref||
    
    Args:
        step_size: Current load step fraction (e.g., 0.05)
        delta_F_external_free: Reference external force vector (free DOFs only)
        K_free: Stiffness matrix (free DOFs only, CSR sparse)
    
    Returns:
        arc_length_radius: The computed Δl value
        du_predictor: The predictor displacement K⁻¹ · F_ref (free DOFs)
    """
    try:
        du_predictor = spsolve(K_free, delta_F_external_free)
        if not np.all(np.isfinite(du_predictor)):
            return step_size, np.zeros_like(delta_F_external_free)
        
        predictor_norm = np.linalg.norm(du_predictor)
        if predictor_norm < 1e-15:
            return step_size, du_predictor
        
        arc_length_radius = step_size * predictor_norm
        return arc_length_radius, du_predictor
    except Exception:
        return step_size, np.zeros_like(delta_F_external_free)


def arc_length_predictor(K_free, F_ref_free, arc_length_radius, sign_lambda):
    """
    Compute the predictor step for the arc-length method.
    
    The predictor finds a tangent point on the equilibrium path and
    scales it to satisfy the arc-length constraint.
    
    Args:
        K_free: Current tangent stiffness matrix (free DOFs, CSR sparse)
        F_ref_free: Reference load vector (free DOFs)
        arc_length_radius: Target arc length Δl
        sign_lambda: Sign of load parameter increment (+1 or -1)
    
    Returns:
        delta_u_pred: Predictor displacement increment (free DOFs)
        delta_lambda_pred: Predictor load parameter increment
        success: Whether the predictor step succeeded
    """
    try:
        du_f = spsolve(K_free, F_ref_free)
        
        if not np.all(np.isfinite(du_f)):
            return np.zeros_like(F_ref_free), 0.0, False
        
        norm_du_f = np.linalg.norm(du_f)
        if norm_du_f < 1e-15:
            return np.zeros_like(F_ref_free), 0.0, False
        
        # Δλ = ±Δl / ||δu_f||
        delta_lambda_pred = sign_lambda * arc_length_radius / norm_du_f
        delta_u_pred = delta_lambda_pred * du_f
        
        return delta_u_pred, delta_lambda_pred, True
    except Exception:
        return np.zeros_like(F_ref_free), 0.0, False


def arc_length_corrector(
    K_free, R_free, F_ref_free,
    delta_u_total, delta_lambda_total,
    arc_length_radius
):
    """
    Compute the corrector step using Crisfield's cylindrical constraint.
    
    Solves two linear systems:
        K · δu_r = R        (residual correction)
        K · δu_f = F_ref    (load correction)
    
    Then enforces the cylindrical constraint:
        ||Δu + δu||² = Δl²
    
    This yields a quadratic in δλ. The root is chosen to minimize
    the angle between old and new displacement increments.
    
    Args:
        K_free: Current tangent stiffness (free DOFs, CSR sparse)
        R_free: Current residual vector (free DOFs)
        F_ref_free: Reference load vector (free DOFs)
        delta_u_total: Accumulated displacement increment for this step (free DOFs)
        delta_lambda_total: Accumulated load parameter for this step
        arc_length_radius: Target arc-length Δl
    
    Returns:
        du_corr: Corrector displacement update (free DOFs)
        d_lambda_corr: Corrector load parameter update
        success: Whether corrector succeeded
    """
    try:
        du_r = spsolve(K_free, R_free)
        du_f = spsolve(K_free, F_ref_free)
        
        if not np.all(np.isfinite(du_r)) or not np.all(np.isfinite(du_f)):
            return np.zeros_like(R_free), 0.0, False
        
        # Crisfield cylindrical arc-length constraint
        # (Δu + δu_r + δλ·δu_f)·(Δu + δu_r + δλ·δu_f) = Δl²
        # Expanding: a·δλ² + b·δλ + c = 0
        
        u_tilde = delta_u_total + du_r  # Δu + δu_r
        
        a = np.dot(du_f, du_f)
        b = 2.0 * np.dot(u_tilde, du_f)
        c = np.dot(u_tilde, u_tilde) - arc_length_radius**2
        
        discriminant = b**2 - 4.0 * a * c
        
        if discriminant < 0:
            # Constraint cannot be satisfied — fall back to pure residual correction
            # This can happen when the arc-length radius is too small
            return du_r, 0.0, True
        
        if abs(a) < 1e-30:
            # du_f is essentially zero — just use residual correction
            return du_r, 0.0, True
        
        sqrt_disc = np.sqrt(discriminant)
        d_lambda_1 = (-b + sqrt_disc) / (2.0 * a)
        d_lambda_2 = (-b - sqrt_disc) / (2.0 * a)
        
        # Choose root that gives positive cosine with current direction
        # (i.e., don't reverse direction along the path)
        du_1 = du_r + d_lambda_1 * du_f
        du_2 = du_r + d_lambda_2 * du_f
        
        new_u_1 = delta_u_total + du_1
        new_u_2 = delta_u_total + du_2
        
        cos_1 = np.dot(delta_u_total, new_u_1) if np.linalg.norm(delta_u_total) > 1e-15 else 1.0
        cos_2 = np.dot(delta_u_total, new_u_2) if np.linalg.norm(delta_u_total) > 1e-15 else 1.0
        
        if cos_1 >= cos_2:
            return du_1, d_lambda_1, True
        else:
            return du_2, d_lambda_2, True
    except Exception:
        return np.zeros_like(R_free), 0.0, False


def run_arc_length_step(
    # Stiffness assembly callback
    assemble_stiffness_fn,
    # Stress computation callback
    compute_stresses_fn,
    # Beam internal force callback
    compute_beam_forces_fn,
    # Current state
    free_dofs, num_dof,
    F_int_initial, delta_F_external,
    total_displacement, current_u_incremental,
    # Settings
    max_iterations, tolerance,
    arc_length_radius,
    sign_lambda,
    # Reference for m_stage
    current_m_stage, is_srm,
    # Optional: separate reference load direction for arc-length constraint
    F_ref_direction=None,
    # Previous converged step displacement (free DOFs) for limit point detection
    prev_delta_u_free=None
):
    """
    Execute one arc-length load step with iterative correction.
    Supports negative LDC (snap-back) via automatic sign_lambda detection.
    
    Returns:
        dict with keys: converged, step_du, delta_lambda, iterations,
                        F_int, stress_data, norm_R, f_base, R_free, error,
                        sign_lambda_next, delta_u_free_converged
    """
    # Use F_ref_direction for arc-length constraint, delta_F_external for residual
    if F_ref_direction is None:
        F_ref_direction = delta_F_external
    F_ref_free = F_ref_direction[free_dofs]
    
    # === PREDICTOR STEP ===
    K_free = assemble_stiffness_fn()
    
    # --- Limit Point Detection ---
    # Before predictor, check if sign_lambda should flip.
    # Compute tangent direction: du_tangent = K^{-1} * F_ref
    # If dot(du_tangent, prev_delta_u) < 0, we passed a limit point.
    if prev_delta_u_free is not None and np.linalg.norm(prev_delta_u_free) > 1e-15:
        try:
            du_tangent = spsolve(K_free, F_ref_free)
            if np.all(np.isfinite(du_tangent)):
                dot_product = np.dot(du_tangent, prev_delta_u_free)
                if dot_product < 0:
                    sign_lambda = -sign_lambda
        except Exception:
            pass  # Keep current sign_lambda if detection fails
    
    delta_u_pred_free, delta_lambda_pred, pred_ok = arc_length_predictor(
        K_free, F_ref_free, arc_length_radius, sign_lambda
    )
    
    if not pred_ok:
        return {
            'converged': False,
            'step_du': np.zeros(num_dof),
            'delta_lambda': 0.0,
            'iterations': 0,
            'F_int': F_int_initial.copy(),
            'stress_data': None,
            'norm_R': np.inf,
            'f_base': 1.0,
            'R_free': np.zeros(len(free_dofs)),
            'error': 'Arc-length predictor failed (singular stiffness)',
            'sign_lambda_next': sign_lambda,
            'delta_u_free_converged': None
        }
    
    # Initialize step variables
    step_du = np.zeros(num_dof)
    step_du[free_dofs] = delta_u_pred_free
    delta_lambda_total = delta_lambda_pred
    
    # Track free-DOF displacement increment for constraint
    delta_u_free = delta_u_pred_free.copy()
    
    converged = False
    iteration = 0
    F_int = None
    stress_data = None
    norm_R = np.inf
    f_base = 1.0
    R_free = np.zeros(len(free_dofs))
    
    while iteration < max_iterations:
        iteration += 1
        
        # Compute target m_stage for this corrector
        target_m_stage = current_m_stage + delta_lambda_total
        
        # Clamp m_stage for non-SRM to [0, 1]
        if not is_srm:
            if target_m_stage > 1.0:
                target_m_stage = 1.0
                delta_lambda_total = 1.0 - current_m_stage
            elif target_m_stage < 0.0:
                target_m_stage = 0.0
                delta_lambda_total = -current_m_stage
        else:
            # For SRM: Msf should not go below 1.0 (no strength amplification)
            if target_m_stage < 1.0:
                target_m_stage = 1.0
                delta_lambda_total = 1.0 - current_m_stage
        
        total_u_candidate = total_displacement + current_u_incremental + step_du
        
        # Compute internal forces and stresses
        F_int_result = compute_stresses_fn(total_u_candidate, target_m_stage)
        F_int = F_int_result[0]
        stress_data = F_int_result[1:]
        
        # Add beam internal forces
        F_int_beams = compute_beam_forces_fn(total_u_candidate, target_m_stage)
        F_int = F_int + F_int_beams
        
        # Residual: R = F_ext(λ) - F_int
        # F_ext(λ) = F_int_initial + target_m_stage * delta_F_external
        R = F_int_initial + (target_m_stage * delta_F_external) - F_int
        R_free = R[free_dofs]
        norm_R = np.linalg.norm(R_free)
        f_base = np.linalg.norm(F_int_initial[free_dofs])
        if not is_srm:
            f_base = np.linalg.norm((F_int_initial + delta_F_external)[free_dofs])
        if f_base < 1.0:
            f_base = 1.0
        
        # Convergence check (skip first iteration for predictor)
        if norm_R / f_base < tolerance and iteration > 1:
            converged = True
            break
        
        # === CORRECTOR STEP ===
        # Reassemble stiffness (tangent)
        K_free = assemble_stiffness_fn()
        
        du_corr_free, d_lambda_corr, corr_ok = arc_length_corrector(
            K_free, R_free, F_ref_free,
            delta_u_free, delta_lambda_total,
            arc_length_radius
        )
        
        if not corr_ok:
            return {
                'converged': False,
                'step_du': step_du,
                'delta_lambda': delta_lambda_total,
                'iterations': iteration,
                'F_int': F_int,
                'stress_data': stress_data,
                'norm_R': norm_R,
                'f_base': f_base,
                'R_free': R_free,
                'error': f'Arc-length corrector failed at iteration {iteration}',
                'sign_lambda_next': sign_lambda,
                'delta_u_free_converged': None
            }
        
        # Check for NaN/Inf
        if not np.all(np.isfinite(du_corr_free)):
            return {
                'converged': False,
                'step_du': step_du,
                'delta_lambda': delta_lambda_total,
                'iterations': iteration,
                'F_int': F_int,
                'stress_data': stress_data,
                'norm_R': norm_R,
                'f_base': f_base,
                'R_free': R_free,
                'error': f'Arc-length corrector returned NaN/Inf at iteration {iteration}',
                'sign_lambda_next': sign_lambda,
                'delta_u_free_converged': None
            }
        
        # Update step displacement and load parameter
        step_du[free_dofs] += du_corr_free
        delta_lambda_total += d_lambda_corr
        delta_u_free += du_corr_free
    
    return {
        'converged': converged,
        'step_du': step_du,
        'delta_lambda': delta_lambda_total,
        'iterations': iteration,
        'F_int': F_int if F_int is not None else F_int_initial.copy(),
        'stress_data': stress_data,
        'norm_R': norm_R,
        'f_base': f_base,
        'R_free': R_free,
        'error': None,
        'sign_lambda_next': sign_lambda,
        'delta_u_free_converged': delta_u_free.copy() if converged else None
    }
