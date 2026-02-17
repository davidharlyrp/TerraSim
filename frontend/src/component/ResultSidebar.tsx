import React, { useState } from 'react';
import { SolverResponse, PhaseRequest, StepPoint, PhaseType } from '../types';
import { useTheme } from '../context/ThemeContext';
import { ChevronDown, CircleCheck, CircleMinus } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const PhaseChart = ({ points, isLive = false, isSafety = false }: { points: StepPoint[], isLive?: boolean, isSafety?: boolean }) => {
    if (!points || points.length < 2) return null;

    const { theme } = useTheme();
    const [isExpanded, setIsExpanded] = React.useState(false);
    const axisColor = theme === 'light' ? '#475569' : '#ffffff';
    const gridColor = theme === 'light' ? '#e2e8f0' : '#334155';
    const tooltipBg = theme === 'light' ? '#ffffff' : '#1e293b';
    const tooltipBorder = theme === 'light' ? '#e2e8f0' : '#334155';
    const tooltipText = theme === 'light' ? '#0f172a' : '#f8fafc';

    const chart = (
        <>
            <div className="h-40 w-full">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={points} margin={{ top: 5, right: 10, bottom: 2, left: -20 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                        <XAxis
                            dataKey="max_disp"
                            type="number"
                            domain={['auto', 'auto']}
                            fontSize={8}
                            stroke={axisColor}
                            tickFormatter={(v) => typeof v === 'number' ? v.toPrecision(2) : v}
                            label={{ value: 'Disp (m)', position: 'insideBottom', offset: 5, fontSize: 8, fill: axisColor }}
                        />
                        <YAxis
                            dataKey="m_stage"
                            domain={[0, 'auto']}
                            fontSize={8}
                            stroke={axisColor}
                            label={{ value: isSafety ? 'Σ Msf' : 'Mstage', angle: -90, position: 'insideLeft', offset: 25, fontSize: 8, fill: axisColor }}
                        />
                        <Tooltip
                            contentStyle={{ backgroundColor: tooltipBg, border: `1px solid ${tooltipBorder}`, borderRadius: '8px', fontSize: '9px', color: tooltipText }}
                            itemStyle={{ color: isLive ? '#60a5fa' : '#4ade80' }}
                            labelStyle={{ color: axisColor }}
                            formatter={(value: any) => [typeof value === 'number' ? value.toPrecision(4) : value, 'Value']}
                            labelFormatter={(value: any) => `Disp: ${typeof value === 'number' ? value.toPrecision(4) : value} m`}
                        />
                        <Line
                            type="monotone"
                            dataKey="m_stage"
                            stroke={isLive ? "#3b82f6" : "#22c55e"}
                            strokeWidth={2}
                            dot={{ r: 2, fill: isLive ? "#3b82f6" : "#22c55e", strokeWidth: 0 }}
                            activeDot={{ r: 4, stroke: axisColor, strokeWidth: 1 }}
                            isAnimationActive={false}
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </>
    )

    return (
        <div className="mt-2 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-200 dark:border-slate-700 animate-in fade-in zoom-in-95 duration-300">

            {isLive ? (
                <>
                    <div className="text-xs font-semibold py-2 tracking-widest text-center">
                        {isLive ? <span className="text-blue-400 animate-pulse">Running </span> : ''}
                        {isSafety ? 'Msf' : 'Mstage'} vs. Disp.
                    </div>
                    {chart}
                </>
            ) : (
                <>
                    <div className="w-full relative text-xs font-semibold py-2 tracking-widest text-center">
                        {isSafety ? 'Msf' : 'Mstage'} vs. Disp.
                        <button onClick={() => setIsExpanded(!isExpanded)} className="cursor-pointer absolute right-2 text-slate-400 dark:text-slate-500 hover:text-slate-900 dark:hover:text-white transition-colors">
                            <ChevronDown size={12} className={`transition ${isExpanded ? 'rotate-180' : ''}`} />
                        </button>
                    </div>
                    {isExpanded && (
                        <div className="h-40 w-full">
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={points} margin={{ top: 5, right: 10, bottom: 2, left: -20 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                                    <XAxis
                                        dataKey="max_disp"
                                        type="number"
                                        domain={['auto', 'auto']}
                                        fontSize={8}
                                        stroke={axisColor}
                                        tickFormatter={(v) => typeof v === 'number' ? v.toPrecision(2) : v}
                                        label={{ value: 'Disp (m)', position: 'insideBottom', offset: 5, fontSize: 8, fill: axisColor }}
                                    />
                                    <YAxis
                                        dataKey="m_stage"
                                        domain={[0, 'auto']}
                                        fontSize={8}
                                        stroke={axisColor}
                                        label={{ value: isSafety ? 'Σ Msf' : 'Mstage', angle: -90, position: 'insideLeft', offset: 25, fontSize: 8, fill: axisColor }}
                                    />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: tooltipBg, border: `1px solid ${tooltipBorder}`, borderRadius: '8px', fontSize: '9px', color: tooltipText }}
                                        itemStyle={{ color: isLive ? '#60a5fa' : '#4ade80' }}
                                        labelStyle={{ color: axisColor }}
                                        formatter={(value: any) => [typeof value === 'number' ? value.toPrecision(4) : value, 'Value']}
                                        labelFormatter={(value: any) => `Disp: ${typeof value === 'number' ? value.toPrecision(4) : value} m`}
                                    />
                                    <Line
                                        type="monotone"
                                        dataKey="m_stage"
                                        stroke={isLive ? "#3b82f6" : "#22c55e"}
                                        strokeWidth={2}
                                        dot={{ r: 2, fill: isLive ? "#3b82f6" : "#22c55e", strokeWidth: 0 }}
                                        activeDot={{ r: 4, stroke: axisColor, strokeWidth: 1 }}
                                        isAnimationActive={false}
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    )}
                </>
            )}
        </div>
    );
};


const ResultSummary = ({ phaseResult, prevPhaseResult, isReset, phaseType }: { phaseResult: any, prevPhaseResult?: any, isReset: boolean, phaseType?: PhaseType }) => {
    if (!phaseResult) return null;

    const summary = React.useMemo(() => {
        const dispMags = phaseResult.displacements.map((d: any) => {
            let ux = d.ux;
            let uy = d.uy;
            if (isReset && prevPhaseResult) {
                const pd = prevPhaseResult.displacements.find((p: any) => p.id === d.id);
                if (pd) {
                    ux -= pd.ux;
                    uy -= pd.uy;
                }
            }
            return Math.hypot(ux, uy);
        });

        const stresses = phaseResult.stresses.map((s: any) => {
            const avg = (s.sig_xx + s.sig_yy) / 2;
            const diff = (s.sig_xx - s.sig_yy) / 2;
            const radius = Math.hypot(diff, s.sig_xy);
            const s1 = avg - radius;
            const s3 = avg + radius;
            const pwp = s.pwp_total || 0;
            return { s1, s3, s1e: s1 - pwp, s3e: s3 - pwp, pwp, yielded: s.is_yielded };
        });

        const getExtrema = (arr: number[]) => ({ min: Math.min(...arr), max: Math.max(...arr) });

        return {
            disp: getExtrema(dispMags),
            s1: getExtrema(stresses.map((s: any) => s.s1)),
            s3: getExtrema(stresses.map((s: any) => s.s3)),
            s1e: getExtrema(stresses.map((s: any) => s.s1e)),
            s3e: getExtrema(stresses.map((s: any) => s.s3e)),
            pwp: getExtrema(stresses.map((s: any) => s.pwp)),
            yieldCount: stresses.filter((s: any) => s.yielded).length
        };
    }, [phaseResult, prevPhaseResult, isReset]);

    const CompactRow = ({ label, values, unit = "kN/m²" }: { label: string, values: { min: number, max: number }, unit?: string }) => (
        <div className="group flex justify-between items-center py-1.5 border-b border-slate-200 dark:border-slate-800/50 hover:bg-slate-100 dark:hover:bg-slate-800/30 transition-colors px-1 rounded">
            <span className="text-[10px] text-slate-600 dark:text-slate-400 font-medium">{label}</span>
            <div className="flex items-center gap-2 text-[10px] font-mono">
                <span className="text-rose-500 dark:text-rose-400/80">{values.min.toPrecision(3)}</span>
                <span className="text-slate-400 dark:text-slate-600">/</span>
                <span className="text-emerald-600 dark:text-emerald-400/80">{values.max.toPrecision(3)}</span>
                <span className="text-[9px] text-slate-500 ml-1 w-8 text-right underline decoration-slate-300 dark:decoration-slate-700">{unit}</span>
            </div>
        </div>
    );

    return (
        <div className="p-1 space-y-0.5 animate-in fade-in slide-in-from-bottom-2 duration-500">
            {!phaseResult.success && (
                <div className="mb-2 p-2 bg-rose-500/10 border-l-2 border-rose-500 flex items-center gap-2">
                    <span className="text-[9px] font-bold text-rose-500 uppercase">Failed</span>
                    <span className="text-[9px] text-rose-300 italic truncate">
                        Step {phaseResult.step_failed_at} (mS: {phaseResult.reached_m_stage?.toFixed(2)})
                    </span>
                </div>
            )}

            {phaseType === PhaseType.SAFETY_ANALYSIS && (
                <div className="group flex justify-between items-center py-1.5 border-b border-slate-200 dark:border-slate-800/50 hover:bg-slate-100 dark:hover:bg-slate-800/30 transition-colors px-1 rounded">
                    <span className="text-[10px] text-slate-600 dark:text-slate-400 font-medium">Safety Factor</span>
                    <div className="flex items-center gap-2 text-[10px] font-mono">
                        <span className="text-emerald-600 dark:text-emerald-400/80">{phaseResult.reached_m_stage?.toFixed(3)}</span>
                    </div>
                </div>
            )}
            <CompactRow label="Displacement" values={summary.disp} unit="m" />
            <CompactRow label="σ1 Total" values={summary.s1} />
            <CompactRow label="σ3 Total" values={summary.s3} />
            <CompactRow label="σ'1 Eff." values={summary.s1e} />
            <CompactRow label="σ'3 Eff." values={summary.s3e} />
            <CompactRow label="Total PWP" values={summary.pwp} />

            <div className="mt-2 pt-2 flex items-center justify-between border-t border-slate-800">
                <span className="text-[10px] text-slate-500 tracking-tighter">Yield Status</span>
                <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold ${summary.yieldCount > 0 ? 'bg-rose-500/20 text-rose-500' : 'bg-emerald-500/20 text-emerald-500'}`}>
                    {summary.yieldCount} <span className="font-normal opacity-70">points</span>
                </div>
            </div>
        </div>
    );
};

interface ResultSidebarProps {
    solverResult: SolverResponse | null;
    isRunning: boolean;
    onRun: () => void;
    onCancel: () => void;
    phases: PhaseRequest[];
    currentPhaseIdx: number;
    onSelectPhase: (idx: number) => void;
    liveStepPoints?: StepPoint[];
    runningPhaseIdx?: number;
}

export const ResultSidebar: React.FC<ResultSidebarProps> = ({
    solverResult, isRunning, onRun, onCancel, phases, currentPhaseIdx, onSelectPhase, liveStepPoints = [], runningPhaseIdx = 0
}) => {
    const isReset = phases[currentPhaseIdx]?.reset_displacements || false;
    const prevPhaseResult = currentPhaseIdx > 0 ? solverResult?.phases?.[currentPhaseIdx - 1] : null;
    const [ResultSidebarOpen, setResultSidebarOpen] = useState(true);
    const isMobile = window.innerWidth < 768;

    // Helper to process points for chart (User requested total displacement in chart)
    const processedPoints = React.useMemo(() => {
        return solverResult?.phases?.[currentPhaseIdx]?.step_points || [];
    }, [solverResult, currentPhaseIdx]);

    const processedLivePoints = React.useMemo(() => {
        return liveStepPoints;
    }, [liveStepPoints]);
    return (
        <div className={`absolute md:top-4 md:right-4 right-0 top-0 md:w-72 w-[calc(100%-40px)] overflow-y-hidden bg-white/95 dark:bg-slate-900/95 backdrop-blur-md md:border border-l border-slate-200 dark:border-slate-700 md:rounded-2xl shadow-2xl flex flex-col md:z-20 z-50 ${isMobile ? 'bottom-0' : ''}`}>
            <div className={"p-5 flex flex-col gap-2"}>
                <div className="flex flex-row justify-between items-center gap-2">
                    <button
                        onClick={onRun}
                        disabled={isRunning}
                        className={`cursor-pointer w-full py-3 rounded-xl font-bold text-xs uppercase tracking-widest transition-all md:shadow-lg ${isRunning
                            ? 'bg-slate-200 dark:bg-slate-800 text-slate-400 dark:text-slate-500 cursor-not-allowed'
                            : 'bg-blue-600 hover:bg-blue-500 text-white shadow-blue-500/20 hover:scale-[1.02]'
                            }`}
                    >
                        {isRunning ? (
                            <span className="flex items-center justify-center gap-2">
                                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                                Solving...
                            </span>
                        ) : 'Run Analysis'}
                    </button>

                    {isRunning && (
                        <button
                            onClick={onCancel}
                            className="cursor-pointer w-full py-2 rounded-xl font-bold text-[10px] uppercase tracking-widest transition-all bg-rose-500/10 border border-rose-500/50 text-rose-400 hover:bg-rose-500/20"
                        >
                            Cancel
                        </button>
                    )}

                    <div className="flex items-center justify-center md:block hidden">
                        <button
                            onClick={() => setResultSidebarOpen(!ResultSidebarOpen)}
                            className="cursor-pointer py-1 rounded-xl font-bold text-[10px] uppercase tracking-widest transition-all"
                        >
                            <ChevronDown className={`transition cursor-pointer w-6 h-6 ${ResultSidebarOpen ? '' : 'rotate-180'}`} />
                        </button>
                    </div>
                </div>
            </div>

            <div className={`flex flex-col transition ${ResultSidebarOpen ? 'p-3 md:h-[calc(65dvh)] h-full overflow-y-auto custom-scrollbar space-y-2 border-t border-slate-200 dark:border-slate-800 ' : 'h-0 overflow-y-hidden'}`}>

                {isRunning && (
                    <div className="col-span-2 md:block hidden">
                        <PhaseChart
                            points={processedLivePoints}
                            isLive={true}
                            isSafety={phases[runningPhaseIdx]?.phase_type === PhaseType.SAFETY_ANALYSIS}
                        />
                    </div>
                )}
                {solverResult && (
                    <>
                        <div className="space-y-2">
                            {solverResult.phases[currentPhaseIdx]?.step_points && (
                                <PhaseChart
                                    points={processedPoints}
                                    isSafety={phases[currentPhaseIdx]?.phase_type === PhaseType.SAFETY_ANALYSIS}
                                />
                            )}

                            <label className="text-xs font-semibold text-slate-500 tracking-widest">Select Phase</label>
                            <div className="grid grid-cols-1 gap-1">
                                {phases.map((p, idx) => {
                                    const result = solverResult.phases[idx];
                                    const isFailed = result && !result.success;
                                    return (
                                        <button
                                            key={idx}
                                            onClick={() => onSelectPhase(idx)}
                                            className={`cursor-pointer px-3 py-2 text-left text-xs rounded-lg border transition-all truncate flex items-center justify-between gap-2 ${currentPhaseIdx === idx
                                                ? (isFailed ? 'bg-rose-600/10 border-rose-500/50 text-rose-600 dark:text-rose-400 font-bold' : 'bg-blue-600/10 border-blue-500/50 text-blue-600 dark:text-blue-400 font-bold')
                                                : 'bg-slate-50 dark:bg-slate-800/40 border-slate-200 dark:border-slate-700/50 text-slate-700 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/60'
                                                }`}
                                        >
                                            <span className="truncate">{idx}. {p.name}</span>
                                            {result && (
                                                result.success ? (
                                                    <CircleCheck className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
                                                ) : (
                                                    <CircleMinus className="w-3.5 h-3.5 text-rose-500 flex-shrink-0" />
                                                )
                                            )}
                                        </button>
                                    );
                                })}
                            </div>
                        </div>

                        <div className="border-t border-slate-200 dark:border-slate-800 md:pb-5 pb-30">
                            <ResultSummary
                                phaseResult={solverResult.phases[currentPhaseIdx]}
                                prevPhaseResult={prevPhaseResult}
                                isReset={isReset}
                                phaseType={phases[currentPhaseIdx]?.phase_type}
                            />
                        </div>
                    </>
                )}

                {!solverResult && !isRunning && (
                    <div className="h-full flex flex-col items-center justify-center text-center p-2 space-y-2">
                        <p className="text-xs text-slate-500 leading-relaxed">No analysis data available. Click "Run Analysis" to start the analysis.</p>
                    </div>
                )}
            </div>
        </div>
    );
};
