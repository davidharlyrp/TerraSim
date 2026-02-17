import React, { useMemo } from 'react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Label } from 'recharts';
import { DrainageType, Material, MaterialModel } from '../types';

interface YieldSurfaceChartProps {
    material: Material;
}

export const YieldSurfaceChart: React.FC<YieldSurfaceChartProps> = ({ material }) => {
    // Data for Shear Stress vs Normal Stress failure envelope
    const chartData = useMemo(() => {
        const points = [];
        const steps = 75; // More steps for smoother curve
        const limit = 500;

        if (material.material_model === MaterialModel.MOHR_COULOMB) {
            const phi = (material.frictionAngle || 0) * (Math.PI / 180);
            const cohesion = material.cohesion || 0;
            const undrainedShearStrength = material.undrainedShearStrength || 0;
            const tanPhi = Math.tan(phi);

            for (let i = 0; i <= steps; i++) {
                const sigma_n = (i / steps) * limit;
                let tau = cohesion + sigma_n * tanPhi;
                if (material.drainage_type === DrainageType.UNDRAINED_B || material.drainage_type === DrainageType.UNDRAINED_C) {
                    tau = undrainedShearStrength;
                }
                else if ((material.cohesion === 0) && (material.drainage_type === DrainageType.DRAINED || material.drainage_type === DrainageType.UNDRAINED_A)) {
                    tau = 0 + sigma_n * tanPhi;
                }
                points.push({
                    sigma_n: parseFloat(sigma_n.toFixed(2)),
                    tau: parseFloat(tau.toFixed(2))
                });
            }
        } else if (material.material_model === MaterialModel.HOEK_BROWN) {
            const sig_ci = material.sigma_ci || 1;
            const mb = material.m_b || 0;
            const s = material.s || 0;
            const a = material.a || 0.5;

            // To plot tau vs sigma_n, we iterate over sigma3 and transform to (sigma_n, tau)
            // sigma1 = sigma3 + sig_ci * (mb * sigma3 / sig_ci + s)^a
            for (let i = 0; i <= steps; i++) {
                const sigma3 = (i / steps) * limit;
                const X = (mb * sigma3 / sig_ci + s);
                if (X >= 0) {
                    const sigma1 = sigma3 + sig_ci * Math.pow(X, a);

                    // Derivative d_sigma1 / d_sigma3
                    // d_sigma1 / d_sigma3 = 1 + a * mb * (mb * sigma3 / sig_ci + s)^(a-1)
                    const M = 1 + a * mb * Math.pow(X, a - 1);

                    // Transform to failure envelope coordinates (sigma_n, tau)
                    // These are the coordinates of the tangent point on the Mohr circle
                    const sigma_n = ((sigma1 + sigma3) / 2) - ((sigma1 - sigma3) / 2) * ((M - 1) / (M + 1));
                    const tau = ((sigma1 - sigma3) / 2) * (2 * Math.sqrt(Math.max(0, M)) / (M + 1));

                    if (!isNaN(sigma_n) && !isNaN(tau)) {
                        points.push({
                            sigma_n: parseFloat(sigma_n.toFixed(2)),
                            tau: parseFloat(tau.toFixed(2))
                        });
                    }
                }
            }
        }
        return { points, limit };
    }, [material]);

    let maxVal = 2 * Math.min(...chartData.points.map((d) => d.tau));
    if ((material.cohesion === 0) && (material.drainage_type === DrainageType.DRAINED || material.drainage_type === DrainageType.UNDRAINED_A)) {
        maxVal = chartData.limit / 2;
    }
    else if (material.material_model === MaterialModel.HOEK_BROWN) {
        maxVal = chartData.limit;
    }

    if (material.material_model !== MaterialModel.MOHR_COULOMB && material.material_model !== MaterialModel.HOEK_BROWN) {
        return (
            <div className="h-full flex items-center justify-center text-slate-400 italic text-sm p-8 text-center">
                Yield surface visualization is not available for {material.material_model} model.
            </div>
        );
    }

    return (
        <div className="w-full h-auto mt-4 p-2 bg-slate-50 dark:bg-slate-800/30 rounded-lg border border-slate-200 dark:border-slate-800">
            <h4 className="text-xs font-semibold mb-2 text-slate-500 text-center tracking-wider">Failure Envelope (τ vs σ)</h4>
            <div className="w-full aspect-square">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData.points} margin={{ top: 5, right: 0, left: -5, bottom: 30 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#8884d8" opacity={0.1} />
                        <XAxis
                            dataKey="sigma_n"
                            type="number"
                            tick={{ fontSize: 10 }}
                            stroke="#888"
                            domain={[0, maxVal]}
                            allowDataOverflow={true}
                        >
                            <Label value="σ (kN/m²)" offset={-15} position="insideBottom" style={{ fontSize: '10px', fill: '#888' }} />
                        </XAxis>
                        <YAxis
                            type="number"
                            tick={{ fontSize: 10 }}
                            stroke="#888"
                            domain={[0, maxVal]}
                            allowDataOverflow={true}
                        >
                            <Label value="τ (kN/m²)" angle={-90} offset={20} position="insideLeft" style={{ fontSize: '10px', fill: '#888' }} />
                        </YAxis>
                        <Tooltip
                            contentStyle={{ backgroundColor: 'rgba(30, 41, 59, 0.9)', border: 'none', borderRadius: '4px', fontSize: '10px', color: '#fff' }}
                            itemStyle={{ color: '#fff' }}
                            formatter={(value: any) => [typeof value === 'number' ? value.toFixed(2) : value, "τ"]}
                            labelFormatter={(label: any) => `σ: ${typeof label === 'number' ? label.toFixed(2) : label}`}
                        />
                        <Line
                            type="monotone"
                            dataKey="tau"
                            stroke="#3b82f6"
                            strokeWidth={2}
                            dot={false}
                            animationDuration={300}
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};
