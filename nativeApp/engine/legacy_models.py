from typing import List, Any, Optional, Dict
from pydantic import BaseModel

# --- Legacy Adapter Models (for Frontend Compatibility) ---

class LegacyStageConfig(BaseModel):
    stage_id: str
    stage_name: str
    stage_sequence: int
    calculation_type: str
    is_initial_stage: bool
    nodes: List[Any] # Raw dictionaries
    elements: List[Any]
    boundaryConditionsFullFixed: List[Any]
    boundaryConditionsNormalFixed: List[Any]
    loads: List[Any]
    materials: List[Any]
    # We ignore water level and other complex props for now if not needed for gravity
    active_polygons: List[str]
    active_point_loads: List[str]
    element_active: Optional[List[bool]] = None

class LegacySequentialRequest(BaseModel):
    stages: List[LegacyStageConfig]
    continue_from_previous: bool

class LegacyStageResult(BaseModel):
    stage_id: str
    stage_name: str
    success: bool
    results: Dict[str, Any] # Contains "summary", "displacements", etc.

class LegacySequentialResponse(BaseModel):
    success: bool
    stage_results: List[LegacyStageResult]
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
