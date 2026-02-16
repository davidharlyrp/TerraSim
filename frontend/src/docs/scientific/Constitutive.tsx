import { InlineMath } from 'react-katex';
import { PhaseWrapper, SubHeader, MathInline } from './Shared';

export const Constitutive = () => (
    <PhaseWrapper
        title="4. Constitutive Laws"
        desc="Mathematical models defining the stress-strain behavior and failure criteria of soil and rock materials."
    >
        <div className="pl-4">
            <SubHeader
                title="4.1 Linear Elasticity"
                desc="The foundation for all stress-strain calculations using Hooke's Law for isotropic materials."
            />
            <div className="pl-8 space-y-8 mb-12">
                <div>
                    <h3 className="text-xl font-bold text-white mb-2">4.1.1 Elastic Stiffness Matrix (<InlineMath math="D" />)</h3>
                    <p className="description2">
                        The material stiffness matrix <InlineMath math="D" /> is calculated using Young's Modulus (<InlineMath math="E" />) and Poisson's ratio (<InlineMath math="\nu" />)
                        under the **Plane Strain** assumption:
                    </p>
                    <MathInline math={"D_{el} = \\frac{E(1-\\nu)}{(1+\\nu)(1-2\\nu)} \\begin{bmatrix} 1 & \\frac{\\nu}{1-\\nu} & 0 \\\\ \\frac{\\nu}{1-\\nu} & 1 & 0 \\\\ 0 & 0 & \\frac{1-2\\nu}{2(1-\\nu)} \\end{bmatrix}"} />
                    <p className="description2 text-xs italic">
                        The third dimension stress <InlineMath math="\sigma_z" /> is derived as <InlineMath math="\sigma_z = \nu(\sigma_x + \sigma_y)" /> since <InlineMath math="\epsilon_z = 0" />.
                    </p>
                </div>
            </div>

            <SubHeader
                title="4.2 Mohr-Coulomb Plasticity"
                desc="A non-associated elastoplastic model that limits the shear strength based on effective stress."
            />
            <div className="pl-8 space-y-8">
                <div>
                    <h3 className="text-xl font-bold text-white mb-2">4.2.1 Yield Function (<InlineMath math="f" />)</h3>
                    <p className="description2">
                        Plasticity occurs when the trial stress exceeds the shear strength defined by Cohesion (<InlineMath math="c" />) and Friction Angle (<InlineMath math="\phi" />):
                    </p>
                    <MathInline math={"f = (\\sigma_1 - \\sigma_3) + (\\sigma_1 + \\sigma_3) \\sin \\phi - 2c \\cos \\phi"} />
                    <div className="mt-4 p-4 rounded-xl bg-slate-900/60 border border-white/5 space-y-2">
                        <p className="description2 text-xs">Principal stresses <InlineMath math="\sigma_{1,3}" /> are computed from the Cartesian stress state:</p>
                        <MathInline math={"\\sigma_{1,3} = \\frac{\\sigma_{xx} + \\sigma_{yy}}{2} \\pm \\sqrt{\\left( \\frac{\\sigma_{xx} - \\sigma_{yy}}{2} \\right)^2 + \\tau_{xy}^2}"} />
                    </div>
                </div>

                <div>
                    <h3 className="text-xl font-bold text-white mb-2">4.2.2 Numerical Integration (Radial Return)</h3>
                    <p className="description2">
                        If <InlineMath math="f > 0" />, the solver projects the stress back to the yield surface.
                        TerraSim uses a stable **Radial Return** algorithm centered on the Mohr circle:
                    </p>
                    <div className="flex flex-col gap-4 my-6">
                        <div className="p-4 rounded-xl bg-slate-900/5 border border-slate-900/10 text-xs">
                            <h4 className="font-black text-slate-500 uppercase mb-2">1. Scaling Factor (<InlineMath math="\eta" />)</h4>
                            <p className="description2">Shrinks the radius of the trial Mohr circle to fit the MC limit.</p>
                            <MathInline math={"\\eta = \\frac{c \\cos \\phi - \\sigma_{avg} \\sin \\phi}{R_{trial}}"} />
                        </div>
                        <div className="p-4 rounded-xl bg-slate-900/5 border border-slate-900/10 text-xs">
                            <h4 className="font-black text-slate-500 uppercase mb-2">2. Reconstruct Stress</h4>
                            <p className="description2">Returns the Cartesian components while maintaining orientation.</p>
                            <MathInline math={"\\tau_{xy, new} = \\eta \\cdot \\tau_{xy}"} />
                        </div>
                    </div>
                </div>

                <div>
                    <h3 className="text-xl font-bold text-white mb-2">4.2.3 Tension Cut-off (Apex)</h3>
                    <p className="description2">
                        If <InlineMath math="\sigma_{avg}" /> is highly tensile, stress is capped at the apex to prevent physically unstable results:
                    </p>
                    <MathInline math={"\\sigma_{apex} = \\frac{c \\cos \\phi}{\\sin \\phi}"} />
                </div>
            </div>

            <SubHeader
                title="4.3 Generalized Hoek-Brown"
                desc="A nonlinear empirical failure criterion widely used for rock mass engineering."
            />
            <div className="pl-8 space-y-8 mb-12">
                <div>
                    <h3 className="text-xl font-bold text-white mb-2">4.3.1 Yield Function</h3>
                    <p className="description2">For rock masses, the solver employs the Generalized Hoek-Brown (2002) criterion:</p>
                    <MathInline math={"f = \\sigma_1 - \\sigma_3 - \\sigma_{ci} \\left( m_b \\frac{\\sigma_3}{\\sigma_{ci}} + s \\right)^a"} />
                </div>

                <div>
                    <h3 className="text-xl font-bold text-white mb-2">4.3.2 Rock Mass Parameters Derivation</h3>
                    <p className="description2">
                        The constants <InlineMath math="m_b, s," /> and <InlineMath math="a" /> are rock mass properties derived from three primary user inputs:
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 my-4">
                        <div className="p-3 rounded-lg bg-slate-900/60 border border-white/5">
                            <h4 className="text-[10px] font-bold text-slate-500"><InlineMath math="GSI" /></h4>
                            <p className="text-[10px] text-slate-300">Geological Strength Index (0-100) based on structure and surface conditions.</p>
                        </div>
                        <div className="p-3 rounded-lg bg-slate-900/60 border border-white/5">
                            <h4 className="text-[10px] font-bold text-slate-500"><InlineMath math="m_i" /></h4>
                            <p className="text-[10px] text-slate-300">Intact rock constant (typically 5-35) representing rock mineralogy.</p>
                        </div>
                        <div className="p-3 rounded-lg bg-slate-900/60 border border-white/5">
                            <h4 className="text-[10px] font-bold text-slate-500"><InlineMath math="D" /></h4>
                            <p className="text-[10px] text-slate-300">Disturbance factor (0-1) reflecting blast damage or stress relief.</p>
                        </div>
                    </div>

                    <div className="space-y-4 bg-slate-900/40 p-6 rounded-2xl border border-white/5">
                        <div className="flex flex-col md:flex-row justify-between items-center gap-4">
                            <div className="flex-1">
                                <span className="text-sm font-bold text-slate-500 block mb-1"><InlineMath math="m_b" /></span>
                                <MathInline math={"m_b = m_i \\exp \\left( \\frac{GSI - 100}{28 - 14D} \\right)"} />
                            </div>
                            <div className="flex-1">
                                <span className="text-sm font-bold text-slate-500 block mb-1"><InlineMath math="s" /></span>
                                <MathInline math={"s = \\exp \\left( \\frac{GSI - 100}{9 - 3D} \\right)"} />
                            </div>
                        </div>
                        <div className="pt-4 border-t border-white/5">
                            <span className="text-sm font-bold text-slate-500 block mb-1"><InlineMath math="a" /></span>
                            <MathInline math={"a = \\frac{1}{2} + \\frac{1}{6} \\left( e^{-GSI/15} - e^{-20/3} \\right)"} />
                        </div>
                    </div>
                </div>
            </div>

            <SubHeader
                title="4.4 Hydraulic Influence & Excess PWP"
                desc="Handling pore water pressure generation under undrained loading conditions."
            />
            <div className="pl-8 space-y-8">
                <div className="bg-slate-900/40 p-6 rounded-2xl border border-white/5">
                    <p className="description2 mb-6">
                        Under undrained (A & B) conditions, pore water pressure generation is modeled via a penalty formulation:
                    </p>
                    <div className="flex flex-col gap-8">
                        <div className="space-y-4">
                            <h5 className="text-[10px] font-bold text-slate-400 uppercase">Pore Pressure Update</h5>
                            <MathInline math={"u_{exc, new} = u_{exc, old} + K_{water} \\cdot \\Delta \\epsilon_{vol}"} />
                            <p className="description2 text-[10px] italic text-slate-500">
                                Penalty <InlineMath math="K_{water} \approx 2.2 \times 10^6 \text{ kPa} / n" />
                            </p>
                        </div>
                        <div className="space-y-4">
                            <h5 className="text-[10px] font-bold text-slate-400 uppercase">Effective Stress Update</h5>
                            <MathInline math={"\\sigma'_{trial} = \\sigma_{total, trial} - (u_{static} + u_{excess})"} />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </PhaseWrapper>
);
