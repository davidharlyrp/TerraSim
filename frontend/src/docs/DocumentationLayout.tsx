import React, { useState, useEffect, useRef } from 'react';
import { NavLink, Outlet, Link, useLocation } from 'react-router-dom';
import { ChevronRight, Menu, X, ArrowLeft } from 'lucide-react';
import { APP_VERSION } from '../version';

export const DocumentationLayout: React.FC = () => {
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    const { pathname } = useLocation();
    const scrollContainerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollContainerRef.current) {
            scrollContainerRef.current.scrollTo(0, 0);
        }
    }, [pathname]);

    const navItems = [
        { path: 'introduction', label: 'Introduction' },
        { path: 'user-manual', label: 'User Manual' },
        { path: 'scientific-reference', label: 'Scientific Reference' },
    ];

    return (
        <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
            {/* Mobile Sidebar Overlay */}
            {isSidebarOpen && (
                <div
                    className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
                    onClick={() => setIsSidebarOpen(false)}
                />
            )}

            {/* Sidebar */}
            <aside className={`
                fixed lg:relative inset-y-0 left-0 w-72 bg-slate-900 border-r border-slate-800 z-50 transform transition-transform duration-300 ease-in-out
                ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
            `}>
                <div className="flex flex-col h-full">
                    <div className="p-6 border-b border-slate-800 flex items-center justify-between">
                        <Link to="/" className="flex items-center gap-3 group">
                            <img src="/Logo.png" className="w-10 h-10" alt="" />
                            <div>
                                <h1 className="text-lg font-bold text-white leading-none">TerraSim</h1>
                                <p className="text-[10px] text-slate-500 font-medium uppercase tracking-wider mt-1">Documentation</p>
                            </div>
                        </Link>
                        <button className="cursor-pointer lg:hidden text-slate-400" onClick={() => setIsSidebarOpen(false)}>
                            <X className="w-6 h-6" />
                        </button>
                    </div>

                    <nav className="flex-1 overflow-y-auto py-6 px-4 space-y-2 custom-scrollbar">
                        <Link
                            to="/"
                            className="flex items-center gap-3 px-4 py-3 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-all mb-4 group"
                        >
                            <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
                            <span className="text-sm font-medium">Back to Application</span>
                        </Link>

                        <div className="text-[10px] font-bold text-slate-600 uppercase tracking-widest px-4 mb-2">Main Topics</div>

                        {navItems.map((item) => (
                            <NavLink
                                key={item.path}
                                to={item.path}
                                className={({ isActive }) => `
                                    flex items-center gap-3 px-4 py-3 rounded-xl transition-all group
                                    ${isActive
                                        ? 'bg-blue-600/10 text-blue-400 ring-1 ring-blue-500/50'
                                        : 'text-slate-400 hover:text-white hover:bg-slate-800'}
                                `}
                                onClick={() => setIsSidebarOpen(false)}
                            >
                                <span className="text-sm font-medium flex-1">{item.label}</span>
                                <ChevronRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
                            </NavLink>
                        ))}
                    </nav>

                    <div className="p-6 border-t border-slate-800">
                        <div className="bg-slate-800/50 rounded-2xl p-4 border border-slate-700/50">
                            <p className="text-[10px] text-slate-500 font-medium leading-relaxed">
                                Version {APP_VERSION}<br />
                                All rights reserved.<br />
                                &copy; 2026 Dahar Engineer
                            </p>
                        </div>
                    </div>
                </div>
            </aside>

            {/* Main Content Area */}
            <main className="flex-1 flex flex-col min-w-0 bg-slate-950 overflow-hidden">
                <header className="lg:hidden h-16 flex items-center justify-between px-6 bg-slate-900 border-b border-slate-800 sticky top-0 z-30">
                    <div className="flex items-center gap-3">
                        <span className="font-bold text-white text-sm tracking-widest">Documentation</span>
                    </div>
                    <button
                        className="cursor-pointer p-2 bg-slate-800 rounded-lg text-white active:scale-95 transition-transform"
                        onClick={() => setIsSidebarOpen(true)}
                    >
                        <Menu className="w-6 h-6" />
                    </button>
                </header>

                <div
                    ref={scrollContainerRef}
                    className="flex-1 overflow-y-auto custom-scrollbar scroll-smooth"
                >
                    <div className="max-w-4xl mx-auto px-6 py-12 lg:px-12">
                        <Outlet />

                        <footer className="mt-20 pt-12 border-t border-slate-800 text-center">
                            <p className="text-slate-500 text-sm">
                                Need help? Contact us at <a href="mailto:support@daharengineer.com" className="text-blue-500 hover:underline">support@daharengineer.com</a>
                            </p>
                        </footer>
                    </div>
                </div>
            </main>
        </div>
    );
};
