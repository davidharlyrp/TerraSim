import React from 'react';

// Modular components
import { Overview } from './scientific/Overview';
import { Elements } from './scientific/Elements';
import { Initialization } from './scientific/Initialization';
import { Constitutive } from './scientific/Constitutive';
import { Algorithms } from './scientific/Algorithms';
import { Interactions } from './scientific/Interactions';

export const ScientificReference: React.FC = () => {
    return (
        <div className="space-y-16 animate-in fade-in slide-in-from-bottom-4 duration-700">
            <header className="space-y-4">
                <h1 className="text-4xl md:text-5xl font-black text-white tracking-tight leading-tight">
                    Scientific Reference
                </h1>
                <p className="text-xl text-slate-400 leading-relaxed max-w-2xl">
                    Detailed mathematical formulation and theoretical background of the TerraSim FEM engine.
                </p>
            </header>

            <div className="space-y-24">
                <Overview />
                <Elements />
                <Initialization />
                <Constitutive />
                <Algorithms />
                <Interactions />
            </div>

            <section className="pt-20 border-t border-white/5">
                <div className="flex items-center gap-4 mb-10">
                    <h2 className="text-2xl font-bold text-white">Literature & References</h2>
                </div>
                <div className="flex flex-col gap-4">
                    {[
                        {
                            title: "A strength reduction method based on the Generalized Hoek-Brown criterion for rock slope stability analysis",
                            author: "Yuan Wei, Li Jiaxin, Li Zonghong, Wang Wei, Sun Xiaoyun",
                            source: "Computers and Geotechnics"
                        }
                    ].map((ref, idx) => (
                        <div key={idx} className="px-5 transition-all flex flex-col justify-center">
                            <h4 className="text-sm font-bold text-white mb-1">{ref.title}</h4>
                            <p className="text-xs text-slate-500 font-medium pl-2">{ref.author} &bull; {ref.source}</p>
                        </div>
                    ))}
                </div>
            </section>
        </div>
    );
};
