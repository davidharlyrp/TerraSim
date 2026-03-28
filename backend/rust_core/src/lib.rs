//! TerraSim Core — High-performance computation kernels for FEA solver.
//!
//! Modules:
//! - `material_models` — MC/HB yield + return mapping
//! - `elements` — T6 & beam element computations
//! - `solver_kernel` — Full stress loop & stiffness assembly
//! - `k0_procedure` — Initial stress (K0) computation

use pyo3::prelude::*;

mod material_models;
mod elements;
mod solver_kernel;
mod k0_procedure;

#[pymodule]
fn terrasim_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Material Models (scalar)
    m.add_function(wrap_pyfunction!(material_models::mohr_coulomb::mohr_coulomb_yield_py, m)?)?;
    m.add_function(wrap_pyfunction!(material_models::mohr_coulomb::return_mapping_mohr_coulomb_py, m)?)?;
    m.add_function(wrap_pyfunction!(material_models::hoek_brown::hoek_brown_yield_py, m)?)?;
    m.add_function(wrap_pyfunction!(material_models::hoek_brown::return_mapping_hoek_brown_py, m)?)?;

    // Solver Kernels (batch loop)
    m.add_function(wrap_pyfunction!(solver_kernel::compute_stresses_loop_py, m)?)?;
    m.add_function(wrap_pyfunction!(solver_kernel::assemble_stiffness_loop_py, m)?)?;

    // K0 Procedure
    m.add_function(wrap_pyfunction!(k0_procedure::compute_k0_stresses_py, m)?)?;

    Ok(())
}
