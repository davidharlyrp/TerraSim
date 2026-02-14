import { useState } from 'react';
import { PhaseRequest, PolygonData, PointLoad, PhaseType, LineLoad } from '../types';
import { Trash, ChevronDown, ChartSpline, SquareArrowDown } from 'lucide-react';
import { propagateMaterialChanges } from '../utils/materialUtils';

// --- Helper Functions & Components ---

const propagateSafetyState = (updatedPhases: PhaseRequest[], parentId: string) => {
    updatedPhases.forEach((ph) => {
        if (ph.parent_id === parentId && ph.phase_type === PhaseType.SAFETY_ANALYSIS) {
            const parent = updatedPhases.find(p => p.id === parentId);
            if (parent) {
                ph.active_polygon_indices = [...parent.active_polygon_indices];
                ph.active_load_ids = [...parent.active_load_ids];
                ph.active_water_level_id = parent.active_water_level_id;
                // Recurse
                propagateSafetyState(updatedPhases, ph.id);
            }
        }
    });
};

interface PhaseTreeItemProps {
    phase: PhaseRequest;
    idx: number;
    allPhases: PhaseRequest[];
    currentPhaseIdx: number;
    expandedPhases: Set<string>;
    waterLevels: { id: string; name: string }[];
    onSelectPhase: (idx: number) => void;
    onPhasesChange: (phases: PhaseRequest[]) => void;
    togglePhaseExpansion: (id: string) => void;
    levels: boolean[]; // Array of booleans: true if level 'i' has a next sibling (needs vertical bar)
}

const PhaseTreeItem: React.FC<PhaseTreeItemProps> = ({
    phase,
    idx,
    allPhases,
    currentPhaseIdx,
    expandedPhases,
    waterLevels,
    onSelectPhase,
    onPhasesChange,
    togglePhaseExpansion,
    levels
}) => {
    // Determine children
    const children = allPhases
        .map((p, i) => ({ ...p, originalIndex: i }))
        .filter(p => p.parent_id === phase.id);

    // Is this the last child of its parent? 
    // We can infer this from the passed `levels`: the last entry corresponds to *this* node's level.
    // Wait, `levels` describes the *indentation* needed for THIS node.
    // Let's adjust: `levels` contains flags for parent levels. 
    // We need to know if *this* node is the last among its siblings to decide its own connector (├─ vs └─).
    // And to pass down the correct `levels` to children.

    // Correction: `levels` passed to this component should already account for parents.
    // But this component needs to know if *it* is the last child to render its own connector.
    // Let's change the prop usage: `isLastChild` boolean.

    // Actually, `levels` as `boolean[]` works best if it represents "does level 'i' continue down?".
    // So for *this* node at depth `D`, we render `D` indent blocks.
    // block `i < D`: render `│` if `levels[i]` is true.
    // block `D`: render `├─` if `levels[D]` is true (has next sibling), else `└─`.

    // So `levels` should include the status of *current* level.
    const depth = levels.length - 1;
    const isLastChild = !levels[depth]; // If current level has no next sibling, it is last.

    return (
        <div className="flex flex-col">
            <div
                className={`flex flex-col gap-2 pr-2 py-1 rounded text-xs transition-all ${idx === currentPhaseIdx
                    ? 'bg-blue-500/10 dark:bg-blue-500/20 ring-1 ring-blue-500/50 text-blue-900 dark:text-white'
                    : 'text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'
                    }`}
            >
                <div className="flex items-center group h-6">
                    {/* Indentation Guides */}
                    {levels.slice(0, -1).map((hasBar, i) => (
                        <div key={i} className="w-5 h-full flex justify-center shrink-0">
                            {hasBar && <div className="w-px bg-slate-300 dark:bg-slate-700 h-full" />}
                        </div>
                    ))}

                    {/* Current Level Connector */}
                    {depth >= 0 && (
                        <div className="w-5 h-full flex justify-center items-center shrink-0 relative">
                            {/* Only render lines if NOT the very first root phase */}
                            {idx !== 0 && (
                                <>
                                    {/* Vertical line from top to center */}
                                    <div className="absolute top-0 w-px bg-slate-300 dark:bg-slate-700 h-1/2" />
                                    {/* Vertical line from center to bottom (only if not last child) */}
                                    {!isLastChild && <div className="absolute bottom-0 w-px bg-slate-300 dark:bg-slate-700 h-1/2" />}
                                    {/* Horizontal line to right */}
                                    <div className="absolute w-2.5 h-px bg-slate-300 dark:bg-slate-700 right-0" />
                                </>
                            )}
                        </div>
                    )}

                    <div
                        className="flex-1 min-w-0 cursor-pointer flex items-center gap-2 pl-1"
                        onClick={() => onSelectPhase(idx)}
                    >
                        <span className="truncate font-medium">{phase.name}</span>

                        {(phase.phase_type === PhaseType.PLASTIC || !phase.phase_type) && (
                            <ChartSpline className='w-3 h-3 opacity-60' />
                        )}
                        {phase.phase_type === PhaseType.SAFETY_ANALYSIS && (
                            <SquareArrowDown className='w-3 h-3 opacity-60' />
                        )}

                        {/* Expand/Collapse - Always visible to allow detail editing */}
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                togglePhaseExpansion(phase.id);
                            }}
                            className="p-0.5 hover:bg-black/5 dark:hover:bg-white/5 rounded transition-colors cursor-pointer ml-auto mr-1"
                        >
                            <ChevronDown className={`w-3 h-3 transition-transform ${expandedPhases.has(phase.id) ? 'rotate-180' : ''}`} />
                        </button>
                    </div>

                    <div className="flex items-center gap-1">
                        {idx > 0 && (
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    if (confirm(`Delete phase "${phase.name}"?`)) {
                                        const newPhases = allPhases.filter((_, i) => i !== idx);
                                        if (idx === currentPhaseIdx) onSelectPhase(Math.max(0, idx - 1));
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

                {expandedPhases.has(phase.id) && (
                    <div className="space-y-3 mt-1 pt-2 pb-2 pl-8 border-t border-slate-200 dark:border-white/5">
                        <div>
                            <label className="itemlabel">Phase Name</label>
                            <input
                                className="w-full bg-slate-50 dark:bg-slate-900/50 text-slate-900 dark:text-white border border-slate-300 dark:border-white/10 rounded px-2 py-1.5 text-[10px] outline-none hover:bg-slate-100 dark:hover:bg-slate-900 transition-colors"
                                value={phase.name}
                                onChange={(e) => {
                                    const newPhases = [...allPhases];
                                    newPhases[idx] = { ...phase, name: e.target.value };
                                    onPhasesChange(newPhases);
                                }}
                            />
                        </div>
                        <div>
                            <label className="itemlabel">Analysis Type</label>
                            <select
                                value={phase.phase_type || PhaseType.PLASTIC}
                                onChange={(e) => {
                                    const newType = e.target.value as PhaseType;
                                    const newPhases = [...allPhases];
                                    const updatedPhase = { ...phase, phase_type: newType };

                                    if (newType === PhaseType.SAFETY_ANALYSIS && phase.parent_id) {
                                        const parent = allPhases.find(ph => ph.id === phase.parent_id);
                                        if (parent) {
                                            updatedPhase.active_polygon_indices = [...parent.active_polygon_indices];
                                            updatedPhase.active_load_ids = [...parent.active_load_ids];
                                            updatedPhase.active_water_level_id = parent.active_water_level_id;
                                        }
                                    }

                                    newPhases[idx] = updatedPhase;
                                    propagateSafetyState(newPhases, updatedPhase.id);
                                    onPhasesChange(newPhases);
                                }}
                                className="w-full bg-slate-50 dark:bg-slate-900/50 text-slate-900 dark:text-white border border-slate-300 dark:border-white/10 rounded px-2 py-1.5 text-[10px] outline-none hover:bg-slate-100 dark:hover:bg-slate-900 transition-colors cursor-pointer"
                            >
                                {idx === 0 ? (
                                    <>
                                        <option value={PhaseType.K0_PROCEDURE}>K0 Procedure (Stress Init)</option>
                                        <option value={PhaseType.GRAVITY_LOADING} disabled>Gravity Loading (Total Stress)</option>
                                    </>
                                ) : (
                                    <>
                                        <option value={PhaseType.PLASTIC}>Plastic Analysis</option>
                                        <option value={PhaseType.SAFETY_ANALYSIS}>Safety Analysis (SRM)</option>
                                    </>
                                )}
                            </select>
                        </div>

                        <div>
                            <label className="itemlabel">Water Level</label>
                            <select
                                value={phase.active_water_level_id || ""}
                                onChange={(e) => {
                                    const val = e.target.value;
                                    const newPhases = [...allPhases];
                                    const updatedPhase = { ...phase, active_water_level_id: val || undefined };
                                    newPhases[idx] = updatedPhase;
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

                        {idx > 0 && (
                            <div>
                                <label className="itemlabel">Start from (Parent)</label>
                                <select
                                    value={phase.parent_id || ""}
                                    onChange={(e) => {
                                        const newParentId = e.target.value;
                                        const newPhases = [...allPhases];
                                        const updatedPhase = { ...phase, parent_id: newParentId };

                                        if (phase.phase_type === PhaseType.SAFETY_ANALYSIS) {
                                            const parent = allPhases.find(ph => ph.id === newParentId);
                                            if (parent) {
                                                updatedPhase.active_polygon_indices = [...parent.active_polygon_indices];
                                                updatedPhase.active_load_ids = [...parent.active_load_ids];
                                                updatedPhase.active_water_level_id = parent.active_water_level_id;
                                            }
                                        }

                                        newPhases[idx] = updatedPhase;
                                        onPhasesChange(newPhases);
                                    }}
                                    className="w-full bg-slate-50 dark:bg-slate-900/50 text-slate-900 dark:text-white border border-slate-300 dark:border-white/10 rounded px-2 py-1.5 text-[10px] outline-none hover:bg-slate-100 dark:hover:bg-slate-900 transition-colors cursor-pointer"
                                >
                                    {allPhases.filter(ph => ph.id !== phase.id).map(ph => (
                                        <option key={ph.id} value={ph.id}>{ph.name}</option>
                                    ))}
                                </select>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Tree Children */}
            {children.length > 0 && (
                <div className="flex flex-col">
                    {children.map((child, index) => {
                        // Is this child the last sibling?
                        const isLast = index === children.length - 1;

                        // FINAL COMBINED LOGIC:
                        // "Indent if parent has siblings OR if children have siblings (branching)."
                        // 1. Parent Sibling Check: If 'phase' (parent) has siblings, its children must indent.
                        // 2. Children Sibling Check: If 'phase' has multiple children, they must indent.
                        // Result: Only strictly linear chains (unique parent -> unique child) get flattened.

                        const parentSiblingsCount = allPhases.filter(p => p.parent_id === phase.parent_id).length;
                        const parentHasSiblings = parentSiblingsCount > 1;
                        const childrenHaveSiblings = children.length > 1;

                        const shouldIndent = parentHasSiblings || childrenHaveSiblings;

                        const nextLevels = shouldIndent
                            ? [...levels, !isLast] // Branching involved -> Indent
                            : [...levels];         // Strict Linear Chain -> Flatten

                        return (
                            <PhaseTreeItem
                                key={child.id}
                                phase={child}
                                idx={child.originalIndex}
                                allPhases={allPhases}
                                currentPhaseIdx={currentPhaseIdx}
                                expandedPhases={expandedPhases}
                                waterLevels={waterLevels}
                                onSelectPhase={onSelectPhase}
                                onPhasesChange={onPhasesChange}
                                togglePhaseExpansion={togglePhaseExpansion}
                                levels={nextLevels}
                            />
                        );
                    })}
                </div>
            )}
        </div>
    );
};

const renderPhaseTree = (
    allPhases: PhaseRequest[],
    currentPhaseIdx: number,
    expandedPhases: Set<string>,
    togglePhaseExpansion: (id: string) => void,
    onSelectPhase: (idx: number) => void,
    onPhasesChange: (phases: PhaseRequest[]) => void,
    waterLevels: { id: string; name: string }[]
) => {
    const roots = allPhases.map((p, i) => ({ ...p, originalIndex: i })).filter(p => {
        if (!p.parent_id) return true;
        return !allPhases.find(parent => parent.id === p.parent_id);
    });

    return roots.map((root, index) => {
        const isLast = index === roots.length - 1;
        // Roots are at level 0. 
        // Their "next sibling" status is based on the root list itself.
        return (
            <PhaseTreeItem
                key={root.id}
                phase={root}
                idx={root.originalIndex}
                allPhases={allPhases}
                currentPhaseIdx={currentPhaseIdx}
                expandedPhases={expandedPhases}
                waterLevels={waterLevels}
                onSelectPhase={onSelectPhase}
                onPhasesChange={onPhasesChange}
                togglePhaseExpansion={togglePhaseExpansion}
                levels={[!isLast]} // Level 0: has next sibling?
            />
        );
    });
};

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

    // propagateSafetyState moved to outer scope

    const togglePolygon = (polyIdx: number) => {
        const newPhases = [...phases]; // Shallow copy array
        // Deep copy phases we modify? Ideally yes.
        // For simplicity, we assume mutable objects in new array or careful updates.
        // Let's do structured clone of the phase we touch to be safe? 
        // Or just mutate since we emit new array. React update requires new references.
        // We'll update objects in place inside the new array, which is dubious for PureComponent but ok here usually.
        // Better:
        const phaseIdx = currentPhaseIdx;
        const current = { ...newPhases[phaseIdx] };
        newPhases[phaseIdx] = current;

        const oldCurrentMat = { ...current.current_material };

        const active = new Set(current.active_polygon_indices);
        const currentMat = { ...current.current_material };

        if (active.has(polyIdx)) {
            // REMOVE
            active.delete(polyIdx);
            delete currentMat[polyIdx];
        } else {
            // ADD
            active.add(polyIdx);
            // Default to parent or base
            if (current.parent_material && current.parent_material[polyIdx]) {
                currentMat[polyIdx] = current.parent_material[polyIdx];
            } else if (polygons[polyIdx]) {
                currentMat[polyIdx] = polygons[polyIdx].materialId;
            }
        }
        current.active_polygon_indices = Array.from(active);
        current.current_material = currentMat;

        // Propagate updates to children
        propagateMaterialChanges(newPhases, current.id, oldCurrentMat, polygons);

        propagateSafetyState(newPhases, current.id);
        onPhasesChange(newPhases);
    };

    const toggleLoad = (loadId: string) => {
        const newPhases = [...phases];
        const current = { ...newPhases[currentPhaseIdx] };
        newPhases[currentPhaseIdx] = current;

        const active = new Set(current.active_load_ids);
        if (active.has(loadId)) active.delete(loadId);
        else active.add(loadId);
        current.active_load_ids = Array.from(active);

        propagateSafetyState(newPhases, current.id);
        onPhasesChange(newPhases);
    };

    const [isPhaseOpen, setIsPhaseOpen] = useState(true);
    const [isComponentExplorerOpen, setIsComponentExplorerOpen] = useState(true);
    const [expandedPhases, setExpandedPhases] = useState<Set<string>>(new Set());

    const togglePhaseExpansion = (phaseId: string) => {
        const newExpanded = new Set<string>();
        // Accordion behavior:
        // If clicking a different phase, open it (and implicitly close others by creating new Set)
        // If clicking the CURRENTLY open phase, close it (toggling off)

        if (!expandedPhases.has(phaseId)) {
            newExpanded.add(phaseId);
        }

        setExpandedPhases(newExpanded);
    };

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
                    {/* Recursive Tree View */}
                    <div className="flex flex-col gap-1">
                        {renderPhaseTree(phases, currentPhaseIdx, expandedPhases, togglePhaseExpansion, onSelectPhase, onPhasesChange, waterLevels)}
                    </div>

                    <button
                        onClick={() => {
                            const nextIdx = phases.length;
                            const newId = `phase_${Date.now()}`;
                            const lastPhase = phases.length > 0 ? phases[phases.length - 1] : null;

                            // Default parent logic: Last phase in list
                            const parentId = lastPhase ? lastPhase.id : undefined;

                            const newPhase: PhaseRequest = {
                                id: newId,
                                name: `Phase ${nextIdx + 1}`,
                                phase_type: PhaseType.PLASTIC, // Default to Plastic
                                active_polygon_indices: lastPhase ? [...lastPhase.active_polygon_indices] : [],
                                active_load_ids: lastPhase ? [...lastPhase.active_load_ids] : [],
                                active_water_level_id: lastPhase ? lastPhase.active_water_level_id : undefined,
                                parent_material: lastPhase ? { ...lastPhase.current_material } : {},
                                current_material: lastPhase ? { ...lastPhase.current_material } : {},
                                parent_id: parentId // Default parent is the previous phase
                            };
                            onPhasesChange([...phases, newPhase]);
                            onPhasesChange([...phases, newPhase]);
                        }}
                        className="add-button mt-4"
                    >
                        + Add Analysis Stage
                    </button>
                    {!phases.length && <div className="text-[10px] text-slate-400 text-center italic mt-2">No phases defined. Add one to start.</div>}
                </div>
            )
            }

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
            {
                isComponentExplorerOpen && (
                    <div className={`p-4 space-y-4 mb-8 ${currentPhase?.phase_type === PhaseType.SAFETY_ANALYSIS ? 'opacity-50 pointer-events-none' : ''}`}>
                        <div>
                            <div className="text-[10px] font-bold text-slate-500 uppercase mb-3 tracking-widest">POLYGONS <span className='font-normal'>({polygons.length})</span></div>
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
                            <div className="text-[10px] font-bold text-slate-500 uppercase mb-3 tracking-widest">WATER LEVELS <span className='font-normal'>({waterLevels.length})</span></div>
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
                            <div className="text-[10px] font-bold text-slate-500 uppercase mb-3 tracking-widest">POINT LOADS <span className='font-normal'>({pointLoads.length})</span></div>
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
                            <div className="text-[10px] font-bold text-slate-500 uppercase mb-3 tracking-widest">LINE LOADS <span className='font-normal'>({lineLoads.length})</span></div>
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

                        <div className="mt-8 pt-4 border-t border-slate-200 dark:border-slate-700 pb-6">
                            {/* <button
                                onClick={() => {
                                    console.log("Starting Material Migration...");
                                    // 1. First pass: Ensure current_material has FULL state (Base + Overrides)
                                    // AND remove legacy material_overrides
                                    const intermediatePhases = phases.map((phase) => {
                                        const activePolys = phase.active_polygon_indices || [];
                                        const baseMaterials: Record<number, string> = {};

                                        // Get Base Materials from Polygons
                                        activePolys.forEach(idx => {
                                            if (polygons[idx]) {
                                                baseMaterials[idx] = polygons[idx].materialId;
                                            }
                                        });

                                        // Merge with existing current_material (overrides)
                                        // Prioritize existing current_material if it exists
                                        const existing = phase.current_material || {};
                                        let merged = { ...baseMaterials, ...existing };

                                        // Filter: Only keep materials for ACTIVE polygons
                                        // (Remove any garbage from deactivated polygons)
                                        const filtered: Record<number, string> = {};
                                        activePolys.forEach(idx => {
                                            if (merged[idx]) filtered[idx] = merged[idx];
                                            else if (baseMaterials[idx]) filtered[idx] = baseMaterials[idx];
                                        });

                                        // Remove legacy field
                                        const { material_overrides, ...rest } = phase as any;

                                        return {
                                            ...rest,
                                            current_material: filtered
                                        };
                                    });

                                    // 2. Second pass: Fix parent_material pointers
                                    const finalPhases = intermediatePhases.map(p => {
                                        const parent = intermediatePhases.find(parent => parent.id === p.parent_id);

                                        return {
                                            ...p,
                                            parent_material: parent ? { ...parent.current_material } : {}
                                        };
                                    });

                                    console.log("Migrated Phases:", finalPhases);
                                    onPhasesChange(finalPhases);
                                    alert("Materials migrated! Check console for details.");
                                }}
                                className="w-full py-2 px-3 bg-amber-100 hover:bg-amber-200 text-amber-800 text-xs rounded border border-amber-300 transition-colors flex items-center justify-center gap-2"
                            >
                                <ChartSpline className="w-3 h-3" />
                                Debug: Fix/Migrate Materials
                            </button> */}
                        </div>
                    </div>
                )
            }
        </div >
    );
};
