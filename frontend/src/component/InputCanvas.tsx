import React, { useMemo, useRef, useEffect, useState, useCallback } from 'react';
import { WizardTab } from './WizardNavigation';
import { Canvas, useThree } from '@react-three/fiber';
import { OrthographicCamera, OrbitControls, Grid, Line } from '@react-three/drei';
import * as THREE from 'three';
import { Ruler } from './Ruler';
import { useTheme } from '../context/ThemeContext';
import { Trash } from 'lucide-react';
import { PolygonData, PointLoad, Material, GeneralSettings, LineLoad, PhaseType } from '../types';

interface InputCanvasProps {
    polygons: PolygonData[];
    pointLoads: PointLoad[];
    lineLoads: LineLoad[];
    materials: Material[];
    water_levels?: { id: string, name: string, points: { x: number, y: number }[] }[]; // CHANGED
    activePolygonIndices?: number[];
    activeLoadIds?: string[];
    activeWaterLevelId?: string; // NEW
    drawMode: string | null;
    onAddPolygon: (vertices: { x: number, y: number }[]) => void;
    onAddPointLoad: (x: number, y: number) => void;
    onAddLineLoad: (x1: number, y1: number, x2: number, y2: number) => void;
    onAddWaterLevel: (vertices: { x: number, y: number }[]) => void;
    onCancelDraw: () => void;
    selectedEntity: { type: string, id: string | number } | null;
    onSelectEntity: (selection: { type: string, id: string | number } | null) => void;
    onDeletePolygon: (idx: number) => void;
    onDeleteLoad: (id: string) => void;
    onDeleteWaterLevel: (id: string) => void; // CHANGED
    onUpdatePolygon?: (idx: number, data: Partial<PolygonData>) => void;
    onToggleActive?: (type: 'polygon' | 'load', id: string | number) => void; // Maybe add water_level later
    onUpdateWaterLevel?: (index: number, wl: any) => void; // NEW
    activeTab?: WizardTab;
    currentPhaseType?: PhaseType;
    generalSettings: GeneralSettings;
    currentMaterial?: Record<number, string>; // polygon_index -> material_id from phase
    onOverrideMaterial?: (polyIdx: number, matId: string) => void; // NEW
}

interface PolygonProps {
    data: PolygonData;
    materials: Material[];
    isSelected: boolean;
    isActive: boolean;
    onSelect: () => void;
    onContextMenu: (x: number, y: number) => void;
    overrideMaterialId?: string; // NEW
}

const Polygon = ({ data, materials, isSelected, isActive, onSelect, onContextMenu, overrideMaterialId }: PolygonProps) => {
    const effectiveMaterialId = overrideMaterialId || data.materialId;
    const material = materials.find(m => m.id === effectiveMaterialId);
    let fillColor = material ? material.color : '#334155';
    let lineColor = useTheme().theme === 'dark' ? 'white' : '#64748b';
    let pointColor = useTheme().theme === 'dark' ? 'white' : '#64748b';

    if (!isActive) {
        fillColor = "#334155"; // Neutral gray for inactive
        lineColor = useTheme().theme === 'dark' ? 'white' : '#64748b';
        pointColor = useTheme().theme === 'dark' ? 'white' : '#64748b';
    }

    const { shape, points } = useMemo(() => {
        const shape = new THREE.Shape();
        const pts: THREE.Vector3[] = [];

        data.vertices.forEach((v, i) => {
            if (i === 0) shape.moveTo(v.x, v.y);
            else shape.lineTo(v.x, v.y);
            pts.push(new THREE.Vector3(v.x, v.y, 2.5));
        });

        shape.closePath();
        pts.push(pts[0]); // Close outline
        return { shape, points: pts };
    }, [data]);

    return (
        <group onContextMenu={(e) => { e.nativeEvent.preventDefault(); e.stopPropagation(); onContextMenu(e.nativeEvent.clientX, e.nativeEvent.clientY); }}>
            {/* Fill */}
            <mesh
                position={[0, 0, (isSelected ? 2 : 0)]}
                onClick={(e) => { e.stopPropagation(); onSelect(); }}
            >
                <shapeGeometry args={[shape]} />
                <meshBasicMaterial
                    color={fillColor}
                    opacity={isSelected ? 1 : (isActive ? 0.8 : 0.2)}
                    transparent
                    side={THREE.DoubleSide}
                />
            </mesh>
            {/* Outline */}
            <Line points={points} color={isSelected ? "#3b82f6" : lineColor} lineWidth={isSelected ? 3 : 1} />
            {/* Nodes */}
            {points.map((p, i) => (
                <mesh key={i} position={p}>
                    <circleGeometry args={[0.05, 16]} />
                    <meshBasicMaterial color={pointColor} />
                </mesh>
            ))}
        </group>
    );
};

const LoadMarker = ({ load, isSelected, isActive, onSelect, onContextMenu }: {
    load: PointLoad,
    isSelected: boolean,
    isActive: boolean,
    onSelect: () => void,
    onContextMenu: (x: number, y: number) => void
}) => {
    const dir = new THREE.Vector3(load.fx, load.fy, 0).normalize();
    const length = 2.0;
    const headLen = 0.5;
    const origin = new THREE.Vector3(load.x, load.y + 0.2, 0.1);
    const shaftStart = origin.clone().sub(dir.clone().multiplyScalar(length));

    const angle = Math.atan2(dir.y, dir.x);
    let color = isSelected ? "#60a5fa" : (isActive ? "#ef4444" : "#475569");

    return (
        <group
            onClick={(e) => { e.stopPropagation(); onSelect(); }}
            onContextMenu={(e) => { e.nativeEvent.preventDefault(); e.stopPropagation(); onContextMenu(e.nativeEvent.clientX, e.nativeEvent.clientY); }}
        >
            {/* Shaft - Thick line */}
            <Line
                points={[shaftStart, origin]}
                color={color}
                lineWidth={3}
            />
            {/* Arrow Head */}
            <mesh position={origin} rotation={[0, 0, angle - Math.PI / 2]}>
                <coneGeometry args={[0.25, headLen, 4]} />
                <meshBasicMaterial color={color} />
            </mesh>
        </group>
    );
};

const LineLoadMarker = ({ load, isSelected, isActive, onSelect, onContextMenu }: {
    load: LineLoad,
    isSelected: boolean,
    isActive: boolean,
    onSelect: () => void,
    onContextMenu: (x: number, y: number) => void
}) => {
    const dir = new THREE.Vector3(load.fx, load.fy, 0);
    const forceMagnitude = dir.length();
    if (forceMagnitude === 0) return null;

    const normalizedDir = dir.clone().normalize();
    const angle = Math.atan2(normalizedDir.y, normalizedDir.x);
    const color = isSelected ? "#60a5fa" : (isActive ? "#ef4444" : "#475569");

    const p1 = new THREE.Vector3(load.x1, load.y1 + 0.2, 0.1);
    const p2 = new THREE.Vector3(load.x2, load.y2 + 0.2, 0.1);
    const l1 = new THREE.Vector3(load.x1, load.y1, 0.1);
    const l2 = new THREE.Vector3(load.x2, load.y2, 0.1);
    const length = p1.distanceTo(p2);
    const numArrows = Math.max(3, Math.floor(length / 2.0));

    const arrows = [];
    for (let i = 0; i < numArrows; i++) {
        const t = i / (numArrows - 1);
        const origin = p1.clone().lerp(p2, t);
        const shaftStart = origin.clone().sub(normalizedDir.clone().multiplyScalar(1.5));
        arrows.push({ origin, shaftStart });
    }

    return (
        <group
            onClick={(e) => { e.stopPropagation(); onSelect(); }}
            onContextMenu={(e) => { e.nativeEvent.preventDefault(); e.stopPropagation(); onContextMenu(e.nativeEvent.clientX, e.nativeEvent.clientY); }}
        >
            <Line points={[l1, l2]} color={color} lineWidth={2} />
            {arrows.map((arrow, idx) => (
                <group key={idx}>
                    <Line points={[arrow.shaftStart, arrow.origin]} color={color} lineWidth={2} />
                    <mesh position={arrow.origin} rotation={[0, 0, angle - Math.PI / 2]}>
                        <coneGeometry args={[0.15, 0.4, 4]} />
                        <meshBasicMaterial color={color} />
                    </mesh>
                </group>
            ))}
        </group>
    );
};


// --- CURSOR TRACKER ---
const CursorTracker = ({ onMouseMove, generalSettings }: { onMouseMove: (x: number, y: number) => void, generalSettings: GeneralSettings }) => {
    const { camera, mouse, raycaster } = useThree();

    const getWorldPos = useCallback(() => {
        raycaster.setFromCamera(mouse, camera);
        const plane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);
        const target = new THREE.Vector3();
        raycaster.ray.intersectPlane(plane, target);

        if (generalSettings.snapToGrid) {
            const s = generalSettings.snapSpacing;
            return {
                x: Math.round(target.x / s) * s,
                y: Math.round(target.y / s) * s
            };
        }
        return { x: target.x, y: target.y };
    }, [camera, mouse, raycaster, generalSettings]);

    useEffect(() => {
        const handleMove = () => {
            const pos = getWorldPos();
            onMouseMove(pos.x, pos.y);
        };

        window.addEventListener('mousemove', handleMove);
        return () => window.removeEventListener('mousemove', handleMove);
    }, [getWorldPos, onMouseMove]);

    return null;
};


// --- DRAWING MANAGER ---
const DrawingManager = ({ mode, onAddPolygon, onAddPointLoad, onAddLineLoad, onAddWaterLevel, onCancel, generalSettings }: {
    mode: string | null;
    onAddPolygon: (pts: { x: number, y: number }[]) => void;
    onAddPointLoad: (x: number, y: number) => void;
    onAddLineLoad: (x1: number, y1: number, x2: number, y2: number) => void;
    onAddWaterLevel: (vertices: { x: number, y: number }[]) => void;
    onCancel: () => void;
    generalSettings: GeneralSettings;
}) => {
    const { camera, mouse, raycaster } = useThree();
    const [tempPoints, setTempPoints] = useState<THREE.Vector3[]>([]);
    const [previewPoint, setPreviewPoint] = useState<THREE.Vector3 | null>(null);
    const mountTime = useRef(Date.now());

    useEffect(() => {
        mountTime.current = Date.now();
        setTempPoints([]);
        setPreviewPoint(null);
    }, [mode]);

    const getWorldPos = useCallback(() => {
        raycaster.setFromCamera(mouse, camera);
        const plane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);
        const target = new THREE.Vector3();
        raycaster.ray.intersectPlane(plane, target);

        if (generalSettings.snapToGrid) {
            const s = generalSettings.snapSpacing;
            return new THREE.Vector3(
                Math.round(target.x / s) * s,
                Math.round(target.y / s) * s,
                0.4
            );
        }
        return new THREE.Vector3(target.x, target.y, 0.4);
    }, [camera, mouse, raycaster, generalSettings]);

    useEffect(() => {
        if (!mode) return;

        const handleDown = (e: MouseEvent) => {
            if (e.button !== 0 || Date.now() - mountTime.current < 200) return;
            const pos = getWorldPos();

            if (mode === 'point_load') {
                onAddPointLoad(pos.x, pos.y);
            } else if (mode === 'rectangle') {
                if (tempPoints.length === 0) {
                    setTempPoints([pos]);
                } else {
                    const p1 = tempPoints[0];
                    const vertices = [
                        { x: p1.x, y: p1.y },
                        { x: pos.x, y: p1.y },
                        { x: pos.x, y: pos.y },
                        { x: p1.x, y: pos.y }
                    ];
                    onAddPolygon(vertices);
                    setTempPoints([]);
                }
            } else if (mode === 'line_load') {
                if (tempPoints.length === 0) {
                    setTempPoints([pos]);
                } else {
                    const p1 = tempPoints[0];
                    onAddLineLoad(p1.x, p1.y, pos.x, pos.y);
                    setTempPoints([]);
                }
            } else if ((mode === 'polygon' || mode === 'water_level') && tempPoints.length >= 3) {
                // Check if clicked the first point to close
                const firstPoint = tempPoints[0];
                const dist = Math.sqrt(Math.pow(pos.x - firstPoint.x, 2) + Math.pow(pos.y - firstPoint.y, 2));
                const snapThreshold = generalSettings.snapToGrid ? 0.1 : 0.2; // Small threshold in world units

                if (dist < snapThreshold) {
                    const vertices = tempPoints.map(p => ({ x: p.x, y: p.y }));
                    if (mode === 'polygon') onAddPolygon(vertices);
                    else if (mode === 'water_level') onAddWaterLevel(vertices);
                    setTempPoints([]);
                    return;
                }
                setTempPoints(prev => [...prev, pos]);
            } else {
                setTempPoints(prev => [...prev, pos]);
            }
        };

        const handleMove = () => {
            setPreviewPoint(getWorldPos());
        };

        const handleKeys = (e: KeyboardEvent) => {
            if (e.key === 'Enter') {
                if (tempPoints.length >= 2) {
                    const vertices = tempPoints.map(p => ({ x: p.x, y: p.y }));
                    if (mode === 'polygon') onAddPolygon(vertices);
                    if (mode === 'water_level') onAddWaterLevel(vertices);
                }
                setTempPoints([]);
            } else if (e.key === 'Escape') {
                setTempPoints([]);
                onCancel();
            }
        };

        window.addEventListener('mousedown', handleDown);
        window.addEventListener('mousemove', handleMove);
        window.addEventListener('keydown', handleKeys);
        return () => {
            window.removeEventListener('mousedown', handleDown);
            window.removeEventListener('mousemove', handleMove);
            window.removeEventListener('keydown', handleKeys);
        };
    }, [mode, getWorldPos, tempPoints, onAddPolygon, onAddPointLoad, onAddWaterLevel, onCancel]);

    if (!mode) return null;

    const linePoints = [...tempPoints];
    if (previewPoint) {
        if (mode === 'rectangle' && tempPoints.length === 1) {
            const p1 = tempPoints[0];
            linePoints.push(new THREE.Vector3(previewPoint.x, p1.y, 0.4));
            linePoints.push(new THREE.Vector3(previewPoint.x, previewPoint.y, 0.4));
            linePoints.push(new THREE.Vector3(p1.x, previewPoint.y, 0.4));
            linePoints.push(new THREE.Vector3(p1.x, p1.y, 0.4));
        } else if (mode === 'line_load' && tempPoints.length === 1) {
            linePoints.push(previewPoint);
        } else if (mode !== 'rectangle' && mode !== 'line_load') {
            linePoints.push(previewPoint);
        }
    }

    return (
        <group>
            {linePoints.length >= 2 && (
                <Line points={linePoints} color="yellow" lineWidth={2} dashed={true} />
            )}
            {tempPoints.map((p, i) => (
                <mesh key={i} position={p}>
                    <circleGeometry args={[0.1, 16]} />
                    <meshBasicMaterial color="yellow" />
                </mesh>
            ))}
            {previewPoint && (
                <mesh position={previewPoint}>
                    <circleGeometry args={[0.1, 16]} />
                    <meshBasicMaterial color="yellow" opacity={0.5} transparent />
                </mesh>
            )}
        </group>
    );
};

export const InputCanvas: React.FC<InputCanvasProps> = ({
    polygons, pointLoads, lineLoads, materials, water_levels,
    activePolygonIndices, activeLoadIds, activeWaterLevelId,
    drawMode, onAddPolygon, onAddPointLoad, onAddLineLoad, onAddWaterLevel, onCancelDraw,
    selectedEntity, onSelectEntity, onDeletePolygon, onDeleteLoad, onDeleteWaterLevel, onToggleActive,
    onUpdatePolygon,
    activeTab,
    currentPhaseType,
    generalSettings,
    currentMaterial,
    onOverrideMaterial
}) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const [contextMenu, setContextMenu] = useState<{ x: number, y: number, target: { type: 'polygon' | 'load', id: string | number } } | null>(null);
    const [cursorPos, setCursorPos] = useState<{ x: number, y: number } | null>(null);

    // Handling Delete Key for canvas-based deletion
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Delete' || e.key === 'Backspace') {
                if (!selectedEntity) return;
                if (document.activeElement?.tagName === 'INPUT' || document.activeElement?.tagName === 'SELECT') return;

                if (selectedEntity.type === 'polygon') {
                    onDeletePolygon(selectedEntity.id as number);
                } else if (selectedEntity.type === 'load') {
                    onDeleteLoad(selectedEntity.id as string);
                } else if (selectedEntity.type === 'water_level') {
                    onDeleteWaterLevel(selectedEntity.id as string);
                }
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [selectedEntity, onDeletePolygon, onDeleteLoad, onDeleteWaterLevel]);

    // Close context menu on click elsewhere
    useEffect(() => {
        const handleGlobalClick = () => setContextMenu(null);
        window.addEventListener('click', handleGlobalClick);
        return () => window.removeEventListener('click', handleGlobalClick);
    }, []);

    const handleContextMenu = (clientX: number, clientY: number, target: { type: 'polygon' | 'load', id: string | number }) => {
        if (!containerRef.current) return;
        const rect = containerRef.current.getBoundingClientRect();

        // Auto-select when right-clicking
        onSelectEntity(target);

        setContextMenu({
            x: clientX - rect.left,
            y: clientY - rect.top,
            target
        });
    };

    const { theme } = useTheme();
    const backgroundColor = theme === 'dark' ? "bg-slate-950" : "bg-slate-50";
    const gridColor = theme === 'dark' ? "#535c66" : "#e2e8f0";
    const gridSpacing = generalSettings.snapSpacing || 1;
    const hideGrid = generalSettings.hideGrid;
    const hideRuler = generalSettings.hideRuler;

    return (
        <div ref={containerRef} className={`w-full h-full ${backgroundColor} overflow-hidden outline-none relative`}>
            <Canvas onPointerMissed={() => onSelectEntity(null)}>
                <OrthographicCamera makeDefault position={[0, 0, 90]} zoom={20} />
                <OrbitControls enableRotate={false} />
                <ambientLight intensity={1.0} />
                {!hideGrid && (
                    <Grid position={[0, 0, -1]} rotation={[Math.PI / 2, 0, 0]} args={[500, 500]} cellColor={gridColor} sectionColor={gridColor} cellSize={gridSpacing} sectionSize={1} fadeDistance={100} />
                )}
                {!hideRuler && (
                    <Ruler />
                )}

                {water_levels && water_levels.map((wl, i) => {

                    const isSelected = selectedEntity?.type === 'water_level' && selectedEntity.id === i;

                    const isActivePhase = activeTab === WizardTab.STAGING ? (wl.id === activeWaterLevelId) : true;

                    let lineColor = isActivePhase ? "cyan" : "#334155";
                    let pointColor = isActivePhase ? "cyan" : "#334155";
                    if (isSelected) lineColor = "#3b82f6";
                    if (isSelected) pointColor = "#3b82f6";

                    return (
                        <group key={wl.id} onClick={(e) => { e.stopPropagation(); }}>
                            <Line
                                points={wl.points.map(p => new THREE.Vector3(p.x, p.y, 5))}
                                color={lineColor}
                                lineWidth={isSelected || isActivePhase ? 3 : 1}
                                dashed={!isActivePhase}
                            />
                            {isActivePhase && wl.points.map((p, ptIdx) => (
                                <mesh
                                    key={ptIdx}
                                    position={[p.x, p.y, 5]}
                                    onClick={(e) => { e.stopPropagation(); onSelectEntity({ type: 'water_level', id: i }); }}
                                >
                                    <circleGeometry args={[isSelected ? 0.3 : 0.05, 16]} />
                                    <meshBasicMaterial color={pointColor} />
                                </mesh>
                            ))}
                        </group>
                    );
                })}

                {polygons.map((poly, i) => {
                    const isSelected = selectedEntity?.type === 'polygon' && selectedEntity.id === i;
                    const isActive = activePolygonIndices ? activePolygonIndices.includes(i) : true;
                    const overrideId = activeTab === WizardTab.STAGING && currentMaterial ? currentMaterial[i] : undefined;
                    return (
                        <Polygon
                            key={i}
                            data={poly}
                            materials={materials}
                            isSelected={isSelected}
                            isActive={isActive}
                            onSelect={() => onSelectEntity({ type: 'polygon', id: i })}
                            onContextMenu={(x, y) => handleContextMenu(x, y, { type: 'polygon', id: i })}
                            overrideMaterialId={overrideId}
                        />
                    );
                })}

                {pointLoads.map((load) => {
                    const isSelected = selectedEntity?.type === 'load' && selectedEntity.id === load.id;
                    const isActive = activeLoadIds ? activeLoadIds.includes(load.id) : true;
                    return (
                        <LoadMarker
                            key={load.id}
                            load={load}
                            isSelected={isSelected}
                            isActive={isActive}
                            onSelect={() => onSelectEntity({ type: 'load', id: load.id })}
                            onContextMenu={(x, y) => handleContextMenu(x, y, { type: 'load', id: load.id })}
                        />
                    );
                })}

                {lineLoads && lineLoads.map((load) => {
                    const isSelected = selectedEntity?.type === 'load' && selectedEntity.id === load.id;
                    const isActive = activeLoadIds ? activeLoadIds.includes(load.id) : true;
                    return (
                        <LineLoadMarker
                            key={load.id}
                            load={load}
                            isSelected={isSelected}
                            isActive={isActive}
                            onSelect={() => onSelectEntity({ type: 'load', id: load.id })}
                            onContextMenu={(x, y) => handleContextMenu(x, y, { type: 'load', id: load.id })}
                        />
                    );
                })}

                <DrawingManager
                    mode={drawMode}
                    onAddPolygon={onAddPolygon}
                    onAddPointLoad={onAddPointLoad}
                    onAddLineLoad={onAddLineLoad}
                    onAddWaterLevel={onAddWaterLevel}
                    onCancel={onCancelDraw}
                    generalSettings={generalSettings}
                />

                <CursorTracker
                    onMouseMove={(x, y) => setCursorPos({ x, y })}
                    generalSettings={generalSettings}
                />
            </Canvas>

            {/* Cursor Coordinate Overlay */}
            {cursorPos && (
                <div className="absolute bottom-4 left-4 z-[50] pointer-events-none">
                    <div className="px-3 py-1.5 rounded-lg bg-slate-100/80 dark:bg-slate-900/80 backdrop-blur-md border border-slate-200 dark:border-slate-700 shadow-lg flex items-center gap-3">
                        <div className="flex items-center gap-1.5">
                            <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">X</span>
                            <span className="text-xs font-mono font-medium text-slate-700 dark:text-slate-200">{cursorPos.x.toFixed(2)}</span>
                        </div>
                        <div className="w-[1px] h-3 bg-slate-200 dark:bg-slate-700" />
                        <div className="flex items-center gap-1.5">
                            <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Y</span>
                            <span className="text-xs font-mono font-medium text-slate-700 dark:text-slate-200">{cursorPos.y.toFixed(2)}</span>
                        </div>
                    </div>
                </div>
            )}

            {contextMenu && (
                <div
                    className="absolute bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-xl py-1 z-50 min-w-[150px]"
                    style={{ left: contextMenu.x, top: contextMenu.y }}
                    onClick={(e) => e.stopPropagation()}
                >
                    {/* Toggle Active (only in staging/if prop exists) */}
                    {onToggleActive && currentPhaseType !== PhaseType.SAFETY_ANALYSIS && (
                        <button
                            className="cursor-pointer w-full text-left px-4 py-2 text-[10px] font-bold text-slate-700 dark:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-700 transition border-b border-slate-200 dark:border-slate-700/50"
                            onClick={() => {
                                onToggleActive(contextMenu.target.type, contextMenu.target.id);
                                setContextMenu(null);
                            }}
                        >
                            {(contextMenu.target.type === 'polygon'
                                ? activePolygonIndices?.includes(contextMenu.target.id as number)
                                : activeLoadIds?.includes(contextMenu.target.id as string))
                                ? 'Deactivate Element'
                                : 'Activate Element'}
                        </button>
                    )}

                    {/* Assign Material (Polygons only) - Visible in INPUT or STAGING (Plastic/K0) */}
                    {contextMenu.target.type === 'polygon' && (onUpdatePolygon || onOverrideMaterial) && (
                        /* Hide if in STAGING but Safety Analysis (locked) */
                        !(activeTab === WizardTab.STAGING && currentPhaseType === PhaseType.SAFETY_ANALYSIS) && (
                            <div className="group/sub relative">
                                <div className="flex items-center justify-between px-4 py-2 text-[10px] font-bold text-slate-700 dark:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-700 transition cursor-default">
                                    <span>{activeTab === WizardTab.STAGING ? "Override Material" : "Assign Material"}</span>
                                    <span className="opacity-50">›</span>
                                </div>
                                <div className="hidden group-hover/sub:block absolute left-full top-0 ml-[-1px] bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-xl py-1 min-w-[120px] max-h-[200px] overflow-y-auto custom-scrollbar">
                                    {materials.map(mat => (
                                        <button
                                            key={mat.id}
                                            className="cursor-pointer w-full text-left px-4 py-2 text-[10px] text-slate-700 dark:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-700 transition flex items-center gap-2"
                                            onClick={() => {
                                                if (activeTab === WizardTab.STAGING && onOverrideMaterial) {
                                                    onOverrideMaterial(contextMenu.target.id as number, mat.id);
                                                } else if (onUpdatePolygon) {
                                                    onUpdatePolygon(contextMenu.target.id as number, { materialId: mat.id });
                                                }
                                                setContextMenu(null);
                                            }}
                                        >
                                            <div className="w-4 h-4" style={{ backgroundColor: mat.color }} />
                                            <span className="truncate">{mat.name}</span>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        ))}

                    {/* Delete Option - Hidden in STAGING */}
                    {activeTab !== WizardTab.STAGING && (
                        <button
                            className="cursor-pointer w-full text-left px-4 py-2 text-[10px] font-bold text-rose-400 hover:bg-rose-500/10 transition flex items-center gap-2"
                            onClick={() => {
                                if (contextMenu.target.type === 'polygon') {
                                    onDeletePolygon(contextMenu.target.id as number);
                                } else if (contextMenu.target.type === 'load') {
                                    onDeleteLoad(contextMenu.target.id as string);
                                }
                                setContextMenu(null);
                            }}
                        >
                            <Trash className="w-3 h-3" />
                            <span>Delete {contextMenu.target.type === 'polygon' ? 'Polygon' : 'Load'}</span>
                        </button>
                    )}
                </div>
            )}
        </div >
    );
};
