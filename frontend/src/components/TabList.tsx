import React from 'react';
import { Tab } from '../types';
import './TabList.css';

interface TabListProps {
    tabs: Tab[];
    activeTabId: string;
    onSelectTab: (id: string) => void;
    onCloseTab: (id: string, event: React.MouseEvent) => void;
    onNewTab: () => void;
}

export const TabList: React.FC<TabListProps> = ({
    tabs,
    activeTabId,
    onSelectTab,
    onCloseTab,
    onNewTab,
}) => {
    return (
        <div className="tab-bar-container">
            <div className="tab-scroll-area">
                {tabs.map((tab) => {
                    const isActive = tab.id === activeTabId;
                    return (
                        <div
                            key={tab.id}
                            className={`tab-item ${isActive ? 'active' : ''} ${tab.isDirty ? 'dirty' : ''}`}
                            onClick={() => onSelectTab(tab.id)}
                            title={tab.path || '未儲存的檔案'}
                        >
                            <span className="tab-icon">📄</span>
                            <span className="tab-name">{tab.name}</span>
                            <button
                                className="tab-close-btn"
                                onClick={(e) => onCloseTab(tab.id, e)}
                                title="關閉分頁"
                            >
                                <span className="close-x">✕</span>
                                <span className="dirty-indicator">●</span>
                            </button>
                        </div>
                    );
                })}
            </div>
            
            <button className="new-tab-btn" onClick={onNewTab} title="新建空白分頁 (Ctrl+N)">
                ➕
            </button>
        </div>
    );
};
