import { InlineMath } from 'react-katex';
import { PhaseWrapper, SubHeader, MathInline } from './Shared';

export const Interactions = () => (
    <PhaseWrapper
        title="6. Line Models"
        desc="Numerical formulations for structural elements like pile rows and anchors embedded within the soil mesh."
    >
        <div className="pl-4">
            <SubHeader
                title="6.1 Embedded Beam Row"
                desc="EBR interaction is modeled through virtual non-linear springs that transfer load without requiring node-sharing."
            />
            <div className="pl-8 space-y-8">
                <div>
                    <h3 className="text-xl font-bold text-white mb-2">6.1.1 Displacement Mapping</h3>
                    <p className="description2">Interaction between beam and soil is modeled as a virtual spring system connecting beam point (<InlineMath math="u_b" />) to soil displacement (<InlineMath math="u_s" />) at the same position:</p>
                    <MathInline math={"u_{soil}(x_{beam}) = \\sum N_i^{soil}(\\xi, \\eta) \\cdot u_i^{soil} \\\\ \\Delta u = u_{beam} - u_{soil}"} />
                </div>

                <div>
                    <h3 className="text-xl font-bold text-white mb-2">6.1.2 Interface Failure Mechanisms</h3>
                    <p className="description2">Failure of EBR occurs if interaction force exceeds its yield limit:</p>
                    <MathInline math={"t_{final} = \\min(R_s \\cdot \\Delta u, T_{max})"} />
                    <ul className="pl-6 space-y-2 list-disc description2 text-sm">
                        <li><strong>Skin Friction Limit (<InlineMath math="T_{max}" />):</strong> Maximum axial shear force (kN/m).</li>
                        <li><strong>Tip Resistance (<InlineMath math="F_{max}" />):</strong> Maximum tensile force at the tip.</li>
                    </ul>
                </div>

                <div>
                    <h3 className="text-xl font-bold text-white mb-2">6.1.3 Equivalent 2D Spacing</h3>
                    <p className="description2">In 2D model, the absolute stiffness of a single pile (<InlineMath math="EA, EI" />) is "dilimited" based on the spacing between piles (<InlineMath math="L_{spacing}" />):</p>
                    <MathInline math={"EA_{2D} = \\frac{EA_{pile}}{L_{spacing}}, \\quad EI_{2D} = \\frac{EI_{pile}}{L_{spacing}}"} />
                </div>
            </div>
        </div>
    </PhaseWrapper>
);
