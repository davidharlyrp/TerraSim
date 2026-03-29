from enum import Enum
from typing import Dict, Any

class ErrorCode(str, Enum):
    # --- Validation Errors (1000-1999) ---
    VAL_TOLERANCE_OOB = "VAL_1001"
    VAL_ITERATIONS_OOB = "VAL_1002"
    VAL_STEP_SIZE_OOB = "VAL_1003"
    VAL_LOAD_FRAC_OOB = "VAL_1004"
    VAL_MAX_STEPS_OOB = "VAL_1005"
    VAL_ITER_MISMATCH = "VAL_1006"
    VAL_EMPTY_MESH = "VAL_1101"
    VAL_OVER_ELEMENT_LIMIT = "VAL_1102"
    
    # --- Convergence & Stability Errors (2000-2999) ---
    SOLVER_DIVERGED = "SLV_2001"
    SOLVER_MAX_ITERATIONS = "SLV_2002"
    SOLVER_STEP_LIMIT = "SLV_2003"
    SOLVER_CUTBACK_LIMIT = "SLV_2004"
    SOLVER_SINGULAR_MATRIX = "SLV_2101"
    SOLVER_UNSTABLE_GEOM = "SLV_2102"
    
    # --- Numerical & Physics Errors (3000-3999) ---
    NUM_OVERFLOW = "NUM_3001"
    NUM_NAN_DETECTED = "NUM_3002"
    SRM_LIMIT_REACHED = "SRM_3101"
    
    # --- Authentication Errors (4000-4999) ---
    AUTH_MISSING_TOKEN = "AUTH_4001"
    AUTH_INVALID_TOKEN = "AUTH_4002"
    AUTH_EXPIRED_TOKEN = "AUTH_4003"
    
    # --- System & Resource Errors (9000-9999) ---
    SYS_OVERLOAD_PREVENTION = "SYS_9001"
    SYS_TIMEOUT = "SYS_9002"
    SYS_RATE_LIMIT_EXCEEDED = "SYS_9003"
    SYS_INTERNAL_ERROR = "SYS_9999"

ERROR_CATALOG: Dict[ErrorCode, Dict[str, str]] = {
    ErrorCode.VAL_TOLERANCE_OOB: {
        "title": "Tolerance Out of Bounds",
        "description": "The convergence tolerance (ε) must be between 0.001 and 0.1. Values outside this range may cause instability or excessive calculation time."
    },
    ErrorCode.VAL_ITERATIONS_OOB: {
        "title": "Max Iterations Out of Bounds",
        "description": "Maximum iterations per step must be between 1 and 100. High values can hang the server, while low values may prevent convergence."
    },
    ErrorCode.VAL_STEP_SIZE_OOB: {
        "title": "Initial Step Size Out of Bounds",
        "description": "The initial MStage step size must be between 0.001 and 1.0."
    },
    ErrorCode.VAL_LOAD_FRAC_OOB: {
        "title": "Max Load Fraction Out of Bounds",
        "description": "The maximum load fraction for adaptive stepping must be between 0.01 and 1.0."
    },
    ErrorCode.VAL_MAX_STEPS_OOB: {
        "title": "Max Total Steps Out of Bounds",
        "description": "The maximum number of allowed load increments must be between 1 and 1000 to prevent infinite loops."
    },
    ErrorCode.VAL_ITER_MISMATCH: {
        "title": "Iteration Range Mismatch",
        "description": "The minimum desired iterations cannot be greater than the maximum desired iterations."
    },
    ErrorCode.VAL_EMPTY_MESH: {
        "title": "Empty Mesh Generated",
        "description": "The mesh generator produced zero elements. This usually happens if the input polygons are overlapping, crossing, or have invalid coordinates."
    },
    ErrorCode.VAL_OVER_ELEMENT_LIMIT: {
        "title": "Element Count Exceeds Limit",
        "description": "The mesh contains more than 10000 elements. This exceeds the maximum allowed element count for performance and displaying reasons."
    },
    ErrorCode.SOLVER_DIVERGED: {
        "title": "Convergence Failure (Divergence)",
        "description": "The solver failed to reach equilibrium. The residual forces are increasing, indicating a possible collapse or unstable model configuration."
    },
    ErrorCode.SOLVER_MAX_ITERATIONS: {
        "title": "Max Iterations Reached",
        "description": "The step failed to converge within the allotted number of iterations. Try reducing the step size or increasing tolerance."
    },
    ErrorCode.SOLVER_STEP_LIMIT: {
        "title": "Maximum Steps Reached",
        "description": "The solver reached the maximum allowed number of load increments (MStage steps) without completing the phase."
    },
    ErrorCode.SOLVER_CUTBACK_LIMIT: {
        "title": "Step Size Limit Reached",
        "description": "The solver attempted to reduce the step size to find equilibrium, but the size became too small to continue. The model is likely at a physical limit state (failure)."
    },
    ErrorCode.SOLVER_SINGULAR_MATRIX: {
        "title": "Singular Stiffness Matrix",
        "description": "The global stiffness matrix is not invertible. This usually means the model is not properly restrained (missing boundary conditions) or has detached elements."
    },
    ErrorCode.NUM_OVERFLOW: {
        "title": "Numerical Overflow",
        "description": "A calculation result exceeded the floating-point limits. This often happens near a catastrophic failure point in the soil."
    },
    ErrorCode.SRM_LIMIT_REACHED: {
        "title": "SRM Limit State",
        "description": "Safety analysis stopped because the model reached a critical failure state where further strength reduction is impossible."
    },
    ErrorCode.SYS_OVERLOAD_PREVENTION: {
        "title": "Overload Prevention",
        "description": "Calculation blocked because the requested settings would likely exceed server safety or memory limits."
    },
    ErrorCode.AUTH_MISSING_TOKEN: {
        "title": "Authentication Token Missing",
        "description": "The request is missing the required 'Authorization: Bearer <token>' header."
    },
    ErrorCode.AUTH_INVALID_TOKEN: {
        "title": "Invalid Authentication Token",
        "description": "The provided token is invalid or malformed. Ensure you are using a valid JWT from PocketBase."
    },
    ErrorCode.AUTH_EXPIRED_TOKEN: {
        "title": "Authentication Token Expired",
        "description": "The provided token has expired. Please log in again to obtain a new token."
    },
    ErrorCode.SYS_RATE_LIMIT_EXCEEDED: {
        "title": "Rate Limit Exceeded",
        "description": "You have exceeded the allowed number of requests (5 per minute). Please wait a moment before trying again."
    }
}

def get_error_info(code: ErrorCode) -> str:
    info = ERROR_CATALOG.get(code, {"title": "Unknown Error", "description": "An unspecified error occurred."})
    return f"[{code.value}] {info['title']}: {info['description']}"
