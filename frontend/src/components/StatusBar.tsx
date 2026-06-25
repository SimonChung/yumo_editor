import React, { useState, useEffect, useRef } from 'react';
import { Tab } from '../types';
import './StatusBar.css';

interface StatusBarProps {
    activeTab: Tab | undefined;
    fontSize: number;
    onConvertEncoding?: (encoding: string) => void;
}

export const StatusBar: React.FC<StatusBarProps> = ({ activeTab, fontSize, onConvertEncoding }) => {
    const [showMenu, setShowMenu] = useState(false);
    const menuRef = useRef<HTMLDivElement>(null);

    const lineCount = activeTab ? activeTab.content.split('\n').length : 0;
    const charCount = activeTab ? activeTab.content.length : 0;
    const filePath = activeTab ? (activeTab.path || '未儲存的空白檔案') : '無開啟的分頁';
    const encoding = activeTab?.encoding || 'UTF-8';

    // 點擊外部自動收合選單
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
                setShowMenu(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleEncodingClick = (newEnc: string) => {
        if (onConvertEncoding) {
            onConvertEncoding(newEnc);
        }
        setShowMenu(false);
    };

    return (
        <div className="status-bar">
            <div className="status-section path-section" title={filePath}>
                <span className="status-icon">📍</span>
                <span className="status-text">{filePath}</span>
            </div>
            
            <div className="status-right">
                <div className="status-section">
                    <span className="status-text">行數: {lineCount}</span>
                </div>
                <div className="status-section">
                    <span className="status-text">字元數: {charCount}</span>
                </div>
                <div className="status-section">
                    <span className="status-text">字型: {fontSize}px</span>
                </div>
                
                {/* 包含下拉選單的編碼區域 */}
                <div className="encoding-section-container" ref={menuRef}>
                    <div 
                        className={`status-section encoding-section ${activeTab ? 'clickable' : ''} ${showMenu ? 'active' : ''}`}
                        onClick={() => activeTab && setShowMenu(!showMenu)}
                        title={activeTab ? "點擊以轉換檔案編碼格式" : ""}
                    >
                        <span className="status-icon">🔤</span>
                        <span className="status-text">{encoding}</span>
                        {activeTab && <span className="encoding-chevron">▾</span>}
                    </div>
                    
                    {showMenu && activeTab && (
                        <div className="encoding-dropdown-menu animate-fade-in">
                            <div className="encoding-menu-header">轉換檔案編碼至:</div>
                            <button 
                                className={`encoding-menu-item ${encoding === 'UTF-8' ? 'selected' : ''}`}
                                onClick={() => handleEncodingClick('UTF-8')}
                            >
                                <span className="item-dot">●</span> UTF-8 (通用 Unicode)
                            </button>
                            <button 
                                className={`encoding-menu-item ${encoding === 'BIG5' ? 'selected' : ''}`}
                                onClick={() => handleEncodingClick('BIG5')}
                            >
                                <span className="item-dot">●</span> BIG5 (繁體中文 ASCII)
                            </button>
                            <button 
                                className={`encoding-menu-item ${encoding === 'GBK' ? 'selected' : ''}`}
                                onClick={() => handleEncodingClick('GBK')}
                            >
                                <span className="item-dot">●</span> GBK (簡體中文 ASCII)
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
