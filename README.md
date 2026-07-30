# 玉墨（YuMo Editor）

玉墨是一個以 Go、Wails v3 與 React 製作的跨平台文字與程式碼編輯器。它提供輕量的多分頁編輯體驗，並內建 Markdown 即時預覽，適合撰寫筆記、文件與小型程式碼檔案。

## 功能

### 檔案與分頁

- 新增、開啟、儲存、另存新檔與關閉分頁。
- 同時開啟多個檔案；再次開啟已載入的檔案時會切換至既有分頁。
- 未儲存的分頁會顯示修改狀態，關閉前會要求確認。
- 內建檔案選擇與儲存對話框。
- 偵測二進位檔，避免誤以文字模式開啟。

### 編輯體驗

- 行號欄與編輯區同步捲動。
- Go、PHP、Python 的語法著色。
- 字型縮放：`Ctrl` + `+`、`Ctrl` + `-`、`Ctrl` + `0`。
- 支援常用快捷鍵：
  - `Ctrl` + `N`：新增檔案
  - `Ctrl` + `O`：開啟檔案
  - `Ctrl` + `S`：儲存
  - `Ctrl` + `Shift` + `S`：另存新檔
  - `Ctrl` + `W`：關閉目前分頁

### Markdown 即時預覽

開啟副檔名為 `.md` 或 `.markdown` 的檔案時，預設顯示左側編輯、右側即時預覽。每次修改 Markdown 內容後，預覽會立即更新。

- 可在「編輯」、「分割預覽」與「預覽」三種模式間切換。
- 支援 GitHub Flavored Markdown（標題、清單、表格、連結、圖片、程式碼區塊、引用等）。
- 預覽輸出會先經過 HTML 淨化處理，避免不安全內容注入應用程式頁面。
- 窄螢幕時，分割畫面會自動改為上下排列。

### 編碼支援

- 開啟檔案時自動嘗試辨識 UTF-8、Big5 與 GBK。
- 可在狀態列選擇以 UTF-8、Big5 或 GBK 儲存。
- 狀態列顯示目前檔案路徑、行數、字元數、字型大小與編碼。

## 技術架構

- 後端：Go 1.26+
- 桌面框架：Wails v3
- 前端：React、TypeScript、Vite
- 語法著色：PrismJS
- Markdown：Marked + DOMPurify

## 開發環境需求

- Go 1.26 或以上
- Node.js 與 npm
- Wails v3 CLI
- Windows 平台需安裝 WebView2 Runtime

安裝 Wails CLI：

```powershell
go install github.com/wailsapp/wails/v3/cmd/wails3@latest
```

若要執行完整編譯流程，另需安裝 [Task](https://taskfile.dev/)：

```powershell
go install github.com/go-task/task/v3/cmd/task@latest
```

## 執行開發模式

首次執行或更新前端相依套件後，先安裝前端套件：

```powershell
cd frontend
npm install
cd ..
```

接著從專案根目錄啟動 Wails 開發模式：

```powershell
wails3 dev
```

若 `wails3` 尚未加入 PATH，可在 Windows 使用：

```powershell
& "$env:USERPROFILE\go\bin\wails3.exe" dev
```

> 請不要使用 `go run main.go` 作為日常開發方式。此專案需要 Wails 同時啟動桌面 WebView 與 React 前端，應使用 `wails3 dev`。

## 建置與驗證

建立發行版：

```powershell
task build
```

單獨建置前端：

```powershell
cd frontend
npm run build
```

執行後端測試與靜態分析：

```powershell
go test ./...
go vet ./...
```

重新產生前後端繫結：

```powershell
wails3 generate bindings
```

## 專案結構

```text
.
├── app.go                  # Wails 對前端公開的檔案操作 API
├── main.go                 # 桌面應用程式進入點
├── internal/
│   ├── editor/             # 文件內容與修改狀態模型
│   └── fs/                 # 讀寫檔案、編碼偵測與二進位檔判斷
├── frontend/
│   └── src/
│       ├── components/     # 編輯器、分頁、選單、狀態列與 Markdown 預覽
│       └── App.tsx         # 前端分頁與檔案操作流程
└── Taskfile.yml            # 開發、建置與驗證工作
```

## 授權

本專案採用 [MIT License](LICENSE)。
