import { InlineMath } from 'react-katex';
import { PhaseWrapper, SubHeader } from './Shared';

export const Overview = () => (
    <PhaseWrapper
        title="1. Solver Overview"
        desc="Dahar Engineering's FEM engine is built for geotechnical precision and computational efficiency, powered by Python with Numba JIT."
    >
        <div className="pl-4">
            <SubHeader
                title="1.1 Architecture & Staged Construction"
                desc="TerraSim employs a Staged Construction approach where each phase represents a construction step and inherits stress history."
            />
            <div className="pl-8 space-y-6">
                <p className="description2">
                    In geotechnical engineering, the history of construction is paramount. Each phase inherits the stresses from the previous state (stress history).
                </p>
                <div className="flex flex-col gap-4">
                    <div className="p-4 rounded-xl bg-slate-900/60 border border-white/5">
                        <h4 className="text-sm font-bold text-white mb-2">Incremental Loading (ΣMstage)</h4>
                        <p className="description2 text-xs">Load is applied incrementally using the <InlineMath math={"\\Sigma M_{stage}"} /> parameter from 0.0 to 1.0. If the solver fails before reaching 1.0, it indicates numerical collapse.</p>
                    </div>
                    <div className="p-4 rounded-xl bg-slate-900/60 border border-white/5">
                        <h4 className="text-sm font-bold text-white mb-2">Stress & Strain Accumulation</h4>
                        <p className="description2 text-xs">Accumulated strain <InlineMath math={"\\epsilon"} /> determines the resulting stress <InlineMath math={"\\sigma"} /> across construction phases such as excavation, loading, or material changes.</p>
                    </div>
                </div>
            </div>
        </div>
    </PhaseWrapper>
);
