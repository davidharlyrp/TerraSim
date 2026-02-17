import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Target, Computer, Cloud, ChartLine } from 'lucide-react';

export const Introduction: React.FC = () => {
    const navigate = useNavigate();
    return (
        <div className="space-y-12 animate-in fade-in slide-in-from-bottom-4 duration-700">
            <header className="space-y-4">
                <h1 className="text-4xl md:text-5xl font-black text-white tracking-tight leading-tight">
                    TerraSim <br />
                    <span className="font-bold text-blue-500 text-3xl">Geotechnical Finite Element Analysis Software</span>
                </h1>
                <p className="text-xl text-slate-400 leading-relaxed max-w-2xl">
                    TerraSim is a web-based application platform designed for geotechnical engineers to perform advanced 2D Finite Element Modeling with ease and precision.
                </p>
            </header>

            <section className="grid sm:grid-cols-2 gap-6">
                {[
                    {
                        title: "FEM Core",
                        desc: "Using Quadratic Triangle Element (QTE) with 6 nodes and 3 Gaussian integration points for reliable simulation results.",
                        icon: <Target className="w-6 h-6 text-blue-500" />,
                        base: "bg-blue-500/5 ring-blue-500/20"
                    },
                    {
                        title: "Server-Based Execution",
                        desc: "Analysis is executed in the background at our server, allowing you to continue working on your project and not to worry about your device's performance.",
                        icon: <Computer className="w-6 h-6 text-blue-500" />,
                        base: "bg-blue-500/5 ring-blue-500/20"
                    },
                    {
                        title: "Cloud Storage",
                        desc: "Save and load your projects anywhere with built-in Cloud Integration and secure storage.",
                        icon: <Cloud className="w-6 h-6 text-blue-500" />,
                        base: "bg-blue-500/5 ring-blue-500/20"
                    },
                    {
                        title: "Result Visualization",
                        desc: "Visualize your results in real-time with built-in visualization tools.",
                        icon: <ChartLine className="w-6 h-6 text-blue-500" />,
                        base: "bg-blue-500/5 ring-blue-500/20"
                    }
                ].map((item, i) => (
                    <div key={i} className={`p-6 rounded-2xl ring-1 ${item.base} hover:scale-[1.02] transition-transform`}>
                        <div className="mb-4">{item.icon}</div>
                        <h3 className="text-lg font-bold text-white mb-2">{item.title}</h3>
                        <p className="text-sm text-slate-400 leading-relaxed">{item.desc}</p>
                    </div>
                ))}
            </section>

            <div className="space-y-8 py-12 border-t border-slate-800/50">
                <h2 className="text-2xl font-bold text-white mb-6">Project Overview</h2>
                <div className="prose prose-invert max-w-none">
                    <p className="text-slate-300 leading-offset leading-relaxed text-lg">
                        Geotechnical engineering often involves complex soil behaviors that are difficult to predict with simple analytical methods.
                        <strong> TerraSim</strong> bridges this gap by providing an accessible yet powerful interface to perform 2D deformation and stress analysis including safety factor analysis.
                    </p>
                    <div className="h-px w-full bg-blue-500/50 my-8" />
                    <p className="text-slate-300 leading-relaxed">
                        Whether you are analyzing foundation settlements, slope stability, or complex multi-stage excavation sequences,
                        TerraSim provides the tools to build a model, mesh, solve, and visualize your geotechnical problems in real-time.
                    </p>
                </div>
            </div>

            <div className="bg-gradient-to-br from-blue-600 to-indigo-700 rounded-3xl p-8 md:p-12 border border-blue-400/20 shadow-2xl relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -translate-y-32 translate-x-32 blur-3xl group-hover:scale-110 transition-transform duration-700" />
                <div className="relative z-10 space-y-6">
                    <h2 className="text-3xl font-bold text-white leading-tight">Ready to start analyzing?</h2>
                    <p className="text-blue-100 text-lg max-w-xl">
                        Explore the User Manual to learn how to create your first project, or dive into the Scientific Reference to understand the mathematics behind the simulation.
                    </p>
                    <div className="flex flex-wrap gap-4 pt-4">
                        <button
                            onClick={() => navigate('/docs/user-manual')}
                            className="cursor-pointer px-8 py-4 bg-white text-blue-600 font-bold rounded-xl hover:bg-blue-50 active:scale-95 transition-all shadow-xl">
                            User Manual
                        </button>
                        <button
                            onClick={() => navigate('/docs/scientific-reference')}
                            className="cursor-pointer px-8 py-4 bg-blue-500/20 text-white border border-white/20 font-bold rounded-xl hover:bg-white/10 active:scale-95 transition-all backdrop-blur-md">
                            Scientific Reference
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};
