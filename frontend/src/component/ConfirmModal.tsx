import React from 'react';
import { X } from 'lucide-react';

interface ConfirmModalProps {
    isOpen: boolean;
    title: string;
    message: string;
    onConfirm: () => void;
    onCancel: () => void;
    confirmText?: string;
    cancelText?: string;
    isDestructive?: boolean;
}

export const ConfirmModal: React.FC<ConfirmModalProps> = ({
    isOpen,
    title,
    message,
    onConfirm,
    onCancel,
    confirmText = 'Confirm',
    cancelText = 'Cancel',
    isDestructive = false
}) => {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-slate-950/40 backdrop-blur-sm animate-in fade-in duration-200">
            <div
                className="bg-white dark:bg-slate-900 w-full max-w-md rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 overflow-hidden animate-in zoom-in-95 slide-in-from-bottom-4 duration-300"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="p-6">
                    <div className="flex items-start gap-4">
                        <div className="flex-1 min-w-0">
                            <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2 truncate">
                                {title}
                            </h3>
                            <p className="text-slate-600 dark:text-slate-400 text-sm leading-relaxed whitespace-pre-wrap">
                                {message}
                            </p>
                        </div>
                        <button
                            onClick={onCancel}
                            className="cursor-pointer p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>
                </div>

                <div className="px-6 py-4 bg-slate-50 dark:bg-slate-800/50 flex gap-3 justify-end">
                    <button
                        onClick={onCancel}
                        className="cursor-pointer px-4 py-2 text-slate-600 dark:text-slate-400 font-bold rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors focus:outline-none"
                    >
                        {cancelText}
                    </button>
                    <button
                        onClick={onConfirm}
                        className={`cursor-pointer px-6 py-2 text-white font-bold rounded-xl hover:opacity-90 transition-opacity focus:outline-none focus:ring-2 ${isDestructive ? 'bg-rose-500 focus:ring-rose-400' : 'bg-slate-900 dark:bg-white dark:text-slate-900 focus:ring-slate-400'}`}
                    >
                        {confirmText}
                    </button>
                </div>
            </div>
        </div>
    );
};
