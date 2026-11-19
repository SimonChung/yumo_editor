# 固定驗收與執行環境

此目錄是控制台外建立的獨立驗收，不可修改。專案仍使用 Wails v3.0.0-beta.30，不升級工具鏈。

公開事件契約採官方範例：原生視窗 `EnableFileDrop: true`；監聽 `events.Common.WindowFilesDropped`，從 `event.Context().DroppedFiles()` 取得真實絕對路徑；以 `application.Get().Event.Emit("files-dropped", map[string]any{"files": files})` 傳送至前端（可用既有 application 變數）。前端 `Events.On` 來自 `@wailsio/runtime`，回呼接收 `event.data.files`，回傳值是取消訂閱函式。編輯範圍使用 `data-file-drop-target`，Wails 會找該節點或其祖先；外部檔案不可用瀏覽器 File.name 拼接絕對路徑。

依據：本機鎖定版本 `examples/drag-n-drop/main.go`、`pkg/application/webview_window_options.go`、runtime events 與 https://v3.wails.io/features/drag-and-drop/files/ 。

`node acceptance/drop-acceptance.cjs` 實際載入 React App 及其子元件，在 jsdom 執行，只有 Wails 事件／檔案 I/O 邊界替換為測試替身；不代表真正 Windows 拖放已驗證。`node acceptance/typecheck.cjs` 連接映像內已固定的前端依賴進行 TypeScript 檢查，結束時移除臨時連結。兩者都不修改產品來源檔案。

依賴位於唯讀 `/opt/yumo-deps/node_modules`；不要把 node_modules、symlink、build/dist、生成綁定或暫存輸出留在 workspace。不要變更既有 Go 測試、驗收腳本、套件版本或 lockfile。Linux worker 沒有 Go／Windows WebView2，外層驗收者在差異檔套用副本與原專案執行 AGENTS.md 的 Go build/test/vet、前端建置和 Windows 原生操作，結果另存證據；在 worker 內不得宣稱那些檢查已通過。

第一輪遵循 red-green：未收到獨立審查與失敗測試回饋前，只重現缺少功能，不修改任何產品檔案。Reviewer 按最終功能判定，初輪不符合就拒絕；後續輪次依獨立回饋實作，保持測試內容不變。
