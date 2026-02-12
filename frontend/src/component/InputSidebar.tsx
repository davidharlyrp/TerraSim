import { PolygonData, Material, PointLoad, LineLoad, WaterLevel } from '../types';
import { ChevronDown, Pencil, Trash, ChevronRight, Plus } from 'lucide-react';
import { MathRender } from './Math';
import { useState } from 'react';

interface InputSidebarProps {
    materials: Material[];
    polygons: PolygonData[];
    pointLoads: PointLoad[];
    lineLoads: LineLoad[];
    waterLevels: WaterLevel[]; // NEW
    onUpdateMaterials: (m: Material[]) => void;
    onUpdatePolygons: (p: PolygonData[]) => void;
    onUpdateLoads: (l: PointLoad[]) => void;
    onUpdateLineLoads: (l: LineLoad[]) => void;
    onAddWaterLevel: (points: { x: number, y: number }[]) => void; // NEW
    onUpdateWaterLevel: (index: number, wl: WaterLevel) => void; // NEW
    onUpdatePolygonPoints: (index: number, points: { x: number, y: number }[]) => void; // NEW
    onEditMaterial: (mat: Material) => void;
    onDeleteMaterial: (id: string) => void;
    onDeletePolygon: (idx: number) => void;
    onDeleteLoad: (id: string) => void;
    onDeleteWaterLevel: (id: string) => void;
    onDeleteWaterPoint: (wlIndex: number, ptIndex: number) => void; // NEW
    selectedEntity: { type: string, id: string | number } | null;
    onSelectEntity: (selection: { type: string, id: string | number } | null) => void;
}

export const InputSidebar: React.FC<InputSidebarProps> = ({
    materials,
    polygons,
    pointLoads,
    lineLoads,
    waterLevels,
    onUpdateMaterials,
    onUpdatePolygons,
    onUpdateLoads,
    onUpdateLineLoads,
    onAddWaterLevel,
    onUpdateWaterLevel,
    onUpdatePolygonPoints,
    onEditMaterial,
    onDeleteMaterial,
    onDeletePolygon,
    onDeleteLoad,
    onDeleteWaterLevel,
    onDeleteWaterPoint,
    selectedEntity,
    onSelectEntity
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

    const handleUpdateMatColor = (id: string, color: string) => {
        onUpdateMaterials(materials.map(m => m.id === id ? { ...m, color } : m));
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
    const [expandedWaterLevelId, setExpandedWaterLevelId] = useState<string | null>(null);
    const [expandedPolygonId, setExpandedPolygonId] = useState<number | null>(null);


    return (
        <div className="md:w-full w-[calc(100vw-40px)] md:h-full h-[calc(100vh-50px)] pb-30 p-2 flex flex-col gap-2 overflow-y-auto bg-white dark:bg-slate-900 border-r md:border-0 border-slate-200 dark:border-slate-700 custom-scrollbar">
            {/* MATERIALS */}
            <button
                className="dropdownlabel2"
                onClick={() => { setIsMaterialOpen(!isMaterialOpen) }}>
                Materials
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

            {/* POLYGONS */}
            <button
                className="dropdownlabel2"
                onClick={() => { setIsPolygonOpen(!isPolygonOpen) }}>
                Polygons
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
                                                <input
                                                    key={j}
                                                    type="number"
                                                    value={v.x}
                                                    onChange={(e) => handleUpdatePolygonPoint(i, j, 'x', Number(e.target.value))}
                                                    className="cursor-pointer bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-[10px] px-1 py-0.5 rounded text-slate-900 dark:text-slate-100 outline-none focus:border-blue-500"
                                                />
                                            </div>
                                            <div className='text-xs'>
                                                y :
                                            </div>
                                            <div className="">
                                                <input
                                                    key={j}
                                                    type="number"
                                                    value={v.y}
                                                    onChange={(e) => handleUpdatePolygonPoint(i, j, 'y', Number(e.target.value))}
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
                Water Levels
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
                                            <input
                                                type="number"
                                                value={pt.x}
                                                onChange={(e) => handleUpdateWaterPoint(i, ptIdx, 'x', Number(e.target.value))}
                                                className="w-1/2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-[10px] px-1 py-0.5 rounded focus:border-blue-500 outline-none"
                                            />
                                            <input
                                                type="number"
                                                value={pt.y}
                                                onChange={(e) => handleUpdateWaterPoint(i, ptIdx, 'y', Number(e.target.value))}
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
                Point Loads
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
                                    <input
                                        type="number"
                                        value={load.x}
                                        onChange={(e) => {
                                            const next = [...pointLoads];
                                            next[i] = { ...next[i], x: Number(e.target.value) };
                                            onUpdateLoads(next);
                                        }}
                                        className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 text-[10px] px-2 py-1 rounded outline-none focus:border-blue-500"
                                    />
                                </div>
                                <div className="flex flex-col gap-1">
                                    <span className="sublabel">Coord Y <MathRender tex="(m)" /></span>
                                    <input
                                        type="number"
                                        value={load.y}
                                        onChange={(e) => {
                                            const next = [...pointLoads];
                                            next[i] = { ...next[i], y: Number(e.target.value) };
                                            onUpdateLoads(next);
                                        }}
                                        className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 text-[10px] px-2 py-1 rounded outline-none focus:border-blue-500"
                                    />
                                </div>
                                <div className="flex flex-col gap-1">
                                    <span className="sublabel">Force Fx <MathRender tex="(kN)" /></span>
                                    <input
                                        type="number"
                                        value={load.fx}
                                        onChange={(e) => {
                                            const next = [...pointLoads];
                                            next[i] = { ...next[i], fx: Number(e.target.value) };
                                            onUpdateLoads(next);
                                        }}
                                        className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 text-[10px] px-2 py-1 rounded outline-none focus:border-blue-500"
                                    />
                                </div>
                                <div className="flex flex-col gap-1">
                                    <span className="sublabel">Force Fy <MathRender tex="(kN)" /></span>
                                    <input
                                        type="number"
                                        value={load.fy}
                                        onChange={(e) => {
                                            const next = [...pointLoads];
                                            next[i] = { ...next[i], fy: Number(e.target.value) };
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
                Line Loads
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
                                <button onClick={(e) => { e.stopPropagation(); onDeleteLoad(load.id); }} className="cursor-pointer p-1.5 text-slate-500 hover:text-rose-500 transition-colors">
                                    <Trash className="w-3.5 h-3.5" />
                                </button>
                            </div>
                            <div className="grid grid-cols-2 gap-2">
                                <div className="flex flex-col gap-1 text-[10px]">
                                    <span className="sublabel text-slate-500 dark:text-slate-400">P1 (X, Y)</span>
                                    <div className="flex gap-1">
                                        <input
                                            type="number"
                                            value={load.x1}
                                            onChange={(e) => {
                                                const next = [...lineLoads];
                                                next[i] = { ...next[i], x1: Number(e.target.value) };
                                                onUpdateLineLoads(next);
                                            }}
                                            className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 px-1 py-0.5 rounded outline-none focus:border-blue-500"
                                        />
                                        <input
                                            type="number"
                                            value={load.y1}
                                            onChange={(e) => {
                                                const next = [...lineLoads];
                                                next[i] = { ...next[i], y1: Number(e.target.value) };
                                                onUpdateLineLoads(next);
                                            }}
                                            className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 px-1 py-0.5 rounded outline-none focus:border-blue-500"
                                        />
                                    </div>
                                </div>
                                <div className="flex flex-col gap-1 text-[10px]">
                                    <span className="sublabel text-slate-500 dark:text-slate-400">P2 (X, Y)</span>
                                    <div className="flex gap-1">
                                        <input
                                            type="number"
                                            value={load.x2}
                                            onChange={(e) => {
                                                const next = [...lineLoads];
                                                next[i] = { ...next[i], x2: Number(e.target.value) };
                                                onUpdateLineLoads(next);
                                            }}
                                            className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 px-1 py-0.5 rounded outline-none focus:border-blue-500"
                                        />
                                        <input
                                            type="number"
                                            value={load.y2}
                                            onChange={(e) => {
                                                const next = [...lineLoads];
                                                next[i] = { ...next[i], y2: Number(e.target.value) };
                                                onUpdateLineLoads(next);
                                            }}
                                            className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 px-1 py-0.5 rounded outline-none focus:border-blue-500"
                                        />
                                    </div>
                                </div>
                                <div className="flex flex-col gap-1">
                                    <span className="sublabel">Force X <MathRender tex="(kN/m)" /></span>
                                    <input
                                        type="number"
                                        value={load.fx}
                                        onChange={(e) => {
                                            const next = [...lineLoads];
                                            next[i] = { ...next[i], fx: Number(e.target.value) };
                                            onUpdateLineLoads(next);
                                        }}
                                        className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 text-[10px] px-2 py-1 rounded outline-none focus:border-blue-500"
                                    />
                                </div>
                                <div className="flex flex-col gap-1">
                                    <span className="sublabel">Force Y <MathRender tex="(kN/m)" /></span>
                                    <input
                                        type="number"
                                        value={load.fy}
                                        onChange={(e) => {
                                            const next = [...lineLoads];
                                            next[i] = { ...next[i], fy: Number(e.target.value) };
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
        </div>
    );
};

