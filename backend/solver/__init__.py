"""
Solver Package
Modular FEA solver with Rust-accelerated compute kernels (terrasim_core).

Main Components:
- element_t6: T6 element shape functions, B-matrix, stiffness
- element_embedded_beam: Embedded beam stiffness and yielding
- k0_procedure: Geostatic initial stress (K0)
- stress_rust: Rust batch stress computation kernel
- arc_length: Crisfield Arc-Length method
- phase_solver: Main analysis phases solver loop

Compute Kernels (Rust - terrasim_core):
- compute_stresses_loop: Full element stress loop
- compute_k0_stresses: K0 initial stresses
- assemble_stiffness_loop: Stiffness assembly
- mohr_coulomb_yield / return_mapping_mohr_coulomb
- hoek_brown_yield / return_mapping_hoek_brown

Usage:
    from backend.solver import solve_phases
"""
from .phase_solver import solve_phases

__all__ = ['solve_phases']
