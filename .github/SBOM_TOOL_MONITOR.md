# 每週 SBOM 工具版本巡檢

[GitHub Actions](https://github.com/SimonChung/yumo_editor/actions/workflows/sbom-tool-versions.yml) 每週一 UTC 01:00（台北 09:00）執行，Mac 不需要開機；也可手動 Run workflow，勾選 `dry_run` 只預覽。排程在預設分支生效，GitHub 可能延遲執行。公開儲存庫若 60 天沒有活動，GitHub 會停用排程，須在 Actions 重新啟用。

## 追蹤範圍

與 codex-skills 相同，追蹤官方 `aquasecurity/trivy` 的正式版本。此儲存庫目前沒有 Trivy 掃描入口；0.76.2 是明列的版本巡檢基準，不代表已安裝掃描器或應用程式通過 SBOM 驗證。

`.github/sbom-tool-monitor.json` 記錄版本來源。必要來源遺失、格式不符或版本互相矛盾會失敗；只有明確標成 optional 的來源不存在時，才允許使用 baseline。未來加入掃描器時，改設實際 pin_sources，避免維護兩份版本。Python、PowerShell 及 Go 來源都只讀文字，不執行掃描腳本。執行摘要的 version_basis 區分 scanner_pin 與 release_baseline。

這是 Trivy 新版通知，並非整個專案相依套件、CycloneDX、govulncheck 或主機工具的全面版本巡檢；不會自動升級工具或取代應用程式 SBOM 驗證。

## 通知規則

- 沒有較新的正式版：只記錄 Actions 摘要，不建立 Issue。
- 有新版：在此儲存庫建立 Issue，指派並提及 SimonChung；通知管道依 GitHub 個人設定。新版映像會核對 Docker Hub 索引 digest 與 linux/amd64、linux/arm64。
- 從目前版本到最新版之間的任一正式版說明有 CVE、GHSA、安全或漏洞修補線索，標題標為「安全修補優先」，建議 24～48 小時內評估；一般更新可排入每月維護。這是官方發布說明線索，並非漏洞適用性判定。
- 同版本的開啟或關閉 Issue 都參與去重。一般更新後來出現安全線索，會在原 Issue 留下單次升級提醒。保留 Issue 與隱藏識別標記，關閉即可，勿刪除。
- API／registry 失敗或資料不完整會使工作流程失敗，不冒充沒有新版；不另發例行 Issue。Actions 失敗通知仍受個人通知設定控制。

## 驗證與維護

本工具及測試使用 Python 標準函式庫、GitHub runner 內建 Python/Git，不新增第三方 action 或套件。Python 是共用 CI 巡檢工具的限定用途；不改變專案應用程式的語言選擇。GITHUB_TOKEN 僅授予 contents: read、issues: write，暫時 askpass 不保存憑證，concurrency 防止同時重複建立 Issue。

```sh
python3 -B -m unittest discover -s .github/tests -p 'test_sbom_tool_versions.py' -v
python3 -B scripts/check_sbom_tool_versions.py --repository SimonChung/yumo_editor
```

本機預覽在有新版、需要查私人 Issues 時也需要 GH_TOKEN；`--publish` 會實際建立／更新 Issue。測試涵蓋無新版靜默、正式版排序、來源缺失、基準與實際版本切換、跨版本安全線索、已關閉 Issue 去重、提醒升級重試、API／registry 失敗與 digest 驗證。

檢查器與測試源自 codex-skills，各儲存庫保留相同副本，讓公開與私人儲存庫都能獨立執行，無須開放私人儲存庫存取權。維護邏輯時同步這三份檔案：工作流程、scripts/check_sbom_tool_versions.py、.github/tests/test_sbom_tool_versions.py。

[GitHub 排程規則](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
