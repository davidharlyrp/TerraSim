import React from 'react';
import { InlineMath } from 'react-katex';

export const PhaseWrapper: React.FC<{ title: string; desc: string; children: React.ReactNode }> = ({ title, desc, children }) => (
    <div className="flex flex-col gap-12 group">
        <div className="flex-1 space-y-4 py-2 border-b border-gray-500">
            <h2 className="text-2xl font-black text-white">{title}</h2>
            <p className="text-lg text-slate-400 leading-relaxed max-w-3xl">
                {desc}
            </p>
        </div>
        {children}
    </div>
);

export const MathInline: React.FC<{ math: string }> = ({ math }) => (
    <div className="my-6 p-6 bg-slate-900/40 rounded-2xl flex justify-center items-center overflow-x-auto backdrop-blur-sm transition-colors">
        <InlineMath math={math} />
    </div>
);

export const SubHeader: React.FC<{ title: string; desc: string }> = ({ title, desc }) => (
    <div className="flex-1 mb-4 space-y-4 py-2 border-b border-gray-500">
        <h2 className="text-2xl font-black text-white">{title}</h2>
        <p className="text-lg text-slate-400 leading-relaxed max-w-3xl">
            {desc}
        </p>
    </div>
);
