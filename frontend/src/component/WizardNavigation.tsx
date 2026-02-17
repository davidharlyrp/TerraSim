
export enum WizardTab {
    INPUT = 'INPUT',
    MESH = 'MESH',
    STAGING = 'STAGING',
    RESULT = 'RESULT'
}

interface WizardNavigationProps {
    activeTab: WizardTab;
    onTabChange: (tab: WizardTab) => void;
}

export const WizardNavigation: React.FC<WizardNavigationProps> = ({ activeTab, onTabChange }) => {
    const tabs = [
        { id: WizardTab.INPUT, label: 'Input' },
        { id: WizardTab.MESH, label: 'Mesh' },
        { id: WizardTab.STAGING, label: 'Staging' },
        { id: WizardTab.RESULT, label: 'Result' },
    ];

    return (
        <div className="flex md:flex-row flex-col gap-2 pt-2 px-4 bg-slate-50 dark:bg-slate-900">
            <div className="flex justify-between gap-2 px-2 mx-10 md:mx-5">
                {tabs.map(tab => {
                    const isActive = activeTab === tab.id;
                    return (
                        <button
                            key={tab.id}
                            onClick={() => onTabChange(tab.id)}
                            className={`cursor-pointer py-2 px-4 text-sm transition-all border-b-2 h-full font-medium
                                    ${isActive
                                    ? 'text-blue-600 dark:text-blue-500 border-blue-600 dark:border-blue-500 bg-blue-50 dark:bg-blue-600/10 rounded-t-lg'
                                    : 'text-slate-600 dark:text-slate-400 border-transparent hover:text-slate-900 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700/50 rounded-t-lg'
                                }`}
                            title={tab.label}
                        >
                            {tab.label}
                        </button>
                    );
                })}
            </div>
        </div>
    );
};
