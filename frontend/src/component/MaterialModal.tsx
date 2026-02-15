import React, { useState } from 'react';
import { Material, MaterialModel, DrainageType } from '../types';
import { MathRender } from './Math';

interface MaterialModalProps {
    material: Material;
    onSave: (mat: Material) => void;
    onClose: () => void;
}

export const MaterialModal: React.FC<MaterialModalProps> = ({ material, onSave, onClose }) => {
    const [edited, setEdited] = useState<Material>({ ...material });

    return (
        <div className="fixed inset-0 w-screen h-screen bg-black/60 backdrop-blur-sm flex items-center justify-center z-[1000] p-4 animate-in fade-in duration-200">
            <div className="bg-white dark:bg-slate-900 p-8 rounded-xl w-full max-w-[800px] max-h-[70vh] overflow-y-auto custom-scrollbar border border-slate-200 dark:border-slate-700 shadow-2xl text-slate-900 dark:text-white transition-colors">
                <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100 border-b border-slate-200 dark:border-slate-800 pb-2">Edit Material: <span className="text-gray-600 dark:text-gray-400">{edited.name}</span></h3>

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

                        <div className="flex flex-col gap-1 border-b border-slate-200 dark:border-slate-800 py-4">
                            <div className="grid grid-cols-2 items-center gap-1">
                                <span className="itemlabel">Material Model</span>
                                <select
                                    value={edited.material_model}
                                    onChange={e => {
                                        const val = e.target.value as MaterialModel;
                                        setEdited({
                                            ...edited,
                                            material_model: val,
                                            drainage_type:
                                                val === MaterialModel.LINEAR_ELASTIC ? DrainageType.NON_POROUS :
                                                    val === MaterialModel.HOEK_BROWN ? DrainageType.DRAINED :
                                                        edited.drainage_type
                                        });
                                    }}
                                    className="input"
                                >
                                    <option value={MaterialModel.LINEAR_ELASTIC}>Linear Elastic</option>
                                    <option value={MaterialModel.MOHR_COULOMB}>Mohr Coulomb</option>
                                    <option value={MaterialModel.HOEK_BROWN}>Hoek-Brown (Rock)</option>
                                    <option disabled title="Under development">Hardening Soil</option>
                                    {/* <option disabled title="Under development">Soft Soil</option> */}
                                    <option disabled title="Under development">Cam Clay</option>
                                </select>
                            </div>

                            <div className="grid grid-cols-2 items-center gap-1">
                                <span className="itemlabel">Drainage Type</span>
                                <select
                                    value={edited.drainage_type}
                                    disabled={edited.material_model === MaterialModel.LINEAR_ELASTIC}
                                    onChange={e => setEdited({ ...edited, drainage_type: e.target.value as DrainageType })}
                                    className="input"
                                >
                                    <option value={DrainageType.DRAINED}>Drained</option>
                                    {edited.material_model === MaterialModel.MOHR_COULOMB && <option value={DrainageType.UNDRAINED_A}>Undrained A</option>}
                                    {edited.material_model === MaterialModel.MOHR_COULOMB && <option value={DrainageType.UNDRAINED_B}>Undrained B</option>}
                                    {edited.material_model === MaterialModel.MOHR_COULOMB && <option value={DrainageType.UNDRAINED_C}>Undrained C</option>}
                                    {(edited.material_model === MaterialModel.LINEAR_ELASTIC || edited.material_model === MaterialModel.HOEK_BROWN) && <option value={DrainageType.NON_POROUS}>Non Porous</option>}
                                </select>
                            </div>
                        </div>

                        {edited.material_model === MaterialModel.HOEK_BROWN && (
                            <div className="flex flex-col gap-1 border-b border-slate-200 dark:border-slate-800 py-4">
                                <span className="italic text-[10px] text-slate-600 dark:text-slate-400 dark:font-light">* Hoek-Brown material model will take much more time to solve.</span>
                            </div>
                        )}
                    </div>

                    <div>
                        <div className='titlelabel mt-2 border-b border-slate-200 dark:border-slate-800 pb-1'>
                            Soil Properties
                        </div>
                        <div className="flex flex-col gap-1 border-b border-slate-200 dark:border-slate-800 py-4">
                            <div className="grid grid-cols-4 items-center gap-1">
                                {(edited.material_model === MaterialModel.LINEAR_ELASTIC || edited.drainage_type === DrainageType.UNDRAINED_C) ? (
                                    <>
                                        <span className="itemlabel col-span-2">Young's Modulus, <MathRender tex="E" /></span>
                                        <input
                                            type="number"
                                            value={edited.youngsModulus}
                                            onChange={e => setEdited({ ...edited, youngsModulus: Number(e.target.value) })}
                                            className="input"
                                        />
                                        <span className="itemlabel text-center"><MathRender tex="kN/m^2" /></span>
                                    </>
                                ) : (
                                    <>
                                        <span className="itemlabel col-span-2">Young's Modulus, <MathRender tex="E'" /></span>
                                        <input
                                            type="number"
                                            value={edited.effyoungsModulus}
                                            onChange={e => setEdited({ ...edited, effyoungsModulus: Number(e.target.value) })}
                                            className="input"
                                        />
                                        <span className="itemlabel text-center"><MathRender tex="kN/m^2" /></span>
                                    </>
                                )}


                                <span className="itemlabel col-span-2">
                                    Poisson's Ratio, <MathRender tex="\nu" />
                                </span>
                                <input
                                    type="number"
                                    step="0.01"
                                    value={edited.poissonsRatio}
                                    onChange={e => setEdited({ ...edited, poissonsRatio: Number(e.target.value) })}
                                    className="input col-span-2"
                                />

                                <span className="itemlabel col-span-2">
                                    {edited.drainage_type === DrainageType.NON_POROUS ? "Unit Weight, " : "Unit Weight Unsaturated, "}
                                    <MathRender tex="\gamma_n" />
                                </span>
                                <input
                                    type="number"
                                    value={edited.unitWeightUnsaturated}
                                    onChange={e => setEdited({ ...edited, unitWeightUnsaturated: Number(e.target.value) })}
                                    className="input"
                                />
                                <span className="itemlabel text-center"><MathRender tex="kN/m^3" /></span>


                                {edited.drainage_type !== DrainageType.NON_POROUS && (
                                    <>
                                        <span className="itemlabel col-span-2">
                                            Unit Weight Saturated, <MathRender tex="\gamma_{sat}" />
                                        </span>
                                        <input
                                            type="number"
                                            value={edited.unitWeightSaturated}
                                            onChange={e => setEdited({ ...edited, unitWeightSaturated: Number(e.target.value) })}
                                            className="input"
                                        />
                                        <span className="itemlabel text-center"><MathRender tex="kN/m^3" /></span>
                                    </>
                                )}
                            </div>

                            {((edited.drainage_type === DrainageType.DRAINED || edited.drainage_type === DrainageType.UNDRAINED_A) && edited.material_model === MaterialModel.MOHR_COULOMB) && (
                                <div className="grid grid-cols-4 items-center gap-1">
                                    <span className="itemlabel col-span-2">
                                        Cohesion, <MathRender tex="c'" />
                                    </span>
                                    <input
                                        type="number"
                                        value={edited.cohesion}
                                        onChange={e => setEdited({ ...edited, cohesion: Number(e.target.value) })}
                                        className="input"
                                    />
                                    <span className="itemlabel text-center"><MathRender tex="kN/m^2" /></span>


                                    <span className="itemlabel col-span-2">
                                        Friction Angle, <MathRender tex="\phi'" />
                                    </span>
                                    <input
                                        type="number"
                                        value={edited.frictionAngle}
                                        onChange={e => setEdited({ ...edited, frictionAngle: Number(e.target.value) })}
                                        className="input"
                                    />
                                    <span className="itemlabel text-center"><MathRender tex="^\circ" /></span>

                                    <span className="itemlabel col-span-2">
                                        Lateral Pressure Coeff, <MathRender tex="K_0" />
                                    </span>
                                    <input
                                        type="number"
                                        placeholder={(1 - Math.sin((edited.frictionAngle || 0) * Math.PI / 180)).toFixed(3)}
                                        value={edited.k0_x ?? ""}
                                        onChange={e => setEdited({ ...edited, k0_x: e.target.value ? Number(e.target.value) : undefined })}
                                        className="input col-span-2"
                                    />
                                </div>
                            )}

                            {(edited.drainage_type === DrainageType.UNDRAINED_B || edited.drainage_type === DrainageType.UNDRAINED_C || edited.material_model === MaterialModel.MOHR_COULOMB) && (
                                <div className="grid grid-cols-4 items-center gap-1">
                                    <span className="itemlabel col-span-2">
                                        Shear Strength, <MathRender tex="S_u" />
                                    </span>
                                    <input
                                        type="number"
                                        value={edited.undrainedShearStrength}
                                        onChange={e => setEdited({ ...edited, undrainedShearStrength: Number(e.target.value) })}
                                        className="input"
                                    />
                                    <span className="itemlabel text-center"><MathRender tex="kN/m^2" /></span>

                                    <span className="itemlabel col-span-2">
                                        <MathRender tex="K_{0x}" />
                                        <div className="text-[10px] text-slate-500 dark:text-slate-400">(Auto via Poisson's Ratio if empty)</div>
                                    </span>
                                    <input
                                        type="number"
                                        placeholder={(edited.poissonsRatio ? (edited.poissonsRatio / (1 - edited.poissonsRatio)).toFixed(3) : "0.5")}
                                        value={edited.k0_x ?? ""}
                                        onChange={e => setEdited({ ...edited, k0_x: e.target.value ? Number(e.target.value) : undefined })}
                                        className="input col-span-2"
                                    />
                                </div>
                            )}

                            {edited.material_model === MaterialModel.HOEK_BROWN && (
                                <div className="grid grid-cols-4 items-center gap-1">
                                    <span className="itemlabel col-span-2">
                                        UCS Rock, <MathRender tex="\sigma_{ci}" />
                                    </span>
                                    <input
                                        type="number"
                                        value={edited.sigma_ci || ""}
                                        onChange={e => setEdited({ ...edited, sigma_ci: Number(e.target.value) })}
                                        className="input"
                                    />
                                    <span className="itemlabel text-center"><MathRender tex="kN/m^2" /></span>

                                    <span className="itemlabel col-span-2">
                                        GSI Index
                                    </span>
                                    <input
                                        type="number"
                                        value={edited.gsi || ""}
                                        min="0"
                                        max="100"
                                        onChange={e => {
                                            const gsi = Number(e.target.value);
                                            const mi = edited.mi || 10;
                                            const D = edited.disturbFactor || 0;
                                            const mb = mi * Math.exp((gsi - 100) / (28 - 14 * D));
                                            const s = Math.exp((gsi - 100) / (9 - 3 * D));
                                            const a = 0.5 + (1 / 6) * (Math.exp(-gsi / 15) - Math.exp(-20 / 3));
                                            setEdited({ ...edited, gsi, m_b: mb, s, a });
                                        }}
                                        className="input"
                                    />
                                    <span className="itemlabel text-center">( 0-100 )</span>

                                    <span className="itemlabel col-span-2">
                                        Intact Parameter, <MathRender tex="m_i" />
                                    </span>
                                    <input
                                        type="number"
                                        value={edited.mi || ""}
                                        min="5"
                                        max="35"
                                        onChange={e => {
                                            const mi = Number(e.target.value);
                                            const gsi = edited.gsi || 50;
                                            const D = edited.disturbFactor || 0;
                                            const mb = mi * Math.exp((gsi - 100) / (28 - 14 * D));
                                            setEdited({ ...edited, mi, m_b: mb });
                                        }}
                                        className="input"
                                    />
                                    <span className="itemlabel text-center">( 5-35 )</span>

                                    <span className="itemlabel col-span-2">
                                        Disturbance Factor, <MathRender tex="D" />
                                    </span>
                                    <input
                                        type="number"
                                        step="0.1"
                                        value={edited.disturbFactor ?? ""}
                                        min="0"
                                        max="1"
                                        onChange={e => {
                                            const D = Number(e.target.value);
                                            const gsi = edited.gsi || 50;
                                            const mi = edited.mi || 10;
                                            const mb = mi * Math.exp((gsi - 100) / (28 - 14 * D));
                                            const s = Math.exp((gsi - 100) / (9 - 3 * D));
                                            setEdited({ ...edited, disturbFactor: D, m_b: mb, s });
                                        }}
                                        className="input"
                                    />
                                    <span className="itemlabel text-center">( 0-1 )</span>

                                    <span className="itemlabel col-span-2 mt-1">
                                        Lateral Pressure Coeff, <MathRender tex="K_0" />
                                    </span>
                                    <input
                                        type="number"
                                        placeholder={(edited.poissonsRatio / (1 - edited.poissonsRatio)).toFixed(3)}
                                        value={edited.k0_x ?? ""}
                                        onChange={e => setEdited({ ...edited, k0_x: e.target.value ? Number(e.target.value) : undefined })}
                                        className="input col-span-2"
                                    />
                                    <div className="col-span-4 grid grid-cols-4 gap-1 mt-2 pt-2 border-t border-slate-100 dark:border-slate-800 opacity-60">
                                        <span className="itemlabel flex items-center">Calculated <MathRender tex="m_b" /></span>
                                        <input type="number" value={edited.m_b?.toFixed(4) || ""} disabled className="input bg-slate-50 dark:bg-slate-800" />
                                        <span className="itemlabel ml-4 flex items-center">Calculated <MathRender tex="s" /></span>
                                        <input type="number" value={edited.s?.toFixed(4) || ""} disabled className="input bg-slate-50 dark:bg-slate-800" />
                                        <span className="itemlabel flex items-center">Calculated <MathRender tex="a" /></span>
                                        <input type="number" value={edited.a?.toFixed(4) || ""} disabled className="input bg-slate-50 dark:bg-slate-800" />
                                    </div>
                                </div>
                            )}
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
