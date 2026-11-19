# macOS 0.3.0（5c4198f）Finder 版 DMG 安裝與開檔驗證

2026-11-19 在 Apple Silicon Mac（macOS 27.2.1、arm64）上，使用含 Finder 服務的 DMG 將 YuMo Editor 從 `a73a7c3` 更新到 `5c4198f6a1183004a3c1e6d012aabd0c6d2b0bfc`。兩次建置的 App 版本號都是 0.3.0，以執行檔內嵌的 Git 提交與 SHA-256 識別此次更新。[前一版安裝紀錄](macos-0.3.0-a73a7c3.md)

## 安裝來源與結果

| 核對項目 | SHA-256 |
| --- | --- |
| 安裝使用的 `YuMo-Editor-0.3.0-macOS-arm64-Finder.dmg` | `c127e255244b4343276cb103fad34f2311368836871b6bc84bec6c0a756f730d` |
| 映像內及安裝後的 `Contents/MacOS/yumo_editor` | `bc1ad2d2b272f7a6acc6e20067595f52d3fd47f35e8996eb9e2d6c0e5fc262ba` |
| 映像內的 `安裝 Finder 右鍵服務.pkg` | `4f9d6aeffb962dfb92dad8382416cdad2cd9d5d9e4fb7e589b86acda2d4478cb` |

`hdiutil verify` 通過後，以唯讀方式掛載映像。正常退出舊版，再從映像更新 `/Applications/YuMo Editor.app`。已逐檔核對安裝副本與映像內的 App，檔案內容、檔案權限與連結目標一致。安裝副本通過 `codesign --verify --deep --strict --verbose=2` 的 ad hoc 簽章驗證。`go version -m` 顯示上列完整提交及 `vcs.modified=false`。

已解開映像內的服務安裝包，比對其中的 `YuMoEditorFinder.service` 與目前使用者在 `~/Library/Services/` 的服務。兩份內容一致，已安裝的服務版本為 1.0，簽章驗證通過，因此本次沿用既有服務。

## Finder 右鍵與 CSV 分割預覽

1. 退出 DMG，並確認 YuMo Editor 已完全退出。
2. 在 Finder 對 `Wails 3.1 中文.csv` 按右鍵，直接點選第一層選單的「在YuMoEditor中開啟」。
3. 確認 Finder 服務啟動了 `/Applications/YuMo Editor.app/Contents/MacOS/yumo_editor`。新版視窗顯示所選檔案的分頁，預設「分割預覽」已開啟。

畫面實際顯示三欄、兩筆資料。第一筆的產地保留引號內的半形逗號，兩行備註也保留在同一個儲存格。

| 名稱 | 產地 | 備註 |
| --- | --- | --- |
| 茶葉 | 南投,鹿谷 | 第一行<br>第二行 |
| 咖啡 | 臺南 | 結案通過 |

開檔前後的 CSV SHA-256 均為 `8ab20d674a22a97587c02178fe6c35fc043837b78684a9f74afc48e01acbc73a`。要重做這項檢查，可使用相同內容的 [README CSV 範例](../../README.md#csv-表格預覽)。

## 相依與安全掃描

這份 CycloneDX 1.6 清單來自本次 macOS App 的 Go 執行檔。清單中的提交、執行檔 SHA-256 與五個元件（主模組、Go 標準函式庫及三個連入模組）已和安裝副本核對。[5c4198f 執行檔 SBOM](macos-0.3.0-5c4198f-app.cdx.json)

Trivy 0.76.2 在來源相依、Go 應用模組、Go 工具模組，以及 App、Wails CLI、esbuild 三個執行檔的六個範圍，均為 **High 0、Critical 0**。建置驗證使用的漏洞資料庫更新於 2026-11-18 13:03 UTC。`npm audit` 涵蓋開發相依，所有嚴重度合計為 0。`govulncheck` 對 App 與 esbuild 均無發現，Wails 建置 CLI 仍列有未評級公告 `GO-2026-6905`，命中模組及套件層級。
