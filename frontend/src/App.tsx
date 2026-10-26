import { useState, useEffect, useRef, useCallback } from 'react';
import { Events } from '@wailsio/runtime';
import './App.css';
import { Tab } from './types';
import { MenuBar } from './components/MenuBar';
import { TabList } from './components/TabList';
import { Editor } from './components/Editor';
import { MarkdownWorkspace } from './components/MarkdownWorkspace';
import { SvgWorkspace } from './components/SvgWorkspace';
import { StatusBar } from './components/StatusBar';

// 匯入 Wails v3 自動生成的 Go 橋接方法
// 注意: 執行 `wails3 generate bindings` 後，此路徑會自動更新至 frontend/bindings/ 下
import { OpenFile, SaveFile, SelectFile, SelectSaveFile, TakeLaunchFiles } from '../bindings/tw.ybak/yumo/app';

const createUntitledTab = (number: number): Tab => ({
    id: 'tab-' + Date.now() + '-' + Math.random().toString(36).substring(2, 9),
    name: `Untitled-${number}`,
    path: '',
    content: '',
    isDirty: false,
    encoding: 'UTF-8',
});

const getBaseName = (path: string) => path.replace(/^.*[\\/]/, '');

function App() {
    // 1. 核心狀態
    const initialTabRef = useRef<Tab | null>(null);
    if (!initialTabRef.current) initialTabRef.current = createUntitledTab(1);
    const [tabs, setTabs] = useState<Tab[]>(() => [initialTabRef.current!]);
    const [activeTabId, setActiveTabId] = useState<string>(() => initialTabRef.current!.id);
    const [fontSize, setFontSize] = useState<number>(16);
    const [untitledCounter, setUntitledCounter] = useState<number>(2);
    const tabsRef = useRef<Tab[]>(tabs);
    const pendingPathsRef = useRef<Set<string>>(new Set());
    const launchOpenQueueRef = useRef<Promise<void>>(Promise.resolve());

    const replaceTabs = useCallback((next: Tab[]) => {
        tabsRef.current = next;
        setTabs(next);
    }, []);

    // 3. 當前選中的分頁物件
    const activeTab = tabs.find((t) => t.id === activeTabId);

    // 偵測檔案語言類型
    const getLanguage = (fileName: string) => {
        const ext = fileName.split('.').pop()?.toLowerCase();
        if (ext === 'go') return 'go';
        if (ext === 'php') return 'php';
        if (ext === 'py') return 'python';
        if (ext === 'svg' || ext === 'html') return 'markup';
        return 'plaintext';
    };

    const isMarkdownFile = (fileName: string) => /\.md(?:own)?$/i.test(fileName);
    const isSvgFile = (fileName: string) => /\.svg$/i.test(fileName);

    // 4. 新建空白分頁 (New File)
    const handleNewFile = () => {
        const newTab = createUntitledTab(untitledCounter);
        replaceTabs([...tabsRef.current, newTab]);
        setActiveTabId(newTab.id);
        setUntitledCounter((prev) => prev + 1);
    };

    // 選單、原生拖放與檔案總管右鍵共用開檔流程，保留既有分頁的未儲存內容。
    const openPath = useCallback(async (path: string) => {
        if (!path) return;

        const existingTab = tabsRef.current.find((tab) => tab.path === path);
        if (existingTab) {
            setActiveTabId(existingTab.id);
            return;
        }

        // This reservation is synchronous, so overlapping native events cannot
        // start a second read before React has committed the first new tab.
        if (pendingPathsRef.current.has(path)) return;
        pendingPathsRef.current.add(path);

        try {
            const result = await OpenFile(path);
            if (!result) return; // 目錄或二進位檔由後端拒絕，不建立空分頁

            const tabOpenedWhileReading = tabsRef.current.find((tab) => tab.path === path);
            if (tabOpenedWhileReading) {
                setActiveTabId(tabOpenedWhileReading.id);
                return;
            }

            const newTab: Tab = {
                id: 'tab-' + Date.now() + '-' + Math.random().toString(36).substring(2, 9),
                name: getBaseName(path),
                path,
                content: result.content,
                isDirty: false,
                encoding: result.encoding,
            };
            const currentTabs = tabsRef.current;
            const canReplacePlaceholder = currentTabs.length === 1
                && currentTabs[0].path === ''
                && currentTabs[0].content === ''
                && !currentTabs[0].isDirty;
            replaceTabs(canReplacePlaceholder ? [newTab] : [...currentTabs, newTab]);
            setActiveTabId(newTab.id);
        } catch (err) {
            alert('無法開啟檔案「' + getBaseName(path) + '」:\n' + err);
        } finally {
            pendingPathsRef.current.delete(path);
        }
    }, [replaceTabs]);

    const openPaths = useCallback(async (paths: string[]) => {
        const uniquePaths = [...new Set(paths.filter((path): path is string => typeof path === 'string' && path.length > 0))];
        for (const path of uniquePaths) {
            await openPath(path);
        }
    }, [openPath]);

    // Wails supplies real native absolute paths in event.data.files.
    useEffect(() => {
        const cancel = Events.On('files-dropped', (event) => {
            const files = (event.data as { files?: unknown } | undefined)?.files;
            if (Array.isArray(files)) void openPaths(files.filter((path): path is string => typeof path === 'string'));
        });
        return cancel;
    }, [openPaths]);

    useEffect(() => {
        const drainLaunchFiles = () => {
            // Serialize startup and later launches, including StrictMode's
            // repeated effect setup. Subscribe before draining to avoid gaps.
            launchOpenQueueRef.current = launchOpenQueueRef.current
                .then(async () => { await openPaths(await TakeLaunchFiles()); })
                .catch((err) => { console.error('無法接收啟動檔案:', err); });
        };
        const cancel = Events.On('launch-files-pending', drainLaunchFiles);
        drainLaunchFiles();
        return cancel;
    }, [openPaths]);

    // 5. 開啟舊檔 (Open File)
    const handleOpenFile = async () => {
        try {
            // 喚起原生選擇對話框
            const path = await SelectFile();
            if (!path) return; // 使用者取消

            await openPath(path);
        } catch (err) {
            alert('無法開啟檔案:\n' + err);
        }
    };

    // 6. 儲存檔案 (Save)
    const handleSaveFile = async () => {
        if (!activeTab) return;

        // 如果是全新檔案，尚未有路徑，執行「另存新檔」流程
        if (!activeTab.path) {
            await handleSaveAsFile();
            return;
        }

        try {
            await SaveFile(activeTab.path, activeTab.content, activeTab.encoding || 'UTF-8');
            // 標記為乾淨
            replaceTabs(tabsRef.current.map((t) =>
                t.id === activeTab.id ? { ...t, isDirty: false } : t
            ));
        } catch (err) {
            alert('儲存檔案失敗:\n' + err);
        }
    };

    // 7. 另存新檔 (Save As)
    const handleSaveAsFile = async () => {
        if (!activeTab) return;

        try {
            const defaultName = activeTab.path ? getBaseName(activeTab.path) : activeTab.name + '.txt';
            const savePath = await SelectSaveFile(defaultName);
            if (!savePath) return; // 使用者取消

            await SaveFile(savePath, activeTab.content, activeTab.encoding || 'UTF-8');

            // 更新目前分頁的狀態與路徑資訊
            const newName = getBaseName(savePath);
            replaceTabs(tabsRef.current.map((t) =>
                    t.id === activeTab.id
                        ? { ...t, name: newName, path: savePath, isDirty: false }
                        : t
            ));
        } catch (err) {
            alert('另存新檔失敗:\n' + err);
        }
    };

    // 8. 關閉分頁 (Close Tab)
    const handleCloseTabById = (idToClose: string) => {
        const targetTab = tabs.find((t) => t.id === idToClose);
        if (!targetTab) return;

        // 若有未儲存的內容，彈出確認視窗
        if (targetTab.isDirty) {
            const confirmClose = window.confirm(`檔案「${targetTab.name}」已被修改但尚未儲存。\n確定要關閉嗎？`);
            if (!confirmClose) return;
        }

        const remainingTabs = tabs.filter((t) => t.id !== idToClose);
        replaceTabs(remainingTabs);

        // 如果關閉的是當前作用中的分頁，需切換 Active Tab ID
        if (activeTabId === idToClose) {
            if (remainingTabs.length > 0) {
                // 優先選擇鄰近分頁
                const closedIndex = tabs.findIndex((t) => t.id === idToClose);
                const nextActiveIndex = Math.min(closedIndex, remainingTabs.length - 1);
                setActiveTabId(remainingTabs[nextActiveIndex].id);
            } else {
                // 若全部被關閉，則自動新增一個空白分頁
                const newId = 'tab-' + Date.now();
                replaceTabs([{
                    id: newId,
                    name: 'Untitled-1',
                    path: '',
                    content: '',
                    isDirty: false,
                    encoding: 'UTF-8',
                }]);
                setActiveTabId(newId);
                setUntitledCounter(2);
            }
        }
    };

    // 選單點擊的 Close 動作（作用於當前分頁）
    const handleCloseActiveTab = () => {
        if (activeTabId) {
            handleCloseTabById(activeTabId);
        }
    };

    // 9. 編輯區文字變更 callback
    const handleContentChange = (newValue: string) => {
        replaceTabs(tabsRef.current.map((t) =>
                t.id === activeTabId
                    ? { ...t, content: newValue, isDirty: true }
                    : t
        ));
    };

    // 10. 字體調整
    const handleZoomIn = () => setFontSize((prev) => Math.min(prev + 2, 40));
    const handleZoomOut = () => setFontSize((prev) => Math.max(prev - 2, 10));
    const handleZoomReset = () => setFontSize(16);

    // 10.5 轉換編碼
    const handleConvertEncoding = (newEncoding: string) => {
        if (!activeTabId) return;
        replaceTabs(tabsRef.current.map((t) =>
                t.id === activeTabId
                    ? { ...t, encoding: newEncoding, isDirty: true }
                    : t
        ));
    };

    // 11. 全域快捷鍵監聽 (Shortcuts)
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            const isCtrlOrCmd = e.ctrlKey || e.metaKey;

            if (isCtrlOrCmd) {
                switch (e.key.toLowerCase()) {
                    case 'n':
                        e.preventDefault();
                        handleNewFile();
                        break;
                    case 'o':
                        e.preventDefault();
                        handleOpenFile();
                        break;
                    case 's':
                        e.preventDefault();
                        if (e.shiftKey) {
                            handleSaveAsFile();
                        } else {
                            handleSaveFile();
                        }
                        break;
                    case 'w':
                        e.preventDefault();
                        handleCloseActiveTab();
                        break;
                    case '=':
                    case '+':
                        e.preventDefault();
                        handleZoomIn();
                        break;
                    case '-':
                        e.preventDefault();
                        handleZoomOut();
                        break;
                    case '0':
                        e.preventDefault();
                        handleZoomReset();
                        break;
                    default:
                        break;
                }
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [activeTabId, tabs, untitledCounter]); // 當 activeTab 改變時重新訂閱，確保 closures 內取到最新狀態

    return (
        <div id="App" className="app-root" data-file-drop-target>
            {/* 1. 頂部選單列 */}
            <MenuBar
                onNewFile={handleNewFile}
                onOpenFile={handleOpenFile}
                onSaveFile={handleSaveFile}
                onSaveAsFile={handleSaveAsFile}
                onCloseTab={handleCloseActiveTab}
                onZoomIn={handleZoomIn}
                onZoomOut={handleZoomOut}
                onZoomReset={handleZoomReset}
            />

            {/* 2. 分頁標籤列 */}
            <TabList
                tabs={tabs}
                activeTabId={activeTabId}
                onSelectTab={setActiveTabId}
                onCloseTab={(id, e) => {
                    e.stopPropagation(); // 阻止事件向上觸發分頁切換
                    handleCloseTabById(id);
                }}
                onNewTab={handleNewFile}
            />

            {/* 3. 編輯主區域 */}
            {activeTab ? (
                isMarkdownFile(activeTab.name) ? (
                    <MarkdownWorkspace
                        content={activeTab.content}
                        onChange={handleContentChange}
                        fontSize={fontSize}
                    />
                ) : isSvgFile(activeTab.name) ? (
                    <SvgWorkspace
                        content={activeTab.content}
                        onChange={handleContentChange}
                        fontSize={fontSize}
                    />
                ) : (
                    <Editor
                        content={activeTab.content}
                        onChange={handleContentChange}
                        fontSize={fontSize}
                        language={getLanguage(activeTab.name)}
                    />
                )
            ) : (
                <div className="no-active-tab-fallback">
                    <div className="fallback-card">
                        <span className="fallback-logo">📂</span>
                        <h2>無開啟的分頁</h2>
                        <p>您可以建立新檔案，或是開啟現有的檔案進行編輯。</p>
                        <div className="fallback-buttons">
                            <button className="fallback-btn btn-primary" onClick={handleNewFile}>新建分頁 (Ctrl+N)</button>
                            <button className="fallback-btn" onClick={handleOpenFile}>開啟檔案 (Ctrl+O)</button>
                        </div>
                    </div>
                </div>
            )}

            {/* 4. 底部狀態列 */}
            <StatusBar activeTab={activeTab} fontSize={fontSize} onConvertEncoding={handleConvertEncoding} />
        </div>
    );
}

export default App;
