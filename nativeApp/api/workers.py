# api/workers.py
# ===========================================================================
# Local Workers — QThread-based background tasks
# ===========================================================================
# These workers perform heavy simulation tasks using the local 'engine'
# WITHOUT freezing the main Qt event loop. Each worker communicates
# status, results, and logs back to the UI thread via Qt Signals.
# ===========================================================================

from __future__ import annotations
import json
import traceback
from PySide6.QtCore import QThread, Signal

# Import local engine components
from engine.models import MeshRequest, SolverRequest
from engine.mesh_generator import generate_mesh
from engine.solver.phase_solver import solve_phases

class MeshWorker(QThread):
    """
    Background worker that executes mesh generation locally.
    
    Signals
    -------
    finished : dict
        Emitted on success with the full MeshResponse as a dict.
    error : str
        Emitted if the generation fails.
    progress : str
        Emitted with status messages for console logging.
    """

    finished = Signal(dict)   # MeshResponse payload
    error    = Signal(str)    # Error message string
    progress = Signal(str)    # Status messages for console

    def __init__(self, payload: dict, parent=None):
        """
        Parameters
        ----------
        payload : dict
            The MeshRequest JSON body (from ProjectState.get_mesh_payload()).
        """
        super().__init__(parent)
        self._payload = payload

    def run(self):
        """Execute mesh generation on the local engine."""
        self.progress.emit("Initializing local mesh generator...")

        try:
            # 1. Convert dict payload to MeshRequest Pydantic model
            req = MeshRequest(**self._payload)
            
            # 2. Run engine logic
            self.progress.emit("Triangulating geometry...")
            response = generate_mesh(req)

            # 3. Handle results
            if not response.success:
                self.error.emit(f"Mesh generation failed: {response.error}")
                return

            n_nodes = len(response.nodes)
            n_elems = len(response.elements)
            self.progress.emit(f"Mesh generated locally: {n_nodes} nodes, {n_elems} elements")

            # 4. Emit results as dict for UI consumption
            self.finished.emit(response.dict())

        except Exception as e:
            err_trace = traceback.format_exc()
            print(f"MeshWorker Exception:\n{err_trace}")
            self.error.emit(f"Local Engine Error: {str(e)}")

class SolveWorker(QThread):
    """
    Background worker that handles the long-running solver calculation locally.
    Iterates over the simulation generator and streams results via signals.

    Signals
    -------
    log_received : str
        Detailed log message from the solver kernel.
    step_point_received : str, dict
        Emitted for each Newton-Raphson step. (phase_id, {m_stage, max_disp})
    phase_finished : str, bool, dict
        Emitted when a phase completes. (phase_id, success, results)
    error : str
        Emitted on internal engine failure.
    finished : dict
        Emitted when the entire calculation process concludes.
    """
    log_received = Signal(str)
    step_point_received = Signal(str, dict)
    phase_started = Signal(str, str, bool) # phase_id, phase_name, is_safety
    phase_finished = Signal(str, bool, dict)
    error = Signal(str)
    finished = Signal(dict)

    def __init__(self, payload: dict, parent=None):
        super().__init__(parent)
        self._payload = payload
        self._is_cancelled = False

    def cancel(self):
        """Request the worker to stop at the next iteration."""
        self._is_cancelled = True

    def run(self):
        """Run the solver engine loop."""
        try:
            # 1. Convert dict payload to SolverRequest Pydantic model
            req = SolverRequest(**self._payload)
            
            # 2. Extract phase IDs for signal mapping
            phase_ids = [p.id for p in req.phases]
            current_phase_idx = 0
            
            # 3. Start local solver generator
            # We pass a stop check function to the engine
            solver_gen = solve_phases(req, should_stop=lambda: self._is_cancelled)

            for item in solver_gen:
                if self._is_cancelled:
                    self.log_received.emit("Calculation cancelled by user.")
                    break
                
                msg_type = item.get("type")
                content = item.get("content")

                if msg_type == "log":
                    self.log_received.emit(str(content))
                    
                elif msg_type == "step_point":
                    if current_phase_idx < len(phase_ids):
                        phase_id = phase_ids[current_phase_idx]
                        self.step_point_received.emit(phase_id, content)

                elif msg_type == "phase_result":
                    res = content
                    # Ensure Pydantic models are converted to dicts for JSON serialization
                    if hasattr(res, "dict"):
                        res = res.dict()
                    elif hasattr(res, "model_dump"):
                        res = res.model_dump()
                    
                    phase_id = res.get("phase_id", "unknown")
                    success = res.get("success", False)
                    self.phase_finished.emit(phase_id, success, res)
                    
                    # Increment phase counter for the next 'step_point'
                    current_phase_idx += 1
                
                elif msg_type == "phase_start":
                    phase_id = content.get("phase_id", "unknown")
                    phase_name = content.get("phase_name", "Unknown Phase")
                    is_safety = content.get("is_safety", False)
                    self.phase_started.emit(phase_id, phase_name, is_safety)

            self.finished.emit({"status": "complete", "cancelled": self._is_cancelled})

        except Exception as e:
            err_trace = traceback.format_exc()
            print(f"SolveWorker Exception:\n{err_trace}")
            self.error.emit(f"Local Solver Engine Error: {str(e)}")
