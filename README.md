# 玉墨（YuMo Editor）

目前版本：**V0.3.0**。

玉墨是一個以 Go、Wails v3 與 React 製作的跨平台文字與程式碼編輯器。它提供輕量的多分頁編輯體驗，並內建 Markdown、SVG 與 CSV 即時預覽，適合撰寫筆記、文件、向量圖與小型程式碼檔案。

## macOS 安裝與更新

2026-11-19 已在 Apple Silicon Mac 實測提交 `5c4198f`。含右鍵服務的映像檔名為 `YuMo-Editor-0.3.0-macOS-arm64-Finder.dmg`。取得 DMG 後可依下列步驟安裝。若手邊只有 Git 原始碼，請見[建置與打包指南](build/README.md)。

1. 更新前先儲存開啟的文件並退出 YuMo Editor。
2. 打開 DMG，將 **YuMo Editor.app** 拖到旁邊的 **Applications**。更新既有版本時選擇「取代」，保留 App 名稱。
3. 若要加入 Finder 右鍵選單，開啟映像內的「安裝 Finder 右鍵服務.pkg」。這是目前使用者的選裝元件，隨附版本 1.0 適用於 Apple Silicon、macOS 27.2 以上。已安裝此版服務者可沿用。
4. 退出磁碟映像，從「應用程式」開啟 YuMo Editor。需要核對版本時，可比對本次 DMG 與執行檔的 SHA-256。[5c4198f 安裝、Finder 右鍵與 CSV 實測紀錄](docs/validation/macos-0.3.0-5c4198f.md)

### 從 Finder 右鍵開檔

在 Finder 選取檔案，按右鍵選擇 **「在YuMoEditor中開啟」**。本機已在右鍵選單第一層驗證這個項目。服務將所選檔案交給 `/Applications/YuMo Editor.app`。若編輯器已開啟，會在既有視窗切換或新增分頁。

若找不到選單項目，請先確認選取的是檔案，再到 Finder 的「前往資料夾」輸入 `~/Library/Services`，查看是否有 `YuMoEditorFinder.service`。若項目出現但無法開檔，請確認 App 的名稱及安裝位置。要解除安裝，可退出編輯器後將 App 移到垃圾桶；要一併移除右鍵項目，再將該使用者的服務移到垃圾桶。

## 功能

### 檔案與分頁

- 新增、開啟、儲存、另存新檔與關閉分頁。
- 可從 Windows 檔案總管將單一或多個檔案拖入編輯區，以原始完整路徑直接開啟；中文與含空白的路徑亦受支援。
- 安裝 Windows 版本後，可在檔案上按右鍵選擇「以 YuMo Editor 編輯」，將檔案開在玉墨的分頁中。
- 同時開啟多個檔案；再次開啟已載入的檔案時會切換至既有分頁。
- 未儲存的分頁會顯示修改狀態，關閉前會要求確認。
- 內建檔案選擇與儲存對話框。
- 偵測二進位檔，避免誤以文字模式開啟。

拖入的檔案與透過「開啟檔案」選擇的檔案共用相同分頁：重複拖入只會切換到既有分頁，不會重新讀取或覆蓋尚未儲存的修改。拖入後可直接編輯並以 `Ctrl` + `S` 儲存回原始路徑，且保留偵測到的編碼；Markdown、SVG 與 CSV 皆可在編輯時即時預覽。若一批檔案中包含目錄、二進位檔或無法讀取的檔案，玉墨會顯示錯誤並繼續處理其餘有效檔案。

2026-10-25 已完成真實 Codex 兩輪修正、中斷恢復、差異檔套用、Windows 建置，以及使用者實拖後的原生編輯／儲存／重開驗證；結果與測試邊界分列於 [拖放驗收紀錄](docs/DRAG-DROP-VALIDATION.md)。

### Windows 檔案總管右鍵選單

執行新版 `yumo_editor-amd64-installer.exe` 安裝或升級後，在任意檔案上按右鍵即可選擇「以 YuMo Editor 編輯」。Windows 11 的傳統選單項目位於「顯示其他選項」中。若安裝後尚未出現，請重新啟動 Windows 檔案總管，使其載入最新的選單註冊。

支援中文與含空白的路徑，也可一次選取多個檔案（傳統選單最多 15 個）。玉墨尚未啟動時會啟動並開檔；已啟動時會喚回既有視窗並新增分頁。再次開啟同一路徑只會切換分頁，保留未儲存內容。目錄不顯示此選單；二進位或無法讀取的檔案沿用既有錯誤處理。

右鍵選單隨安裝註冊、隨解除安裝移除，不變更副檔名的預設開啟程式。直接執行可攜式主程式不會註冊選單，但可傳入一個或多個檔案路徑，例如：

```powershell
& '.\build\bin\yumo_editor.exe' 'C:\文件\中文 筆記.txt' 'C:\文件\說明.md'
```

建置、原生開檔與選單註冊的驗證結果及限制，見 [右鍵選單驗收紀錄](docs/CONTEXT-MENU-VALIDATION.md)。

### 編輯體驗

下列快捷鍵在 macOS 也可使用 `⌘` 作為修飾鍵，例如 `⌘S` 儲存、`⇧⌘S` 另存新檔。

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
- 預覽以 SVG 圖片呈現，保留透明背景與即時更新。SVG 內的指令碼不會執行。
- 開啟與另存新檔對話框皆提供 `.svg` 檔案篩選。

### CSV 表格預覽

開啟 `.csv` 或將目前檔案另存為 `.csv`，即可在編輯原文時即時查看表格。預設使用「分割預覽」，也可切換到「編輯」或「預覽」。第一筆記錄顯示為欄名，超過 200 筆資料時可翻頁瀏覽。

以逗號分隔欄位。含逗號或換行的欄位用雙引號包住，欄位內的雙引號寫成 `""`。引號格式有誤時，預覽會指出記錄與欄位，修正後即恢復表格。

可將下列內容存成 UTF-8 的 `茶葉.csv`。表格應有三欄、兩筆資料。第一筆的產地是完整的「南投,鹿谷」，備註中的兩行會顯示在同一格。在分割預覽中把「臺南」改成「臺中」，預覽應立即更新。儲存、關閉分頁再開啟，即可核對磁碟上的結果。

```csv
名稱,產地,備註
茶葉,"南投,鹿谷","第一行
第二行"
咖啡,臺南,結案通過
```

### 編碼支援

- 開啟檔案時自動嘗試辨識 UTF-8、Big5 與 GBK。
- 可在狀態列選擇以 UTF-8、Big5 或 GBK 儲存。
- 狀態列顯示目前檔案路徑、行數、字元數、字型大小與編碼。

## 技術架構

- 後端：Go 1.27.4
- 桌面框架：Wails v3.1.0（CLI、Go module 與 `@wailsio/runtime` 使用相同版本）
- 前端：React／React DOM 19.3.1、TypeScript 7.0.2、esbuild 0.28.2（由 Go 依 `build/tools/go.mod` 編譯）
- 語法著色：PrismJS
- Markdown：Marked + DOMPurify

Wails 3.1.0 的相依套件與建置驗證請見 [CycloneDX SBOM](docs/validation/wails-3.1.0-source.cdx.json) 與 [驗證結果](docs/validation/wails-3.1.0-verification.json)。CSV 預覽初版的 Windows 測試另見 [CSV 驗證紀錄](docs/validation/csv-preview-verification.json)。

## 開發環境需求

- Go 1.27.4（`go.mod` 已固定最低版本；較舊的 Go 在 `GOTOOLCHAIN=auto` 時會自動下載所需工具鏈）
- Node.js 20.x 自 20.19.0 起，或 22.12.0 以上。此次 macOS 打包使用 Node.js 24.15.0、npm 11.12.1。
- macOS 需有 Xcode Command Line Tools 或含命令列工具的 Xcode，可用 `xcode-select -p` 確認。
- 專案鎖定的 Wails v3.1.0 CLI（由下方入口建置）
- Windows 平台需安裝 WebView2 Runtime
- 產生 Windows 安裝檔另需 [NSIS 3](https://nsis.sourceforge.io/Download)

Wails CLI 由 `build/tools/go.mod`、`go.sum` 鎖定，透過下列入口以 Go 1.27.4 建置並執行；同時固定已修補的建置工具依賴，無須安裝全域 Wails CLI：

```powershell
node build/wails.mjs version
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
node build/wails.mjs dev
```

此入口會保留呼叫端工作目錄，Go module、CLI 與前端 runtime 的版本一致性仍由建置流程檢查。

## 建置與驗證

macOS 從專案根目錄執行以下指令，可產出並檢查本機架構的正式 App。若要一併產生 DMG，執行 `bash build.sh dmg`。加入 Finder 服務與比對安裝副本的步驟見[建置與打包指南](build/README.md)。

```sh
bash build.sh build_installer
codesign --verify --deep --strict --verbose=2 build/bin/yumo_editor.app
open build/bin/yumo_editor.app
```

Windows 建立主程式與 NSIS 安裝檔（預設為 amd64／x64）：

```powershell
.\build.bat
```

輸出：

- `build/bin/yumo_editor.exe`：主程式。
- `build/bin/yumo_editor-amd64-installer.exe`：可分發的 Windows 安裝檔。

安裝檔會安裝到 `Program Files\ybak\YuMo Editor`，建立開始選單／桌面捷徑、檔案右鍵「以 YuMo Editor 編輯」及解除安裝項目，需要管理員權限。內含 Microsoft 簽章的 WebView2 bootstrapper；目標電腦缺少 WebView2 Runtime 時，仍需連網下載 Runtime。應用程式與安裝檔尚未做程式碼簽章。

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

在 `frontend` 下執行 `npm run preview` 可在本機 4173 埠檢查正式建置的資產。`npm run dev` 預設使用 5173 埠，修改前端原始碼會重新載入頁面。有未儲存分頁時會保留畫面，可在儲存後手動重新載入。桌面開檔與儲存功能需透過 Wails 開發模式或桌面執行檔測試。

執行後端測試與靜態分析：

```powershell
go build ./...
go test ./...
go vet ./...
```

重新產生前後端繫結（含乾淨 checkout 所需的嵌入資產準備）：

```powershell
task generate:bindings
```

### 歷史紀錄：2026-10-18 的 Windows 工具鏈升級

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
│       ├── components/     # 編輯器、分頁、選單、狀態列及 Markdown／SVG／CSV 預覽
│       └── App.tsx         # 前端分頁與檔案操作流程
└── Taskfile.yml            # 開發、建置與驗證工作
```

## 授權

本專案採用 [MIT License](LICENSE)。

## 專案工具版本巡檢

GitHub Actions 每週檢查本專案實際使用的工具；固定版本依來源比較，未固定工具追蹤啟用後的新發布。有新版才通知，安全修補優先。工具清單、來源與通知去重方式見[巡檢說明](.github/SBOM_TOOL_MONITOR.md)。

2026-11-11 升級 Go 1.27.4 並鎖定修補後的 Wails 建置工具；功能測試、SBOM 覆蓋與保留的上游公告見[驗證紀錄](docs/validation/go-1.27.4-20261111.md)。
