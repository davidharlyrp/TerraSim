import React, { useState, useRef } from 'react';
import { X, Image as ImageIcon, Loader2, AlertCircle } from 'lucide-react';
import { pb } from '../pb';
import { APP_VERSION } from '../version';
import { useAuth } from '../context/AuthContext';

interface FeedbackModalProps {
    onClose: () => void;
}

export const FeedbackModal: React.FC<FeedbackModalProps> = ({ onClose }) => {
    const { user } = useAuth();
    const [title, setTitle] = useState('');
    const [subject, setSubject] = useState('General');
    const [description, setDescription] = useState('');
    const [images, setImages] = useState<File[]>([]);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            const newFiles = Array.from(e.target.files);
            setImages(prev => [...prev, ...newFiles]);
        }
    };

    const removeImage = (index: number) => {
        setImages(prev => prev.filter((_, i) => i !== index));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!description.trim()) return;

        setIsSubmitting(true);
        setStatus('idle');

        try {
            const formData = new FormData();
            formData.append('title', title || `Feedback from ${new Date().toLocaleDateString()}`);
            formData.append('subject', subject);
            formData.append('description', description);
            formData.append('version', APP_VERSION);
            formData.append('date', new Date().toISOString());

            if (user) {
                formData.append('user', user.id);
            }

            images.forEach((image) => {
                formData.append('images', image);
            });

            await pb.collection('terrasim_feedback').create(formData);

            setStatus('success');
            setTimeout(() => {
                onClose();
            }, 2000);
        } catch (error) {
            console.error('Feedback submission failed:', error);
            setStatus('error');
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-300">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-3xl shadow-2xl w-full max-w-xl overflow-hidden animate-in zoom-in-95 duration-300 transition-colors">
                {/* Header */}
                <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/30 flex items-center justify-between transition-colors">
                    <div className="flex items-center gap-3">
                        <div>
                            <h2 className="text-lg font-bold text-slate-900 dark:text-white tracking-tight">Feedback & Bug Report</h2>
                            <p className="text-[10px] text-slate-500 dark:text-slate-400 font-medium">Help us improve TerraSim</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-xl text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors cursor-pointer"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-6 space-y-4">
                    {status === 'success' ? (
                        <div className="py-12 flex flex-col items-center justify-center text-center space-y-4">
                            <div>
                                <h3 className="text-xl font-bold text-slate-900 dark:text-white">Thank You!</h3>
                                <p className="text-slate-600 dark:text-slate-400 text-sm mt-1">Your feedback has been submitted successfully.</p>
                            </div>
                        </div>
                    ) : (
                        <>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-1.5">
                                    <label className="text-[10px] font-semibold text-slate-600 dark:text-slate-500 tracking-widest pl-1">Title</label>
                                    <input
                                        type="text"
                                        value={title}
                                        onChange={(e) => setTitle(e.target.value)}
                                        placeholder="Brief title..."
                                        className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all placeholder:text-slate-400 dark:placeholder:text-slate-600"
                                    />
                                </div>
                                <div className="space-y-1.5">
                                    <label className="text-[10px] font-semibold text-slate-600 dark:text-slate-500 tracking-widest pl-1">Subject</label>
                                    <select
                                        value={subject}
                                        onChange={(e) => setSubject(e.target.value)}
                                        className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all cursor-pointer"
                                    >
                                        <option value="General">General Feedback</option>
                                        <option value="Bug">Bug Report</option>
                                        <option value="Feature">Feature Request</option>
                                        <option value="UX">UI/UX Suggestion</option>
                                        <option value="Other">Other</option>
                                    </select>
                                </div>
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-[10px] font-semibold text-slate-600 dark:text-slate-500 tracking-widest pl-1">Description <span className="text-rose-500">*</span></label>
                                <textarea
                                    required
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    rows={5}
                                    placeholder="Please describe your findings, expectations, or suggestions in detail. If it's a bug, tell us how to reproduce it..."
                                    className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all resize-none placeholder:text-slate-400 dark:placeholder:text-slate-600"
                                />
                            </div>

                            <div className="space-y-3">
                                <div className="flex items-center justify-between">
                                    <label className="text-[10px] font-semibold text-slate-600 dark:text-slate-500 tracking-widest pl-1">Attachments (Images)</label>
                                    <button
                                        type="button"
                                        onClick={() => fileInputRef.current?.click()}
                                        className="cursor-pointer text-[10px] font-semibold text-blue-600 dark:text-blue-400 hover:text-blue-500 dark:hover:text-blue-300 transition-colors tracking-widest flex items-center gap-1.5"
                                    >
                                        <ImageIcon className="w-3 h-3" />
                                        Upload Images
                                    </button>
                                    <input
                                        type="file"
                                        ref={fileInputRef}
                                        onChange={handleImageChange}
                                        multiple
                                        accept="image/*"
                                        className="hidden"
                                    />
                                </div>

                                {images.length > 0 && (
                                    <div className="grid grid-cols-4 gap-3 p-3 bg-slate-50 dark:bg-slate-950 rounded-2xl border border-slate-200 dark:border-slate-800">
                                        {images.map((img, idx) => (
                                            <div key={idx} className="relative aspect-square rounded-lg overflow-hidden group border border-slate-200 dark:border-slate-800">
                                                <img
                                                    src={URL.createObjectURL(img)}
                                                    alt="Preview"
                                                    className="w-full h-full object-cover"
                                                />
                                                <button
                                                    type="button"
                                                    onClick={() => removeImage(idx)}
                                                    className="cursor-pointer absolute top-1 right-1 p-1 bg-rose-500 rounded-md text-white opacity-0 group-hover:opacity-100 transition-opacity"
                                                >
                                                    <X className="w-3 h-3" />
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            {status === 'error' && (
                                <div className="p-3 bg-rose-500/10 border border-rose-500/50 rounded-xl flex items-center gap-3 text-rose-500 dark:text-rose-400">
                                    <AlertCircle className="w-5 h-5 shrink-0" />
                                    <p className="text-xs font-medium">Something went wrong. Please try again later.</p>
                                </div>
                            )}

                            <div className="pt-4 flex items-center justify-between">
                                <div className="text-[10px] text-slate-400 dark:text-slate-500 font-mono">
                                    TerraSim v{APP_VERSION}
                                </div>
                                <div className="flex gap-3">
                                    <button
                                        type="button"
                                        onClick={onClose}
                                        className="cursor-pointer px-6 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 text-sm font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        disabled={isSubmitting || !description.trim()}
                                        className="cursor-pointer px-8 py-2.5 rounded-xl bg-blue-600 text-sm font-bold text-white hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2 shadow-lg shadow-blue-600/20"
                                    >
                                        {isSubmitting ? (
                                            <>
                                                <Loader2 className="w-4 h-4 animate-spin" />
                                                Sending...
                                            </>
                                        ) : (
                                            <>
                                                Send
                                            </>
                                        )}
                                    </button>
                                </div>
                            </div>
                        </>
                    )}
                </form>
            </div>
        </div>
    );
};
