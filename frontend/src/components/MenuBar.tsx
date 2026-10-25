import React, { useState, useEffect, useRef } from 'react';
import './MenuBar.css';

interface MenuBarProps {
    onNewFile: () => void;
    onOpenFile: () => void;
    onSaveFile: () => void;
    onSaveAsFile: () => void;
    onCloseTab: () => void;
    onZoomIn: () => void;
    onZoomOut: () => void;
    onZoomReset: () => void;
}

export const MenuBar: React.FC<MenuBarProps> = ({
    onNewFile,
    onOpenFile,
    onSaveFile,
    onSaveAsFile,
    onCloseTab,
    onZoomIn,
    onZoomOut,
    onZoomReset,
}) => {
    const [activeMenu, setActiveMenu] = useState<string | null>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    // 點擊選單外部時自動收合
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
                setActiveMenu(null);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const toggleMenu = (menuName: string) => {
        if (activeMenu === menuName) {
            setActiveMenu(null);
        } else {
            setActiveMenu(menuName);
        }
    };

    const handleItemClick = (action: () => void) => {
        action();
        setActiveMenu(null);
    };

    return (
        <div className="menu-bar" ref={containerRef}>
            <div className="menu-logo">
                <span className="logo-icon">📂</span>
                <span className="logo-text">玉墨 (YuMo Editor)</span>
            </div>
            
            <div className="menu-items">
                {/* 檔案選單 */}
                <div className={`menu-dropdown ${activeMenu === 'file' ? 'active' : ''}`}>
                    <button className="menu-trigger" onClick={() => toggleMenu('file')}>
                        檔案 (File)
                    </button>
                    {activeMenu === 'file' && (
                        <div className="menu-options animate-fade-in">
                            <button className="menu-option" onClick={() => handleItemClick(onNewFile)}>
                                <span className="option-icon">➕</span>
                                <span className="option-label">新建檔案</span>
                                <span className="option-shortcut">Ctrl+N</span>
                            </button>
                            <button className="menu-option" onClick={() => handleItemClick(onOpenFile)}>
                                <span className="option-icon">📂</span>
                                <span className="option-label">開啟檔案...</span>
                                <span className="option-shortcut">Ctrl+O</span>
                            </button>
                            <button className="menu-option" onClick={() => handleItemClick(onSaveFile)}>
                                <span className="option-icon">💾</span>
                                <span className="option-label">儲存檔案</span>
                                <span className="option-shortcut">Ctrl+S</span>
                            </button>
                            <button className="menu-option" onClick={() => handleItemClick(onSaveAsFile)}>
                                <span className="option-icon">📝</span>
                                <span className="option-label">另存新檔...</span>
                                <span className="option-shortcut">Shift+Ctrl+S</span>
                            </button>
                            <div className="menu-divider"></div>
                            <button className="menu-option" onClick={() => handleItemClick(onCloseTab)}>
                                <span className="option-icon">❌</span>
                                <span className="option-label">關閉分頁</span>
                                <span className="option-shortcut">Ctrl+W</span>
                            </button>
                        </div>
                    )}
                </div>

                {/* 檢視選單 */}
                <div className={`menu-dropdown ${activeMenu === 'view' ? 'active' : ''}`}>
                    <button className="menu-trigger" onClick={() => toggleMenu('view')}>
                        檢視 (View)
                    </button>
                    {activeMenu === 'view' && (
                        <div className="menu-options animate-fade-in">
                            <button className="menu-option" onClick={() => handleItemClick(onZoomIn)}>
                                <span className="option-icon">🔍</span>
                                <span className="option-label">放大字體</span>
                                <span className="option-shortcut">Ctrl +</span>
                            </button>
                            <button className="menu-option" onClick={() => handleItemClick(onZoomOut)}>
                                <span className="option-icon">🔎</span>
                                <span className="option-label">縮小字體</span>
                                <span className="option-shortcut">Ctrl -</span>
                            </button>
                            <button className="menu-option" onClick={() => handleItemClick(onZoomReset)}>
                                <span className="option-icon">🔄</span>
                                <span className="option-label">重設字體大小</span>
                                <span className="option-shortcut">Ctrl 0</span>
                            </button>
                        </div>
                    )}
                </div>
            </div>
            
            <div className="menu-status-badge">
                <span className="badge-text">v3.0 (Wails v3 + React)</span>
            </div>
        </div>
    );
};
