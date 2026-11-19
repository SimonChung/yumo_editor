# 玉墨（YuMo Editor）0.3.0 規格

## 目標
使用 Golang 打造一個輕量級、跨平台的 GUI 文字編輯器，允許使用者透過分頁 (Tab) 介面同時編輯多個檔案。

### 使用者情境
- 作為使用者，我希望能夠新建一個空白檔案並開始編輯。
- 作為使用者，我希望能夠開啟多個檔案，並透過分頁在它們之間切換。
- 作為使用者，我希望能夠調整編輯器的顯示字體與大小，以符合我的閱讀習慣。
- 作為使用者，我希望能夠將更改儲存到檔案系統中。
- 作為使用者，我希望編輯器能原生運行在 Windows 和 macOS 上。
- 作為使用者，我希望能從檔案右鍵選單開啟既有檔案，並在編輯原文時預覽 Markdown、SVG 或 CSV。

## 技術棧
- Go 1.27.4、Wails 3.1.0、React 19.3.1、TypeScript 7.0.2、esbuild 0.28.2。Go 應用、Wails CLI 與前端 runtime 在建置時核對版本。
- 已有交付格式為 Windows amd64 的 NSIS 安裝檔，以及 macOS arm64 的 App 與本機 DMG。Linux 仍是目標平台，目前 Task 只有打包提示。

## 指令
從專案根目錄執行。首次啟動開發模式前使用 `npm --prefix frontend ci` 安裝鎖定的前端套件。

| 工作 | 入口 |
| --- | --- |
| 桌面開發與正式編譯 | `node build/wails.mjs dev`、`task build` |
| macOS App、Windows 安裝檔 | 對應平台使用 `bash build.sh build_installer` 或 `.\build.bat` |
| Wails 繫結 | `task generate:bindings` |
| Go 測試與靜態分析 | `go test ./...`、`go vet ./...` |
| 清理建置產物 | `task clean`，會移除整個 `build/bin/` |

DMG 組裝、安裝副本比對與平台資產見[建置與打包指南](build/README.md)。

## 開檔與預覽行為

- 開檔、拖放與第二次啟動均沿用分頁開檔流程。同一路徑再次開啟時會切回原分頁，保留尚未儲存的文字。檔案讀取後依偵測的編碼顯示，儲存時可選 UTF-8、Big5 或 GBK。
- Windows 安裝檔註冊「以 YuMo Editor 編輯」。macOS 完整 DMG 提供目前使用者可選裝的 Finder 服務「在YuMoEditor中開啟」，將所選檔案的路徑傳給安裝於「應用程式」的編輯器。
- Markdown、SVG、CSV 預設使用分割預覽，也可切換純編輯或純預覽。Markdown 經 Marked 解析與 DOMPurify 淨化；SVG 經序列化後由圖片解碼器顯示。
- CSV 使用逗號分隔、雙引號包覆欄位，支援引號內逗號、換行與成對雙引號。首筆為欄名，每頁最多 200 筆資料。格式錯誤時提示記錄與欄位位置，修正後重新顯示表格。

## 專案結構
```
.
├── main.go            → Wails 進入點
├── app.go             → 後端業務邏輯 (Wails App)
├── launch_files.go    → 啟動參數與既有視窗的待開檔佇列
├── frontend/          → React 前端專案
│   ├── bindings/      → Wails v3 產生的 JavaScript 繫結
│   ├── src/           → UI 組件與狀態管理
│   ├── package.json
│   └── ...
├── internal/          → 核心邏輯
│   ├── editor/        → 文字緩衝區管理
│   └── fs/            → 檔案系統抽象
├── build/             → 平台資產、CLI 入口與 Go 建置工具鎖檔
├── Taskfile.yml       → 跨平台建置工作
├── docs/validation/   → 有明確版本的驗證紀錄與 SBOM
├── AGENTS.md           → 代理配置與驗證指令
└── SPEC.md             → 本規格書
```

## 程式碼風格
- **慣用 Go 風格:** 遵循 `effective go` 與 `uber-go/guide`。
- **並行處理:** 啟動參數佇列由 mutex 保護；前端使用非同步 Wails 繫結呼叫後端檔案 I/O。
- **命名規範:** 匯出識別符使用 CamelCase，內部識別符使用 mixedCaps。

後端 `OpenFile(path string) (*FileResult, error)` 回傳內容與編碼；偵測到二進位檔時會顯示提示並回傳空結果。前端從 `../bindings/tw.ybak/yumo/app` 匯入 `OpenFile`、`SaveFile` 等方法，再更新分頁狀態。[後端服務](app.go) · [前端開檔流程](frontend/src/App.tsx)

## 測試策略
- **Go 測試**涵蓋編輯資料模型、檔案讀寫、編碼與待開檔佇列。
- **桌面驗收**在正式 App 依序測試檔案選擇、分頁去重、三種預覽模式、即時編輯與存檔重開；各平台實際執行過的項目以對應日期的驗證紀錄為準。[macOS DMG 與 Finder 開檔](docs/validation/macos-0.3.0-5c4198f.md) · [Windows 拖放](docs/DRAG-DROP-VALIDATION.md) · [Windows 右鍵](docs/CONTEXT-MENU-VALIDATION.md)
- **依賴檢查**涵蓋應用及工具 Go 模組、含開發相依的 npm 鎖檔，以及實際建置的執行檔。交付時應記錄對應產物雜湊與 High、Critical 數量。

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
- [x] Task 與平台腳本可產生 Windows 安裝檔與可直接啟動的 macOS App。
- [x] Apple Silicon 本機 DMG 的 App 已與安裝副本逐檔核對，並實測 CSV 的引號逗號與跨行資料。
- [x] 應用程式能正常關閉。

## 開放問題
- 是否需要「全部儲存」功能？
- [已實作] 編輯器是否應支援特定語言（如 Go, JSON）的基礎語法高亮？ -> 已首波支援 Go, PHP, Python。
- 是否需要檔案瀏覽器側邊欄，還是僅提供「檔案 -> 開啟」選單？
