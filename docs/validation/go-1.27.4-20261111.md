# Go 1.27.4 升級驗證

2026-11-11 在 Apple Silicon macOS 驗證，完整結果及來源／產物 SHA-256 見同目錄的 `go-1.27.4-20261111.json`。Windows、Linux 與較舊 macOS 未實機驗證；macOS 建置仍有既有 deployment target 警告，不能據此宣稱支援舊版系統。

## 變更

- 根模組與 Wails 建置工具模組皆使用 Go 1.27.4。
- 修補 `x/net`、`x/text`、`x/image`、`klauspost/compress`、`goldmark`、`jsonparser` 與 `x/crypto` 的已知公告；`x/crypto` 固定官方公告指出的修復 commit，該修復尚未包含在最新正式 tag 內。
- 根模組的版本限定 `replace` 約束 Wails 帶入但未直接編入應用程式的依賴圖；建置工具模組另固定實際使用的安全版本。未自動改寫 Wails 版本。
- `node build/wails.mjs` 以 `build/tools/go.mod`、`go.sum` 建置 CLI，避免全域 CLI 的依賴版本覆蓋驗證結果。Windows 安裝檔工作目錄亦予以保留。

## 功能與安全驗證

- 根模組與建置工具 `go mod tidy -diff`、`go mod verify` 通過。
- `go test ./...`、`go vet ./...`、`bash build.sh build` 通過，含繫結生成、前端建置及桌面程式編譯。
- CLI／Go module／前端 runtime 版本一致；模擬 Go 下載進度輸出不影響版本檢查，缺少 Go 時會失敗。
- Trivy 0.76.2 固定映像 digest，掃描來源 manifest（含 npm 開發／可選相依）、Go 來源模組及兩個實際 Mach-O 產物，HIGH／CRITICAL 為 0。未使用忽略清單或 `--ignore-unfixed`。
- CycloneDX Go 清單以 `cyclonedx-gomod v1.12.0` 產生；來源使用 `mod -std -test -json`，產物使用 `bin -std -json`。執行時明確設定 `GOTOOLCHAIN=go1.27.4`，避免產生器從外部工作目錄讀到不同的標準函式庫版本。
- 來源清單核對全部 Go manifest 與 npm lock 元件，二進位清單核對 `go version -m`；另以 OSV 查詢兩個完整模組圖與 `stdlib@1.27.4`，共 238 組套件版本。npm audit 含開發相依，所有嚴重度合計為 0。

## 保留的上游發現

[GO-2026-6905](https://pkg.go.dev/vuln/GO-2026-6905) 影響 Wails 建置 CLI 間接使用的 `github.com/blakesmith/ar`；官方公告未評級且尚無修正版，因此本次結果不是「零已知漏洞」。這筆發現完整保留在版本掃描紀錄中，沒有加入忽略清單。

`govulncheck v1.9.0 -mode=binary` 對實際 Wails CLI 回傳 0，仍列出模組／套件層級命中，未列出受影響函式。nFPM 的正式打包程式使用 `ar.NewWriter`；`ar.NewReader` 出現在其測試中。這些是影響範圍的補充證據，沒有刪除版本掃描發現。後續更新 Wails 或 nFPM 時應重新檢查此公告及嚴重度。
