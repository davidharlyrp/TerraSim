import { useState } from 'react';
import { PhaseRequest, PolygonData, PointLoad, PhaseType, LineLoad } from '../types';
import { Trash, ChevronDown } from 'lucide-react';

interface StagingSidebarProps {
    phases: PhaseRequest[];
    currentPhaseIdx: number;
    polygons: PolygonData[];
    pointLoads: PointLoad[];
    lineLoads: LineLoad[];
    waterLevels: { id: string; name: string }[]; // NEW
    onPhasesChange: (phases: PhaseRequest[]) => void;
    onSelectPhase: (idx: number) => void;
}

export const StagingSidebar: React.FC<StagingSidebarProps> = ({
    phases,
    currentPhaseIdx,
    polygons,
    pointLoads,
    lineLoads,
    waterLevels,
    onPhasesChange,
    onSelectPhase
}) => {
    const currentPhase = phases[currentPhaseIdx];

    const propagateSafetyState = (updatedPhases: PhaseRequest[], parentId: string) => {
        updatedPhases.forEach((ph) => {
            if (ph.parent_id === parentId && ph.phase_type === PhaseType.SAFETY_ANALYSIS) {
                const parent = updatedPhases.find(p => p.id === parentId);
                if (parent) {
                    ph.active_polygon_indices = [...parent.active_polygon_indices];
                    ph.active_load_ids = [...parent.active_load_ids];
                    ph.active_water_level_id = parent.active_water_level_id; // NEW
                    // Recurse to handle children of children if any
                    propagateSafetyState(updatedPhases, ph.id);
                }
            }
        });
    };

    const togglePolygon = (polyIdx: number) => {
        const newPhases = [...phases];
        const current = newPhases[currentPhaseIdx];
        const active = new Set(current.active_polygon_indices);
        if (active.has(polyIdx)) active.delete(polyIdx);
        else active.add(polyIdx);
        current.active_polygon_indices = Array.from(active);

        propagateSafetyState(newPhases, current.id);
        onPhasesChange(newPhases);
    };

    const toggleLoad = (loadId: string) => {
        const newPhases = [...phases];
        const current = newPhases[currentPhaseIdx];
        const active = new Set(current.active_load_ids);
        if (active.has(loadId)) active.delete(loadId);
        else active.add(loadId);
        current.active_load_ids = Array.from(active);

        propagateSafetyState(newPhases, current.id);
        onPhasesChange(newPhases);
    };

    const [isPhaseOpen, setIsPhaseOpen] = useState(true);
    const [isComponentExplorerOpen, setIsComponentExplorerOpen] = useState(true);

    return (
        <div className="md:w-full w-[calc(100vw-40px)] md:h-full h-[calc(100vh-50px)] pb-30 p-2 overflow-y-auto flex flex-col gap-2 border-r md:border-0 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 custom-scrollbar">
            {/* PHASE */}
            <button
                className="dropdownlabel2"
                onClick={() => { setIsPhaseOpen(!isPhaseOpen) }}>
                Phases
                <div
                    className="p-1.5 text-slate-600 dark:text-slate-300 rounded transition-colors">
                    <ChevronDown className={`w-4 h-4 transition ${isPhaseOpen ? "rotate-180" : ""}`} />
                </div>
            </button>
            {isPhaseOpen && (
                <div className="px-4 py-2 space-y-2">
                    {phases.map((p, i) => (
                        <div
                            key={p.id}
                            className={`flex flex-col gap-2 px-3 py-2 rounded text-xs transition-all ${i === currentPhaseIdx
                                ? 'bg-blue-500/20 ring-1 ring-blue-500/50 text-blue-900 dark:text-white'
                                : 'bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'
                                }`}
                        >
                            <div className="flex justify-between items-center cursor-pointer group" onClick={() => onSelectPhase(i)}>
                                <div className="flex-1 min-w-0">
                                    {i === currentPhaseIdx ? (
                                        <input
                                            autoFocus
                                            className="w-full bg-white dark:bg-slate-900/50 border-none outline-none text-slate-900 dark:text-white px-1 py-0.5 rounded"
                                            value={p.name}
                                            onChange={(e) => {
                                                const newPhases = [...phases];
                                                newPhases[i] = { ...p, name: e.target.value };
                                                onPhasesChange(newPhases);
                                            }}
                                            onClick={(e) => e.stopPropagation()}
                                        />
                                    ) : (
                                        <span className="truncate">{p.name}</span>
                                    )}
                                    {p.parent_id && (
                                        <div className="text-[9px] opacity-50 mt-0.5">
                                            Parent: {phases.find(ph => ph.id === p.parent_id)?.name || 'Unknown'}
                                        </div>
                                    )}
                                </div>

                                <div className="flex items-center gap-2">
                                    {i > 0 && (
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                if (confirm(`Delete phase "${p.name}"?`)) {
                                                    const newPhases = phases.filter((_, idx) => idx !== i);
                                                    // If we deleted current, select previous
                                                    if (i === currentPhaseIdx) onSelectPhase(Math.max(0, i - 1));
                                                    onPhasesChange(newPhases);
                                                }
                                            }}
                                            className="p-1 opacity-0 group-hover:opacity-100 hover:text-red-400 transition-all cursor-pointer"
                                            title="Delete Phase"
                                        >
                                            <Trash className='w-3.5 h-3.5' />
                                        </button>
                                    )}
                                </div>
                            </div>

                            {i === currentPhaseIdx && (
                                <div className="space-y-3 mt-1 pt-2 border-t border-white/5">
                                    <div>
                                        <label className="itemlabel">Analysis Type</label>
                                        <select
                                            value={p.phase_type || PhaseType.PLASTIC}
                                            onChange={(e) => {
                                                const newType = e.target.value as PhaseType;
                                                const newPhases = [...phases];
                                                const updatedPhase = { ...p, phase_type: newType };

                                                // Handle Safety Analysis Inheritance
                                                if (newType === PhaseType.SAFETY_ANALYSIS && p.parent_id) {
                                                    const parent = phases.find(ph => ph.id === p.parent_id);
                                                    if (parent) {
                                                        updatedPhase.active_polygon_indices = [...parent.active_polygon_indices];
                                                        updatedPhase.active_load_ids = [...parent.active_load_ids];
                                                        updatedPhase.active_water_level_id = parent.active_water_level_id;
                                                    }
                                                }

                                                newPhases[i] = updatedPhase;

                                                // If we just changed a PLASTIC phase, we might need to update its SAFETY children
                                                // (Actually propagateSafetyState handles this if we call it)
                                                propagateSafetyState(newPhases, updatedPhase.id);

                                                onPhasesChange(newPhases);
                                            }}
                                            className="w-full bg-slate-50 dark:bg-slate-900/50 text-slate-900 dark:text-white border border-slate-300 dark:border-white/10 rounded px-2 py-1.5 text-[10px] outline-none hover:bg-slate-100 dark:hover:bg-slate-900 transition-colors cursor-pointer"
                                        >
                                            {i === 0 ? (
                                                <>
                                                    <option value={PhaseType.K0_PROCEDURE}>K0 Procedure (Stress Init)</option>
                                                    <option value={PhaseType.GRAVITY_LOADING}>Gravity Loading (Total Stress)</option>
                                                </>
                                            ) : (
                                                <>
                                                    <option value={PhaseType.PLASTIC}>Plastic Analysis</option>
                                                    {/* <option value={PhaseType.FLOW}>Flow Only</option> */}
                                                    <option value={PhaseType.SAFETY_ANALYSIS}>Safety Analysis (SRM)</option>
                                                </>
                                            )}
                                        </select>
                                    </div>

                                    <div>
                                        <label className="itemlabel">Water Level</label>
                                        <select
                                            value={p.active_water_level_id || ""}
                                            onChange={(e) => {
                                                const val = e.target.value;
                                                const newPhases = [...phases];
                                                const updatedPhase = { ...p, active_water_level_id: val || undefined };
                                                newPhases[i] = updatedPhase;

                                                // Propagation for Safety phases if needed, though they usually lock active state. 
                                                // If we change parent's water level, children might need update if we enforce strict inheritance.
                                                propagateSafetyState(newPhases, updatedPhase.id);

                                                onPhasesChange(newPhases);
                                            }}
                                            className="w-full bg-slate-50 dark:bg-slate-900/50 text-slate-900 dark:text-white border border-slate-300 dark:border-white/10 rounded px-2 py-1.5 text-[10px] outline-none hover:bg-slate-100 dark:hover:bg-slate-900 transition-colors cursor-pointer"
                                        >
                                            <option value="">(None)</option>
                                            {waterLevels && waterLevels.map(wl => (
                                                <option key={wl.id} value={wl.id}>{wl.name}</option>
                                            ))}
                                        </select>
                                    </div>

                                    {i > 0 && (
                                        <div>
                                            <label className="itemlabel">Start from (Parent)</label>
                                            <select
                                                value={p.parent_id || ""}
                                                onChange={(e) => {
                                                    const newParentId = e.target.value;
                                                    const newPhases = [...phases];
                                                    const updatedPhase = { ...p, parent_id: newParentId };

                                                    if (p.phase_type === PhaseType.SAFETY_ANALYSIS) {
                                                        const parent = phases.find(ph => ph.id === newParentId);
                                                        if (parent) {
                                                            updatedPhase.active_polygon_indices = [...parent.active_polygon_indices];
                                                            updatedPhase.active_load_ids = [...parent.active_load_ids];
                                                            updatedPhase.active_water_level_id = parent.active_water_level_id;
                                                        }
                                                    }

                                                    newPhases[i] = updatedPhase;
                                                    onPhasesChange(newPhases);
                                                }}
                                                className="w-full bg-slate-50 dark:bg-slate-900/50 text-slate-900 dark:text-white border border-slate-300 dark:border-white/10 rounded px-2 py-1.5 text-[10px] outline-none hover:bg-slate-100 dark:hover:bg-slate-900 transition-colors cursor-pointer"
                                            >
                                                {phases.filter(ph => ph.id !== p.id).map(ph => (
                                                    <option key={ph.id} value={ph.id}>{ph.name}</option>
                                                ))}
                                            </select>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    ))}
                    <button
                        onClick={() => {
                            const nextIdx = phases.length;
                            const newId = `phase_${Date.now()}`; // More unique ID
                            onPhasesChange([...phases, {
                                id: newId,
                                name: `Phase ${nextIdx}`,
                                parent_id: phases[phases.length - 1].id,
                                active_polygon_indices: [...phases[phases.length - 1].active_polygon_indices],
                                active_load_ids: [...phases[phases.length - 1].active_load_ids],
                                active_water_level_id: phases[phases.length - 1].active_water_level_id,
                                reset_displacements: false
                            }]);
                        }}
                        className="add-button mt-2"
                    >
                        + Add Analysis Stage
                    </button>
                </div>
            )}

            {/* COMPONENT EXPLORER */}
            <button
                className="dropdownlabel2"
                onClick={() => { setIsComponentExplorerOpen(!isComponentExplorerOpen) }}>
                Component Explorer
                <div
                    className="p-1.5 text-slate-600 dark:text-slate-300 rounded transition-colors">
                    <ChevronDown className={`w-4 h-4 transition ${isComponentExplorerOpen ? "rotate-180" : ""}`} />
                </div>
            </button>
            {isComponentExplorerOpen && (
                <div className={`p-4 space-y-4 mb-8 ${currentPhase?.phase_type === PhaseType.SAFETY_ANALYSIS ? 'opacity-50 pointer-events-none' : ''}`}>
                    <div>
                        <div className="text-[10px] font-bold text-slate-500 uppercase mb-3 tracking-widest">POLYGONS</div>
                        <div className="space-y-2">
                            {polygons.map((poly, i) => (
                                <label key={i} className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300 cursor-pointer hover:text-slate-900 dark:hover:text-white transition-colors">
                                    <input
                                        type="checkbox"
                                        checked={currentPhase?.active_polygon_indices.includes(i)}
                                        onChange={() => togglePolygon(i)}
                                        className="w-3 h-3 rounded border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 text-blue-600 focus:ring-offset-slate-900"
                                    />
                                    <span>Polygon {i + 1} <span className="opacity-50 font-mono text-[10px]">({poly.materialId})</span></span>
                                </label>
                            ))}
                        </div>
                    </div>

                    <div>
                        <div className="text-[10px] font-bold text-slate-500 uppercase mb-3 tracking-widest">WATER LEVELS</div>
                        <div className="space-y-2">
                            {waterLevels && waterLevels.map((wl) => (
                                <label key={wl.id} className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300 cursor-pointer hover:text-slate-900 dark:hover:text-white transition-colors">
                                    <input
                                        type="checkbox"
                                        checked={currentPhase?.active_water_level_id === wl.id}
                                        onChange={() => {
                                            const newPhases = [...phases];
                                            const current = newPhases[currentPhaseIdx];
                                            const newValue = current.active_water_level_id === wl.id ? undefined : wl.id;
                                            current.active_water_level_id = newValue;

                                            propagateSafetyState(newPhases, current.id);
                                            onPhasesChange(newPhases);
                                        }}
                                        className="w-3 h-3 rounded border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 text-blue-600 focus:ring-offset-slate-900"
                                    />
                                    <span>{wl.name}</span>
                                </label>
                            ))}
                        </div>
                    </div>

                    <div>
                        <div className="text-[10px] font-bold text-slate-500 uppercase mb-3 tracking-widest">POINT LOADS</div>
                        <div className="space-y-2">
                            {pointLoads.map((load) => (
                                <label key={load.id} className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300 cursor-pointer hover:text-slate-900 dark:hover:text-white transition-colors">
                                    <input
                                        type="checkbox"
                                        checked={currentPhase?.active_load_ids?.includes(load.id)}
                                        onChange={() => toggleLoad(load.id)}
                                        className="w-3 h-3 rounded border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 text-blue-600 focus:ring-offset-slate-900"
                                    />
                                    <span>{load.id} <span className="opacity-50 text-[10px]">(@{load.x},{load.y})</span></span>
                                </label>
                            ))}
                        </div>
                    </div>

                    <div>
                        <div className="text-[10px] font-bold text-slate-500 uppercase mb-3 tracking-widest">LINE LOADS</div>
                        <div className="space-y-2">
                            {lineLoads.map((load) => (
                                <label key={load.id} className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300 cursor-pointer hover:text-slate-900 dark:hover:text-white transition-colors">
                                    <input
                                        type="checkbox"
                                        checked={currentPhase?.active_load_ids?.includes(load.id)}
                                        onChange={() => toggleLoad(load.id)}
                                        className="w-3 h-3 rounded border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 text-blue-600 focus:ring-offset-slate-900"
                                    />
                                    <span>{load.id} <span className="opacity-50 text-[10px]">(@{load.x1},{load.y1} to @{load.x2},{load.y2})</span></span>
                                </label>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </div >
    );
};
