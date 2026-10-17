# 玉墨（YuMo Editor）

玉墨是一個以 Go、Wails v3 與 React 製作的跨平台文字與程式碼編輯器。它提供輕量的多分頁編輯體驗，並內建 Markdown 與 SVG 即時預覽，適合撰寫筆記、文件、向量圖與小型程式碼檔案。

## 功能

### 檔案與分頁

- 新增、開啟、儲存、另存新檔與關閉分頁。
- 同時開啟多個檔案；再次開啟已載入的檔案時會切換至既有分頁。
- 未儲存的分頁會顯示修改狀態，關閉前會要求確認。
- 內建檔案選擇與儲存對話框。
- 偵測二進位檔，避免誤以文字模式開啟。

### 編輯體驗

- 行號欄與編輯區同步捲動。
- Go、PHP、Python、HTML 與 SVG 的語法著色。
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

### SVG 即時預覽

開啟副檔名為 `.svg` 的檔案時，預設顯示左側原始碼編輯、右側即時預覽。每次修改 SVG 內容後，預覽會立即更新。

- 可在「編輯」、「分割預覽」與「預覽」三種模式間切換。
- SVG 預覽使用透明背景棋盤格，方便辨識圖像的透明區域。
- 預覽會在 sandbox iframe 中呈現，隔離 SVG 內可能包含的指令碼。
- 開啟與另存新檔對話框皆提供 `.svg` 檔案篩選。

### 編碼支援

- 開啟檔案時自動嘗試辨識 UTF-8、Big5 與 GBK。
- 可在狀態列選擇以 UTF-8、Big5 或 GBK 儲存。
- 狀態列顯示目前檔案路徑、行數、字元數、字型大小與編碼。

## 技術架構

- 後端：Go 1.27.2
- 桌面框架：Wails v3.0.0-beta.30（CLI、Go module 與 `@wailsio/runtime` 使用相同版本）
- 前端：React／React DOM 19.3.1、TypeScript 7.0.2、Vite 8.3.4
- 語法著色：PrismJS
- Markdown：Marked + DOMPurify

## 開發環境需求

- Go 1.27.2（`go.mod` 已固定最低版本；較舊的 Go 在 `GOTOOLCHAIN=auto` 時會自動下載所需工具鏈）
- Node.js 20.19+ 或 22.12+；本次以 Node.js 24.15.0、npm 11.13.0 驗證
- Wails v3.0.0-beta.30 CLI（v3 目前仍為預發行版）
- Windows 平台需安裝 WebView2 Runtime
- 產生 Windows 安裝檔另需 [NSIS 3](https://nsis.sourceforge.io/Download)

安裝 Wails CLI：

```powershell
go install github.com/wailsapp/wails/v3/cmd/wails3@v3.0.0-beta.30
```

若要執行完整編譯流程，另需安裝 [Task](https://taskfile.dev/)：

```powershell
go install github.com/go-task/task/v3/cmd/task@latest
```

## 執行開發模式

首次執行或更新前端相依套件後，先安裝前端套件：

```powershell
cd frontend
npm ci
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

Windows 建立主程式與 NSIS 安裝檔（預設為 amd64／x64）：

```powershell
.\build.bat
```

輸出：

- `build/bin/yumo_editor.exe`：主程式。
- `build/bin/yumo_editor-amd64-installer.exe`：可分發的 Windows 安裝檔。

安裝檔會安裝到 `Program Files\ybak\YuMo Editor`，建立開始選單／桌面捷徑及解除安裝項目，需要管理員權限。內含 Microsoft 簽章的 WebView2 bootstrapper；目標電腦缺少 WebView2 Runtime 時，仍需連網下載 Runtime。應用程式與安裝檔尚未做程式碼簽章。

`build.bat` 會切換到自身所在目錄，支援從其他目錄呼叫，並搜尋 PATH、`%USERPROFILE%\go\bin` 與 NSIS 預設安裝位置。缺少工具或建置失敗會回傳非零結束碼。

| 指令 | 行為 |
| --- | --- |
| `build.bat`、`build.bat all` | 建置主程式與安裝檔 |
| `build.bat build_installer`、`build.bat build-installer` | 建置主程式與安裝檔 |
| `build.bat build` | 僅建置主程式 |
| `build.bat dev` | 啟動開發模式 |
| `build.bat clean` | 移除主程式、安裝檔、前端產物及 Windows syso |
| `build.bat clean_all`、`build.bat clean-all` | 另外移除 `node_modules`，保留 `package-lock.json` |

亦可直接使用 Task（工具需在 PATH）：

```powershell
task build
task package
```

`task build` 會檢查 Wails CLI／runtime 版本、重新產生繫結、建置前端，再以 `production` build tag 編譯主程式。`task package` 接續產生目前平台的套件；Windows 使用 NSIS。前端依 `package-lock.json` 執行 `npm ci`，避免每台電腦取得不同版本。

單獨建置前端：

```powershell
cd frontend
npm run build
```

執行後端測試與靜態分析：

```powershell
go build ./...
go test ./...
go vet ./...
```

重新產生前後端繫結：

```powershell
wails3 generate bindings
```

### 本次升級與驗證（2026-10-18）

版本以 [Go 官方下載](https://go.dev/dl/)、[Wails beta.30 發布](https://github.com/wailsapp/wails/releases/tag/v3.0.0-beta.30)、[React 版本頁](https://react.dev/versions) 及 npm registry 的 `latest` 標籤核對。

Go 使用自動工具鏈切換：本專案內 `go version` 為 1.27.2；本機 `C:\Program Files\Go` 的基礎安裝仍是 1.26.4，未替換系統 MSI。Wails CLI 已更新至 beta.30。

- 已驗證：Go build／test／vet、前端 TypeScript／Vite build、Wails 繫結生成。
- 已驗證：從專案外目錄執行 `clean_all` 後再執行無參數 `build.bat`，成功產出安裝檔；清除不再接續打包，且保留 lockfile。
- 已驗證：NSIS 安裝檔可完整解壓縮，內含主程式 SHA-256 與建置產物一致，並包含簽章有效的 Microsoft WebView2 bootstrapper。
- 已驗證：以隱藏視窗啟動原生主程式，確認「玉墨」視窗建立、WebView2 初始化成功，關閉後結束碼為 0；此項未涵蓋畫面與操作驗收。
- 待驗證：乾淨 Windows 電腦的安裝／升級／解除安裝、缺少 WebView2 時的下載安裝，以及完整桌面開啟／儲存與預覽操作。

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
│       ├── components/     # 編輯器、分頁、選單、狀態列及 Markdown／SVG 預覽
│       └── App.tsx         # 前端分頁與檔案操作流程
└── Taskfile.yml            # 開發、建置與驗證工作
```

## 授權

本專案採用 [MIT License](LICENSE)。
