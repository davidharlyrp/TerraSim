//! TerraSim Core — High-performance computation kernels for FEA solver.

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

    // Embedded Beam Rows (EBR)
    m.add_function(wrap_pyfunction!(elements::embedded_beam::compute_beam_element_matrix_py, m)?)?;
    m.add_function(wrap_pyfunction!(elements::embedded_beam::compute_beam_internal_force_yield_py, m)?)?;
    m.add_function(wrap_pyfunction!(elements::embedded_beam::compute_beam_forces_local_py, m)?)?;

    Ok(())
}
