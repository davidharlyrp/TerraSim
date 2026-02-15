import React, { useState } from 'react';
import { X } from 'lucide-react';
import { GeneralSettings, SolverSettings } from '../types';
import { MathRender } from './Math';

interface SettingsModalProps {
    generalSettings: GeneralSettings;
    solverSettings: SolverSettings;
    onSave: (general: GeneralSettings, solver: SolverSettings) => void;
    onClose: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
    generalSettings,
    solverSettings,
    onSave,
    onClose
}) => {
    const [localGeneral, setLocalGeneral] = useState<GeneralSettings>({ ...generalSettings });
    const [localSolver, setLocalSolver] = useState<SolverSettings>({ ...solverSettings });
    const [activeSection, setActiveSection] = useState<'general' | 'solver'>('general');

    const handleSave = () => {
        onSave(localGeneral, localSolver);
        onClose();
    };

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl shadow-2xl w-full max-w-md overflow-hidden flex flex-col max-h-[90vh] transition-colors">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 transition-colors">
                    <div className="flex items-center gap-2">
                        <h2 className="text-lg font-bold text-slate-900 dark:text-white tracking-tight">Application Settings</h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="cursor-pointer p-2 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Tabs */}
                <div className="flex border-b border-slate-200 dark:border-slate-700 transition-colors">
                    <button
                        onClick={() => setActiveSection('general')}
                        className={`cursor-pointer flex-1 py-3 text-sm font-medium transition-all flex items-center justify-center gap-2 ${activeSection === 'general'
                            ? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400 bg-blue-50 dark:bg-blue-400/5'
                            : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800'
                            }`}
                    >
                        General
                    </button>
                    <button
                        onClick={() => setActiveSection('solver')}
                        className={`cursor-pointer flex-1 py-3 text-sm font-medium transition-all flex items-center justify-center gap-2 ${activeSection === 'solver'
                            ? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400 bg-blue-50 dark:bg-blue-400/5'
                            : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800'
                            }`}
                    >
                        Solver
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-4 space-y-2 custom-scrollbar">
                    {activeSection === 'general' ? (
                        <div className="grid grid-cols-2 gap-2 animate-in fade-in slide-in-from-bottom-2">




                            <div className="flex items-center justify-between group p-3 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800/50 transition-colors">
                                <div className="space-y-1">
                                    <label className="text-sm font-semibold text-slate-700 dark:text-slate-200">Hide Grid</label>
                                </div>
                                <label className="relative inline-flex items-center cursor-pointer">
                                    <input
                                        type="checkbox"
                                        className="sr-only peer"
                                        checked={localGeneral.hideGrid}
                                        onChange={e => setLocalGeneral({ ...localGeneral, hideGrid: e.target.checked })}
                                    />
                                    <div className="w-11 h-6 bg-slate-200 dark:bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                                </label>
                            </div>

                            <div className="flex items-center justify-between group p-3 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800/50 transition-colors">
                                <div className="space-y-1">
                                    <label className="text-sm font-semibold text-slate-700 dark:text-slate-200">Hide Ruler</label>
                                </div>
                                <label className="relative inline-flex items-center cursor-pointer">
                                    <input
                                        type="checkbox"
                                        className="sr-only peer"
                                        checked={localGeneral.hideRuler}
                                        onChange={e => setLocalGeneral({ ...localGeneral, hideRuler: e.target.checked })}
                                    />
                                    <div className="w-11 h-6 bg-slate-200 dark:bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                                </label>
                            </div>

                            <div className="flex items-center justify-between group p-3 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800/50 transition-colors">
                                <div className="space-y-1">
                                    <label className="text-sm font-semibold text-slate-700 dark:text-slate-200">Snap to Grid</label>
                                </div>
                                <label className="relative inline-flex items-center cursor-pointer">
                                    <input
                                        type="checkbox"
                                        className="sr-only peer"
                                        checked={localGeneral.snapToGrid}
                                        onChange={e => setLocalGeneral({ ...localGeneral, snapToGrid: e.target.checked })}
                                    />
                                    <div className="w-11 h-6 bg-slate-200 dark:bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                                </label>
                            </div>

                            <div className="space-y-2 p-3 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800/50 transition-colors">
                                <label className="text-sm font-semibold text-slate-700 dark:text-slate-200">Snap Grid Spacing (m)</label>
                                <div className="flex items-center gap-4">
                                    <input
                                        type="number"
                                        min="0.1"
                                        max="5.0"
                                        step="0.1"
                                        className="input"
                                        value={localGeneral.snapSpacing}
                                        onChange={e => setLocalGeneral({ ...localGeneral, snapSpacing: parseFloat(e.target.value) })}
                                    />
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-2 animate-in fade-in slide-in-from-bottom-2">
                            <div className="grid grid-cols-2 gap-1 ">
                                <div className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800/50 transition-colors">
                                    <label className="itemlabel">Tolerance <MathRender tex="\epsilon" /></label>
                                    <input
                                        type="number"
                                        min="0.01"
                                        max="0.1"
                                        step="0.001"
                                        className="input"
                                        value={localSolver.tolerance}
                                        onChange={e => setLocalSolver({ ...localSolver, tolerance: parseFloat(e.target.value) })}
                                    />
                                </div>
                                <div className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800/50 transition-colors">
                                    <label className="itemlabel">Max Iterations <MathRender tex="n_{max}" /></label>
                                    <input
                                        type="number"
                                        min="1"
                                        max="100"
                                        step="1"
                                        className="input"
                                        value={localSolver.max_iterations}
                                        onChange={e => setLocalSolver({ ...localSolver, max_iterations: parseInt(e.target.value) })}
                                    />
                                </div>
                                <div className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800/50 transition-colors">
                                    <label className="itemlabel">Initial Step <MathRender tex="\Delta\lambda_0" /></label>
                                    <input
                                        type="number"
                                        min="0.01"
                                        max="1"
                                        step="0.01"
                                        className="input"
                                        value={localSolver.initial_step_size}
                                        onChange={e => setLocalSolver({ ...localSolver, initial_step_size: parseFloat(e.target.value) })}
                                    />
                                </div>
                                <div className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800/50 transition-colors">
                                    <label className="itemlabel">Max Load Frac</label>
                                    <input
                                        type="number"
                                        min="0.01"
                                        max="1"
                                        step="0.01"
                                        className="input"
                                        value={localSolver.max_load_fraction}
                                        onChange={e => setLocalSolver({ ...localSolver, max_load_fraction: parseFloat(e.target.value) })}
                                    />
                                </div>
                                <div className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800/50 transition-colors">
                                    <label className="itemlabel">Min Desired It.</label>
                                    <input
                                        type="number"
                                        className="input"
                                        min="1"
                                        max="10"
                                        step="1"
                                        value={localSolver.min_desired_iterations}
                                        onChange={e => setLocalSolver({ ...localSolver, min_desired_iterations: parseInt(e.target.value) })}
                                    />
                                </div>
                                <div className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800/50 transition-colors">
                                    <label className="itemlabel">Max Desired It.</label>
                                    <input
                                        type="number"
                                        className="input"
                                        min="1"
                                        max="10"
                                        step="1"
                                        value={localSolver.max_desired_iterations}
                                        onChange={e => setLocalSolver({ ...localSolver, max_desired_iterations: parseInt(e.target.value) })}
                                    />
                                </div>
                                <div className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800/50 transition-colors">
                                    <label className="itemlabel">Max Total Steps</label>
                                    <input
                                        type="number"
                                        className="input"
                                        min="1"
                                        max="1000"
                                        step="1"
                                        value={localSolver.max_steps}
                                        onChange={e => setLocalSolver({ ...localSolver, max_steps: parseInt(e.target.value) })}
                                    />
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-6 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/30 flex gap-3 transition-colors">
                    <button
                        onClick={onClose}
                        className="cursor-pointer flex-1 px-4 py-2.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-300 font-medium hover:bg-slate-100 dark:hover:bg-slate-700 transition-all"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSave}
                        className="cursor-pointer flex-1 px-4 py-2.5 rounded-lg bg-blue-600 text-white font-bold hover:bg-blue-500 shadow-lg shadow-blue-500/20 dark:shadow-blue-900/20 transition-all active:scale-[0.98]"
                    >
                        Save Changes
                    </button>
                </div>
            </div>
        </div>
    );
};
