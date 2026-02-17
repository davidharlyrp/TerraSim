import { useState, useEffect } from 'react';
import { X, Cloud, Download, Trash2, Edit2, Check, Loader2 } from 'lucide-react';
import { pb } from '../pb';
import { ProjectFile } from '../types';

interface CloudLoadModalProps {
    onLoad: (projectData: ProjectFile, recordId: string) => void;
    onClose: () => void;
}

interface ProjectRecord {
    id: string;
    name: string;
    data: ProjectFile;
    updated: string;
    expand?: {
        user?: {
            name: string;
            email: string;
        }
    }
}

export const CloudLoadModal: React.FC<CloudLoadModalProps> = ({ onLoad, onClose }) => {
    const [projects, setProjects] = useState<ProjectRecord[]>([]);
    const [loading, setLoading] = useState(true);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [editName, setEditName] = useState('');

    useEffect(() => {
        fetchProjects();
    }, []);

    const fetchProjects = async () => {
        setLoading(true);
        try {
            const result = await pb.collection('terrasim_projects').getList<ProjectRecord>(1, 50, {
                sort: '-updated',
                expand: 'user'
            });
            setProjects(result.items);
        } catch (error: any) {
            if (error.isAbort) return;
            console.error("Failed to fetch projects:", error);
            alert("Failed to load projects from cloud. Please check your connection.");
        } finally {
            setLoading(false);
        }
    };

    const handleLoad = (record: ProjectRecord) => {
        onLoad(record.data, record.id);
        onClose();
    };

    const handleDelete = async (id: string, e: React.MouseEvent) => {
        e.stopPropagation();
        if (!window.confirm("Are you sure you want to delete this project from the cloud?")) return;

        try {
            await pb.collection('terrasim_projects').delete(id);
            setProjects(projects.filter(p => p.id !== id));
        } catch (error) {
            console.error("Failed to delete project:", error);
            alert("Failed to delete project.");
        }
    };

    const startEdit = (project: ProjectRecord, e: React.MouseEvent) => {
        e.stopPropagation();
        setEditingId(project.id);
        setEditName(project.name);
    };

    const saveEdit = async (id: string, e: React.MouseEvent) => {
        e.stopPropagation();
        try {
            await pb.collection('terrasim_projects').update(id, { name: editName });
            setProjects(projects.map(p => p.id === id ? { ...p, name: editName } : p));
            setEditingId(null);
        } catch (error) {
            console.error("Failed to update name:", error);
            alert("Failed to update project name.");
        }
    };

    const handleDownload = (record: ProjectRecord, e: React.MouseEvent) => {
        e.stopPropagation();
        const blob = new Blob([JSON.stringify(record.data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${record.name.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.tsm`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-2xl w-[600px] max-h-[80dvh] flex flex-col overflow-hidden transition-colors">
                <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 transition-colors">
                    <div className="flex items-center gap-2 text-slate-900 dark:text-white font-bold">
                        <h3>Your Cloud Projects</h3>
                    </div>
                    <button onClick={onClose} className="cursor-pointer text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-2">
                    {loading ? (
                        <div className="flex flex-col items-center justify-center py-10 text-slate-500 gap-2">
                            <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
                            <p className="text-sm">Fetching projects...</p>
                        </div>
                    ) : projects.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-10 text-slate-500">
                            <Cloud className="w-12 h-12 mb-2 opacity-20" />
                            <p>No projects found in cloud.</p>
                        </div>
                    ) : (
                        projects.map(project => (
                            <div
                                key={project.id}
                                onClick={() => handleLoad(project)}
                                className="group flex items-center justify-between p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/20 hover:bg-slate-100 dark:hover:bg-slate-800/50 hover:border-slate-300 dark:hover:border-slate-700 transition-all cursor-pointer"
                            >
                                <div className="flex flex-col gap-1 flex-1">
                                    <div className="flex items-center gap-2">
                                        {editingId === project.id ? (
                                            <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
                                                <input
                                                    type="text"
                                                    value={editName}
                                                    onChange={e => setEditName(e.target.value)}
                                                    className="bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-600 rounded px-2 py-0.5 text-sm text-slate-900 dark:text-white focus:border-blue-500 focus:outline-none"
                                                    autoFocus
                                                />
                                                <button onClick={(e) => saveEdit(project.id, e)} className="cursor-pointer p-1 hover:text-green-600 dark:hover:text-green-400 text-slate-400">
                                                    <Check className="w-4 h-4" />
                                                </button>
                                            </div>
                                        ) : (
                                            <h4 className="font-semibold text-slate-700 dark:text-slate-200 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">{project.name}</h4>
                                        )}
                                    </div>
                                    <div className="flex items-center gap-2 text-[10px] text-slate-500">
                                        <span>v {project.data.version || '0.0.0'}</span>
                                        <span>| Updated {new Date(project.updated).toLocaleDateString()}</span>
                                    </div>
                                </div>

                                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                    {editingId !== project.id && (
                                        <button
                                            onClick={(e) => startEdit(project, e)}
                                            className="cursor-pointer p-2 rounded-lg hover:bg-blue-500/10 text-slate-400 hover:text-blue-600 dark:text-slate-500 dark:hover:text-blue-400 transition-colors"
                                            title="Rename"
                                        >
                                            <Edit2 className="w-4 h-4" />
                                        </button>
                                    )}
                                    <button
                                        onClick={(e) => handleDownload(project, e)}
                                        className="cursor-pointer p-2 rounded-lg hover:bg-blue-500/10 text-slate-400 hover:text-blue-600 dark:text-slate-500 dark:hover:text-blue-400 transition-colors"
                                        title="Download .tsm"
                                    >
                                        <Download className="w-4 h-4" />
                                    </button>
                                    <button
                                        onClick={(e) => handleDelete(project.id, e)}
                                        className="cursor-pointer p-2 rounded-lg hover:bg-red-500/10 text-slate-400 hover:text-red-600 dark:text-slate-500 dark:hover:text-red-400 transition-colors"
                                        title="Delete"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
};
