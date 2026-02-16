import { InlineMath } from 'react-katex';
import { PhaseWrapper, SubHeader, MathInline } from './Shared';

export const Initialization = () => (
    <PhaseWrapper
        title="3. Initial Stress (K0 Procedure)"
        desc="Establishing accurate in-situ stress states prior to construction simulation is fundamental to geotechnical modeling."
    >
        <SubHeader
            title="3.1 Input Data Structure (SolverRequest)"
            desc="The solver receives a comprehensive request object containing all geometry, material, and staging data."
        />
        <div className="pl-8 space-y-6 mb-12">
            <p className="description2">
                The finite element engine processes a <span className="font-bold text-white">SolverRequest</span> object, which maps mesh elements to specific material properties and hydraulic conditions.
            </p>
            <div className="flex flex-col gap-4">
                <div className="p-4 rounded-xl bg-slate-900/60 border border-white/5">
                    <h4 className="text-sm font-bold text-white mb-2">Geometry & Mesh</h4>
                    <p className="description2 text-xs">Lists of Nodes (coordinates) and Elements (T6 connectivity). Elements are grouped by <span className="font-bold text-white">PolygonID</span> for material mapping.</p>
                </div>
                <div className="p-4 rounded-xl bg-slate-900/60 border border-white/5">
                    <h4 className="text-sm font-bold text-white mb-2">Phases & Water</h4>
                    <p className="description2 text-xs">Sequential construction stages. Phreatic lines for each phase determine the regional pore water pressure.</p>
                </div>
            </div>
        </div>

        <SubHeader
            title="3.2 Initial Stress Calculation (K0 Procedure)"
            desc="Establishing accurate in-situ stress states prior to construction simulation is fundamental to geotechnical modeling."
        />
        <div className="pl-8 space-y-8">
            <div>
                <h3 className="text-xl font-bold text-white mb-2">3.2.1 Vertical Stress Integration</h3>
                <p className="description2">
                    The solver identifies the ground surface <InlineMath math="y_{surf}" /> for each horizontal position <InlineMath math="x_{gp}" />.
                    Total vertical stress is calculated by integrating unit weights:
                </p>
                <MathInline math={"\\sigma_{v, total} = \\int_{y_{gp}}^{y_{surf}} \\gamma(y) \\, dy"} />
                <p className="description2 text-xs">
                    The unit weight <InlineMath math="\gamma" /> switches between <InlineMath math="\gamma_{unsat}" /> and <InlineMath math="\gamma_{sat}" />
                    dynamically as the integration passes the phreatic level.
                </p>
            </div>

            <div>
                <h3 className="text-xl font-bold text-white mb-2">3.2.2 Pore Water Pressure (<InlineMath math="u_w" />)</h3>
                <p className="description2">Pore water pressure is determined hydrostatically based on the distance to the phreatic surface (<InlineMath math="y_{water}" />):</p>
                <MathInline math={"u_w = \\gamma_w \\cdot (y_{water} - y_{gp}), \\quad y_{gp} \\le y_{water}"} />
                <p className="description2 text-xs">For zones above the water table (<InlineMath math="y_{gp} \gt y_{water}" />), <InlineMath math="u_w" /> is assumed zero.</p>
            </div>

            <div>
                <h3 className="text-xl font-bold text-white mb-2">3.2.3 Horizontal Stress & K0 Formula</h3>
                <p className="description2">Effective horizontal stress is derived using the Coefficient of Earth Pressure at Rest (<InlineMath math="K_0" />):</p>
                <MathInline math={"\\sigma'_h = K_0 \\cdot \\sigma'_v, \\quad \\sigma'_v = \\sigma_{v, total} - u_w"} />

                <div className="mt-4 flex flex-col gap-6">
                    <div className="space-y-2">
                        <h4 className="text-xs font-semibold text-white text-indigo-400">Normally Consolidated (Mohr-Coulomb)</h4>
                        <p className="description2 text-xs">Uses Jaky's Formula (1944) if not manually overridden:</p>
                        <MathInline math={"K_0 = 1 - \\sin(\\phi)"} />
                    </div>
                    <div className="space-y-2">
                        <h4 className="text-xs font-semibold text-white text-blue-400">Linear Elastic Theory</h4>
                        <p className="description2 text-xs">Uses pure elasticity theory if friction angle is not applicable:</p>
                        <MathInline math={"K_0 = \\frac{\\nu}{1 - \\nu}"} />
                    </div>
                </div>
                <div>
                    <h3 className="text-xl font-bold text-white mb-2">3.2.4 Initial Shear Stress (<InlineMath math="\tau_{xy}" />)</h3>
                    <p className="description2">
                        For standard K0 procedures, the ground is assumed to be level (level ground assumption). Consequently, initial shear stresses are assumed to be zero:
                    </p>
                    <MathInline math={"\\tau_{xy} = 0"} />
                </div>

                <div className="bg-slate-900/40 p-6 rounded-2xl border border-white/5">
                    <h4 className="text-sm font-bold text-white mb-4 uppercase tracking-tighter">Drainage Influence on K0 Calculation</h4>
                    <div className="overflow-x-auto">
                        <table className="w-full text-xs text-left border-collapse">
                            <thead>
                                <tr className="border-b border-white/10 text-[10px] text-slate-500 uppercase font-black">
                                    <th className="py-2 pb-4">Drainage Type</th>
                                    <th className="py-2 pb-4 pl-4">Initial PWP Handling</th>
                                    <th className="py-2 pb-4 pl-4">K0 Stress Calculation</th>
                                    <th className="py-2 pb-4 pl-4">Subsequent Analysis</th>
                                </tr>
                            </thead>
                            <tbody className="description2 leading-relaxed">
                                <tr className="border-b border-white/5">
                                    <td className="py-4 font-bold text-white">DRAINED</td>
                                    <td className="py-4 pl-4">Hydrostatic (<InlineMath math="u_w = \gamma_w z_w" />)</td>
                                    <td className="py-4 pl-4"><InlineMath math="\sigma'_h = K_0 \cdot (\sigma_{v,total} - u_w)" /></td>
                                    <td className="py-4 pl-4">Effective Stress</td>
                                </tr>
                                <tr className="border-b border-white/5">
                                    <td className="py-4 font-bold text-white">UNDRAINED A</td>
                                    <td className="py-4 pl-4">Hydrostatic (Initial)</td>
                                    <td className="py-4 pl-4">Same as Drained</td>
                                    <td className="py-4 pl-4">Effective (w/ stiffness correction)</td>
                                </tr>
                                <tr className="border-b border-white/5">
                                    <td className="py-4 font-bold text-white">UNDRAINED B</td>
                                    <td className="py-4 pl-4">Hydrostatic (Initial)</td>
                                    <td className="py-4 pl-4">Same as Drained</td>
                                    <td className="py-4 pl-4">Effective (using <InlineMath math="c = S_u" />)</td>
                                </tr>
                                <tr className="border-b border-white/5">
                                    <td className="py-4 font-bold text-white">UNDRAINED C</td>
                                    <td className="py-4 pl-4 ">Ignored (<InlineMath math="u_w = 0" />)</td>
                                    <td className="py-4 pl-4"><InlineMath math="\sigma_{h,total} = K_0 \cdot \sigma_{v,total}" /></td>
                                    <td className="py-4 pl-4">Total Stress (<InlineMath math="\phi=0" />)</td>
                                </tr>
                                <tr>
                                    <td className="py-4 font-bold text-white">NON-POROUS</td>
                                    <td className="py-4 pl-4">Ignored (<InlineMath math="u_w = 0" />)</td>
                                    <td className="py-4 pl-4">Same as Undrained C</td>
                                    <td className="py-4 pl-4">Impermeable Material</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    <div className="mt-6 p-4">
                        <p className="text-[10px] leading-relaxed text-slate-500 italic">
                            <strong>Note on Undrained K0:</strong> For materials using <InlineMath math="S_u" /> where <InlineMath math="\phi=0" />, the Jaky formula yields <InlineMath math="K_0 = 1.0" /> (hydrostatic state). If neither <InlineMath math="K_{0,x}" /> nor <InlineMath math="\phi" /> is provided, the solver defaults to 0.5 to prevent numerical instability.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    </PhaseWrapper>
);
