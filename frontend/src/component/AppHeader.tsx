import { Settings, LogOut, Bell, Calendar, ChevronRight, Save, FolderOpen, CloudUpload, CloudDownload, Loader2, Book, MessageSquare, Sun, Moon, X, ChevronDown, BookOpen, Plus, FileDown } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { APP_VERSION } from '../version';
import { SOFTWARE_UPDATES } from '../data/updates';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';

interface AppHeaderProps {
    projectName: string;
    setProjectName: (name: string) => void;
    onOpenSettings: () => void;
    onSaveProject: () => void;
    onLoadProject: (file: File) => void;
    onOpenSampleGallery: () => void;
    onCloudSave: () => void;
    onCloudLoad: () => void;
    onOpenFeedback: () => void;
    isCloudSaving: boolean;
    onNewProject: () => void;
    onCloudSaveAsNew: () => void;
}

export const AppHeader: React.FC<AppHeaderProps> = ({
    projectName,
    setProjectName,
    onOpenSettings,
    onSaveProject,
    onLoadProject,
    onOpenSampleGallery,
    onCloudSave,
    onCloudLoad,
    onOpenFeedback,
    isCloudSaving,
    onNewProject,
    onCloudSaveAsNew
}) => {
    const { user, logout } = useAuth();
    const { theme, toggleTheme } = useTheme();
    const [isUpdateOpen, setIsUpdateOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);
    const userPanelRef = useRef<HTMLDivElement>(null);
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const [isUserPanelOpen, setIsUserPanelOpen] = useState(false);
    const isWindowSizeSmall = window.innerWidth < 768;
    const [isAppNameShowed, setAppNameShowed] = useState(false);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsUpdateOpen(false);
            }
            if (userPanelRef.current && !userPanelRef.current.contains(event.target as Node)) {
                setIsUserPanelOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    return (
        <div className="flex flex-col bg-slate-50 dark:bg-slate-900 z-50">
            <header className="flex items-center justify-between px-4 py-2 border-b border-slate-200 dark:border-slate-700 h-12">
                <div className="flex items-center gap-2 w-full">
                    <img
                        src="/Logo.png"
                        alt="Logo"
                        className="cursor-pointer w-6 h-6 z-20"
                        onMouseEnter={() => setAppNameShowed(true)}
                        onMouseLeave={() => setAppNameShowed(false)}
                    />
                    <span className={`text-slate-600 text-lg font-bold dark:text-slate-200 transition ${isAppNameShowed ? 'translate-x-0 opacity-100' : '-translate-x-full opacity-0'}`}>TerraSim</span>
                    <div className={`flex items-center gap-2 md:w-full w-55 transition ${!isAppNameShowed ? '-translate-x-20' : 'translate-x-0'}`}>
                        <div className="rotate-15 w-0.5 h-6 mx-2 bg-slate-300 dark:bg-slate-700" />
                        <input
                            type="text"
                            value={projectName}
                            onChange={(e) => setProjectName(e.target.value)}
                            className="bg-transparent border-0 hover:border-1 md:text-sm md:w-full w-60 text-xs font-semibold text-slate-600 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500 rounded px-1"
                            placeholder="Project Name"

                        />
                    </div>
                </div>

                <div className="hidden md:flex items-center justify-center w-[50%]">
                    <span className='text-xs font-semibold text-slate-800 dark:text-slate-300'>
                        TERRASIM <span className='text-[10px]'>v {APP_VERSION} BETA</span>
                    </span>
                </div>

                <div className="flex items-center justify-end gap-2 w-full">
                    {!isWindowSizeSmall && (
                        <div className="flex gap-2" >
                            <button
                                onClick={onOpenFeedback}
                                className={`cursor-pointer p-2.5 rounded-xl transition-all group relative active:scale-95 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700/50 hover:text-blue-600 dark:hover:text-blue-400`}
                                title="Feedback & Bug Report"
                            >
                                <MessageSquare className="w-5 h-5 transition-transform group-hover:scale-110" />
                            </button>

                            <button
                                onClick={onOpenSampleGallery}
                                className={`cursor-pointer p-2.5 rounded-xl transition-all group relative active:scale-95 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700/50 hover:text-blue-600 dark:hover:text-blue-400`}
                                title="Open Sample Project"
                            >
                                <FileDown className="w-5 h-5 transition-transform group-hover:scale-110" />
                            </button>

                            <button
                                onClick={() => setIsUpdateOpen(!isUpdateOpen)}
                                className={`cursor-pointer p-2.5 rounded-xl transition-all group relative active:scale-95 ${isUpdateOpen ? 'bg-blue-500/20 text-blue-600 dark:text-blue-400' : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700/50 hover:text-blue-600 dark:hover:text-blue-400'}`}
                                title="Software Updates"
                            >
                                <Bell className={`w-5 h-5 ${isUpdateOpen ? 'animate-pulse' : 'group-hover:shake'}`} />
                                <span className="absolute top-2 right-2 w-2 h-2 bg-blue-500 rounded-full border-2 border-slate-800"></span>
                                {isUpdateOpen && (
                                    <div className="absolute right-0 mt-2 w-80 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-2xl overflow-hidden z-[100] animate-in fade-in zoom-in duration-200">
                                        <div className="p-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                                            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                                                Software Updates
                                            </h3>
                                        </div>
                                        <div className="max-h-[400px] overflow-y-auto custom-scrollbar">
                                            {SOFTWARE_UPDATES.map((update, index) => (
                                                <div key={index} className="p-4 border-b border-slate-100 dark:border-slate-800 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors">
                                                    <div className="flex justify-between items-start mb-2">
                                                        <span className="text-xs font-semibold text-blue-400 bg-blue-400/10 px-2 py-0.5 rounded-full">{update.version}</span>
                                                        <div className="flex items-center gap-1 text-[10px] text-slate-500">
                                                            <Calendar className="w-3 h-3" />
                                                            {update.date}
                                                        </div>
                                                    </div>
                                                    <ul className="space-y-1.5">
                                                        {update.changes.map((change, cIndex) => (
                                                            <li key={cIndex} className="text-[11px] text-slate-600 dark:text-slate-300 flex items-start gap-2">
                                                                <ChevronRight className="w-3 h-3 mt-0.5 text-slate-400 dark:text-slate-500 shrink-0" />
                                                                <span>{change}</span>
                                                            </li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </button>

                            <button
                                className={`relative cursor-pointer p-2.5 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-700/50 active:scale-95 transition-all text-slate-600 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 group relative`}
                                title="Documentation"
                            >
                                <Link to="/docs" target="_blank" rel="noopener noreferrer">
                                    <Book className={`w-5 h-5 group-hover:opacity-0 group-hover:rotate-45 transition-transform duration-300`} />
                                    <BookOpen className={`absolute w-5 h-5 top-2.5 right-2.5 opacity-0 group-hover:opacity-100 group-hover:rotate-45 transition-transform duration-300`} />
                                </Link>
                            </button>

                            <button
                                onClick={onOpenSettings}
                                className="cursor-pointer p-2.5 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-all text-slate-600 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 group relative active:scale-95"
                                title="Global Settings"
                            >
                                <Settings className="w-5 h-5 group-hover:rotate-45 transition-transform duration-300" />
                            </button>

                            <button
                                onClick={toggleTheme}
                                className="cursor-pointer p-2.5 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-all text-slate-600 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 group relative active:scale-95"
                                title={theme === 'light' ? 'Switch to Dark Mode' : 'Switch to Light Mode'}
                            >
                                {theme === 'light' ? (
                                    <Moon className="w-5 h-5 group-hover:-rotate-12 transition-transform duration-300" />
                                ) : (
                                    <Sun className="w-5 h-5 group-hover:rotate-45 transition-transform duration-300" />
                                )}
                            </button>

                            <div className="flex items-center gap-2" ref={userPanelRef}>
                                <button
                                    onClick={() => setIsUserPanelOpen(!isUserPanelOpen)}
                                    // Removed onMouseEnter/onMouseLeave to prevent closing when file dialog opens
                                    className="relative w-8 h-8 flex items-center justify-center rounded-full bg-blue-500/20 hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-all text-slate-600 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 group relative active:scale-95"
                                    title="User Panel"
                                >
                                    <span className='relative cursor-pointer p-2.5'>
                                        <span className={`text-sm font-medium text-slate-900 dark:text-slate-100 transition ${isUserPanelOpen ? 'rotate-180 opacity-0' : ''}`}>
                                            {user?.name.charAt(0).toUpperCase()}
                                        </span>
                                        <span className={`absolute top-3 right-1.25 text-sm font-medium text-slate-900 dark:text-slate-100 transition ${isUserPanelOpen ? '' : 'opacity-0 rotate-180'}`}>
                                            <ChevronDown className="w-5 h-5" />
                                        </span>
                                    </span>
                                    {isUserPanelOpen && (
                                        <div
                                            className="absolute top-full right-0 mt-2 w-60 bg-white dark:bg-slate-800 rounded-xl shadow-lg border border-slate-200 dark:border-slate-700"
                                            onClick={(e) => e.stopPropagation()}
                                        >
                                            <div className="p-4">
                                                <div className="flex items-center gap-2 mb-4 border-b border-slate-200 dark:border-slate-700 pb-4">
                                                    <div className="flex-1">
                                                        <div className="text-sm font-medium text-slate-900 dark:text-slate-100">{user?.name}</div>
                                                        <div className="text-xs text-slate-500 dark:text-slate-400">{user?.email}</div>
                                                    </div>
                                                </div>
                                                <div className='flex flex-col gap-1 mb-4 border-b border-slate-200 dark:border-slate-700 pb-4'>
                                                    <button
                                                        onClick={() => {
                                                            setIsUserPanelOpen(false);
                                                            onNewProject();
                                                        }}
                                                        className="cursor-pointer flex items-center text-left text-sm gap-2 p-2.5 rounded-xl transition-all group relative active:scale-95 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-900/20"
                                                        title="Create New Project"
                                                    >
                                                        <FolderOpen className="w-5 h-5" />
                                                        New Project
                                                    </button>
                                                    <button
                                                        onClick={onSaveProject}
                                                        className="cursor-pointer flex items-center text-left text-sm gap-2 p-2.5 rounded-xl transition-all group relative active:scale-95 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700/50 hover:text-blue-600 dark:hover:text-blue-400"
                                                        title="Download Project"
                                                    >
                                                        <Save className="w-5 h-5" />
                                                        Download Project
                                                    </button>
                                                    <button
                                                        onClick={onCloudSave}
                                                        disabled={isCloudSaving}
                                                        className="cursor-pointer flex items-center text-left text-sm gap-2 p-2.5 rounded-xl transition-all group relative active:scale-95 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700/50 hover:text-blue-600 dark:hover:text-blue-400 disabled:opacity-50 disabled:cursor-not-allowed"
                                                        title="Save Project on Cloud"
                                                    >
                                                        {isCloudSaving ? (
                                                            <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
                                                        ) : (
                                                            <CloudUpload className="w-5 h-5" />
                                                        )}
                                                        Save Project on Cloud
                                                    </button>
                                                    <button
                                                        onClick={onCloudSaveAsNew}
                                                        disabled={isCloudSaving}
                                                        className="cursor-pointer flex items-center text-left text-sm gap-2 p-2.5 rounded-xl transition-all group relative active:scale-95 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700/50 hover:text-blue-600 dark:hover:text-blue-400 disabled:opacity-50 disabled:cursor-not-allowed"
                                                        title="Save as New Project on Cloud"
                                                    >
                                                        {isCloudSaving ? (
                                                            <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
                                                        ) : (
                                                            <div className="relative">
                                                                <CloudUpload className="w-5 h-5" />
                                                                <div className="absolute -bottom-1 -right-1 text-[8px] font-bold bg-blue-500 text-white px-1 rounded-full">+</div>
                                                            </div>
                                                        )}
                                                        Save as New Project
                                                    </button>
                                                    <button
                                                        onClick={onCloudLoad}
                                                        className="cursor-pointer flex items-center text-left text-sm gap-2 p-2.5 rounded-xl transition-all group relative active:scale-95 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700/50 hover:text-blue-600 dark:hover:text-blue-400"
                                                        title="Load Project from Cloud"
                                                    >
                                                        <CloudDownload className="w-5 h-5" />
                                                        Load Project from Cloud
                                                    </button>
                                                    <label
                                                        className="cursor-pointer flex items-center text-left text-sm gap-2 p-2.5 rounded-xl transition-all group relative active:scale-95 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700/50 hover:text-blue-600 dark:hover:text-blue-400"
                                                        title="Open Project"
                                                    >
                                                        <input
                                                            type="file"
                                                            accept=".tsm"
                                                            className="hidden"
                                                            onChange={(e) => {
                                                                const file = e.target.files?.[0];
                                                                if (file) {
                                                                    onLoadProject(file);
                                                                    e.target.value = '';
                                                                }
                                                            }}
                                                        />
                                                        <FolderOpen className="w-5 h-5" />
                                                        Open Project
                                                    </label>
                                                </div>
                                                <button
                                                    onClick={logout}
                                                    className="cursor-pointer w-full flex items-center gap-2 px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                                                >
                                                    <LogOut className="w-4 h-4" />
                                                    Logout
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                </button>
                            </div>
                        </div>
                    )}
                </div>

                {/* updates section on mobile */}
                {isWindowSizeSmall && (
                    <>
                        <button
                            onClick={() => setIsUpdateOpen(!isUpdateOpen)}
                            className={`sticky top-0 right-14 cursor-pointer p-2.5 relative rounded-xl transition-all group active:scale-95 ${isUpdateOpen ? 'bg-blue-500/20 text-blue-600 dark:text-blue-400' : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700/50 hover:text-blue-600 dark:hover:text-blue-400'}`}
                            title="Software Updates"
                        >
                            <Bell className={`w-5 h-5 ${isUpdateOpen ? 'animate-pulse' : 'group-hover:shake'}`} />
                            <span className="absolute top-2 right-2 w-2 h-2 bg-blue-500 rounded-full border-2 border-slate-800"></span>
                        </button>
                        {isUpdateOpen && (
                            <div className="fixed top-10 right-10 mt-2 w-80 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-2xl overflow-hidden z-[100] animate-in fade-in zoom-in duration-200">
                                <div className="p-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                                    <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                                        Software Updates
                                    </h3>
                                </div>
                                <div className="max-h-[400px] overflow-y-auto custom-scrollbar">
                                    {SOFTWARE_UPDATES.map((update, index) => (
                                        <div key={index} className="p-4 border-b border-slate-100 dark:border-slate-800 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors">
                                            <div className="flex justify-between items-start mb-2">
                                                <span className="text-xs font-semibold text-blue-400 bg-blue-400/10 px-2 py-0.5 rounded-full">{update.version}</span>
                                                <div className="flex items-center gap-1 text-[10px] text-slate-500">
                                                    <Calendar className="w-3 h-3" />
                                                    {update.date}
                                                </div>
                                            </div>
                                            <ul className="space-y-1.5">
                                                {update.changes.map((change, cIndex) => (
                                                    <li key={cIndex} className="text-[11px] text-slate-600 dark:text-slate-300 flex items-start gap-2">
                                                        <ChevronRight className="w-3 h-3 mt-0.5 text-slate-400 dark:text-slate-500 shrink-0" />
                                                        <span>{change}</span>
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                        <button
                            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                            className={`sticky relative z-72 top-4 right-4 block cursor-pointer transition ${isMobileMenuOpen ? 'rotate-180' : 'bg-blue-500/20'} w-8 h-8 flex items-center justify-center rounded-full  hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-all text-slate-600 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 group relative active:scale-95`}
                            title="User Panel"
                        >
                            <span className={`cursor-pointer p-2.5 transition ${isMobileMenuOpen ? 'opacity-0' : 'opacity-100'}`}>
                                {user?.name.charAt(0).toUpperCase()}
                            </span>
                            <span className={`absolute cursor-pointer p-2.5 transition ${isMobileMenuOpen ? 'opacity-100' : 'opacity-0'}`}>
                                <X className="w-5 h-5" />
                            </span>
                        </button>
                    </>
                )}
            </header>


            {/* mobile menu button */}
            {isWindowSizeSmall && (
                <>
                    {/* mobile menu */}
                    <div className={`md:hidden block fixed z-70 top-0 left-0 right-0 bottom-0 h-full w-full overflow-y-auto custom-scrollbar bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700 transition ${isMobileMenuOpen ? 'translate-y-0' : '-translate-y-[calc(100vh)]'}`}>
                        <div className="flex items-center gap-2 px-3 py-1.5 w-full border-b border-slate-200 dark:border-slate-700">
                            <div className="flex flex-col items-end py-4">
                                <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 leading-none">Welcome, {user?.name}</span>
                            </div>
                        </div>
                        <div className="flex flex-col items-center gap-2 px-3 py-2 w-full border-b border-slate-200 dark:border-slate-700">
                            <button
                                onClick={onNewProject}
                                className="buttonlabel">
                                <Plus className="w-5 h-5 text-blue-600 dark:text-white" />
                                <span className="text-xs font-semibold text-slate-900 dark:text-white leading-none">New Project</span>
                            </button>
                            <button
                                onClick={onSaveProject}
                                className="buttonlabel">
                                <Save className="w-5 h-5 text-blue-600 dark:text-white" />
                                <span className="text-xs font-semibold text-slate-900 dark:text-white leading-none">Download Project</span>
                            </button>
                            <button
                                onClick={onCloudSave}
                                disabled={isCloudSaving}
                                className="buttonlabel">
                                {isCloudSaving ? (
                                    <Loader2 className="w-5 h-5 animate-spin text-blue-600 dark:text-white" />
                                ) : (
                                    <CloudUpload className="w-5 h-5 text-blue-600 dark:text-white" />
                                )}
                                <span className="text-xs font-semibold text-slate-900 dark:text-white leading-none">Save to Cloud</span>
                            </button>
                            <button
                                onClick={onCloudSaveAsNew}
                                className="buttonlabel">
                                {isCloudSaving ? (
                                    <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
                                ) : (
                                    <div className="relative">
                                        <CloudUpload className="w-5 h-5" />
                                        <div className="absolute -bottom-1 -right-1 text-[8px] font-bold bg-blue-500 text-white px-1 rounded-full">+</div>
                                    </div>
                                )}
                                <span className="text-xs font-semibold text-slate-900 dark:text-white leading-none">Save as New</span>
                            </button>
                            <button
                                onClick={onCloudLoad}
                                className="buttonlabel">
                                <CloudDownload className="w-5 h-5 text-blue-600 dark:text-white" />
                                <span className="text-xs font-semibold text-slate-900 dark:text-white leading-none">Load from Cloud</span>
                            </button>
                            <label
                                className="buttonlabel"
                                title="Open Project"
                            >
                                <input
                                    type="file"
                                    accept=".tsm"
                                    className="hidden"
                                    onChange={(e) => {
                                        const file = e.target.files?.[0];
                                        if (file) {
                                            onLoadProject(file);
                                            e.target.value = '';
                                        }
                                    }}
                                />
                                <FolderOpen className="w-5 h-5 text-blue-600 dark:text-white" />
                                <span className="text-xs font-semibold text-slate-900 dark:text-white leading-none">Open Project</span>
                            </label>
                        </div>
                        <div className="flex flex-col items-center gap-2 px-3 py-2 w-full border-b border-slate-200 dark:border-slate-700">
                            <Link
                                to="/docs"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="buttonlabel">
                                <Book className="w-5 h-5 text-blue-600 dark:text-white" />
                                <span className="text-xs font-semibold text-slate-900 dark:text-white leading-none">Documentation</span>
                            </Link>
                            <button
                                onClick={onOpenFeedback}
                                className="buttonlabel">
                                <MessageSquare className="w-5 h-5 text-blue-600 dark:text-white" />
                                <span className="text-xs font-semibold text-slate-900 dark:text-white leading-none">Feedback</span>
                            </button>
                            <button
                                onClick={onOpenSettings}
                                className="buttonlabel">
                                <Settings className="w-5 h-5 text-blue-600 dark:text-white" />
                                <span className="text-xs font-semibold text-slate-900 dark:text-white leading-none">Settings</span>
                            </button>
                            <button
                                onClick={toggleTheme}
                                className="buttonlabel">
                                {theme === 'light' ? <Moon className="w-5 h-5 text-blue-600 dark:text-white" /> : <Sun className="w-5 h-5 text-blue-600 dark:text-white" />}
                                <span className="text-xs font-semibold text-slate-900 dark:text-white leading-none">{theme === 'light' ? 'Dark Mode' : 'Light Mode'}</span>
                            </button>
                            <button
                                onClick={logout}
                                className="buttonlabel">
                                <LogOut className="w-5 h-5 text-red-500" />
                                <span className="text-xs font-semibold text-red-500 leading-none">Logout</span>
                            </button>
                        </div>

                        <div className="p-4">
                            <div className="items-center justify-center flex flex-col bg-slate-100 dark:bg-slate-900/90 backdrop-blur-md py-2 px-4 rounded-xl border border-slate-200 dark:border-slate-700 shadow-2xl text-slate-600 dark:text-slate-400 z-[20]">
                                <div className="text-[10px]">TerraSim v{APP_VERSION} (Beta) | Copyright © 2026</div>
                                <div className="text-[10px] border-b border-slate-200 dark:border-slate-700 w-full text-center mb-1 pb-1">Dahar Engineer | All rights reserved.</div>
                                <div className="text-[8px]">This software is still under development.</div>
                                <div className="text-[8px]">Please use it at your own risk.</div>
                            </div>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
};
