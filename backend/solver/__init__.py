"""
Solver Package
Modular FEA solver implementation for geotechnical analysis.

Main Components:
- element_cst: CST element stiffness and force computation
- k0_procedure: Geostatic initial stress initialization
- mohr_coulomb: Mohr-Coulomb plasticity model
- hoek_brown: Hoek-Brown plasticity model
- phase_solver: Main analysis phases solver loop

Usage:
    from backend.solver import solve_phases
"""
from .phase_solver import solve_phases

__all__ = ['solve_phases']
