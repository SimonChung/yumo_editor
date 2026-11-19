# macOS 0.3.0 本機 DMG 與安裝驗證

2026-11-19 在 Apple Silicon Mac（macOS 27.2.1）用原專案的 `main` 提交 `a73a7c315c5a44555c0ecc5ef8e973e9a9e1fed9` 重新建置。當時已比對 `origin/main`；正式執行檔的 Go build info 包含相同的 `vcs.revision`、`vcs.modified=false`、`GOARCH=arm64` 與 `production` 標籤。

## 產物與核對值

| 項目 | 位置 | SHA-256 |
| --- | --- | --- |
| 本機磁碟映像 | `build/bin/YuMo-Editor-0.3.0-macOS-arm64.dmg` | `f120f831f45da3150f19e51f93e311c837d448f6d7d462b678bc172aa2c428ad` |
| 正式 App 內的執行檔 | `Contents/MacOS/yumo_editor` | `bf3cf4f059fb7a507977955d037307b1cd7c706da557b1eca0c39f9b30f7a384` |
| 映像內的選裝服務 | `安裝 Finder 右鍵服務.pkg` | `4f9d6aeffb962dfb92dad8382416cdad2cd9d5d9e4fb7e589b86acda2d4478cb` |

專案建置產物是 `build/bin/yumo_editor.app`。映像內使用「YuMo Editor.app」作為顯示檔名，另有通往 `/Applications` 的捷徑、Finder 服務安裝包和「安裝說明.txt」。這次 DMG 沿用前一版的服務安裝包，其 SHA-256 已逐一核對。服務 1.0 安裝在目前使用者的 `~/Library/Services/YuMoEditorFinder.service`，需 Apple Silicon 與 macOS 27.2 以上。

## 建置與實機結果

| 檢查 | 本次結果 |
| --- | --- |
| 建置與測試 | `bash build.sh build_installer`、`go build ./...`、`go test -count=1 ./...`、`go vet ./...`、應用與工具模組的 `go mod verify` 均通過。建置包含 Wails 繫結、TypeScript 與 esbuild。 |
| 映像與簽章 | `hdiutil verify` 通過。建置、掛載映像及安裝後的 App 均通過 `codesign --verify --deep --strict --verbose=2`。簽章類型為 ad hoc，本次交付範圍為本機使用。 |
| 安裝與啟動 | 從唯讀映像複製到 `/Applications/YuMo Editor.app`。已比對 App 內所有檔案內容、權限與連結目標，並確認執行中的程序來自該安裝路徑。 |
| CSV 實機預覽 | 從已安裝的 App 開啟「Wails 3.1 中文.csv」。分割預覽有「名稱／產地／備註」三欄、兩筆資料；「南投,鹿谷」在同一格，「第一行」與「第二行」在同一格內換行。 |

同日稍早的 Wails 3.1.0 驗證另涵蓋 CSV 編輯後的即時更新、UTF-8 存檔重開，以及 Markdown、一般 SVG 與省略命名空間的 SVG 預覽。該次驗證使用升級候選建置，核對本次安裝檔時請使用上表的雜湊。[Wails 升級驗證紀錄](wails-3.1.0-verification.json)

App 的 `Info.plist` 宣告最低 macOS 12.0；本次實機只有 macOS 27.2.1。連結器曾提示部分物件使用的 SDK 建置目標高於 11.0，舊版 macOS 與 Intel Mac 的執行相容性仍待實測。

## 相依與安全掃描

本次使用 Go 1.27.4、Wails 3.1.0、esbuild 0.28.2。Trivy 0.76.2 的漏洞資料庫更新於 2026-11-18 13:03 UTC。下表為這份建置當時的結果。

| 範圍 | High | Critical | 覆蓋 |
| --- | ---: | ---: | --- |
| 來源清單 | 0 | 0 | 應用 Go manifest 9 項、工具 Go manifest 136 項、npm 鎖檔 33 項，含開發相依 |
| 兩份 Go 模組 SBOM | 0 | 0 | 應用模組與工具模組各自掃描，包含標準函式庫及測試相依 |
| 實際 macOS App 執行檔 | 0 | 0 | 對照 `go version -m` 及 CycloneDX，涵蓋主模組、連入的模組與標準函式庫 |
| Wails CLI 與 esbuild 執行檔 | 0 | 0 | 對兩個實際建置工具分別產生並掃描 SBOM |

`npm audit` 包含開發相依，所有嚴重度合計為 0。前端鎖檔、已安裝套件、打包後資產及受檢的三個執行檔均未找到 `picomatch`。另以 `govulncheck` 掃描實際執行檔，App 與 esbuild 沒有命中；Wails CLI 保留未評級公告 `GO-2026-6905`，命中模組及套件層級，未列出受影響的函式。[本次 macOS 執行檔 SBOM](macos-0.3.0-a73a7c3-app.cdx.json) · [建置工具公告紀錄](go-1.27.4-20261111.md#保留的上游發現)

## 如何重查

在原專案目錄執行以下指令可核對這份既有 DMG 與已安裝執行檔。重新產生的映像需保存自己的 SHA-256。

```sh
dmg=build/bin/YuMo-Editor-0.3.0-macOS-arm64.dmg
installed="/Applications/YuMo Editor.app"
hdiutil verify "$dmg"
codesign --verify --deep --strict --verbose=2 "$installed"
shasum -a 256 "$dmg" "$installed/Contents/MacOS/yumo_editor"
go version -m "$installed/Contents/MacOS/yumo_editor"
```

本機原始紀錄位於 `build/bin/verification/dmg-20261119-102958-a73a7c3/`。其中 `release.json` 記錄安裝比對與實機表格，`security.json` 記錄鎖檔雜湊、各範圍計數及公告；同目錄保有原始 SBOM、掃描 JSON 與建置日誌。[重新打包操作](../../build/README.md#製作-dmg)
