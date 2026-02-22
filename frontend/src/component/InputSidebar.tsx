import { PolygonData, Material, PointLoad, LineLoad, WaterLevel, EmbeddedBeam, EmbeddedBeamMaterial } from '../types';
import { ChevronDown, Pencil, Trash, ChevronRight, Plus } from 'lucide-react';
import { MathRender } from './Math';
import { useState, useEffect } from 'react';
import React from 'react';

interface InputSidebarProps {
    materials: Material[];
    polygons: PolygonData[];
    pointLoads: PointLoad[];
    lineLoads: LineLoad[];
    waterLevels: WaterLevel[]; // NEW
    embeddedBeams: EmbeddedBeam[]; // NEW
    beamMaterials: EmbeddedBeamMaterial[]; // NEW
    onUpdateMaterials: (m: Material[]) => void;
    onUpdateBeamMaterials: (m: EmbeddedBeamMaterial[]) => void; // NEW
    onUpdatePolygons: (p: PolygonData[]) => void;
    onUpdateLoads: (l: PointLoad[]) => void;
    onUpdateLineLoads: (l: LineLoad[]) => void;
    onUpdateEmbeddedBeams: (b: EmbeddedBeam[]) => void; // NEW
    onAddWaterLevel: (points: { x: number, y: number }[]) => void; // NEW
    onUpdateWaterLevel: (index: number, wl: WaterLevel) => void; // NEW
    onUpdatePolygonPoints: (index: number, points: { x: number, y: number }[]) => void; // NEW
    onEditMaterial: (mat: Material) => void;
    onEditBeamMaterial: (mat: EmbeddedBeamMaterial) => void; // NEW
    onDeleteMaterial: (id: string) => void;
    onDeleteBeamMaterial: (id: string) => void; // NEW
    onDeletePolygon: (idx: number) => void;
    onDeleteLoad: (id: string) => void;
    onDeleteLineLoad: (id: string) => void; // NEW (MISSING IN ORIGINAL?)
    onDeleteEmbeddedBeam: (id: string) => void; // NEW
    onDeleteWaterLevel: (id: string) => void;
    onDeleteWaterPoint: (wlIndex: number, ptIndex: number) => void; // NEW
    selectedEntity: { type: string, id: string | number } | null;
    onSelectEntity: (selection: { type: string, id: string | number } | null) => void;
}

const NumericInput: React.FC<{
    value: number;
    onChange: (v: number) => void;
    className?: string;
}> = ({ value, onChange, className }) => {
    const [localValue, setLocalValue] = useState(value.toString());

    useEffect(() => {
        if (parseFloat(localValue) !== value && localValue !== '-' && localValue !== '.') {
            setLocalValue(value.toString());
        }
    }, [value]);

    return (
        <input
            type="text"
            className={className}
            value={localValue}
            onChange={(e) => {
                const val = e.target.value;
                if (val === '' || val === '-' || val === '.' || val === '-.' || /^-?\d*\.?\d*$/.test(val)) {
                    setLocalValue(val);
                    const n = parseFloat(val);
                    if (!isNaN(n)) {
                        onChange(n);
                    } else {
                        onChange(0);
                    }
                }
            }}
            onBlur={() => {
                // Ensure valid number on blur
                setLocalValue(value.toString());
            }}
        />
    );
};

export const InputSidebar: React.FC<InputSidebarProps> = ({
    materials,
    beamMaterials,
    polygons,
    pointLoads,
    lineLoads,
    embeddedBeams,
    waterLevels,
    onUpdateMaterials,
    onUpdateBeamMaterials,
    onUpdatePolygons,
    onUpdateLoads,
    onUpdateLineLoads,
    onUpdateEmbeddedBeams,
    onAddWaterLevel,
    onUpdateWaterLevel,
    onUpdatePolygonPoints,
    onEditMaterial,
    onEditBeamMaterial,
    onDeleteMaterial,
    onDeleteBeamMaterial,
    onDeletePolygon,
    onDeleteLoad,
    onDeleteLineLoad,
    onDeleteEmbeddedBeam,
    onDeleteWaterLevel,
    onDeleteWaterPoint,
    selectedEntity,
    onSelectEntity,
}) => {
    const handleAddMaterial = () => {
        const firstMat = materials[0];
        const newMat: Material = {
            id: `mat_${Date.now()}`,
            name: 'New Material',
            color: '#' + Math.floor(Math.random() * 16777215).toString(16).padStart(6, '0'),
            youngsModulus: 20000,
            poissonsRatio: 0.3,
            unitWeightSaturated: 20,
            unitWeightUnsaturated: 18,
            material_model: firstMat?.material_model,
            drainage_type: firstMat?.drainage_type
        };
        onUpdateMaterials([...materials, newMat]);
    };

    const handleAddBeamMaterial = () => {
        const newMat: EmbeddedBeamMaterial = {
            id: `bmat_${Date.now()}`,
            name: 'New Beam Mat',
            color: '#' + Math.floor(Math.random() * 16777215).toString(16).padStart(6, '0'),
            youngsModulus: 30000000,
            crossSectionArea: 0.28,
            momentOfInertia: 0.006,
            unitWeight: 7,
            spacing: 2.0,
            skinFrictionMax: 200,
            tipResistanceMax: 1000,
            shape: 'user_defined'
        };
        onUpdateBeamMaterials([...beamMaterials, newMat]);
    };

    const handleUpdateMatColor = (id: string, color: string) => {
        onUpdateMaterials(materials.map(m => m.id === id ? { ...m, color } : m));
    };

    const handleUpdateBeamMatColor = (id: string, color: string) => {
        onUpdateBeamMaterials(beamMaterials.map(m => m.id === id ? { ...m, color } : m));
    };

    const handleUpdateEmbeddedBeamMat = (idx: number, matId: string) => {
        const newBeams = [...embeddedBeams];
        newBeams[idx] = { ...newBeams[idx], materialId: matId };
        onUpdateEmbeddedBeams(newBeams);
    };

    const handleUpdatePolygonMat = (idx: number, matId: string) => {
        const newPolys = [...polygons];
        newPolys[idx] = { ...newPolys[idx], materialId: matId };
        onUpdatePolygons(newPolys);
    };

    const handleAddLoad = () => {
        const newLoad: PointLoad = {
            id: `load_${pointLoads.length + 1}`,
            x: 0,
            y: 10,
            fx: 0,
            fy: -100
        };
        onUpdateLoads([...pointLoads, newLoad]);
    };

    const handleAddLineLoad = () => {
        const newLoad: LineLoad = {
            id: `line_load_${lineLoads.length + 1}`,
            x1: 0, y1: 10,
            x2: 10, y2: 10,
            fx: 0,
            fy: -50
        };
        onUpdateLineLoads([...lineLoads, newLoad]);
    };

    const handleAddEmbeddedBeam = () => {
        // This is usually done via Canvas tool, but if added here manually:
        const mat = beamMaterials[0]?.id || "";
        const newBeam: EmbeddedBeam = {
            id: `beam_${embeddedBeams.length + 1}`,
            points: [{ x: 5, y: 10 }, { x: 5, y: 0 }],
            materialId: mat
        };
        onUpdateEmbeddedBeams([...embeddedBeams, newBeam]);
    };

    // WATER LEVEL HANDLERS
    const handleAddWaterLevelClick = () => {
        // Create a default flat water level
        onAddWaterLevel([
            { x: 0, y: 5 },
            { x: 10, y: 5 }
        ]);
    };

    const handleUpdateWaterPoint = (wlIndex: number, ptIndex: number, field: 'x' | 'y', value: number) => {
        const wl = waterLevels[wlIndex];
        const newPoints = [...wl.points];
        newPoints[ptIndex] = { ...newPoints[ptIndex], [field]: value };
        onUpdateWaterLevel(wlIndex, { ...wl, points: newPoints });
    };

    const handleAddPointToWaterLevel = (wlIndex: number) => {
        const wl = waterLevels[wlIndex];
        const lastPt = wl.points[wl.points.length - 1] || { x: 0, y: 0 };
        const newPt = { x: lastPt.x + 5, y: lastPt.y };
        onUpdateWaterLevel(wlIndex, { ...wl, points: [...wl.points, newPt] });
    };

    const handleDeletePointFromWaterLevel = (wlIndex: number, ptIndex: number) => {
        const wl = waterLevels[wlIndex];
        if (wl.points.length <= 1) return;
        onDeleteWaterPoint(wlIndex, ptIndex);
    };

    const handleRenameWaterLevel = (wlIndex: number, newName: string) => {
        const wl = waterLevels[wlIndex];
        onUpdateWaterLevel(wlIndex, { ...wl, name: newName });
    };

    const handleUpdatePolygonPoint = (polyIndex: number, ptIndex: number, field: 'x' | 'y', value: number) => {
        const poly = polygons[polyIndex];
        const newPoints = [...poly.vertices];
        newPoints[ptIndex] = { ...newPoints[ptIndex], [field]: value };
        onUpdatePolygonPoints(polyIndex, newPoints);
    };

    const [isMaterialOpen, setIsMaterialOpen] = useState(true);
    const [isPolygonOpen, setIsPolygonOpen] = useState(true);
    const [isLoadOpen, setIsLoadOpen] = useState(true);
    const [isLineLoadOpen, setIsLineLoadOpen] = useState(true);
    const [isWaterOpen, setIsWaterOpen] = useState(true);
    const [isBeamMaterialOpen, setIsBeamMaterialOpen] = useState(true);
    const [isEmbeddedBeamOpen, setIsEmbeddedBeamOpen] = useState(true);
    const [expandedWaterLevelId, setExpandedWaterLevelId] = useState<string | null>(null);
    const [expandedPolygonId, setExpandedPolygonId] = useState<number | null>(null);


    return (
        <div className="md:w-[400px] w-[calc(100vw-40px)] md:h-full h-[calc(100dvh-50px)] pb-30 p-2 flex flex-col gap-2 overflow-y-auto bg-slate-50 dark:bg-slate-900 border-r md:border-0 border-slate-200 dark:border-slate-700 md:custom-scrollbarleft custom-scrollbar">
            {/* MATERIALS */}
            <button
                className="dropdownlabel2"
                onClick={() => { setIsMaterialOpen(!isMaterialOpen) }}>
                Materials ({materials.length})
                <div
                    className="p-1.5 text-slate-600 dark:text-slate-300 rounded transition-colors">
                    <ChevronDown className={`w-4 h-4 transition ${isMaterialOpen ? "rotate-180" : ""}`} />
                </div>
            </button>
            {isMaterialOpen && (
                <div className="p-3 space-y-2">
                    {materials.map(mat => (
                        <div
                            key={mat.id}
                            onClick={() => onSelectEntity({ type: 'material', id: mat.id })}
                            className={`flex flex-col gap-1 p-2 bg-slate-50 dark:bg-slate-800 rounded-lg border transition-all cursor-pointer ${selectedEntity?.type === 'material' && selectedEntity.id === mat.id ? 'border-blue-500 ring-1 ring-blue-500/50' : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'}`}
                        >
                            <div className="flex items-center gap-2">
                                <input
                                    type="color"
                                    value={mat.color}
                                    onChange={(e) => handleUpdateMatColor(mat.id, e.target.value)}
                                    className="w-6 h-6 p-0 border-none bg-transparent cursor-pointer rounded overflow-hidden"
                                />
                                <div className="flex-1 min-w-0">
                                    <div className="itemlabel">{mat.name}</div>
                                </div>
                                <div className="flex gap-1">
                                    <button
                                        onClick={(e) => { e.stopPropagation(); onEditMaterial(mat); }}
                                        className="cursor-pointer p-1.5 rounded hover:bg-slate-600 hover:text-white transition-colors"
                                        title="Edit Material"
                                    >
                                        <Pencil className='w-3.5 h-3.5' />
                                    </button>
                                    <button
                                        onClick={(e) => { e.stopPropagation(); onDeleteMaterial(mat.id); }}
                                        className="cursor-pointer p-1.5 rounded hover:bg-rose-500/20 hover:text-rose-500 transition-colors"
                                        title="Delete Material"
                                    >
                                        <Trash className='w-3.5 h-3.5' />
                                    </button>
                                </div>
                            </div>
                        </div>
                    ))}
                    <button onClick={handleAddMaterial} className="add-button">+ Add Material</button>
                </div>
            )}

            {/* BEAM MATERIALS */}
            <button
                className="dropdownlabel2"
                onClick={() => { setIsBeamMaterialOpen(!isBeamMaterialOpen) }}>
                Beam Materials ({beamMaterials.length})
                <div
                    className="p-1.5 text-slate-600 dark:text-slate-300 rounded transition-colors">
                    <ChevronDown className={`w-4 h-4 transition ${isBeamMaterialOpen ? "rotate-180" : ""}`} />
                </div>
            </button>
            {isBeamMaterialOpen && (
                <div className="p-3 space-y-2">
                    {beamMaterials.map(mat => (
                        <div
                            key={mat.id}
                            onClick={() => onSelectEntity({ type: 'beamMaterial', id: mat.id })}
                            className={`flex flex-col gap-1 p-2 bg-slate-50 dark:bg-slate-800 rounded-lg border transition-all cursor-pointer ${selectedEntity?.type === 'beamMaterial' && selectedEntity.id === mat.id ? 'border-blue-500 ring-1 ring-blue-500/50' : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'}`}
                        >
                            <div className="flex items-center gap-2">
                                <input
                                    type="color"
                                    value={mat.color}
                                    onChange={(e) => handleUpdateBeamMatColor(mat.id, e.target.value)}
                                    className="w-6 h-6 p-0 border-none bg-transparent cursor-pointer rounded overflow-hidden"
                                    title="Change Color"
                                />
                                <div className="flex-1 min-w-0">
                                    <div className="itemlabel">{mat.name}</div>
                                </div>
                                <div className="flex gap-1">
                                    <button
                                        onClick={(e) => { e.stopPropagation(); onEditBeamMaterial(mat); }}
                                        className="cursor-pointer p-1.5 rounded hover:bg-slate-600 hover:text-white transition-colors"
                                        title="Edit Beam Material"
                                    >
                                        <Pencil className='w-3.5 h-3.5' />
                                    </button>
                                    <button
                                        onClick={(e) => { e.stopPropagation(); onDeleteBeamMaterial(mat.id); }}
                                        className="cursor-pointer p-1.5 rounded hover:bg-rose-500/20 hover:text-rose-500 transition-colors"
                                        title="Delete Beam Material"
                                    >
                                        <Trash className='w-3.5 h-3.5' />
                                    </button>
                                </div>
                            </div>
                        </div>
                    ))}
                    <button onClick={handleAddBeamMaterial} className="add-button">+ Add Beam Material</button>
                </div>
            )}

            {/* POLYGONS */}
            <button
                className="dropdownlabel2"
                onClick={() => { setIsPolygonOpen(!isPolygonOpen) }}>
                Polygons ({polygons.length})
                <div
                    className="p-1.5 text-slate-600 dark:text-slate-300 rounded transition-colors">
                    <ChevronDown className={`w-4 h-4 transition ${isPolygonOpen ? "rotate-180" : ""}`} />
                </div>
            </button>
            {isPolygonOpen && (
                <div className="p-3 space-y-2">
                    {polygons.map((poly, i) => (
                        <div
                            key={i}
                            onClick={() => onSelectEntity({ type: 'polygon', id: i })}
                            className={`flex flex-col gap-1 p-2 bg-slate-50 dark:bg-slate-800 rounded-lg border transition-all cursor-pointer ${selectedEntity?.type === 'polygon' && selectedEntity.id === i ? 'border-blue-500 ring-1 ring-blue-500/50' : 'border-slate-200 dark:border-slate-700'}`}
                        >
                            <div className="flex justify-between items-center">
                                <span className="itemlabel">Poly {i + 1}</span>
                                <div className="flex gap-2">
                                    <select
                                        value={poly.materialId}
                                        onChange={(e) => handleUpdatePolygonMat(i, e.target.value)}
                                        className="cursor-pointer bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-[10px] px-1 py-0.5 rounded text-slate-900 dark:text-slate-100 outline-none focus:border-blue-500"
                                    >
                                        {materials.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
                                    </select>
                                    <button
                                        onClick={(e) => { e.stopPropagation(); setExpandedPolygonId(i); }}
                                        className="cursor-pointer p-1.5 rounded hover:bg-blue-500/20 hover:text-blue-500 transition-colors"
                                        title="Edit Point"
                                    >
                                        <Pencil className='w-3.5 h-3.5' />
                                    </button>
                                    <button
                                        onClick={(e) => { e.stopPropagation(); onDeletePolygon(i); }}
                                        className="cursor-pointer p-1.5 rounded hover:bg-rose-500/20 hover:text-rose-500 transition-colors"
                                        title="Delete Polygon"
                                    >
                                        <Trash className='w-3.5 h-3.5' />
                                    </button>
                                </div>
                            </div>
                            {expandedPolygonId === i && (
                                <div className="p-3 gap-2">
                                    {polygons[i].vertices.map((v, j) => (
                                        <div className='flex gap-2 items-center'>
                                            <div className='text-xs'>
                                                x :
                                            </div>
                                            <div className="">
                                                <NumericInput
                                                    key={j}
                                                    value={v.x}
                                                    onChange={(val) => handleUpdatePolygonPoint(i, j, 'x', val)}
                                                    className="cursor-pointer bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-[10px] px-1 py-0.5 rounded text-slate-900 dark:text-slate-100 outline-none focus:border-blue-500"
                                                />
                                            </div>
                                            <div className='text-xs'>
                                                y :
                                            </div>
                                            <div className="">
                                                <NumericInput
                                                    key={j}
                                                    value={v.y}
                                                    onChange={(val) => handleUpdatePolygonPoint(i, j, 'y', val)}
                                                    className="cursor-pointer bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-[10px] px-1 py-0.5 rounded text-slate-900 dark:text-slate-100 outline-none focus:border-blue-500"
                                                />
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {/* WATER LEVELS */}
            <button
                className="dropdownlabel2"
                onClick={() => { setIsWaterOpen(!isWaterOpen) }}>
                Water Levels ({waterLevels.length})
                <div
                    className="p-1.5 text-slate-600 dark:text-slate-300 rounded transition-colors">
                    <ChevronDown className={`w-4 h-4 transition ${isWaterOpen ? "rotate-180" : ""}`} />
                </div>
            </button>
            {isWaterOpen && (
                <div className="p-3 space-y-2">
                    {waterLevels.map((wl, i) => (
                        <div key={wl.id} className="bg-slate-50 dark:bg-slate-800 rounded border border-slate-200 dark:border-slate-700 overflow-hidden">
                            <div
                                className="flex items-center justify-between p-2 cursor-pointer"
                                onClick={() => setExpandedWaterLevelId(expandedWaterLevelId === wl.id ? null : wl.id)}
                            >
                                <div className="flex items-center gap-2">
                                    <ChevronRight className={`w-3 h-3 text-slate-500 dark:text-slate-400 transition-transform ${expandedWaterLevelId === wl.id ? 'rotate-90' : ''}`} />
                                    <input
                                        type="text"
                                        value={wl.name}
                                        onClick={(e) => e.stopPropagation()}
                                        onChange={(e) => handleRenameWaterLevel(i, e.target.value)}
                                        className="bg-transparent text-xs font-medium text-slate-700 dark:text-slate-200 focus:outline-none focus:border-b border-blue-500 w-32"
                                    />
                                </div>
                                <button
                                    onClick={(e) => { e.stopPropagation(); onDeleteWaterLevel(wl.id); }}
                                    className="p-1 text-slate-500 hover:text-rose-500 transition-colors"
                                >
                                    <Trash className="w-3 h-3" />
                                </button>
                            </div>

                            {expandedWaterLevelId === wl.id && (
                                <div className="p-2 bg-slate-100/50 dark:bg-slate-900/50 border-t border-slate-200 dark:border-slate-700 space-y-1">
                                    <div className="flex px-1 mb-1 text-[10px] text-slate-500">
                                        <div className="w-1/2">X (m)</div>
                                        <div className="w-1/2">Y (m)</div>
                                        <div className="w-6"></div>
                                    </div>
                                    {wl.points.map((pt, ptIdx) => (
                                        <div key={ptIdx} className="flex gap-1 items-center">
                                            <NumericInput
                                                value={pt.x}
                                                onChange={(val) => handleUpdateWaterPoint(i, ptIdx, 'x', val)}
                                                className="w-1/2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-[10px] px-1 py-0.5 rounded focus:border-blue-500 outline-none"
                                            />
                                            <NumericInput
                                                value={pt.y}
                                                onChange={(val) => handleUpdateWaterPoint(i, ptIdx, 'y', val)}
                                                className="w-1/2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-[10px] px-1 py-0.5 rounded focus:border-blue-500 outline-none"
                                            />
                                            <button
                                                onClick={() => handleDeletePointFromWaterLevel(i, ptIdx)}
                                                className="w-6 flex items-center justify-center text-slate-500 hover:text-rose-500"
                                            >
                                                <Trash className="w-3 h-3" />
                                            </button>
                                        </div>
                                    ))}
                                    <button
                                        onClick={() => handleAddPointToWaterLevel(i)}
                                        className="mt-2 w-full py-1 text-[10px] text-blue-400 hover:text-blue-300 border border-dashed border-blue-500/30 hover:border-blue-500/50 rounded flex items-center justify-center gap-1"
                                    >
                                        <Plus className="w-3 h-3" /> Add Point
                                    </button>
                                </div>
                            )}
                        </div>
                    ))}
                    <button onClick={handleAddWaterLevelClick} className="add-button">+ New Water Level</button>
                </div>
            )}

            {/* POINT LOADS */}
            <button
                className="dropdownlabel2"
                onClick={() => { setIsLoadOpen(!isLoadOpen) }}>
                Point Loads ({pointLoads.length})
                <div
                    className="p-1.5 text-slate-600 dark:text-slate-300 rounded transition-colors">
                    <ChevronDown className={`w-4 h-4 transition ${isLoadOpen ? "rotate-180" : ""}`} />
                </div>
            </button>
            {isLoadOpen && (
                <div className="p-4 space-y-2">
                    {pointLoads.map((load, i) => (
                        <div
                            key={load.id}
                            onClick={() => onSelectEntity({ type: 'load', id: load.id })}
                            className={`flex flex-col gap-1 p-2 bg-slate-50 dark:bg-slate-800 rounded border transition-all cursor-pointer ${selectedEntity?.type === 'load' && selectedEntity.id === load.id ? 'border-blue-500 ring-1 ring-blue-500/50' : 'border-slate-200 dark:border-slate-700'}`}
                        >
                            <div className="flex justify-between items-center">
                                <span className="itemlabel">{load.id}</span>
                                <button onClick={(e) => { e.stopPropagation(); onDeleteLoad(load.id); }} className="cursor-pointer p-1.5 text-slate-500 hover:text-rose-500 transition-colors">
                                    <Trash className="w-3.5 h-3.5" />
                                </button>
                            </div>
                            <div className="grid grid-cols-2 gap-2">
                                <div className="flex flex-col gap-1">
                                    <span className="sublabel">Coord X <MathRender tex="(m)" /></span>
                                    <NumericInput
                                        value={load.x}
                                        onChange={(val) => {
                                            const next = [...pointLoads];
                                            next[i] = { ...next[i], x: val };
                                            onUpdateLoads(next);
                                        }}
                                        className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 text-[10px] px-2 py-1 rounded outline-none focus:border-blue-500"
                                    />
                                </div>
                                <div className="flex flex-col gap-1">
                                    <span className="sublabel">Coord Y <MathRender tex="(m)" /></span>
                                    <NumericInput
                                        value={load.y}
                                        onChange={(val) => {
                                            const next = [...pointLoads];
                                            next[i] = { ...next[i], y: val };
                                            onUpdateLoads(next);
                                        }}
                                        className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 text-[10px] px-2 py-1 rounded outline-none focus:border-blue-500"
                                    />
                                </div>
                                <div className="flex flex-col gap-1">
                                    <span className="sublabel">Force Fx <MathRender tex="(kN)" /></span>
                                    <NumericInput
                                        value={load.fx}
                                        onChange={(val) => {
                                            const next = [...pointLoads];
                                            next[i] = { ...next[i], fx: val };
                                            onUpdateLoads(next);
                                        }}
                                        className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 text-[10px] px-2 py-1 rounded outline-none focus:border-blue-500"
                                    />
                                </div>
                                <div className="flex flex-col gap-1">
                                    <span className="sublabel">Force Fy <MathRender tex="(kN)" /></span>
                                    <NumericInput
                                        value={load.fy}
                                        onChange={(val) => {
                                            const next = [...pointLoads];
                                            next[i] = { ...next[i], fy: val };
                                            onUpdateLoads(next);
                                        }}
                                        className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 text-[10px] px-2 py-1 rounded outline-none focus:border-blue-500"
                                    />
                                </div>
                            </div>
                        </div>
                    ))}
                    <button onClick={handleAddLoad} className="add-button">+ Add Load</button>
                </div>
            )}

            {/* LINE LOADS */}
            <button
                className="dropdownlabel2"
                onClick={() => { setIsLineLoadOpen(!isLineLoadOpen) }}>
                Line Loads ({lineLoads.length})
                <div
                    className="p-1.5 text-slate-600 dark:text-slate-300 rounded transition-colors">
                    <ChevronDown className={`w-4 h-4 transition ${isLineLoadOpen ? "rotate-180" : ""}`} />
                </div>
            </button>
            {isLineLoadOpen && (
                <div className="p-4 space-y-2">
                    {lineLoads.map((load, i) => (
                        <div
                            key={load.id}
                            onClick={() => onSelectEntity({ type: 'load', id: load.id })}
                            className={`flex flex-col gap-1 p-2 bg-slate-50 dark:bg-slate-800 rounded border transition-all cursor-pointer ${selectedEntity?.type === 'load' && selectedEntity.id === load.id ? 'border-blue-500 ring-1 ring-blue-500/50' : 'border-slate-200 dark:border-slate-700'}`}
                        >
                            <div className="flex justify-between items-center">
                                <span className="itemlabel">{load.id}</span>
                                <button onClick={(e) => { e.stopPropagation(); onDeleteLineLoad(load.id); }} className="cursor-pointer p-1.5 text-slate-500 hover:text-rose-500 transition-colors">
                                    <Trash className="w-3.5 h-3.5" />
                                </button>
                            </div>
                            <div className="grid grid-cols-2 gap-2">
                                <div className="flex flex-col gap-1 text-[10px]">
                                    <span className="sublabel text-slate-500 dark:text-slate-400">P1 (X, Y)</span>
                                    <div className="flex gap-1">
                                        <NumericInput
                                            value={load.x1}
                                            onChange={(val) => {
                                                const next = [...lineLoads];
                                                next[i] = { ...next[i], x1: val };
                                                onUpdateLineLoads(next);
                                            }}
                                            className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 px-1 py-0.5 rounded outline-none focus:border-blue-500"
                                        />
                                        <NumericInput
                                            value={load.y1}
                                            onChange={(val) => {
                                                const next = [...lineLoads];
                                                next[i] = { ...next[i], y1: val };
                                                onUpdateLineLoads(next);
                                            }}
                                            className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 px-1 py-0.5 rounded outline-none focus:border-blue-500"
                                        />
                                    </div>
                                </div>
                                <div className="flex flex-col gap-1 text-[10px]">
                                    <span className="sublabel text-slate-500 dark:text-slate-400">P2 (X, Y)</span>
                                    <div className="flex gap-1">
                                        <NumericInput
                                            value={load.x2}
                                            onChange={(val) => {
                                                const next = [...lineLoads];
                                                next[i] = { ...next[i], x2: val };
                                                onUpdateLineLoads(next);
                                            }}
                                            className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 px-1 py-0.5 rounded outline-none focus:border-blue-500"
                                        />
                                        <NumericInput
                                            value={load.y2}
                                            onChange={(val) => {
                                                const next = [...lineLoads];
                                                next[i] = { ...next[i], y2: val };
                                                onUpdateLineLoads(next);
                                            }}
                                            className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 px-1 py-0.5 rounded outline-none focus:border-blue-500"
                                        />
                                    </div>
                                </div>
                                <div className="flex flex-col gap-1">
                                    <span className="sublabel">Force X <MathRender tex="(kN/m)" /></span>
                                    <NumericInput
                                        value={load.fx}
                                        onChange={(val) => {
                                            const next = [...lineLoads];
                                            next[i] = { ...next[i], fx: val };
                                            onUpdateLineLoads(next);
                                        }}
                                        className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 text-[10px] px-2 py-1 rounded outline-none focus:border-blue-500"
                                    />
                                </div>
                                <div className="flex flex-col gap-1">
                                    <span className="sublabel">Force Y <MathRender tex="(kN/m)" /></span>
                                    <NumericInput
                                        value={load.fy}
                                        onChange={(val) => {
                                            const next = [...lineLoads];
                                            next[i] = { ...next[i], fy: val };
                                            onUpdateLineLoads(next);
                                        }}
                                        className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 text-[10px] px-2 py-1 rounded outline-none focus:border-blue-500"
                                    />
                                </div>
                            </div>
                        </div>
                    ))}
                    <button onClick={handleAddLineLoad} className="add-button">+ Add Line Load</button>
                </div>
            )}

            {/* EMBEDDED BEAMS */}
            <button
                className="dropdownlabel2"
                onClick={() => { setIsEmbeddedBeamOpen(!isEmbeddedBeamOpen) }}>
                Embedded Beams ({embeddedBeams.length})
                <div
                    className="p-1.5 text-slate-600 dark:text-slate-300 rounded transition-colors">
                    <ChevronDown className={`w-4 h-4 transition ${isEmbeddedBeamOpen ? "rotate-180" : ""}`} />
                </div>
            </button>
            {isEmbeddedBeamOpen && (
                <div className="p-4 space-y-2">
                    {embeddedBeams.map((beam, i) => (
                        <div
                            key={beam.id}
                            onClick={() => onSelectEntity({ type: 'embeddedBeam', id: beam.id })}
                            className={`flex flex-col gap-1 p-2 bg-slate-50 dark:bg-slate-800 rounded border transition-all cursor-pointer ${selectedEntity?.type === 'embeddedBeam' && selectedEntity.id === beam.id ? 'border-blue-500 ring-1 ring-blue-500/50' : 'border-slate-200 dark:border-slate-700'}`}
                        >
                            <div className="flex justify-between items-center">
                                <span className="itemlabel">{beam.id}</span>
                                <div className="flex gap-2">
                                    <select
                                        value={beam.materialId}
                                        onChange={(e) => handleUpdateEmbeddedBeamMat(i, e.target.value)}
                                        onClick={(e) => e.stopPropagation()}
                                        className="cursor-pointer bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-[10px] px-1 py-0.5 rounded text-slate-900 dark:text-slate-100 outline-none focus:border-blue-500 max-w-[100px]"
                                    >
                                        {beamMaterials.length === 0 && <option value="">No material</option>}
                                        {beamMaterials.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
                                    </select>
                                    <button onClick={(e) => { e.stopPropagation(); onDeleteEmbeddedBeam(beam.id); }} className="cursor-pointer p-1.5 text-slate-500 hover:text-rose-500 transition-colors">
                                        <Trash className="w-3.5 h-3.5" />
                                    </button>
                                </div>
                            </div>
                            <div className="text-[10px] text-slate-500 dark:text-slate-400">
                                ({beam.points[0].x.toFixed(2)}, {beam.points[0].y.toFixed(2)}) → ({beam.points[1].x.toFixed(2)}, {beam.points[1].y.toFixed(2)})
                            </div>
                        </div>
                    ))}
                    <button onClick={handleAddEmbeddedBeam} className="add-button">+ Add Beam (Manual)</button>
                </div>
            )}
        </div>
    );
};

