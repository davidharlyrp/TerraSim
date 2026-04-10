import React, { useState, useMemo, useRef } from 'react';
import { X, Download, Image as ImageIcon, ArrowLeftRight, ArrowUpDown } from 'lucide-react';
import { SolverResponse, TrackPoint, PhaseRequest } from '../types';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer } from 'recharts';
import * as htmlToImage from 'html-to-image';

interface CurveChartModalProps {
    isOpen: boolean;
    onClose: () => void;
    solverResult: SolverResponse | null;
    trackPoints: TrackPoint[];
    phases: PhaseRequest[];
}

export const CurveChartModal: React.FC<CurveChartModalProps> = ({ isOpen, onClose, solverResult, trackPoints, phases }) => {
    const [selectedX, setSelectedX] = useState<string>('step');
    const [selectedY, setSelectedY] = useState<string>('total_uy');
    const [selectedPointId, setSelectedPointId] = useState<string>(trackPoints[0]?.id || '');
    const [visiblePhases, setVisiblePhases] = useState<Set<string>>(new Set());
    const [flipX, setFlipX] = useState<boolean>(false);
    const [flipY, setFlipY] = useState<boolean>(false);

    const chartContainerRef = useRef<HTMLDivElement>(null);

    // Auto-update if tracking points change or selected point gets removed
    React.useEffect(() => {
        if (trackPoints.length > 0 && !trackPoints.find(p => p.id === selectedPointId)) {
            setSelectedPointId(trackPoints[0].id);
        }
    }, [trackPoints, selectedPointId]);

    const activePoint = trackPoints.find(p => p.id === selectedPointId);

    const chartPhases = useMemo(() => {
        if (!solverResult || !activePoint || !phases) return [];

        const phaseSegments: { id: string, name: string, data: any[] }[] = [];
        const base_steps: Record<string, number> = {};
        const base_mstages: Record<string, number> = {};
        const last_points: Record<string, any> = {};

        phases.forEach((p, pIdx) => {
            let c_step = 1; // start from 1
            let c_mstage = 0;
            let pData: any[] = [];

            if (p.parent_id) {
                c_step = base_steps[p.parent_id] || 1;
                c_mstage = base_mstages[p.parent_id] || 0;

                const lastPt = last_points[p.parent_id];
                if (lastPt) {
                    pData.push({
                        ...lastPt,
                        // Reset incremental/local phase variables to 0 for the start of the new phase
                        m_stage: 0,
                        raw_step: 0, // It's step 0 of the new phase locally
                        ux: 0,
                        uy: 0,
                        phase_name: p.name,
                        phase_id: p.id
                    });
                }
            }

            const phaseRes = solverResult.phases[pIdx];
            if (phaseRes && phaseRes.track_data && phaseRes.track_data[activePoint.id]) {
                const phaseRaw = phaseRes.track_data[activePoint.id];
                phaseRaw.forEach(d => {
                    const q = activePoint.type === 'gp' ? Math.sqrt(Math.pow(d.sig_xx - d.sig_yy, 2) + Math.pow(d.sig_yy - d.sig_zz, 2) + Math.pow(d.sig_zz - d.sig_xx, 2) + 6 * Math.pow(d.sig_xy, 2)) / Math.SQRT2 : 0;
                    const p_prime = activePoint.type === 'gp' ? (d.sig_xx + d.sig_yy + d.sig_zz) / 3 : 0;
                    const eps_v = activePoint.type === 'gp' ? (d.eps_xx + d.eps_yy) : 0;
                    const eps_q = activePoint.type === 'gp' ? (Math.SQRT2 / 3) * Math.sqrt(Math.pow(d.eps_xx - d.eps_yy, 2) + Math.pow(d.eps_yy, 2) + Math.pow(-d.eps_xx, 2) + 6 * Math.pow(d.eps_xy, 2)) : 0;

                    const u = activePoint.type === 'node' ? Math.sqrt(Math.pow(d.ux || 0, 2) + Math.pow(d.uy || 0, 2)) : 0;
                    const total_u = activePoint.type === 'node' ? Math.sqrt(Math.pow(d.total_ux || 0, 2) + Math.pow(d.total_uy || 0, 2)) : 0;

                    const newPt = {
                        ...d,
                        raw_step: d.step, // save local step if needed
                        step: c_step++,
                        sum_m_stage: c_mstage + d.m_stage,
                        phase_name: p.name,
                        phase_id: p.id,
                        q, p_prime, eps_v, eps_q,
                        u, total_u
                    };
                    pData.push(newPt);
                });

                if (pData.length > 0) {
                    last_points[p.id] = pData[pData.length - 1];
                    if (phaseRaw.length > 0) {
                        c_mstage += phaseRaw[phaseRaw.length - 1].m_stage;
                    }
                }
            }

            base_steps[p.id] = c_step;
            base_mstages[p.id] = c_mstage;

            if (pData.length > 0) {
                phaseSegments.push({
                    id: p.id,
                    name: p.name,
                    data: pData
                });
            }
        });

        return phaseSegments;
    }, [solverResult, activePoint, phases]);

    // Auto-select all phases initially
    React.useEffect(() => {
        if (phases.length > 0) {
            setVisiblePhases(new Set(phases.map(p => p.id)));
        }
    }, [phases]);

    if (!isOpen) return null;

    const availableVariables = activePoint?.type === 'node' ? [
        { key: 'step', label: 'Calculation Step (Continuous)' },
        { key: 'sum_m_stage', label: 'Sum M-Stage (Cumulative)' },
        { key: 'm_stage', label: 'Phase M-Stage (Load Multiplier)' },
        { key: 'raw_step', label: 'Phase Step ID (Local)' },
        { key: 'ux', label: 'Incremental Ux (m)' },
        { key: 'uy', label: 'Incremental Uy (m)' },
        { key: 'u', label: 'Incremental |U| (m)' },
        { key: 'total_ux', label: 'Total Displacement X (m)' },
        { key: 'total_uy', label: 'Total Displacement Y (m)' },
        { key: 'total_u', label: 'Total Displacement |U| (m)' },
    ] : [
        { key: 'step', label: 'Calculation Step (Continuous)' },
        { key: 'sum_m_stage', label: 'Sum M-Stage (Cumulative)' },
        { key: 'm_stage', label: 'Phase M-Stage (Load Multiplier)' },
        { key: 'raw_step', label: 'Phase Step ID (Local)' },
        { key: 'sig_xx', label: 'Effective Stress XX, σ\'xx (kPa)' },
        { key: 'sig_yy', label: 'Effective Stress YY, σ\'yy (kPa)' },
        { key: 'sig_zz', label: 'Effective Stress ZZ, σ\'zz (kPa)' },
        { key: 'sig_xy', label: 'Shear Stress XY, τxy (kPa)' },
        { key: 'p_prime', label: 'Mean Effective Stress, p\' (kPa)' },
        { key: 'q', label: 'Deviatoric Stress, q (kPa)' },
        { key: 'pwp_excess', label: 'Excess Pore Pressure (kPa)' },
        { key: 'eps_xx', label: 'Strain XX (εxx)' },
        { key: 'eps_yy', label: 'Strain YY (εyy)' },
        { key: 'eps_xy', label: 'Shear Strain (γxy)' },
        { key: 'eps_v', label: 'Volumetric Strain (εv)' },
        { key: 'eps_q', label: 'Deviatoric Strain (εq)' },
    ];

    const getXLabel = () => availableVariables.find(v => v.key === selectedX)?.label || selectedX;
    const getYLabel = () => availableVariables.find(v => v.key === selectedY)?.label || selectedY;

    const downloadCSV = () => {
        const activePhases = chartPhases.filter(p => visiblePhases.has(p.id));
        if (!activePhases.length) return;
        const allData = activePhases.map(p => p.data).flat();
        if (!allData.length) return;
        const keys = Object.keys(allData[0]);
        const header = keys.join(',');
        const rows = allData.map(row => keys.map(k => row[k]).join(',')).join('\n');
        const csv = `${header}\n${rows}`;
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `TerraSim_curve_data_${activePoint?.label}_${Date.now()}.csv`;
        a.click();
    };

    const exportPNG = async () => {
        if (!chartContainerRef.current) return;
        try {
            const dataUrl = await htmlToImage.toPng(chartContainerRef.current, {
                backgroundColor: document.documentElement.classList.contains('dark') ? '#020617' : '#ffffff',
                pixelRatio: 2
            });
            const a = document.createElement('a');
            a.href = dataUrl;
            a.download = `TerraSim_curve_chart_${activePoint?.label}_${Date.now()}.png`;
            a.click();
        } catch (error) {
            console.error('Failed to export chart as PNG', error);
        }
    };

    return (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-999 flex items-center justify-center p-4">
            <div className="bg-white dark:bg-slate-900 rounded-xl shadow-2xl w-full max-w-7xl h-[85vh] flex flex-col overflow-hidden border border-slate-200 dark:border-slate-800">

                {/* Header */}
                <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50 dark:bg-slate-900">
                    <div>
                        <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
                            Point History Plot
                        </h2>
                        <p className="text-sm text-slate-500 dark:text-slate-400">Generate X-Y plots from analysis history points</p>
                    </div>
                    <button onClick={onClose} className="cursor-pointer p-2 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-full transition-colors text-slate-500">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
                    {/* Left Sidebar - Controls */}
                    <div className="w-full lg:w-72 border-r border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 p-6 flex flex-col gap-6 overflow-y-auto custom-scrollbar">

                        {trackPoints.length === 0 ? (
                            <div className="text-sm text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 p-4 rounded-lg border border-amber-200 dark:border-amber-800/50">
                                You haven't selected any points yet. Use the "Select Points" tool to add nodes or Gauss points before generating curves.
                            </div>
                        ) : (
                            <>
                                {/* Point Selection */}
                                <div className="space-y-2">
                                    <label className="text-sm font-semibold text-slate-700 dark:text-slate-300">Selected Point</label>
                                    <select
                                        value={selectedPointId}
                                        onChange={(e) => setSelectedPointId(e.target.value)}
                                        className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                                    >
                                        {trackPoints.map(tp => (
                                            <option key={tp.id} value={tp.id}>Point {tp.label} ({tp.type === 'node' ? 'Node' : 'Stress Point'})</option>
                                        ))}
                                    </select>
                                </div>

                                {/* X-Axis Selection */}
                                <div className="space-y-2">
                                    <label className="text-sm font-semibold text-slate-700 dark:text-slate-300">X-Axis Variable</label>
                                    <select
                                        value={selectedX}
                                        onChange={(e) => setSelectedX(e.target.value)}
                                        className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                                    >
                                        {availableVariables.map(v => (
                                            <option key={v.key} value={v.key}>{v.label}</option>
                                        ))}
                                    </select>
                                </div>

                                {/* Y-Axis Selection */}
                                <div className="space-y-2">
                                    <label className="text-sm font-semibold text-slate-700 dark:text-slate-300">Y-Axis Variable</label>
                                    <select
                                        value={selectedY}
                                        onChange={(e) => setSelectedY(e.target.value)}
                                        className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                                    >
                                        {availableVariables.map(v => (
                                            <option key={v.key} value={v.key}>{v.label}</option>
                                        ))}
                                    </select>
                                </div>

                                {/* Flip Toggles */}
                                <div className="space-y-2">
                                    <label className="text-sm font-semibold text-slate-700 dark:text-slate-300">Axis Direction</label>
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => setFlipX(!flipX)}
                                            className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold border transition-colors ${flipX ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-400' : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700/50'}`}
                                            title="Flip X Axis"
                                        >
                                            <ArrowLeftRight className="w-3.5 h-3.5" />
                                            Flip X
                                        </button>
                                        <button
                                            onClick={() => setFlipY(!flipY)}
                                            className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold border transition-colors ${flipY ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-400' : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700/50'}`}
                                            title="Flip Y Axis"
                                        >
                                            <ArrowUpDown className="w-3.5 h-3.5" />
                                            Flip Y
                                        </button>
                                    </div>
                                </div>

                                {/* Phase Filter */}
                                {phases.length > 0 && (
                                    <div className="space-y-2">
                                        <label className="text-sm font-semibold text-slate-700 dark:text-slate-300">Phases</label>
                                        <div className="flex flex-col gap-2 max-h-80 overflow-y-auto pr-2">
                                            {phases.map((p) => (
                                                <label key={p.id} className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300 cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800 p-1.5 rounded-md transition-colors">
                                                    <input
                                                        type="checkbox"
                                                        checked={visiblePhases.has(p.id)}
                                                        onChange={(e) => {
                                                            const newSet = new Set(visiblePhases);
                                                            if (e.target.checked) newSet.add(p.id);
                                                            else newSet.delete(p.id);
                                                            setVisiblePhases(newSet);
                                                        }}
                                                        className="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                                                    />
                                                    <span>{p.name}</span>
                                                </label>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                <div className="mt-auto pt-6 border-t border-slate-200 dark:border-slate-800 flex flex-col gap-2">
                                    <button
                                        onClick={downloadCSV}
                                        disabled={chartPhases.length === 0}
                                        className="cursor-pointer w-full flex items-center justify-center gap-2 bg-slate-900 hover:bg-slate-800 dark:bg-slate-100 dark:hover:bg-white text-white dark:text-slate-900 px-4 py-2 text-sm font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm rounded-lg"
                                    >
                                        <Download className="w-4 h-4" />
                                        Export CSV Table
                                    </button>
                                    <button
                                        onClick={exportPNG}
                                        disabled={chartPhases.length === 0}
                                        className="cursor-pointer w-full flex items-center justify-center gap-2 bg-white hover:bg-slate-50 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 px-4 py-2 text-sm font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm rounded-lg"
                                    >
                                        <ImageIcon className="w-4 h-4" />
                                        Export Chart as PNG
                                    </button>
                                </div>
                            </>
                        )}
                    </div>

                    {/* Right Area - Chart */}
                    <div className="flex-1 p-6 flex flex-col bg-white dark:bg-slate-950 overflow-hidden">
                        {chartPhases.length > 0 ? (
                            <div className="flex-1 w-full h-full min-h-[400px]" ref={chartContainerRef}>
                                <ResponsiveContainer width="100%" height="100%">
                                    <LineChart
                                        margin={{ top: 20, right: 30, left: 50, bottom: 20 }}
                                    >
                                        <CartesianGrid strokeDasharray="3 3" stroke="#cbd5e1" opacity={0.5} />
                                        <XAxis
                                            dataKey={selectedX}
                                            type="number"
                                            domain={['auto', 'auto']}
                                            allowDuplicatedCategory={false}
                                            reversed={flipX}
                                            tickFormatter={(val) => val.toPrecision(3)}
                                            label={{ value: getXLabel(), position: 'bottom', offset: 0, fill: '#64748b', fontSize: 13, fontWeight: 500 }}
                                        />
                                        <YAxis
                                            domain={['auto', 'auto']}
                                            reversed={flipY}
                                            tickFormatter={(val) => val.toPrecision(3)}
                                            label={{ value: getYLabel(), angle: -90, position: 'left', offset: 30, fill: '#64748b', fontSize: 13, fontWeight: 500 }}
                                        />
                                        <RechartsTooltip
                                            contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                                            formatter={(value: any, name: any) => [Number(value).toPrecision(4), String(name)]}
                                        />
                                        <Legend verticalAlign="top" height={36} />
                                        {chartPhases.filter(p => visiblePhases.has(p.id)).map((phaseSegment) => {
                                            const globalIndex = chartPhases.findIndex(p => p.id === phaseSegment.id);
                                            return (
                                                <Line
                                                    key={phaseSegment.id}
                                                    data={phaseSegment.data}
                                                    type="monotone"
                                                    dataKey={selectedY}
                                                    name={phaseSegment.name}
                                                    stroke={['#ef4444', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'][globalIndex % 8]}
                                                    activeDot={{ r: 8 }}
                                                    strokeWidth={2}
                                                    dot={false}
                                                />
                                            );
                                        })}
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        ) : (
                            <div className="flex-1 flex items-center justify-center text-slate-400 dark:text-slate-600 border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-xl m-4">
                                {trackPoints.length > 0 ? "No data available. Run analysis first to populate curve points." : "Select Points to generate curves."}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};
