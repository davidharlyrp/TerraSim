import React, { useMemo, useState, useEffect, useRef } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrthographicCamera, OrbitControls, Grid, Line, Html } from '@react-three/drei';
import * as THREE from 'three';
import { MeshResponse, SolverResponse, OutputType, PhaseRequest, PolygonData, Material, GeneralSettings } from '../types';
import { MathRender } from './Math';
import { ChevronDown } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

interface OutputCanvasProps {
    mesh: MeshResponse | null;
    polygon: PolygonData[];
    solverResult: SolverResponse | null;
    currentPhaseIdx: number;
    phases: PhaseRequest[];
    showControls?: boolean;
    ignorePhases?: boolean;
    generalSettings: GeneralSettings;
    materials: Material[];
    beamMaterials: any[]; // NEW
}

interface PolygonProps {
    data: PolygonData;
}

// Helper to map 0-1 to Rainbow Color (Blue -> Cyan -> Green -> Yellow -> Red)
const getJetColor = (v: number) => {
    const t = Math.max(0, Math.min(1, v));
    // Simple segmented interpolation for Jet-like scale
    if (t < 0.125) return [0, 0, 0.5 + 4 * t]; // Dark Blue to Blue
    if (t < 0.375) return [0, 4 * (t - 0.125), 1]; // Blue to Cyan
    if (t < 0.625) return [4 * (t - 0.375), 1, 1 - 4 * (t - 0.375)]; // Cyan to Yellow
    if (t < 0.875) return [1, 1 - 4 * (t - 0.625), 0]; // Yellow to Red
    return [1.0 - 0.5 * (t - 0.875), 0, 0]; // Red to Dark Red
};

// User Request: Negative (min) = Red, Positive (max) = Blue
const getStressColor = (v: number) => {
    // Invert the Jet color mapping
    return getJetColor(1 - v);
};

// const BoundaryOverlay = ({
//     mesh,
//     phaseResult,
//     phaseRequest,
//     deformationScale,
//     prevPhaseResult,
//     beamMaterials
// }: {
//     mesh: MeshResponse,
//     phaseResult: any,
//     phaseRequest: PhaseRequest,
//     deformationScale: number,
//     prevPhaseResult: any,
//     beamMaterials: any[]
// }) => {
//     const { fixedPositions, rollerPositions } = useMemo(() => {
//         const fixed: number[] = [];
//         const roller: number[] = [];

//         // Helper to get deformed pos
//         const getDeformedPos = (nIdx: number) => {
//             let x = mesh.nodes[nIdx][0];
//             let y = mesh.nodes[nIdx][1];
//             if (phaseResult) {
//                 const d = phaseResult.displacements.find((d: any) => d.id === nIdx + 1);
//                 if (d) {
//                     const resetVisual = phaseRequest?.reset_displacements || false;
//                     let dx = d.ux;
//                     let dy = d.uy;
//                     if (resetVisual && prevPhaseResult) {
//                         const dPrev = prevPhaseResult.displacements.find((d: any) => d.id === nIdx + 1);
//                         if (dPrev) {
//                             dx -= dPrev.ux;
//                             dy -= dPrev.uy;
//                         }
//                     }
//                     x += dx * deformationScale;
//                     y += dy * deformationScale;
//                 }
//             }
//             return [x, y, 0.01]; // Slight Z offset
//         };

//         if (mesh.boundary_conditions) {
//             mesh.boundary_conditions.full_fixed.forEach(bc => {
//                 const [x, y, z] = getDeformedPos(bc.node);
//                 fixed.push(x, y, z);
//             });
//             mesh.boundary_conditions.normal_fixed.forEach(bc => {
//                 const [x, y, z] = getDeformedPos(bc.node);
//                 roller.push(x, y, z);
//             });
//         }

//         return {
//             fixedPositions: new Float32Array(fixed),
//             rollerPositions: new Float32Array(roller)
//         };
//     }, [mesh, phaseResult, deformationScale, phaseRequest, prevPhaseResult, beamMaterials]);

//     return (
//         <group>
//             {/* Full Fixed - Red Squares */}
//             {fixedPositions.length > 0 && (
//                 <points>
//                     <bufferGeometry>
//                         <bufferAttribute
//                             attach="attributes-position"
//                             count={fixedPositions.length / 3}
//                             array={fixedPositions}
//                             itemSize={3}
//                             args={[fixedPositions, 3]}
//                         />
//                     </bufferGeometry>
//                     <pointsMaterial color="red" size={6} sizeAttenuation={false} />
//                 </points>
//             )}
//             {/* Roller - Orange Circles */}
//             {rollerPositions.length > 0 && (
//                 <points>
//                     <bufferGeometry>
//                         <bufferAttribute
//                             attach="attributes-position"
//                             count={rollerPositions.length / 3}
//                             array={rollerPositions}
//                             itemSize={3}
//                             args={[rollerPositions, 3]}
//                         />
//                     </bufferGeometry>
//                     <pointsMaterial color="orange" size={5} sizeAttenuation={false} />
//                 </points>
//             )}
//         </group>
//     );
// };

const EmbeddedBeamOverlay = ({
    mesh,
    phaseResult,
    phaseRequest,
    deformationScale,
    prevPhaseResult,
    beamMaterials
}: {
    mesh: MeshResponse,
    phaseResult: any,
    phaseRequest: PhaseRequest,
    deformationScale: number,
    prevPhaseResult: any,
    beamMaterials: any[]
}) => {
    const lines = useMemo(() => {
        if (!mesh.embedded_beam_assignments) return [];

        return mesh.embedded_beam_assignments.map((assignment) => {
            const pts: THREE.Vector3[] = assignment.nodes.map(nIdxBase1 => {
                const nIdx = nIdxBase1 - 1;
                let x = mesh.nodes[nIdx][0];
                let y = mesh.nodes[nIdx][1];

                if (phaseResult) {
                    const d = phaseResult.displacements.find((d: any) => d.id === nIdx + 1);
                    if (d) {
                        const resetVisual = phaseRequest?.reset_displacements || false;
                        let dx = d.ux;
                        let dy = d.uy;
                        if (resetVisual && prevPhaseResult) {
                            const dPrev = prevPhaseResult.displacements.find((d: any) => d.id === nIdx + 1);
                            if (dPrev) {
                                dx -= dPrev.ux;
                                dy -= dPrev.uy;
                            }
                        }
                        x += dx * deformationScale;
                        y += dy * deformationScale;
                    }
                }
                return new THREE.Vector3(x, y, 0.05); // Higher Z than BCs but lower than labels
            });

            // Find material color
            const beamInstance = (phaseRequest as any).embedded_beams?.find((b: any) => b.id === assignment.beam_id);
            const bMat = beamMaterials.find(m => m.id === beamInstance?.materialId);
            const color = bMat?.color || "#f59e0b";
            const isActive = phaseRequest?.active_beam_ids?.includes(assignment.beam_id);

            return { pts, color, id: assignment.beam_id, isActive };
        });
    }, [mesh, phaseResult, deformationScale, phaseRequest, prevPhaseResult, beamMaterials]);

    return (
        <group>
            {lines.map((line, i) => (
                <Line
                    key={i}
                    points={line.pts}
                    color={line.isActive ? line.color : "#94a3b8"}
                    lineWidth={2}
                    dashed={!line.isActive}
                    frustumCulled={false}
                />
            ))}
        </group>
    );
};

const MeshResult = ({
    mesh,
    solverResult,
    currentPhaseIdx,
    phases,
    deformationScale,
    outputType,
    onValueRangeChange,
    ignorePhases = false,
    materials, // NEW
    beamMaterials
}: {
    mesh: MeshResponse,
    solverResult: SolverResponse | null,
    currentPhaseIdx: number,
    phases: PhaseRequest[],
    deformationScale: number,
    outputType: OutputType,
    onValueRangeChange: (min: number, max: number, label: React.ReactNode) => void,
    ignorePhases?: boolean,
    materials: Material[],
    beamMaterials: any[]
}) => {
    // ... existing MeshResult logic ...
    const { positions, colors, wireframePositions, rangeData } = useMemo(() => {
        if (!mesh) return {
            positions: new Float32Array(0),
            indices: new Uint32Array(0),
            colors: new Float32Array(0),
            wireframePositions: new Float32Array(0),
            rangeData: { min: 0, max: 0, label: "" }
        };

        const phaseResult = solverResult?.phases?.[currentPhaseIdx];
        const phaseRequest = phases[currentPhaseIdx];
        const activePolygons = new Set(phaseRequest?.active_polygon_indices || []);
        const currentMaterialMap = phaseRequest?.current_material || {}; // Get current material state

        const isSolidMaterial = outputType === OutputType.DEFORMED_MESH;

        // Find active elements (logic unchanged)
        const activeElementIndices: number[] = [];
        mesh.elements.forEach((_, i) => {
            const elemMaterial = mesh.element_materials[i];
            const isMeshActive = ignorePhases || (elemMaterial && (elemMaterial.polygon_id === undefined || activePolygons.has(elemMaterial.polygon_id)));
            if (isMeshActive) {
                activeElementIndices.push(i);
            }
        });

        // Helper to get deformed position (unchanged)
        const getDeformedPos = (nIdx: number) => {
            let x = mesh.nodes[nIdx][0];
            let y = mesh.nodes[nIdx][1];
            if (phaseResult) {
                const d = phaseResult.displacements.find(d => d.id === nIdx + 1);
                if (d) {
                    const resetVisual = phaseRequest?.reset_displacements || false;
                    const parentPhaseResult = currentPhaseIdx > 0 ? solverResult?.phases?.[currentPhaseIdx - 1] : null;
                    let dx = d.ux;
                    let dy = d.uy;
                    if (resetVisual && parentPhaseResult) {
                        const pd = parentPhaseResult.displacements.find(pd => pd.id === nIdx + 1);
                        if (pd) {
                            dx -= pd.ux;
                            dy -= pd.uy;
                        }
                    }
                    x += dx * deformationScale;
                    y += dy * deformationScale;
                }
            }
            return [x, y, 0];
        };

        if (isSolidMaterial) {
            // 1 Triangle per element for solid materials (efficiency + clean edges)
            const pos = new Float32Array(activeElementIndices.length * 3 * 3);
            const col = new Float32Array(activeElementIndices.length * 3 * 3);
            const wfPos = new Float32Array(activeElementIndices.length * 6 * 2 * 3); // 6 outer segments

            activeElementIndices.forEach((elemIdx, i) => {
                const elem = mesh.elements[elemIdx];
                const elemMatInfo = mesh.element_materials[elemIdx];

                // Determine effective material
                let mat = elemMatInfo?.material;
                if (!ignorePhases && elemMatInfo?.polygon_id !== undefined && elemMatInfo.polygon_id !== null) {
                    const overrideId = currentMaterialMap[elemMatInfo.polygon_id];
                    if (overrideId) {
                        const foundMat = materials.find(m => m.id === overrideId);
                        if (foundMat) mat = foundMat;
                    }
                }

                const mColor = mat?.color ? new THREE.Color(mat.color) : new THREE.Color(0.23, 0.51, 0.96);

                const [n1, n2, n3, n12, n23, n31] = elem;

                // Fill: Use standard 3 corner nodes for a solid triangle
                const triNodes = [n1, n2, n3];
                triNodes.forEach((nIdx, vIdx) => {
                    const dPos = getDeformedPos(nIdx);
                    const baseIdx = (i * 3 + vIdx) * 3;
                    pos[baseIdx] = dPos[0];
                    pos[baseIdx + 1] = dPos[1];
                    pos[baseIdx + 2] = dPos[2];
                    col[baseIdx] = mColor.r;
                    col[baseIdx + 1] = mColor.g;
                    col[baseIdx + 2] = mColor.b;
                });

                // Wireframe: 6 outer segments forming the quadratic boundary (visualized linearly)
                const wfEdges = [[n1, n12], [n12, n2], [n2, n23], [n23, n3], [n3, n31], [n31, n1]];
                wfEdges.forEach((edge, eIdx) => {
                    const p1 = getDeformedPos(edge[0]);
                    const p2 = getDeformedPos(edge[1]);
                    const baseIdx = (i * 6 + eIdx) * 6;
                    wfPos[baseIdx] = p1[0]; wfPos[baseIdx + 1] = p1[1]; wfPos[baseIdx + 2] = p1[2];
                    wfPos[baseIdx + 3] = p2[0]; wfPos[baseIdx + 4] = p2[1]; wfPos[baseIdx + 5] = p2[2];
                });
            });

            return {
                positions: pos,
                indices: new Uint32Array(0),
                colors: col,
                wireframePositions: wfPos,
                rangeData: { min: 0, max: 0, label: "" }
            };
        } else {
            // NEW: Define helper at top level of useMemo scope
            const getStressValue = (s: any) => {
                const p_steady = s.pwp_steady || 0;
                const p_excess = s.pwp_excess || 0;
                const p_total = s.pwp_total || 0;
                if (outputType === OutputType.PWP_STEADY) return p_steady;
                if (outputType === OutputType.PWP_EXCESS) return p_excess;
                if (outputType === OutputType.PWP_TOTAL) return p_total;

                if (outputType === OutputType.STRAIN_1 || outputType === OutputType.STRAIN_3) {
                    const exx = s.eps_xx || 0;
                    const eyy = s.eps_yy || 0;
                    const exy = s.eps_xy || 0;
                    const center = (exx + eyy) / 2;
                    const radius = Math.sqrt(Math.pow((exx - eyy) / 2, 2) + Math.pow(exy, 2));
                    return outputType === OutputType.STRAIN_1 ? center + radius : center - radius;
                }

                const avg = (s.sig_xx + s.sig_yy) / 2;
                const diff = (s.sig_xx - s.sig_yy) / 2;
                const radius = Math.sqrt(diff * diff + s.sig_xy * s.sig_xy);
                if (outputType === OutputType.SIGMA_1) return avg - radius;
                if (outputType === OutputType.SIGMA_3) return avg + radius;
                if (outputType === OutputType.SIGMA_1_EFF) return (avg - radius) - p_total;
                if (outputType === OutputType.SIGMA_3_EFF) return (avg + radius) - p_total;
                return 0;
            };

            const polygonGroups = new Map<number, number[]>();
            activeElementIndices.forEach(elemIdx => {
                const mat = mesh.element_materials[elemIdx];
                const polyId = mat?.polygon_id ?? -1;
                if (!polygonGroups.has(polyId)) polygonGroups.set(polyId, []);
                polygonGroups.get(polyId)!.push(elemIdx);
            });

            const groupNodeValues = new Map<number, Map<number, number>>();
            let currentLabel: React.ReactNode = "";

            if (outputType === OutputType.PWP_STEADY) currentLabel = <span className="flex items-center gap-1">PWP Steady <MathRender tex="(kN/m^2)" /></span>;
            else if (outputType === OutputType.PWP_EXCESS) currentLabel = <span className="flex items-center gap-1">PWP Excess <MathRender tex="(kN/m^2)" /></span>;
            else if (outputType === OutputType.PWP_TOTAL) currentLabel = <span className="flex items-center gap-1">PWP Total <MathRender tex="(kN/m^2)" /></span>;
            else if (outputType === OutputType.SIGMA_1) currentLabel = <span className="flex items-center gap-1"><MathRender tex="\sigma_1" /> <MathRender tex="(kN/m^2)" /></span>;
            else if (outputType === OutputType.SIGMA_3) currentLabel = <span className="flex items-center gap-1"><MathRender tex="\sigma_3" /> <MathRender tex="(kN/m^2)" /></span>;
            else if (outputType === OutputType.SIGMA_1_EFF) currentLabel = <span className="flex items-center gap-1"><MathRender tex="\sigma'_1" /> <MathRender tex="(kN/m^2)" /></span>;
            else if (outputType === OutputType.SIGMA_3_EFF) currentLabel = <span className="flex items-center gap-1"><MathRender tex="\sigma'_3" /> <MathRender tex="(kN/m^2)" /></span>;
            else if (outputType === OutputType.STRAIN_1) currentLabel = <span className="flex items-center gap-1"><MathRender tex="\epsilon_1" /></span>;
            else if (outputType === OutputType.STRAIN_3) currentLabel = <span className="flex items-center gap-1"><MathRender tex="\epsilon_3" /></span>;

            const stressMap = new Map<number, any>();
            phaseResult?.stresses.forEach(s => stressMap.set(s.element_id, s));
            const dispMap = new Map<number, any>();
            phaseResult?.displacements.forEach(d => dispMap.set(d.id, d));
            const parentDispMap = new Map<number, any>();
            const isReset = phaseRequest?.reset_displacements || false;
            if (isReset && currentPhaseIdx > 0) {
                solverResult?.phases?.[currentPhaseIdx - 1]?.displacements.forEach(d => parentDispMap.set(d.id, d));
            }

            // Loop for Smoothing to Nodes
            polygonGroups.forEach((elemIndices, polyId) => {
                const localValues = new Map<number, number>();
                const localWeights = new Map<number, number>();
                elemIndices.forEach(eIdx => {
                    const elem = mesh.elements[eIdx];
                    const s = stressMap.get(eIdx + 1);
                    if (outputType === OutputType.DEFORMED_CONTOUR) {
                        elem.forEach(nIdx => {
                            const d = dispMap.get(nIdx + 1);
                            if (d) {
                                const isReset = phaseRequest?.reset_displacements || false;
                                const parentPhaseResult = currentPhaseIdx > 0 ? solverResult?.phases?.[currentPhaseIdx - 1] : null;

                                let dx = d.ux; let dy = d.uy;
                                if (isReset && parentPhaseResult) {
                                    const pd = parentPhaseResult.displacements.find((pd: any) => pd.id === d.id);
                                    if (pd) { dx -= pd.ux; dy -= pd.uy; }
                                }
                                let val = Math.sqrt(dx * dx + dy * dy);

                                localValues.set(nIdx, (localValues.get(nIdx) || 0) + val);
                                localWeights.set(nIdx, (localWeights.get(nIdx) || 0) + 1);
                            }
                        });
                        currentLabel = "Displacement (m)";
                    } else if (outputType === OutputType.DEFORMED_CONTOUR_UX) {
                        elem.forEach(nIdx => {
                            const d = dispMap.get(nIdx + 1);
                            if (d) {
                                const isReset = phaseRequest?.reset_displacements || false;
                                const parentPhaseResult = currentPhaseIdx > 0 ? solverResult?.phases?.[currentPhaseIdx - 1] : null;

                                let dx = d.ux;
                                if (isReset && parentPhaseResult) {
                                    const pd = parentPhaseResult.displacements.find((pd: any) => pd.id === d.id);
                                    if (pd) { dx -= pd.ux; }
                                }
                                let val = Math.sqrt(dx * dx);

                                localValues.set(nIdx, (localValues.get(nIdx) || 0) + val);
                                localWeights.set(nIdx, (localWeights.get(nIdx) || 0) + 1);
                            }
                        });
                        currentLabel = "Displacement ux (m)";
                    } else if (outputType === OutputType.DEFORMED_CONTOUR_UY) {
                        elem.forEach(nIdx => {
                            const d = dispMap.get(nIdx + 1);
                            if (d) {
                                const isReset = phaseRequest?.reset_displacements || false;
                                const parentPhaseResult = currentPhaseIdx > 0 ? solverResult?.phases?.[currentPhaseIdx - 1] : null;

                                let dy = d.uy;
                                if (isReset && parentPhaseResult) {
                                    const pd = parentPhaseResult.displacements.find((pd: any) => pd.id === d.id);
                                    if (pd) { dy -= pd.uy; }
                                }
                                let val = Math.sqrt(dy * dy);

                                localValues.set(nIdx, (localValues.get(nIdx) || 0) + val);
                                localWeights.set(nIdx, (localWeights.get(nIdx) || 0) + 1);
                            }
                        });
                        currentLabel = "Displacement uy (m)";
                    } else if (s) {
                        const val = outputType === OutputType.YIELD_STATUS ? (s.is_yielded ? 1 : 0) : getStressValue(s);
                        if (outputType === OutputType.YIELD_STATUS) currentLabel = "Yield Status";
                        elem.forEach(nIdx => {
                            localValues.set(nIdx, (localValues.get(nIdx) || 0) + val);
                            localWeights.set(nIdx, (localWeights.get(nIdx) || 0) + 1);
                        });
                    }
                });
                localWeights.forEach((w, nIdx) => {
                    localValues.set(nIdx, (localValues.get(nIdx) || 0) / w);
                });
                groupNodeValues.set(polyId, localValues);
            });

            // Calculate Extrema
            // NEW STRATEGY: For flat shading, use min/max of AVERAGED triangle values (not raw GP values)
            // This better represents what's actually displayed
            let min = Infinity, max = -Infinity;

            // NEW: Flat-shaded subdivision approach
            // Each element subdivided into ~15 small triangles connecting nodes, GPs, and centroid
            // Estimate: 15 triangles per element * 3 vertices * 3 floats (x,y,z)
            const TRIS_PER_ELEM = 15;
            const pos = new Float32Array(activeElementIndices.length * TRIS_PER_ELEM * 3 * 3);
            const col = new Float32Array(activeElementIndices.length * TRIS_PER_ELEM * 3 * 3);
            const wfPos = new Float32Array(activeElementIndices.length * 6 * 2 * 3);

            // Gauss Point natural coordinates for tri-6 (standard 3-point integration)
            const GP_NAT_COORDS = [
                [1 / 6, 1 / 6],   // GP1
                [2 / 3, 1 / 6],   // GP2
                [1 / 6, 2 / 3]    // GP3
            ];

            // Shape functions for tri-6 at natural coordinates (r, s)
            const shapeFunctions = (r: number, s: number) => {
                const t = 1 - r - s;
                return [
                    t * (2 * t - 1),      // N1 (corner)
                    r * (2 * r - 1),      // N2 (corner)
                    s * (2 * s - 1),      // N3 (corner)
                    4 * r * t,          // N12 (mid-side)
                    4 * r * s,          // N23 (mid-side)
                    4 * s * t           // N31 (mid-side)
                ];
            };

            // PASS 1: Calculate all averaged triangle values to find min/max
            const triangleData: Array<{
                p1: [number, number, number],
                p2: [number, number, number],
                p3: [number, number, number],
                avgVal: number
            }> = [];

            let activeElemInOrderIdx = 0;
            let rawMin = Infinity, rawMax = -Infinity; // Range for Legend (Pure values)

            polygonGroups.forEach((elemIndices, polyId) => {
                const localVals = groupNodeValues.get(polyId)!;

                elemIndices.forEach(eIdx => {
                    const elem = mesh.elements[eIdx];

                    // Get node positions and values
                    const nodePositions = elem.map(nIdx => getDeformedPos(nIdx)) as [number, number, number][];
                    const nodeValues = elem.map(nIdx => localVals.get(nIdx) || 0);

                    // Calculate GP positions and values
                    const gpPositions: [number, number, number][] = [];
                    const gpValues: number[] = [];

                    const stressInfo = stressMap.get(eIdx + 1);

                    GP_NAT_COORDS.forEach(([r, s], gpIdx) => {
                        const N = shapeFunctions(r, s);
                        let x = 0, y = 0, val = 0;

                        for (let i = 0; i < 6; i++) {
                            x += N[i] * nodePositions[i][0];
                            y += N[i] * nodePositions[i][1];
                            val += N[i] * nodeValues[i];
                        }

                        // For stress views, use actual GP value
                        if (outputType !== OutputType.DEFORMED_CONTOUR && outputType !== OutputType.DEFORMED_CONTOUR_UX && outputType !== OutputType.DEFORMED_CONTOUR_UY && outputType !== OutputType.YIELD_STATUS && stressInfo && phaseResult) {
                            const gpStress = phaseResult.stresses.find(s => s.element_id === eIdx + 1 && s.gp_id === gpIdx + 1);
                            if (gpStress) {
                                val = getStressValue(gpStress);
                            }
                        }

                        gpPositions.push([x, y, 0]);
                        gpValues.push(val);
                    });

                    // Calculate centroid position and value (average of GPs)
                    const centroidPos: [number, number, number] = [
                        (gpPositions[0][0] + gpPositions[1][0] + gpPositions[2][0]) / 3,
                        (gpPositions[0][1] + gpPositions[1][1] + gpPositions[2][1]) / 3,
                        0
                    ];
                    const centroidVal = (gpValues[0] + gpValues[1] + gpValues[2]) / 3;

                    // Helper to record triangle data
                    const recordTriangle = (
                        p1: [number, number, number], p2: [number, number, number], p3: [number, number, number],
                        v1: number, v2: number, v3: number
                    ) => {
                        const avgVal = (v1 + v2 + v3) / 3;
                        triangleData.push({ p1, p2, p3, avgVal });

                        // Update min/max based on AVERAGED values for coloring (Smooth Look)
                        if (outputType !== OutputType.YIELD_STATUS) {
                            if (avgVal < min) min = avgVal;
                            if (avgVal > max) max = avgVal;

                            // Update rawMin/rawMax based on RAW values for Legend (Accurate Extremes)
                            const triMin = Math.min(v1, v2, v3);
                            const triMax = Math.max(v1, v2, v3);
                            if (triMin < rawMin) rawMin = triMin;
                            if (triMax > rawMax) rawMax = triMax;
                        }
                    };

                    // Record all triangles
                    // Inner triangles (centroid to GPs)
                    recordTriangle(centroidPos, gpPositions[0], gpPositions[1], centroidVal, gpValues[0], gpValues[1]);
                    recordTriangle(centroidPos, gpPositions[1], gpPositions[2], centroidVal, gpValues[1], gpValues[2]);
                    recordTriangle(centroidPos, gpPositions[2], gpPositions[0], centroidVal, gpValues[2], gpValues[0]);

                    // Outer triangles (GPs to nodes)
                    // Region 1 (around n1, connected to GP1)
                    recordTriangle(gpPositions[0], nodePositions[0], nodePositions[3], gpValues[0], nodeValues[0], nodeValues[3]);
                    recordTriangle(gpPositions[0], nodePositions[3], centroidPos, gpValues[0], nodeValues[3], centroidVal);
                    recordTriangle(gpPositions[0], centroidPos, nodePositions[5], gpValues[0], centroidVal, nodeValues[5]);
                    recordTriangle(gpPositions[0], nodePositions[5], nodePositions[0], gpValues[0], nodeValues[5], nodeValues[0]);

                    // Region 2 (around n2, connected to GP2)
                    recordTriangle(gpPositions[1], nodePositions[1], nodePositions[4], gpValues[1], nodeValues[1], nodeValues[4]);
                    recordTriangle(gpPositions[1], nodePositions[4], centroidPos, gpValues[1], nodeValues[4], centroidVal);
                    recordTriangle(gpPositions[1], centroidPos, nodePositions[3], gpValues[1], centroidVal, nodeValues[3]);
                    recordTriangle(gpPositions[1], nodePositions[3], nodePositions[1], gpValues[1], nodeValues[3], nodeValues[1]);

                    // Region 3 (around n3, connected to GP3)
                    recordTriangle(gpPositions[2], nodePositions[2], nodePositions[5], gpValues[2], nodeValues[2], nodeValues[5]);
                    recordTriangle(gpPositions[2], nodePositions[5], centroidPos, gpValues[2], nodeValues[5], centroidVal);
                    recordTriangle(gpPositions[2], centroidPos, nodePositions[4], gpValues[2], centroidVal, nodeValues[4]);
                    recordTriangle(gpPositions[2], nodePositions[4], nodePositions[2], gpValues[2], nodeValues[4], nodeValues[2]);
                });
            });

            if (min === Infinity) { min = 0; max = 0; }

            // Apply Noise Threshold Filters
            const NOISE_DISP = 1e-7; // 0.1 micrometer
            const NOISE_STRESS = 1e-3; // 1 Pa
            const NOISE_STRAIN = 1e-6; // 1 microstrain

            // Use the currentLabel from the outer scope or determine it here if needed for range display
            let currentThreshold;
            if (outputType === OutputType.DEFORMED_CONTOUR || outputType === OutputType.DEFORMED_CONTOUR_UX || outputType === OutputType.DEFORMED_CONTOUR_UY) {
                currentThreshold = NOISE_DISP;
            } else if (outputType === OutputType.STRAIN_1 || outputType === OutputType.STRAIN_3) {
                currentThreshold = NOISE_STRAIN;
            } else {
                currentThreshold = NOISE_STRESS;
            }

            if (outputType === OutputType.YIELD_STATUS) currentThreshold = 0;

            if (max - min < currentThreshold) {
                // Too small range -> Likely numerical noise. Clamp to neutral.
                min = 0;
                max = currentThreshold;
            }

            if (min === max) max = min + 1e-9;
            if (rawMin === Infinity) { rawMin = 0; rawMax = 0; } // Fallback for raw

            // PASS 2: Render all triangles with normalized colors
            let vPtr = 0;
            activeElemInOrderIdx = 0;

            let triIdx = 0;
            polygonGroups.forEach((elemIndices) => {
                elemIndices.forEach(eIdx => {
                    // Material color for Yield Status
                    const elemMatInfo = mesh.element_materials[eIdx];
                    let mat = elemMatInfo?.material;
                    if (!ignorePhases && elemMatInfo?.polygon_id !== undefined && elemMatInfo.polygon_id !== null) {
                        const overrideId = currentMaterialMap[elemMatInfo.polygon_id];
                        if (overrideId) {
                            const foundMat = materials.find(m => m.id === overrideId);
                            if (foundMat) mat = foundMat;
                        }
                    }
                    const mColor = mat?.color ? new THREE.Color(mat.color) : new THREE.Color(0.23, 0.51, 0.96);

                    const elem = mesh.elements[eIdx];
                    const [n1, n2, n3, n12, n23, n31] = elem;

                    // Render 15 triangles for this element
                    for (let i = 0; i < 15; i++) {
                        const tri = triangleData[triIdx++];

                        let rgb: number[];
                        if (outputType === OutputType.YIELD_STATUS) {
                            rgb = [mColor.r, mColor.g, mColor.b];
                        } else {
                            // Use AVERAGED min/max for smooth coloring (as requested)
                            const norm = (tri.avgVal - min) / (max - min);
                            rgb = outputType === OutputType.DEFORMED_CONTOUR || outputType === OutputType.DEFORMED_CONTOUR_UX || outputType === OutputType.DEFORMED_CONTOUR_UY ? getJetColor(norm) : getStressColor(norm);
                        }

                        // Add all 3 vertices with same color (flat shading)
                        [tri.p1, tri.p2, tri.p3].forEach(p => {
                            pos[vPtr * 3] = p[0];
                            pos[vPtr * 3 + 1] = p[1];
                            pos[vPtr * 3 + 2] = p[2];
                            col[vPtr * 3] = rgb[0];
                            col[vPtr * 3 + 1] = rgb[1];
                            col[vPtr * 3 + 2] = rgb[2];
                            vPtr++;
                        });
                    }

                    // Wireframe (outer boundary only)
                    const wfEdges = [[n1, n12], [n12, n2], [n2, n23], [n23, n3], [n3, n31], [n31, n1]];
                    wfEdges.forEach((edge, eInWfIdx) => {
                        const p1 = getDeformedPos(edge[0]);
                        const p2 = getDeformedPos(edge[1]);
                        const baseIdx = (activeElemInOrderIdx * 6 + eInWfIdx) * 6;
                        wfPos[baseIdx] = p1[0]; wfPos[baseIdx + 1] = p1[1]; wfPos[baseIdx + 2] = p1[2];
                        wfPos[baseIdx + 3] = p2[0]; wfPos[baseIdx + 4] = p2[1]; wfPos[baseIdx + 5] = p2[2];
                    });
                    activeElemInOrderIdx++;
                });
            });

            return {
                positions: pos,
                indices: new Uint32Array(0),
                colors: col,
                wireframePositions: wfPos,
                rangeData: { min: rawMin, max: rawMax, label: currentLabel } // Use RAW range for Legend
            };
        }
    }, [mesh, solverResult, currentPhaseIdx, phases, deformationScale, outputType, ignorePhases, materials, beamMaterials]);

    // Update range legend via effect
    React.useEffect(() => {
        onValueRangeChange(rangeData.min, rangeData.max, rangeData.label);
    }, [rangeData, onValueRangeChange]);

    if (!mesh) return null;

    return (
        <group>
            <mesh key={`solid-m-${currentPhaseIdx}-${outputType}`}>
                <bufferGeometry>
                    <bufferAttribute attach="attributes-position" args={[positions, 3]} />
                    <bufferAttribute attach="attributes-color" args={[colors, 3]} />
                </bufferGeometry>
                <meshBasicMaterial
                    vertexColors={true}
                    transparent
                    opacity={1}
                    side={THREE.DoubleSide}
                    polygonOffset
                    polygonOffsetFactor={1}
                />
            </mesh>

            {wireframePositions && (
                <lineSegments key={`wire-m-${currentPhaseIdx}-${outputType}`}>
                    <bufferGeometry>
                        <bufferAttribute attach="attributes-position" count={wireframePositions.length / 3} array={wireframePositions} itemSize={3} args={[wireframePositions, 3]} />
                    </bufferGeometry>
                    <lineBasicMaterial color="#d4d4d4" transparent opacity={0.4} />
                </lineSegments>
            )}

            <EmbeddedBeamOverlay
                mesh={mesh}
                phaseResult={solverResult?.phases?.[currentPhaseIdx]}
                phaseRequest={phases[currentPhaseIdx]}
                deformationScale={deformationScale}
                prevPhaseResult={currentPhaseIdx > 0 ? solverResult?.phases?.[currentPhaseIdx - 1] : null}
                beamMaterials={beamMaterials}
            />

            {/* <BoundaryOverlay
                mesh={mesh}
                phaseResult={solverResult?.phases?.[currentPhaseIdx]}
                phaseRequest={phases[currentPhaseIdx]}
                deformationScale={deformationScale}
                prevPhaseResult={currentPhaseIdx > 0 ? solverResult?.phases?.[currentPhaseIdx - 1] : null}
                beamMaterials={beamMaterials}
            /> */}
        </group>
    );
};

const Polygon = ({ data }: PolygonProps) => {
    const { points } = useMemo(() => {
        const shape = new THREE.Shape();
        const pts: THREE.Vector3[] = [];

        data.vertices.forEach((v, i) => {
            if (i === 0) shape.moveTo(v.x, v.y);
            else shape.lineTo(v.x, v.y);
            pts.push(new THREE.Vector3(v.x, v.y, 0.05));
        });

        shape.closePath();
        pts.push(pts[0]); // Close outline
        return { shape, points: pts };
    }, [data]);
    let lineColor = useTheme().theme === 'dark' ? 'white' : '#88909d';

    return (
        <group onContextMenu={(e) => { e.nativeEvent.preventDefault(); e.stopPropagation(); }}>
            {/* Outline */}
            <Line points={points} color={lineColor} lineWidth={2} />
        </group>
    );
};

const Legend = ({ min, max, label, visible, outputType }: { min: number, max: number, label: React.ReactNode, visible: boolean, outputType: OutputType }) => {
    if (!visible) return null;

    const formatValue = (val: number) => {
        if (Math.abs(val) < 0.001 && val !== 0) return val.toExponential(2);
        if (Math.abs(val) > 1000) return val.toFixed(0);
        return val.toFixed(3);
    };

    const isStressOrPwp = outputType !== OutputType.DEFORMED_CONTOUR && outputType !== OutputType.DEFORMED_CONTOUR_UX && outputType !== OutputType.DEFORMED_CONTOUR_UY;
    const gradient = isStressOrPwp
        ? 'linear-gradient(to right, #800000, #FF0000, #FFFF00, #00FFFF, #0000FF, #000080)'
        : 'linear-gradient(to right, #000080, #0000FF, #00FFFF, #FFFF00, #FF0000, #800000)';

    return (
        <div className="fixed bottom-5 right-0 left-0 mx-auto w-fit z-52 items-center justify-center flex flex-col bg-white/90 dark:bg-slate-900/90 backdrop-blur-md p-4 rounded-xl border border-slate-200 dark:border-slate-700 shadow-2xl text-slate-900 dark:text-white z-[20]">
            <div className="text-xs font-semibold mb-2 tracking-widest">{label}</div>
            <div className="flex items-center gap-3">
                <div className="text-[10px] font-mono text-slate-600 dark:text-slate-400">{formatValue(min)}</div>
                <div className="w-32 h-3 rounded-full border border-slate-900/20 dark:border-white/20" style={{ background: gradient }}></div>
                <div className="text-[10px] font-mono text-slate-600 dark:text-slate-400">{formatValue(max)}</div>
            </div>
        </div>
    );
};

export const OutputCanvas: React.FC<OutputCanvasProps> = ({
    mesh,
    polygon,
    solverResult,
    currentPhaseIdx,
    phases,
    showControls = true,
    ignorePhases = false,
    materials,
    beamMaterials
}) => {
    const [sliderValue, setSliderValue] = useState(100);
    const [outputType, setOutputType] = useState<OutputType>(OutputType.DEFORMED_CONTOUR);
    const [outputCategory, setOutputCategory] = useState<string>('deformed');
    const [range, setRange] = useState<{ min: number, max: number, label: React.ReactNode }>({ min: 0, max: 0, label: "" });
    const [showNodes, setShowNodes] = useState(false);
    const [showGaussPoints, setShowGaussPoints] = useState(false);
    const [showLog, setShowLog] = useState(false);
    const [showLogOnDesktop, setShowLogOnDesktop] = useState(true);


    useEffect(() => {
        if (outputType === OutputType.YIELD_STATUS) {
            setShowGaussPoints(true);
        }
    }, [outputType]);

    const scale = outputType === OutputType.DEFORMED_MESH ? sliderValue : 0;

    const logEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (logEndRef.current) {
            logEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [solverResult?.log]);

    const handleRangeChange = React.useCallback((min: number, max: number, label: React.ReactNode) => {
        setRange({ min, max, label });
    }, []);

    const { theme } = useTheme();
    const backgroundColor = theme === 'dark' ? "bg-slate-950" : "bg-slate-50";
    const categories = {
        deformed: {
            label: "Deformed View",
            types: [OutputType.DEFORMED_MESH, OutputType.DEFORMED_CONTOUR, OutputType.DEFORMED_CONTOUR_UX, OutputType.DEFORMED_CONTOUR_UY]
        },
        sigmaTotal: {
            label: "Principal Total Stress",
            types: [OutputType.SIGMA_1, OutputType.SIGMA_3]
        },
        sigmaEff: {
            label: "Principal Eff. Stress",
            types: [OutputType.SIGMA_1_EFF, OutputType.SIGMA_3_EFF]
        },
        pwp: {
            label: "Pore Water Pressure",
            types: [OutputType.PWP_STEADY, OutputType.PWP_EXCESS, OutputType.PWP_TOTAL]
        },
        strains: {
            label: "Principal Strains",
            types: [OutputType.STRAIN_1, OutputType.STRAIN_3]
        },
        yieldStatus: {
            label: "Yield Points",
            types: [OutputType.YIELD_STATUS]
        }
    };

    const isMobile = window.innerWidth < 768;

    const [hoveredItem, setHoveredItem] = useState<{
        type: 'node' | 'gp',
        id: number | string,
        position: [number, number, number],
        label: React.ReactNode
    } | null>(null);

    return (
        <div className={`w-full h-full ${backgroundColor} absolute inset-0 overflow-hidden`}>
            {showControls && (
                <div className="absolute top-4 left-10 right-4 z-16 w-64 flex mx-auto md:mx-0 flex-col gap-4">
                    {/* Control Panel */}
                    <div className="bg-white/90 dark:bg-slate-900/90 backdrop-blur-md md:p-5 p-2 px-5 rounded-xl border border-slate-200 dark:border-slate-700 shadow-2xl md:space-y-4 space-y-2 shrink-0">
                        <div>
                            <label className="block text-[10px] font-semibold text-slate-700 dark:text-slate-500 mb-2 tracking-widest">Output View</label>
                            <select
                                value={outputCategory}
                                onChange={(e) => {
                                    const cat = e.target.value;
                                    setOutputCategory(cat);
                                    // Set default type for category
                                    setOutputType(categories[cat as keyof typeof categories].types[0]);
                                }}
                                className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 text-xs p-2 rounded outline-none focus:border-blue-500 transition-colors cursor-pointer"
                            >
                                <option value="deformed">Deformation</option>
                                <option value="sigmaTotal">Principal Total Stress</option>
                                <option value="sigmaEff">Principal Eff. Stress</option>
                                <option value="strains">Principal Strains</option>
                                <option value="pwp">Pore Water Pressure</option>
                                <option value="yieldStatus">Yield Points</option>
                            </select>
                        </div>

                        {outputCategory === 'deformed' && (
                            <div className="space-y-3">
                                <div className="flex flex-col gap-2">
                                    <label className="flex items-center gap-2 cursor-pointer group">
                                        <input
                                            type="radio"
                                            name="deformedMode"
                                            checked={outputType === OutputType.DEFORMED_MESH}
                                            onChange={() => setOutputType(OutputType.DEFORMED_MESH)}
                                            className="w-3 h-3 accent-blue-500 cursor-pointer"
                                        />
                                        <span className="text-[10px] font-semibold text-slate-700 dark:text-slate-500 tracking-widest">Deformed Mesh</span>
                                    </label>
                                    <div className="flex items-center justify-between gap-2 border-t border-slate-200 dark:border-slate-800 pt-2">
                                        <label className="flex items-center gap-1.5 cursor-pointer group">
                                            <input
                                                type="radio"
                                                name="deformedMode"
                                                checked={outputType === OutputType.DEFORMED_CONTOUR}
                                                onChange={() => setOutputType(OutputType.DEFORMED_CONTOUR)}
                                                className="w-3 h-3 accent-blue-500 cursor-pointer"
                                            />
                                            <span className="text-[10px] font-semibold text-slate-700 dark:text-slate-500 tracking-widest">|u|</span>
                                        </label>
                                        <label className="flex items-center gap-1.5 cursor-pointer group">
                                            <input
                                                type="radio"
                                                name="deformedMode"
                                                checked={outputType === OutputType.DEFORMED_CONTOUR_UX}
                                                onChange={() => setOutputType(OutputType.DEFORMED_CONTOUR_UX)}
                                                className="w-3 h-3 accent-blue-500 cursor-pointer"
                                            />
                                            <span className="text-[10px] font-semibold text-slate-700 dark:text-slate-500 tracking-widest">ux</span>
                                        </label>
                                        <label className="flex items-center gap-1.5 cursor-pointer group">
                                            <input
                                                type="radio"
                                                name="deformedMode"
                                                checked={outputType === OutputType.DEFORMED_CONTOUR_UY}
                                                onChange={() => setOutputType(OutputType.DEFORMED_CONTOUR_UY)}
                                                className="w-3 h-3 accent-blue-500 cursor-pointer"
                                            />
                                            <span className="text-[10px] font-semibold text-slate-700 dark:text-slate-500 tracking-widest">uy</span>
                                        </label>
                                    </div>
                                </div>
                            </div>
                        )}

                        {outputCategory === 'sigmaTotal' && (
                            <div className='flex items-center justify-between gap-4 mx-2'>
                                <label className="flex items-center gap-2 cursor-pointer group">
                                    <input
                                        type="radio"
                                        name="sigmaTotalMode"
                                        checked={outputType === OutputType.SIGMA_1}
                                        onChange={() => setOutputType(OutputType.SIGMA_1)}
                                        className="w-3 h-3 accent-blue-500 cursor-pointer"
                                    />
                                    <label className="text-[10px] font-semibold text-slate-700 dark:text-slate-500 tracking-widest"><MathRender tex='\sigma_1'></MathRender></label>
                                </label>
                                <label className="flex items-center gap-2 cursor-pointer group">
                                    <input
                                        type="radio"
                                        name="sigmaTotalMode"
                                        checked={outputType === OutputType.SIGMA_3}
                                        onChange={() => setOutputType(OutputType.SIGMA_3)}
                                        className="w-3 h-3 accent-blue-500 cursor-pointer"
                                    />
                                    <label className="text-[10px] font-semibold text-slate-700 dark:text-slate-500 tracking-widest"><MathRender tex='\sigma_3'></MathRender></label>
                                </label>
                            </div>
                        )}

                        {outputCategory === 'sigmaEff' && (
                            <div className='flex items-center justify-between gap-4 mx-2'>
                                <label className="flex items-center gap-2 cursor-pointer group">
                                    <input
                                        type="radio"
                                        name="sigmaEffMode"
                                        checked={outputType === OutputType.SIGMA_1_EFF}
                                        onChange={() => setOutputType(OutputType.SIGMA_1_EFF)}
                                        className="w-3 h-3 accent-blue-500 cursor-pointer"
                                    />
                                    <label className="text-[10px] font-semibold text-slate-700 dark:text-slate-500 tracking-widest"><MathRender tex='\sigma_1^\prime'></MathRender></label>
                                </label>
                                <label className="flex items-center gap-2 cursor-pointer group">
                                    <input
                                        type="radio"
                                        name="sigmaEffMode"
                                        checked={outputType === OutputType.SIGMA_3_EFF}
                                        onChange={() => setOutputType(OutputType.SIGMA_3_EFF)}
                                        className="w-3 h-3 accent-blue-500 cursor-pointer"
                                    />
                                    <label className="text-[10px] font-semibold text-slate-700 dark:text-slate-500 tracking-widest"><MathRender tex='\sigma_3^\prime'></MathRender></label>
                                </label>
                            </div>
                        )}

                        {outputCategory === 'pwp' && (
                            <div className='grid grid-cols-2 gap-2'>
                                <label className="flex items-center gap-2 cursor-pointer group">
                                    <input
                                        type="radio"
                                        name="pwpMode"
                                        checked={outputType === OutputType.PWP_STEADY}
                                        onChange={() => setOutputType(OutputType.PWP_STEADY)}
                                        className="w-3 h-3 accent-blue-500 cursor-pointer"
                                    />
                                    <span className="text-[10px] font-semibold text-slate-700 dark:text-slate-500 tracking-widest"><MathRender tex='U_{hydrostatic}'></MathRender></span>
                                </label>
                                <label className="flex items-center gap-2 cursor-pointer group">
                                    <input
                                        type="radio"
                                        name="pwpMode"
                                        checked={outputType === OutputType.PWP_EXCESS}
                                        onChange={() => setOutputType(OutputType.PWP_EXCESS)}
                                        className="w-3 h-3 accent-blue-500 cursor-pointer"
                                    />
                                    <span className="text-[10px] font-semibold text-slate-700 dark:text-slate-500 tracking-widest"><MathRender tex='U_{excess}'></MathRender></span>
                                </label>
                                <label className="flex items-center gap-2 cursor-pointer group">
                                    <input
                                        type="radio"
                                        name="pwpMode"
                                        checked={outputType === OutputType.PWP_TOTAL}
                                        onChange={() => setOutputType(OutputType.PWP_TOTAL)}
                                        className="w-3 h-3 accent-blue-500 cursor-pointer"
                                    />
                                    <span className="text-[10px] font-semibold text-slate-700 dark:text-slate-500 tracking-widest"><MathRender tex='U_{total}'></MathRender></span>
                                </label>
                            </div>
                        )}

                        {outputCategory === 'strains' && (
                            <div className='flex items-center justify-between gap-4 mx-2'>
                                <label className="flex items-center gap-2 cursor-pointer group">
                                    <input
                                        type="radio"
                                        name="strainMode"
                                        checked={outputType === OutputType.STRAIN_1}
                                        onChange={() => setOutputType(OutputType.STRAIN_1)}
                                        className="w-3 h-3 accent-blue-500 cursor-pointer"
                                    />
                                    <label className="text-[10px] font-semibold text-slate-700 dark:text-slate-500 tracking-widest"><MathRender tex='\epsilon_1'></MathRender></label>
                                </label>
                                <label className="flex items-center gap-2 cursor-pointer group">
                                    <input
                                        type="radio"
                                        name="strainMode"
                                        checked={outputType === OutputType.STRAIN_3}
                                        onChange={() => setOutputType(OutputType.STRAIN_3)}
                                        className="w-3 h-3 accent-blue-500 cursor-pointer"
                                    />
                                    <label className="text-[10px] font-semibold text-slate-700 dark:text-slate-500 tracking-widest"><MathRender tex='\epsilon_3'></MathRender></label>
                                </label>
                            </div>
                        )}

                        {outputType === OutputType.DEFORMED_MESH && (
                            <div>
                                <div className="flex justify-between items-center mb-2">
                                    <label className="text-[10px] font-semibold text-slate-700 dark:text-slate-500 tracking-widest">Deformation Scale</label>
                                    <div className="flex items-center gap-2">
                                        <span className="text-[10px] font-mono bg-blue-100 dark:bg-blue-500/10 px-1.5 py-0.5 rounded text-blue-800 dark:text-blue-100">
                                            {scale < 10 ? scale.toFixed(2) : scale.toFixed(0)}x
                                        </span>
                                        <button
                                            onClick={() => setSliderValue(1)}
                                            className="text-[10px] text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors"
                                            title="Actual Scale"
                                        >
                                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                                            </svg>
                                        </button>
                                    </div>
                                </div>
                                <input
                                    type="range"
                                    min="0"
                                    max="1000"
                                    step="1"
                                    value={sliderValue}
                                    onChange={(e) => setSliderValue(Number(e.target.value))}
                                    className="w-full h-1.5 bg-slate-200 dark:bg-slate-800 rounded-lg appearance-none cursor-pointer accent-blue-500"
                                />
                            </div>
                        )}

                        {/* Point Display Toggles */}
                        <div className="pt-2 grid grid-cols-2 gap-2 items-center border-t border-slate-200 dark:border-slate-700">
                            <label className="flex items-center gap-2 cursor-pointer group">
                                <input
                                    type="checkbox"
                                    checked={showNodes}
                                    onChange={(e) => setShowNodes(e.target.checked)}
                                    className="w-3 h-3 accent-blue-500 cursor-pointer"
                                />
                                <span className="text-[10px] font-semibold text-slate-700 dark:text-slate-500 group-hover:text-slate-900 dark:group-hover:text-slate-300 transition-colors tracking-widest">
                                    Nodes
                                </span>
                            </label>
                            <label className="flex items-center gap-2 cursor-pointer group">
                                <input
                                    type="checkbox"
                                    checked={showGaussPoints}
                                    onChange={(e) => setShowGaussPoints(e.target.checked)}
                                    className="w-3 h-3 accent-blue-500 cursor-pointer"
                                />
                                <span className="text-[10px] font-semibold text-slate-700 dark:text-slate-500 group-hover:text-slate-900 dark:group-hover:text-slate-300 transition-colors tracking-widest">
                                    Gauss Points
                                </span>
                            </label>
                        </div>

                        {isMobile && (
                            <div className="">
                                <div className="flex items-center justify-between border-t py-2 border-slate-200 dark:border-slate-700">
                                    <label className="text-xs font-semibold text-slate-700 dark:text-slate-500 tracking-widest">Analysis Log Progress</label>
                                    <button
                                        onClick={() => setShowLog(!showLog)}
                                        className="text-[10px] text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors"
                                        title="Toggle Log"
                                    >
                                        <ChevronDown className={showLog ? 'rotate-180 w-4 h-4' : 'w-4 h-4'} />
                                    </button>
                                </div>
                                {showLog && solverResult && solverResult.log && (
                                    <div className="flex-1 overflow-y-auto p-2 font-mono text-[9px] max-h-[350px] text-slate-600 dark:text-slate-400 custom-scrollbar space-y-1">
                                        {solverResult.log.map((line, i) => (
                                            <div key={i} className="leading-relaxed border-b border-slate-200 dark:border-slate-800/50 pb-1 last:border-0 hover:text-slate-900 dark:hover:text-slate-200 transition-colors">
                                                {line}
                                            </div>
                                        ))}
                                        <div ref={logEndRef} />
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Log Panel */}
                    {!isMobile && solverResult && solverResult.log && (
                        <div className="bg-white/70 dark:bg-slate-900/90 backdrop-blur-md flex flex-col rounded-xl max-h-[600px] border border-slate-200 dark:border-slate-700 shadow-2xl overflow-y-hidden flex-1">
                            <div className="flex justify-between px-5 py-3 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/30">
                                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-500 tracking-widest">Analysis Log Progress</label>
                                <button
                                    onClick={() => setShowLogOnDesktop(!showLogOnDesktop)}
                                    className="cursor-pointer text-[10px] text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors"
                                    title="Toggle Log"
                                >
                                    <ChevronDown className={showLogOnDesktop ? 'rotate-180 w-4 h-4' : 'w-4 h-4'} />
                                </button>
                            </div>
                            {showLogOnDesktop && solverResult && solverResult.log && (
                                <div className="flex-1 overflow-y-auto p-5 font-mono text-[9px] text-slate-600 dark:text-slate-400 custom-scrollbar space-y-1 ">
                                    {solverResult.log.map((line, i) => (
                                        <div key={i} className="leading-relaxed border-b border-slate-200 dark:border-slate-800/50 pb-1 last:border-0 hover:text-slate-900 dark:hover:text-slate-200 transition-colors">
                                            {line}
                                        </div>
                                    ))}
                                    <div ref={logEndRef} />
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}

            <Legend
                min={range.min}
                max={range.max}
                label={range.label}
                visible={showControls && outputType !== OutputType.DEFORMED_MESH}
                outputType={outputType}
            />

            <Canvas>
                <OrthographicCamera makeDefault position={[0, 0, 90]} zoom={40} />
                <OrbitControls enableRotate={false} />
                <Grid position={[0, 0, -1]} args={[100, 100]} cellColor="gray" sectionColor="#475569" fadeDistance={50} />

                {outputType !== OutputType.DEFORMED_MESH && (
                    polygon.map((poly, i) => {
                        return (
                            <Polygon
                                key={i}
                                data={poly}
                            />
                        );
                    })
                )}

                {mesh && (
                    <>
                        <MeshResult
                            mesh={mesh}
                            solverResult={solverResult}
                            currentPhaseIdx={currentPhaseIdx}
                            phases={phases}
                            deformationScale={scale}
                            outputType={outputType}
                            onValueRangeChange={handleRangeChange}
                            ignorePhases={ignorePhases}
                            materials={materials}
                            beamMaterials={beamMaterials}
                        />

                        {/* Render Nodes if enabled */}
                        {showNodes && outputType !== OutputType.DEFORMED_MESH && (
                            <>
                                {mesh.nodes.map((node, i) => {
                                    // Calculate displacement for this node
                                    const nodeId = i + 1;
                                    let content: React.ReactNode = `Node ${nodeId}`;

                                    const phaseResult = solverResult?.phases?.[currentPhaseIdx];
                                    if (phaseResult) {
                                        const d = phaseResult.displacements.find(d => d.id === nodeId);
                                        if (d) {
                                            const total = Math.sqrt(d.ux ** 2 + d.uy ** 2);
                                            content = (
                                                <div className="text-[10px] w-30 bg-white dark:bg-slate-800 text-slate-900 dark:text-white p-2 rounded shadow-lg border border-slate-200 dark:border-slate-600">
                                                    <div className="font-bold border-b border-slate-200 dark:border-slate-600 mb-1">Node {nodeId}</div>
                                                    <div>Ux: {d.ux.toExponential(3)} m</div>
                                                    <div>Uy: {d.uy.toExponential(3)} m</div>
                                                    <div>|U|: {total.toExponential(3)} m</div>
                                                </div>
                                            );
                                        }
                                    }

                                    return (
                                        <mesh
                                            key={`node-${i}`}
                                            position={[node[0], node[1], 0.1]}
                                            onPointerOver={(e) => {
                                                if (outputType === OutputType.DEFORMED_CONTOUR || outputType === OutputType.DEFORMED_CONTOUR_UX || outputType === OutputType.DEFORMED_CONTOUR_UY) {
                                                    // No specific node value for these, just general info
                                                } else if (outputType === OutputType.STRAIN_1 || outputType === OutputType.STRAIN_3) {
                                                    // Strain values are at GPs, not directly at nodes in this context
                                                    // Could interpolate, but for now, no specific node strain value tooltip
                                                } else {
                                                    // Stress values are at GPs, not directly at nodes in this context
                                                    // Could interpolate, but for now, no specific node stress value tooltip
                                                }
                                                e.stopPropagation();
                                                setHoveredItem({
                                                    type: 'node',
                                                    id: nodeId,
                                                    position: [node[0], node[1], 0.1],
                                                    label: content
                                                });
                                            }}
                                        >
                                            <circleGeometry args={[0.02, 8]} />
                                            <meshBasicMaterial color="#ffffff" />
                                        </mesh>
                                    );
                                })}
                            </>
                        )}

                        {/* Render Gauss Points if enabled */}
                        {showGaussPoints && outputType !== OutputType.DEFORMED_MESH && (
                            <>
                                {mesh.elements.map((elem, elemIdx) => {
                                    // 6-node element: [n1, n2, n3, n4, n5, n6]
                                    // n4 is mid 1-2, n5 is mid 2-3, n6 is mid 3-1
                                    const nodes = elem.map(idx => mesh.nodes[idx]);

                                    // Find stress results for this element
                                    // Optimization: This search is O(N_results), could be slow for huge info.
                                    // Better to assume sorted or use map. For now simple find.
                                    const phaseRes = solverResult?.phases[currentPhaseIdx];
                                    if (!phaseRes) return null;

                                    // 3-point Gauss quadrature (Natural coords)
                                    const gaussPoints = [
                                        { xi: 1 / 6, eta: 1 / 6, id: 1 },
                                        { xi: 2 / 3, eta: 1 / 6, id: 2 },
                                        { xi: 1 / 6, eta: 2 / 3, id: 3 }
                                    ];

                                    return gaussPoints.map((gp, gpIdx) => {
                                        const { xi, eta } = gp;
                                        const zeta = 1 - xi - eta;

                                        // T6 Shape Functions
                                        const N1 = zeta * (2 * zeta - 1);
                                        const N2 = xi * (2 * xi - 1);
                                        const N3 = eta * (2 * eta - 1);
                                        const N4 = 4 * zeta * xi;
                                        const N5 = 4 * xi * eta;
                                        const N6 = 4 * eta * zeta;

                                        const N = [N1, N2, N3, N4, N5, N6];

                                        let x = 0, y = 0;
                                        for (let i = 0; i < 6; i++) {
                                            if (nodes[i]) {
                                                x += N[i] * nodes[i][0];
                                                y += N[i] * nodes[i][1];
                                            }
                                        }
                                        let gpColor = "#ffffff";

                                        // Dynamic coloring for Yield Status
                                        if (outputType === OutputType.YIELD_STATUS) {
                                            const sRes = phaseRes.stresses.find(s => s.element_id === elemIdx + 1 && s.gp_id === gpIdx + 1);
                                            if (sRes && sRes.is_yielded) {
                                                gpColor = "#ff0000"; // Red for Yield
                                            } else {
                                                gpColor = "#00ff00"; // Green for Elastic
                                            }
                                        }

                                        return (
                                            <mesh
                                                key={`gp-${elemIdx}-${gpIdx}`}
                                                position={[x, y, 0.12]}
                                                onPointerOver={(e) => {
                                                    e.stopPropagation();

                                                    // Find Value
                                                    let valLabel: React.ReactNode = null;

                                                    // Backend returns flat list of StressResult per GP
                                                    // We need to find the specific GP result
                                                    const sr_gp = phaseRes.stresses.find(s => s.element_id === elemIdx + 1 && s.gp_id === gpIdx + 1);

                                                    if (sr_gp) {
                                                        const { sig_xx, sig_yy, sig_xy, sig_zz, is_yielded, pwp_excess, pwp_steady, pwp_total } = sr_gp;

                                                        let title = `GP ${elemIdx + 1}.${gpIdx + 1}`;
                                                        let body = <></>;
                                                        let val = 0;

                                                        const s_avg = (sig_xx + sig_yy) / 2;
                                                        const R = Math.sqrt(Math.pow((sig_xx - sig_yy) / 2, 2) + Math.pow(sig_xy, 2));
                                                        const sigma1 = s_avg + R;
                                                        const sigma3 = s_avg - R;

                                                        if (outputType === OutputType.STRAIN_1 || outputType === OutputType.STRAIN_3) {
                                                            const exx = sr_gp.eps_xx || 0;
                                                            const eyy = sr_gp.eps_yy || 0;
                                                            const exy = sr_gp.eps_xy || 0;
                                                            const center = (exx + eyy) / 2;
                                                            const radius = Math.sqrt(Math.pow((exx - eyy) / 2, 2) + Math.pow(exy, 2));
                                                            val = outputType === OutputType.STRAIN_1 ? center + radius : center - radius;
                                                        } else {
                                                            val = (outputType === OutputType.SIGMA_1 || outputType === OutputType.SIGMA_1_EFF) ? sigma1 : sigma3;
                                                        }

                                                        switch (outputType) {
                                                            case OutputType.SIGMA_1:
                                                                title += " - Sigma 1 Total";
                                                                body = <div>{val.toFixed(3)} kPa</div>;
                                                                break;
                                                            case OutputType.SIGMA_3:
                                                                title += " - Sigma 3 Total";
                                                                body = <div>{val.toFixed(3)} kPa</div>;
                                                                break;
                                                            case OutputType.SIGMA_1_EFF:
                                                                title += " - Sigma 1 Effective";
                                                                body = <div>{(sigma1 - (pwp_total || 0)).toFixed(3)} kPa</div>;
                                                                break;
                                                            case OutputType.SIGMA_3_EFF:
                                                                title += " - Sigma 3 Effective";
                                                                body = <div>{(sigma3 - (pwp_total || 0)).toFixed(3)} kPa</div>;
                                                                break;
                                                            case OutputType.STRAIN_1:
                                                                title += " - Principal Strain 1";
                                                                body = <div>{(val * 100).toFixed(4)} %</div>;
                                                                break;
                                                            case OutputType.STRAIN_3:
                                                                title += " - Principal Strain 3";
                                                                body = <div>{(val * 100).toFixed(4)} %</div>;
                                                                break;
                                                            case OutputType.PWP_EXCESS:
                                                                title += " - PWP Excess";
                                                                body = <div>{(pwp_excess || 0).toFixed(3)} kPa</div>;
                                                                break;
                                                            case OutputType.PWP_STEADY:
                                                                title += " - PWP Steady";
                                                                body = <div>{(pwp_steady || 0).toFixed(3)} kPa</div>;
                                                                break;
                                                            case OutputType.PWP_TOTAL:
                                                                title += " - PWP Total";
                                                                body = <div>{(pwp_total || 0).toFixed(3)} kPa</div>;
                                                                break;
                                                            case OutputType.YIELD_STATUS:
                                                                title += " - Yield Status";
                                                                body = <div className={is_yielded ? "text-red-400 font-bold" : "text-green-400"}>{is_yielded ? "YIELDED" : "Elastic"}</div>;
                                                                break;
                                                            default:
                                                                body = (
                                                                    <div className="grid grid-cols-2 gap-x-2 gap-y-0.5">
                                                                        <span>σx:</span> <span className="text-right font-mono">{sig_xx.toExponential(2)}</span>
                                                                        <span>σy:</span> <span className="text-right font-mono">{sig_yy.toExponential(2)}</span>
                                                                        <span>τxy:</span> <span className="text-right font-mono">{sig_xy.toExponential(2)}</span>
                                                                        <span>σz:</span> <span className="text-right font-mono">{sig_zz.toExponential(2)}</span>
                                                                    </div>
                                                                );
                                                                break;
                                                        }

                                                        valLabel = (
                                                            <div className="text-[10px] bg-slate-800 text-white p-2 rounded shadow-lg border border-slate-600 min-w-[120px]">
                                                                <div className="font-bold border-b border-slate-600 mb-1 flex justify-between items-center">
                                                                    <span>{title}</span>
                                                                </div>
                                                                {body}
                                                            </div>
                                                        );
                                                    }

                                                    setHoveredItem({
                                                        type: 'gp',
                                                        id: `${elemIdx}-${gpIdx}`,
                                                        position: [x, y, 0.12],
                                                        label: valLabel
                                                    });
                                                }}
                                                onPointerOut={() => setHoveredItem(null)}
                                            >
                                                <circleGeometry args={[0.02, 8]} />
                                                <meshBasicMaterial color={gpColor} />
                                            </mesh>
                                        );
                                    });
                                })}
                            </>
                        )}

                        {/* Render Tooltip */}
                        {hoveredItem && (
                            <Html position={hoveredItem.position} style={{ pointerEvents: 'none' }} zIndexRange={[100, 0]}>
                                <div className="pointer-events-none transform -translate-x-1/2 -translate-y-[calc(100%+10px)]">
                                    {hoveredItem.label}
                                </div>
                            </Html>
                        )}
                    </>
                )}
            </Canvas>
        </div >
    );
};
