import React, { useState, useEffect } from 'react';
import { EmbeddedBeamMaterial } from '../types';
import { MathRender } from './Math';

interface EmbeddedBeamMaterialModalProps {
    material: EmbeddedBeamMaterial;
    onSave: (mat: EmbeddedBeamMaterial) => void;
    onClose: () => void;
}

const calculateProperties = (shape: string, width?: number, diameter?: number, thickness?: number) => {
    let area = 0;
    let momentOfInertia = 0;
    let width_calc = width || 0;
    let diameter_calc = diameter || 0;
    let thickness_calc = thickness || 0;

    if (shape === "square") {
        area = width_calc * width_calc;
        momentOfInertia = (width_calc * width_calc * width_calc * width_calc) / 12;
    } else if (shape === "circular") {
        area = Math.PI * (diameter_calc / 2) * (diameter_calc / 2);
        momentOfInertia = (Math.PI * Math.pow(diameter_calc, 4)) / 64;
    } else if (shape === "circular_with_void") {
        const outerArea = Math.PI * (diameter_calc / 2) * (diameter_calc / 2);
        const innerDiameter = Math.max(0, diameter_calc - 2 * thickness_calc);
        const innerArea = Math.PI * (innerDiameter / 2) * (innerDiameter / 2);
        area = outerArea - innerArea;
        momentOfInertia = (Math.PI * (Math.pow(diameter_calc, 4) - Math.pow(innerDiameter, 4))) / 64;
    }

    return { area, momentOfInertia };
};

export const EmbeddedBeamMaterialModal: React.FC<EmbeddedBeamMaterialModalProps> = ({ material, onSave, onClose }) => {
    const [edited, setEdited] = useState<EmbeddedBeamMaterial>({ ...material });

    // Auto-calculate properties when shape or dimensions change
    useEffect(() => {
        if (edited.shape !== "user_defined") {
            const { area, momentOfInertia } = calculateProperties(
                edited.shape,
                edited.width,
                edited.diameter,
                edited.thickness
            );
            setEdited(prev => ({
                ...prev,
                crossSectionArea: parseFloat(area.toFixed(6)),
                momentOfInertia: parseFloat(momentOfInertia.toFixed(8))
            }));
        }
    }, [edited.shape, edited.width, edited.diameter, edited.thickness]);

    const isUserDefined = edited.shape === "user_defined";

    return (
        <div className="fixed inset-0 w-screen h-screen bg-black/60 backdrop-blur-sm flex items-center justify-center z-[1000] p-4 animate-in fade-in duration-200">
            <div className="bg-white dark:bg-slate-900 p-8 rounded-xl w-full max-w-[800px] max-h-[70dvh] overflow-y-auto custom-scrollbar border border-slate-200 dark:border-slate-700 shadow-2xl text-slate-900 dark:text-white transition-colors">
                <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100 border-b border-slate-200 dark:border-slate-800 pb-2">Edit Beam Material: <span className="text-gray-600 dark:text-gray-400">{edited.name}</span></h3>

                <div className="grid md:grid-cols-2 grid-cols-1 gap-6">
                    <div className='border-r border-slate-200 dark:border-slate-800 pr-2'>
                        <div className='titlelabel mt-2 border-b border-slate-200 dark:border-slate-800 pb-1'>
                            General Information
                        </div>
                        <div className="flex flex-col gap-1 border-b border-slate-200 dark:border-slate-800 py-4">
                            <div className="grid grid-cols-2 items-center gap-1">
                                <span className="itemlabel">Name</span>
                                <input
                                    type="text"
                                    value={edited.name}
                                    onChange={e => setEdited({ ...edited, name: e.target.value })}
                                    className="input"
                                />
                            </div>

                            <div className="grid grid-cols-2 items-center gap-1">
                                <span className="itemlabel">Color</span>
                                <div className="flex items-center gap-2">
                                    <input
                                        type="color"
                                        value={edited.color}
                                        onChange={e => setEdited({ ...edited, color: e.target.value })}
                                        className="w-6 h-6 p-0 border-none bg-transparent cursor-pointer rounded overflow-hidden"
                                    />
                                    <span className="itemlabel w-[100px]">{edited.color}</span>
                                </div>
                            </div>
                        </div>

                        <div className='titlelabel mt-2 border-b border-slate-200 dark:border-slate-800 pb-1'>
                            Geometry & Stiffness
                        </div>
                        <div className="flex flex-col gap-1 border-b border-slate-200 dark:border-slate-800 py-4">
                            <div className="grid grid-cols-4 items-center gap-1">
                                <span className="itemlabel col-span-2">Shape</span>
                                <select
                                    value={edited.shape}
                                    onChange={e => setEdited({ ...edited, shape: e.target.value })}
                                    className="input col-span-2"
                                >
                                    <option value="user_defined">User Defined</option>
                                    <option value="square">Square</option>
                                    <option value="circular">Circular</option>
                                    <option value="circular_with_void">Circular with void</option>
                                </select>

                                {edited.shape === "square" && (
                                    <>
                                        <span className="itemlabel col-span-2">Width, <MathRender tex="b" /></span>
                                        <input
                                            type="number"
                                            value={edited.width}
                                            onChange={e => setEdited({ ...edited, width: Number(e.target.value) })}
                                            className="input"
                                        />
                                        <span className="itemlabel text-center"><MathRender tex="m" /></span>
                                    </>
                                )}

                                {(edited.shape === "circular" || edited.shape === "circular_with_void") && (
                                    <>
                                        <span className="itemlabel col-span-2">Diameter, <MathRender tex="D" /></span>
                                        <input
                                            type="number"
                                            value={edited.diameter}
                                            onChange={e => setEdited({ ...edited, diameter: Number(e.target.value) })}
                                            className="input"
                                        />
                                        <span className="itemlabel text-center"><MathRender tex="m" /></span>
                                    </>
                                )}

                                {edited.shape === "circular_with_void" && (
                                    <>
                                        <span className="itemlabel col-span-2">Wall Thickness, <MathRender tex="t" /></span>
                                        <input
                                            type="number"
                                            value={edited.thickness}
                                            onChange={e => setEdited({ ...edited, thickness: Number(e.target.value) })}
                                            className="input"
                                        />
                                        <span className="itemlabel text-center"><MathRender tex="m" /></span>
                                    </>
                                )}

                                <span className="itemlabel col-span-2">Young's Modulus, <MathRender tex="E" /></span>
                                <input
                                    type="number"
                                    value={edited.youngsModulus}
                                    onChange={e => setEdited({ ...edited, youngsModulus: Number(e.target.value) })}
                                    className="input"
                                />
                                <span className="itemlabel text-center"><MathRender tex="kN/m^2" /></span>

                                <span className="itemlabel col-span-2">Area, <MathRender tex="A" /></span>
                                <input
                                    type="number"
                                    value={edited.crossSectionArea}
                                    onChange={e => setEdited({ ...edited, crossSectionArea: Number(e.target.value) })}
                                    disabled={!isUserDefined}
                                    className={`input ${!isUserDefined ? 'bg-slate-100 dark:bg-slate-800 cursor-not-allowed opacity-70' : ''}`}
                                />
                                <span className="itemlabel text-center"><MathRender tex="m^2" /></span>

                                <span className="itemlabel col-span-2">Inertia, <MathRender tex="I" /></span>
                                <input
                                    type="number"
                                    value={edited.momentOfInertia}
                                    onChange={e => setEdited({ ...edited, momentOfInertia: Number(e.target.value) })}
                                    disabled={!isUserDefined}
                                    className={`input ${!isUserDefined ? 'bg-slate-100 dark:bg-slate-800 cursor-not-allowed opacity-70' : ''}`}
                                />
                                <span className="itemlabel text-center"><MathRender tex="m^4" /></span>
                            </div>
                        </div>
                    </div>

                    <div>
                        <div className='titlelabel mt-2 border-b border-slate-200 dark:border-slate-800 pb-1'>
                            Properties & Interface
                        </div>
                        <div className="flex flex-col gap-1 border-b border-slate-200 dark:border-slate-800 py-4">
                            <div className="grid grid-cols-4 items-center gap-1">
                                <span className="itemlabel col-span-2">Weight per Length, <MathRender tex="w" /></span>
                                <input
                                    type="number"
                                    value={edited.unitWeight}
                                    onChange={e => setEdited({ ...edited, unitWeight: Number(e.target.value) })}
                                    className="input"
                                />
                                <span className="itemlabel text-center"><MathRender tex="kN/m" /></span>

                                <span className="itemlabel col-span-2">Spacing, <MathRender tex="L_{spacing}" /></span>
                                <input
                                    type="number"
                                    value={edited.spacing}
                                    onChange={e => setEdited({ ...edited, spacing: Number(e.target.value) })}
                                    className="input"
                                />
                                <span className="itemlabel text-center"><MathRender tex="m" /></span>

                                <span className="itemlabel col-span-2">Max Skin Friction, <MathRender tex="T_{max}" /></span>
                                <input
                                    type="number"
                                    value={edited.skinFrictionMax}
                                    onChange={e => setEdited({ ...edited, skinFrictionMax: Number(e.target.value) })}
                                    className="input"
                                />
                                <span className="itemlabel text-center"><MathRender tex="kN/m" /></span>

                                <span className="itemlabel col-span-2">Max Tip Resistance, <MathRender tex="F_{max}" /></span>
                                <input
                                    type="number"
                                    value={edited.tipResistanceMax}
                                    onChange={e => setEdited({ ...edited, tipResistanceMax: Number(e.target.value) })}
                                    className="input"
                                />
                                <span className="itemlabel text-center"><MathRender tex="kN" /></span>
                            </div>
                        </div>

                        <div className="mt-4 p-3 bg-slate-50 dark:bg-slate-900/20 rounded text-xs text-slate-800 dark:text-slate-200">
                            <strong>Note on Spacing:</strong> All properties (EA, EI, Tmax, Fmax) are defined for a single pile. The solver automatically divides these by Spacing to get equivalent properties per meter width for the 2D plane strain model.
                        </div>
                    </div>
                </div>

                <div className="flex justify-end gap-3 mt-10 p-4 -m-8 bg-slate-100 dark:bg-slate-800/50 rounded-b-xl border-t border-slate-200 dark:border-slate-800 transition-colors">
                    <button onClick={onClose} className="cursor-pointer px-4 py-2 text-sm text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 transition-colors">Cancel</button>
                    <button onClick={() => onSave(edited)} className="cursor-pointer px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-bold rounded shadow-lg shadow-blue-500/20 transition-all">Save Changes</button>
                </div>
            </div>
        </div>
    );
};
