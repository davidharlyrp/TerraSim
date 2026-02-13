import React from 'react';
import { MeshResponse, MeshSettings } from '../types';

interface MeshSidebarProps {
    mesh: MeshResponse | null;
    isGenerating: boolean;
    onGenerate: () => void;
    meshSettings: MeshSettings;
    onSettingsChange: (settings: MeshSettings) => void;
}

export const MeshSidebar: React.FC<MeshSidebarProps> = ({
    mesh,
    isGenerating,
    onGenerate,
    meshSettings,
    onSettingsChange
}) => {
    return (
        <div className="md:w-full w-[calc(100vw-40px)] md:h-full h-[calc(100vh-50px)] overflow-y-auto flex flex-col border-r md:border-0 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900">
            <div className="label2">Mesh Options</div>

            {/* Global Mesh Settings */}
            <div className="p-4 bg-slate-50 dark:bg-slate-900">
                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                        <label className="itemlabel">Mesh Size (m)</label>
                        <input
                            type="number"
                            min="0.1"
                            max="50.0"
                            step="0.1"
                            value={meshSettings.mesh_size}
                            onChange={(e) => onSettingsChange({ ...meshSettings, mesh_size: parseFloat(e.target.value) || 0.1 })}
                            className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 text-xs p-2 rounded outline-none focus:border-blue-500 transition-colors"
                        />
                    </div>

                    <div className="space-y-1.5">
                        <label className="itemlabel">Refinement</label>
                        <input
                            type="number"
                            min="0.1"
                            max="10.0"
                            step="0.1"
                            value={meshSettings.boundary_refinement_factor}
                            onChange={(e) => onSettingsChange({ ...meshSettings, boundary_refinement_factor: parseFloat(e.target.value) || 1.0 })}
                            className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 text-xs p-2 rounded outline-none focus:border-blue-500 transition-colors"
                        />
                    </div>
                </div>

                <button
                    onClick={onGenerate}
                    disabled={isGenerating}
                    className={`cursor-pointer w-full py-3 mt-4 rounded-lg font-bold text-white transition-all ${isGenerating ? 'bg-slate-700 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-500 shadow-lg shadow-blue-500/20'
                        }`}
                >
                    {isGenerating ? 'Generating...' : 'Generate Mesh'}
                </button>
            </div>

            {mesh && mesh.success && (
                <div className="flex-1 overflow-y-auto custom-scrollbar bg-slate-50 dark:bg-slate-900">
                    <div className="label2">Summary</div>
                    <div className="p-4 py-2 text-xs grid grid-cols-2 gap-2 bg-slate-50 dark:bg-slate-900">
                        <div className="text-slate-600 dark:text-slate-400">Nodes:</div>
                        <div className="font-semibold text-slate-900 dark:text-slate-100">{mesh.nodes.length}</div>
                        <div className="text-slate-600 dark:text-slate-400">Elements:</div>
                        <div className="font-semibold text-slate-900 dark:text-slate-100">{mesh.elements.length}</div>
                    </div>

                    {/* <div className="dropdownlabel">Elements Table</div>
                    <div className="p-2">
                        <table className="w-full text-[10px] border-collapse">
                            <thead>
                                <tr className="text-left text-slate-400 border-b border-slate-700">
                                    <th className="p-1">ID</th>
                                    <th className="p-1">Nodes</th>
                                </tr>
                            </thead>
                            <tbody>
                                {mesh.elements.slice(0, 100).map((el, i) => (
                                    <tr key={i} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors text-slate-300">
                                        <td className="p-1">{i + 1}</td>
                                        <td className="p-1 font-mono opacity-80">{el.join(', ')}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                        {mesh.elements.length > 100 && (
                            <div className="text-[10px] p-2 text-center text-slate-500 bg-slate-800/20 rounded-b mt-1 italic">
                                Showing first 100 of {mesh.elements.length} elements
                            </div>
                        )}
                    </div> */}
                </div>
            )}
        </div>
    );
};
