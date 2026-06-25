# 規格書: Go GUI 文字編輯器 (YuMo Editor)

## 目標
使用 Golang 打造一個輕量級、跨平台的 GUI 文字編輯器，允許使用者透過分頁 (Tab) 介面同時編輯多個檔案。

### 使用者情境
- 作為使用者，我希望能夠新建一個空白檔案並開始編輯。
- 作為使用者，我希望能夠開啟多個檔案，並透過分頁在它們之間切換。
- 作為使用者，我希望能夠調整編輯器的顯示字體與大小，以符合我的閱讀習慣。
- 作為使用者，我希望能夠將更改儲存到檔案系統中。
- 作為使用者，我希望編輯器能原生運行在 Windows 和 macOS 上。

## 技術棧
- **語言:** Go (1.21+), TypeScript/JavaScript
- **GUI 框架:** [Wails](https://wails.io/) + React
- **目標作業系統:** Windows, macOS, Linux

## 指令
- **開發模式:** `wails dev` 或 `make dev` (透過 `Makefile.win` / `Makefile.mac`)
- **編譯打包:** `wails build` 或 `make build`
- **清理產出:** `make clean`
- **測試:** `go test ./...` (後端)
- **靜態分析:** `go vet ./...`


## 專案結構
```
.
├── main.go            → Wails 進入點
├── app.go             → 後端業務邏輯 (Wails App)
├── frontend/          → React 前端專案
│   ├── src/           → UI 組件與狀態管理
│   ├── package.json
│   └── ...
├── internal/          → 核心邏輯
│   ├── editor/        → 文字緩衝區管理
│   └── fs/            → 檔案系統抽象
├── AGENTS.md           → 代理配置與驗證指令
└── SPEC.md             → 本規格書
```

## 程式碼風格
- **慣用 Go 風格:** 遵循 `effective go` 與 `uber-go/guide`。
- **並行處理:** 使用 channels 與 goroutines 實作非阻塞的檔案 I/O。
- **命名規範:** 匯出識別符使用 CamelCase，內部識別符使用 mixedCaps。

UI 與後端綁定範例:

```go
// 後端 Go (app.go) - 定義綁定至前端的方法
type App struct {
    ctx context.Context
}

func (a *App) OpenFile(path string) (string, error) {
    return fs.ReadFile(path)
}
```

```tsx
// 前端 React (frontend/src/App.tsx) - 調用後端綁定方法
import { OpenFile } from "../wailsjs/go/main/App";

function Editor() {
    const handleOpenFile = async (path: string) => {
        try {
            const content = await OpenFile(path);
            addTab(path, content);
        } catch (err) {
            showError("開啟檔案失敗: " + err);
        }
    };
    // ...
}
```

## 測試策略
- **單元測試:** 對 `internal/editor` 與 `internal/fs` 的邏輯使用 `testing` 套件。
- **UI 測試:** 使用 React Testing Library / Vitest 進行前端元件測試，驗證 UI 狀態與事件觸發。
- **手動驗證:** 在 Windows 與 macOS 上進行跨平台編譯檢查。

## 邊界與規範
- **務必執行 (Always):**
    - 在嘗試開啟/儲存前驗證檔案路徑。
    - 使用 UI 警告優雅地處理 I/O 錯誤。
    - 在完成任何功能前執行 `go vet`。
- **先詢問 (Ask first):**
    - 除了 Wails 與 React 生態系之外新增其他外部依賴。
    - 修改專案目錄結構。
- **絕不可做 (Never):**
    - 使用沉重的 I/O 操作阻塞主 UI 執行緒。
    - 提交 API 金鑰或環境特定路徑。

## 成功標準
- [x] 應用程式可在 Windows 和 macOS 上以視窗形式啟動。
- [x] 使用者可以新建一個空白檔案分頁。
- [x] 使用者可以從磁碟開啟檔案。
- [x] 使用者可以開啟多個檔案，且每個檔案出現在獨立的分頁中。
- [x] 使用者可以在分頁之間切換並編輯各分頁的文字。
- [x] 使用者可以透過 View 選單變更全局字體大小。
- [x] 使用者可以將目前分頁的內容儲存回磁碟。
- [x] 編輯器支援 Go、PHP、Python 語言之關鍵字語法高亮 (Keyword Highlighting)，並自動偵測檔名副檔名。
- [x] `Makefile.win` 與 `Makefile.mac` 已修正並支援 Wails 工作流。
- [x] 應用程式能正常關閉。

## 開放問題
- 是否需要「全部儲存」功能？
- [已實作] 編輯器是否應支援特定語言（如 Go, JSON）的基礎語法高亮？ -> 已首波支援 Go, PHP, Python。
- 是否需要檔案瀏覽器側邊欄，還是僅提供「檔案 -> 開啟」選單？
