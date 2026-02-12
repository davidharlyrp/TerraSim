import { Folder, Square, ArrowDownToDot, Pen, ChartNoAxesColumnDecreasing, ChartNoAxesColumnIncreasing, ArrowDownToLine, ArrowDown, Pentagon } from 'lucide-react';

interface InputToolbarProps {
    drawMode: string | null;
    onDrawModeChange: (mode: string | null) => void;
    onImportDXF?: (file: File) => void;
}

export const InputToolbar: React.FC<InputToolbarProps> = ({ drawMode, onDrawModeChange, onImportDXF }) => {
    return (
        <div className="absolute top-16 right-4 flex flex-col gap-2 p-2 bg-white dark:bg-slate-800 rounded-xl shadow-lg border border-slate-200 dark:border-slate-700 z-5">
            <label
                className="cursor-pointer w-10 h-10 p-2 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors flex items-center justify-center relative group"
                title="Import DXF (Polylines)"
            >
                <input
                    type="file"
                    accept=".dxf"
                    className="hidden"
                    onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file && onImportDXF) {
                            onImportDXF(file);
                        }
                        e.target.value = ''; // Reset input
                    }}
                />
                <Folder className="w-5 h-5" />
                <ArrowDown className="absolute bottom-1 right-1 w-3 h-3 bg-white dark:bg-slate-800 rounded-full" />
                <span className="absolute right-12 bg-slate-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                    Import DXF
                </span>
            </label>

            <div className="w-full h-px bg-slate-200 dark:bg-slate-700 my-1" />

            <button
                onClick={() => onDrawModeChange(drawMode === 'polygon' ? null : 'polygon')}
                title="Draw Polygon"
                className={`cursor-pointer w-10 h-10 p-2 rounded-lg transition-colors relative group flex items-center justify-center ${drawMode === 'polygon' ? 'bg-blue-100 dark:bg-blue-600/20 text-blue-600 dark:text-blue-500' : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
                    }`}
            >
                <div className="relative">
                    <Pentagon className="w-5 h-5" />
                    <Pen className='absolute -top-1 -right-1 w-3 h-3' />
                </div>
                <span className="absolute right-12 bg-slate-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                    Draw Polygon
                </span>
            </button>

            <button
                onClick={() => onDrawModeChange(drawMode === 'rectangle' ? null : 'rectangle')}
                title="Draw Rectangle"
                className={`cursor-pointer w-10 h-10 p-2 rounded-lg transition-colors relative group flex items-center justify-center ${drawMode === 'rectangle' ? 'bg-blue-100 dark:bg-blue-600/20 text-blue-600 dark:text-blue-500' : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
                    }`}
            >
                <div className="relative">
                    <Square className="w-5 h-5" />
                    <Pen className='absolute -top-1 -right-1 w-3 h-3' />
                </div>
                <span className="absolute right-12 bg-slate-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                    Draw Rectangle
                </span>
            </button>

            <button
                onClick={() => onDrawModeChange(drawMode === 'point_load' ? null : 'point_load')}
                title="Draw Point Load"
                className={`cursor-pointer w-10 h-10 p-2 rounded-lg transition-colors relative group flex items-center justify-center ${drawMode === 'point_load' ? 'bg-blue-100 dark:bg-blue-600/20 text-blue-600 dark:text-blue-500' : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
                    }`}
            >
                <div className="relative">
                    <ArrowDownToDot className="w-5 h-5" />
                    <Pen className='absolute -top-1 -right-1 w-3 h-3' />
                </div>
                <span className="absolute right-12 bg-slate-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                    Draw Point Load
                </span>
            </button>

            <button
                onClick={() => onDrawModeChange(drawMode === 'line_load' ? null : 'line_load')}
                title="Draw Line Load"
                className={`cursor-pointer w-10 h-10 p-2 rounded-lg transition-colors relative group flex items-center justify-center ${drawMode === 'line_load' ? 'bg-blue-100 dark:bg-blue-600/20 text-blue-600 dark:text-blue-500' : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
                    }`}
            >
                <div className="relative">
                    <ArrowDownToLine className="w-5 h-5" />
                    <Pen className='absolute -top-1 -right-1 w-3 h-3' />
                </div>
                <span className="absolute right-12 bg-slate-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                    Draw Line Load
                </span>
            </button>

            <div className="w-full h-px bg-slate-200 dark:bg-slate-700 my-1" />

            <button
                onClick={() => onDrawModeChange(drawMode === 'water_level' ? null : 'water_level')}
                title="Draw Water Level"
                className={`cursor-pointer w-10 h-10 p-2 rounded-lg transition-colors relative group flex items-center justify-center ${drawMode === 'water_level' ? 'bg-blue-100 dark:bg-blue-600/20 text-blue-600 dark:text-blue-500' : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
                    }`}
            >
                <div className="relative w-5 h-5">
                    <ChartNoAxesColumnIncreasing className='absolute bottom-0 -left-0.5 w-4 h-4 -rotate-90' />
                    <ChartNoAxesColumnDecreasing className='absolute top-1 -right-0.5 w-4 h-4 rotate-90' />
                    <Pen className='absolute -top-1 -right-1 w-3 h-3' />
                </div>
                <span className="absolute right-12 bg-slate-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                    Draw Water Level
                </span>
            </button>
        </div>
    );
};
