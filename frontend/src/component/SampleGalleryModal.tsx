
import React from 'react';
import { X, ChevronRight, Loader2 } from 'lucide-react';
import { AVAILABLE_SAMPLES, SampleManifest } from '../data/samples';

interface SampleGalleryModalProps {
    onClose: () => void;
    onLoad: (sample: SampleManifest) => void;
}

export const SampleGalleryModal: React.FC<SampleGalleryModalProps> = ({ onClose, onLoad }) => {
    return (
        <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-300">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-3xl shadow-2xl w-full max-w-2xl overflow-hidden animate-in zoom-in-95 duration-300 transition-colors">
                {/* Header */}
                <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/30 flex items-center justify-between transition-colors">
                    <div className="flex items-center gap-3">
                        <div>
                            <h2 className="text-lg font-bold text-slate-900 dark:text-white tracking-tight">Sample Projects</h2>
                            <p className="text-[10px] text-slate-500 dark:text-slate-400 font-medium">Explore examples to get started quickly</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-xl text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors cursor-pointer"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 max-h-[60dvh] overflow-y-auto custom-scrollbar">
                    <div className="grid grid-cols-1 gap-4">
                        {AVAILABLE_SAMPLES.map((sample) => (
                            <div
                                key={sample.id}
                                className="group relative flex items-start gap-4 p-4 rounded-2xl border border-slate-200 dark:border-slate-800 hover:border-blue-500/50 dark:hover:border-blue-500/50 bg-slate-50/50 dark:bg-slate-900/50 hover:bg-blue-50/50 dark:hover:bg-blue-900/10 transition-all cursor-default"
                            >
                                <div className="flex-1">
                                    <h3 className="font-bold text-slate-900 dark:text-white mb-1 transition-colors">
                                        {sample.name}
                                    </h3>
                                    <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
                                        {sample.description}
                                    </p>
                                </div>
                                <button
                                    onClick={() => onLoad(sample)}
                                    className="cursor-pointer self-center px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm font-semibold text-slate-600 dark:text-slate-300 group-hover:bg-blue-600 group-hover:border-blue-600 group-hover:text-white dark:group-hover:bg-blue-600 dark:group-hover:border-blue-600 dark:group-hover:text-white transition-all shadow-sm flex items-center gap-2"
                                >
                                    Load
                                    <ChevronRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity -ml-2 group-hover:ml-0" />
                                </button>
                            </div>
                        ))}

                        {AVAILABLE_SAMPLES.length === 0 && (
                            <div className="text-center py-10 text-slate-500 dark:text-slate-400">
                                <Loader2 className="w-8 h-8 mx-auto mb-3 animate-spin opacity-50" />
                                <p>No samples available yet</p>
                            </div>
                        )}
                    </div>
                </div>

                {/* Footer */}
                <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/30 flex justify-end">
                    <button
                        onClick={onClose}
                        className="cursor-pointer px-4 py-2 text-sm font-semibold text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 transition-colors"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
};
