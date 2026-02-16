import { InlineMath } from 'react-katex';
import { PhaseWrapper, SubHeader, MathInline } from './Shared';

export const Algorithms = () => (
    <PhaseWrapper
        title="5. Solver Algorithms"
        desc="The numerical engines driving the non-linear calculation process and safety factor assessments."
    >
        <div className="pl-4">
            <SubHeader
                title="5.1 Nonlinear Iteration & Safety Analysis"
                desc="TerraSim solve the equation system iteratively using the Newton-Raphson method and performs slope stability via SRM."
            />
            <div className="pl-8 space-y-8">
                <div>
                    <h3 className="text-xl font-bold text-white mb-2">5.1.1 Global Sparse Assembly</h3>
                    <p className="description2">Sparse assembly of global stiffness matrix <InlineMath math="[K]" /> using Coordinate (COO) format for memory efficiency:</p>
                    <MathInline math={"K_{global} = \\sum_{e=1}^{N_{el}} L_e^T K_e L_e"} />
                    <p className="description2">Global index determination for each node using DOF mapping:</p>
                    <MathInline math={"DOF_x = 2 \\times NodeID, \\quad DOF_y = 2 \\times NodeID + 1"} />
                </div>

                <div>
                    <h3 className="text-xl font-bold text-white mb-2">5.1.2 Newton-Raphson Iteration</h3>
                    <p className="description2">Solving the equation <InlineMath math={"K \\cdot \\Delta u = F_{ext} - F_{int}"} /> iteratively until convergence:</p>
                    <MathInline math={"[K_t] \\cdot \\delta u = F_{ext, target} - F_{int} \\\\ u_{new} = u_{old} + \\delta u"} />
                    <p className="description2 text-xs">Convergence criteria: <InlineMath math="\frac{\\|R\\|}{\\|F_{base}\\|} &lt; 0.01" />. If divergence, step size will be automatically reduced.</p>
                </div>

                <div>
                    <h3 className="text-xl font-bold text-white mb-2">5.1.3 Strength Reduction Method (SRM)</h3>
                    <p className="description2">Safety Factor (SF) is calculated by reducing soil strength parameters iteratively until numerical collapse:</p>
                    <MathInline math={"c_{red} = \\frac{c}{\\Sigma M_{sf}}, \\quad \\tan\\phi_{red} = \\frac{\\tan\\phi}{\\Sigma M_{sf}}"} />
                    <p className="description2 text-xs">The last <InlineMath math="\Sigma M_{sf}" /> value that still produces a convergent solution is recorded as Safety Factor.</p>
                </div>
            </div>
        </div>
    </PhaseWrapper>
);
