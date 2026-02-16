import { InlineMath } from 'react-katex';
import { PhaseWrapper, SubHeader, MathInline } from './Shared';

export const Elements = () => (
    <PhaseWrapper
        title="2. Element Formulation"
        desc="The core mathematical building block of the TerraSim finite element mesh."
    >
        <div className="pl-4">
            <SubHeader
                title="2.1 T6 Quadratic Triangle"
                desc="T6 elements are chosen for their superior accuracy in capturing complex stress gradients compared to linear elements."
            />

            <div className="pl-8 mb-12 flex w-full justify-center">
                <div className="relative w-full max-w-lg aspect-[4/3] bg-slate-900/40 rounded-xl border border-white/5 overflow-hidden group/viz flex items-center justify-center">
                    <svg viewBox="0 0 400 300" className="w-full h-full p-2">
                        {/* Glow effect */}
                        <defs>
                            <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                                <feGaussianBlur stdDeviation="4" result="blur" />
                                <feComposite in="SourceGraphic" in2="blur" operator="over" />
                            </filter>
                        </defs>

                        {/* Triangle Body */}
                        <path
                            d="M 200 50 L 350 250 L 50 250 Z"
                            className="fill-indigo-500/10 stroke-indigo-500/40 stroke-[2]"
                        />

                        {/* Integration Points (Gauss Points) */}
                        <g className="filter-glow">
                            <circle cx="200" cy="120" r="5" className="fill-emerald-400 scale-100" />
                            <circle cx="125" cy="215" r="5" className="fill-emerald-400 scale-100" />
                            <circle cx="275" cy="215" r="5" className="fill-emerald-400 scale-100" />
                        </g>

                        {/* Vertex Nodes (1, 2, 3) */}
                        <circle cx="200" cy="50" r="6" className="fill-white stroke-slate-900 stroke-2" />
                        <circle cx="350" cy="250" r="6" className="fill-white stroke-slate-900 stroke-2" />
                        <circle cx="50" cy="250" r="6" className="fill-white stroke-slate-900 stroke-2" />

                        {/* Midside Nodes (4, 5, 6) */}
                        <circle cx="275" cy="150" r="5" className="fill-blue-500 stroke-slate-900 stroke-1" />
                        <circle cx="200" cy="250" r="5" className="fill-blue-500 stroke-slate-900 stroke-1" />
                        <circle cx="125" cy="150" r="5" className="fill-blue-500 stroke-slate-900 stroke-1" />

                        {/* Text Labels */}
                        <g className="text-[14px] font-black fill-slate-300 font-sans tracking-tighter">
                            <text x="212" y="55">1</text>
                            <text x="362" y="255">2</text>
                            <text x="32" y="255">3</text>
                            <text x="285" y="155" className="fill-slate-500">4</text>
                            <text x="193" y="275" className="fill-slate-500">5</text>
                            <text x="105" y="155" className="fill-slate-500">6</text>
                        </g>

                        {/* Legend */}
                        <g className="text-[10px] font-bold fill-slate-400 font-sans">
                            <circle cx="20" cy="20" r="4" className="fill-white" />
                            <text x="32" y="24">Vertex Nodes</text>

                            <circle cx="20" cy="40" r="3.5" className="fill-blue-500" />
                            <text x="32" y="44" className="fill-blue-500">Midside Nodes</text>

                            <circle cx="20" cy="60" r="4" className="fill-emerald-400" />
                            <text x="32" y="64" className="fill-emerald-400">3 Gauss Points</text>
                        </g>
                    </svg>
                </div>
            </div>
            <div className="pl-8 space-y-8">
                <div>
                    <h3 className="text-xl font-bold text-white mb-2">2.1.1 Shape Functions (N)</h3>
                    <p className="description2">Shape functions are defined in natural coordinates <InlineMath math="(\xi, \eta)" /> for quadratic interpolation:</p>
                    <MathInline math={"\\zeta = 1 - \\xi - \\eta \\\\ N_1 = \\zeta(2\\zeta - 1) \\\\ N_2 = \\xi(2\\xi - 1) \\\\ N_3 = \\eta(2\\eta - 1) \\\\ N_4 = 4\\zeta\\xi \\\\ N_5 = 4\\xi\\eta \\\\ N_6 = 4\\eta\\zeta"} />
                    <p className="description2 text-xs italic">Node 1-3 are vertex nodes, while Node 4-6 are midside nodes.</p>
                </div>

                <div>
                    <h3 className="text-xl font-bold text-white mb-2">2.1.2 Strain-Displacement Matrix (B)</h3>
                    <p className="description2">Strain-displacement matrix <InlineMath math="B" /> connects nodal displacement vector (<InlineMath math="u" />) with strain vector (<InlineMath math="\epsilon" />):</p>
                    <MathInline math={"\\epsilon = B \\cdot u = \\begin{bmatrix} \\epsilon_{xx} \\\\ \\epsilon_{yy} \\\\ \\gamma_{xy} \\end{bmatrix}"} />
                    <p className="description2">For each node <InlineMath math="i" />, sub-matrix <InlineMath math="B_i" /> is composed of the derivatives of shape functions with respect to physical coordinates (<InlineMath math="x, y" />):</p>
                    <MathInline math={"B_i = \\begin{bmatrix} \\frac{\\partial N_i}{\\partial x} & 0 \\\\ 0 & \\frac{\\partial N_i}{\\partial y} \\\\ \\frac{\\partial N_i}{\\partial y} & \\frac{\\partial N_i}{\\partial x} \\end{bmatrix}"} />
                    <p className="description2">The final element stiffness matrix <InlineMath math="B" /> is a combination of 6 sub-matrices <InlineMath math="B_i" /> (<InlineMath math="3 \times 12" />):</p>
                    <MathInline math={"B = [B_1, B_2, B_3, B_4, B_5, B_6]"} />
                </div>

                <div>
                    <h3 className="text-xl font-bold text-white mb-2">2.1.3 Element Stiffness Matrix (K)</h3>
                    <p className="description2">Element stiffness is calculated through volume integration (assumes Plane Strain):</p>
                    <MathInline math={"K_{el} = \\int_{A} B^T D B \\, dA"} />
                    <p className="description2">Solved using **3 Gauss Points** numerical integration:</p>
                    <MathInline math={"K_{el} \\approx \\sum_{g=1}^{3} (B_g^T D B_g) \\cdot \\det(J)_g \\cdot w_g"} />
                    <ul className="pl-6 space-y-2 list-disc description2 text-sm">
                        <li><InlineMath math="D" />: Material constitutive matrix (Elastic or Elastoplastic).</li>
                        <li><InlineMath math="\\det(J)_g" />: Determinant of the Jacobian for coordinate transformation.</li>
                        <li><InlineMath math="w_g" />: Gauss integration weights (<InlineMath math="\frac{1}{6}" /> for T6 3-Gauss Points).</li>
                    </ul>
                </div>

                <div>
                    <h3 className="text-xl font-bold text-white mb-2">2.1.4 Gravity Loading (<InlineMath math="F_{grav}" />)</h3>
                    <p className="description2">Gravity loading is calculated as a volume integral of body force:</p>
                    <MathInline math={"\\mathbf{F}_{grav} = \\int_{V} \\mathbf{N}^T \\mathbf{b} \\, dV"} />
                    <p className="description2">Resulting in a <InlineMath math="12 \times 1" /> vector containing vertical loads at each node:</p>
                    <MathInline math={"\\mathbf{F}_{grav} = \\sum_{g=1}^{3} \\begin{bmatrix} 0 \\\\ -N_1 \\rho \\\\ \\vdots \\\\ 0 \\\\ -N_6 \\rho \\end{bmatrix}_g \\cdot \\det(J)_g \\cdot w_g"} />
                </div>
            </div>
        </div>
    </PhaseWrapper>
);
