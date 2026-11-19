# Windows x64 0.3.0（314d4d6）執行檔 SBOM 驗證

2026-11-19 從 GitHub 的 `0.3.0` Release 下載 NSIS 安裝檔，以 7-Zip 解出 `yumo_editor.exe`。這個 Windows x64 主程式內嵌的建置提交是 `314d4d6bf3f8641fada76a1fd2192bfe5d0c424b`，`vcs.modified=false`，使用 Go 1.27.4 與 Wails v3.0.0-beta.30。同一 Release 的 macOS Finder 版建置自 `5c4198f`。[Windows 安裝檔](https://github.com/SimonChung/yumo_editor/releases/download/0.3.0/yumo_editor-amd64-installer.exe) · [macOS 驗證紀錄](macos-0.3.0-5c4198f.md)

## 檔案核對

| 檔案 | SHA-256 |
| --- | --- |
| Release 安裝檔 `yumo_editor-amd64-installer.exe` | `b14c66d57367d44d47494ce0cb1bdd3d4ccdb6a5081c5d4b7c576daf41641404` |
| 安裝檔內的 `yumo_editor.exe` | `dbc016795f60e3ac342aca758e6f4b048e0b203e37a31899c1fe76f0b978f3ef` |
| `windows-0.3.0-amd64-314d4d6-app.cdx.json` | `2ae26be394e12decf157dbece2bd485e51c53c651e1bfb7b850cdd3cae0cb030` |

以 `cyclonedx-gomod v1.12.0` 的 `bin -std` 模式從主程式產生 SBOM，並通過 CycloneDX 1.6 JSON Schema 驗證。核對 PE 標頭、`go version -m` 與 SBOM 後，確認平台為 `windows/amd64`，主模組、Go 標準函式庫及 6 個連入模組的名稱與版本均相符。專案收錄的 SBOM 與 Release 附件逐位元組一致。[專案內的 SBOM](windows-0.3.0-amd64-314d4d6-app.cdx.json) · [Release 上的 SBOM](https://github.com/SimonChung/yumo_editor/releases/download/0.3.0/windows-0.3.0-amd64-314d4d6-app.cdx.json)

## 漏洞掃描

| 工具 | 輸入 | 結果 |
| --- | --- | --- |
| Trivy 0.76.2 `rootfs` | 只含解出主程式的目錄 | High 0、Critical 0 |
| Trivy 0.76.2 `sbom` | Release 的 CycloneDX SBOM | High 0、Critical 0 |
| govulncheck v1.9.0 `-mode binary` | 解出的主程式 | 0 筆發現 |

Trivy 在兩次掃描都辨識出上述 8 個元件，漏洞資料庫更新於 2026-11-18 13:03 UTC。govulncheck 使用的 Go 漏洞資料庫更新於 2026-11-11 02:51 UTC。驗證範圍為 Windows 主程式與其 Go 元件。本次在 macOS 上靜態檢查，未在 Windows 執行安裝或 GUI 測試。[原始驗證摘要（JSON）](windows-0.3.0-amd64-314d4d6-verification.json)

## 重做檢查

將上方的安裝檔與 SBOM 下載到空目錄後，在 macOS 或 Linux 執行下列指令。將三個 SHA-256 與上表比對，並在 Go 建置資訊中核對 `vcs.revision`。

```sh
7zz x -oextracted yumo_editor-amd64-installer.exe yumo_editor.exe
sbom=windows-0.3.0-amd64-314d4d6-app.cdx.json
shasum -a 256 yumo_editor-amd64-installer.exe extracted/yumo_editor.exe "$sbom"
go version -m extracted/yumo_editor.exe
trivy rootfs --scanners vuln --ignorefile /dev/null --severity HIGH,CRITICAL --exit-code 1 extracted
trivy sbom --scanners vuln --ignorefile /dev/null --severity HIGH,CRITICAL --exit-code 1 "$sbom"
govulncheck -mode binary extracted/yumo_editor.exe
```
