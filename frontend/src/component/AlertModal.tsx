import React from 'react';
import { X, AlertTriangle, AlertCircle } from 'lucide-react';

export type AlertType = 'info' | 'warning' | 'error' | 'success';

interface AlertModalProps {
    isOpen: boolean;
    title: string;
    message: string;
    type?: AlertType;
    onClose: () => void;
}

export const AlertModal: React.FC<AlertModalProps> = ({
    isOpen,
    title,
    message,
    type = 'info',
    onClose
}) => {
    if (!isOpen) return null;

    const getIcon = () => {
        switch (type) {
            case 'warning': return <AlertTriangle className="w-6 h-6 text-amber-500" />;
            case 'error': return <AlertCircle className="w-6 h-6 text-rose-500" />;
        }
    };

    const getBorderColor = () => {
        switch (type) {
            case 'warning': return 'border-amber-500/50';
            case 'error': return 'border-rose-500/50';
        }
    };

    return (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-slate-950/40 backdrop-blur-sm animate-in fade-in duration-200">
            <div
                className={`bg-white dark:bg-slate-900 w-full max-w-md rounded-2xl shadow-2xl border ${getBorderColor()} overflow-hidden animate-in zoom-in-95 slide-in-from-bottom-4 duration-300`}
                onClick={(e) => e.stopPropagation()}
            >
                <div className="p-6">
                    <div className="flex items-start gap-4">
                        {type !== 'success' && (
                            <div className="p-2 rounded-xl bg-slate-50 dark:bg-slate-800 flex-shrink-0">
                                {getIcon()}
                            </div>
                        )}
                        <div className="flex-1 min-w-0">
                            <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2 truncate">
                                {title}
                            </h3>
                            <p className="text-slate-600 dark:text-slate-400 text-sm leading-relaxed whitespace-pre-wrap">
                                {message}
                            </p>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>
                </div>

                <div className="px-6 py-4 bg-slate-50 dark:bg-slate-800/50 flex justify-end">
                    <button
                        onClick={onClose}
                        className="cursor-pointer px-6 py-2 bg-slate-900 dark:bg-white text-white dark:text-slate-900 font-bold rounded-xl hover:opacity-90 transition-opacity focus:outline-none focus:ring-2 focus:ring-slate-400 dark:focus:ring-slate-500"
                    >
                        OK
                    </button>
                </div>
            </div>
        </div>
    );
};
