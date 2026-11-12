# 專案實際使用工具的版本巡檢

[GitHub Actions](https://github.com/SimonChung/yumo_editor/actions/workflows/sbom-tool-versions.yml)：每週一 UTC 01:00（台北 09:00）在 GitHub-hosted Ubuntu runner 執行，Mac 不需要開機；排程在預設分支生效。有排程的專案也可手動 Run workflow，勾選 `dry_run` 只預覽。

## 追蹤範圍

- **Go**：`go.mod`、`build/tools/go.mod`。

以 `.github/sbom-tool-monitor.json` 的 schema 2 `tools` 清單啟用工具。只有專案實際使用且有可讀取版本來源的工具才列入；未使用的工具不列入清單，回報 `not_used`，不連線查版本、不讀取或建立通知 Issue。已移除所有固定版本通知基準，不因其他專案使用某工具而在此專案追蹤。

啟用的工具至少要有一個 `pin_sources`；每個來源都必須存在且能解析。來源遺失、格式錯誤或 Trivy 多處版本不一致會失敗，不會悄悄改成未使用。停用工具時移除對應設定；新增工具時先加入實際版本來源，再啟用設定。所有來源只讀文字，不執行來源程式。`baseline`、optional 來源與舊版設定格式皆不接受。

Trivy 讀取掃描腳本或版本 guard，查詢官方 `aquasecurity/trivy` 正式 Releases。Go 讀取 go.mod（含 toolchain）、CI 或 Dockerfile，保留所有來源並以最低版本比較；查詢 [Go 官方下載 JSON](https://go.dev/dl/?mode=json) 與[發布紀錄](https://go.dev/doc/devel/release)，略過 beta／RC，涵蓋中間版本的安全修補。

這套巡檢目前支援 Trivy 與 Go，不會因移除未使用工具而自動加入其他工具，也不取代應用程式的建置、測試與 SBOM 驗證。

## 通知規則

- 沒有較新正式版：只記錄 Actions 摘要，不建立 Issue。
- 有新版：在該儲存庫建立 Issue，指派並提及 SimonChung；通知管道依 GitHub 個人設定。Trivy 新版映像另核對 Docker Hub 索引 digest 與 linux/amd64、linux/arm64。
- 尚未採用的正式版有 CVE、GHSA、安全或漏洞修補線索，標題標為「安全修補優先」，建議 24～48 小時內評估；一般更新可排入每月維護。線索不是漏洞適用性判定。
- 以「工具＋最新版」去重，包含已關閉 Issue。一般更新後來出現安全線索，會在原 Issue 留下單次升級提醒。保留 Issue 與隱藏識別標記，關閉即可。
- 兩種工具分別檢查，其中一種失敗仍會處理另一種。必要來源、API／registry／發布紀錄失敗或不完整，流程回傳非 0，不冒充沒有新版；不另發例行 Issue。

## 驗證與維護

檢查器與測試只使用 Python 標準函式庫；沿用 runner 內建 Python/Git，沒有新增第三方 action 或套件。工作流程使用 contents: read，有通知需求的專案另授予 issues: write；暫時 askpass 不保存憑證，concurrency 防止重複執行。

```sh
python3 -B -m unittest discover -s .github/tests -p 'test_sbom_tool_versions.py' -v
python3 -B scripts/check_sbom_tool_versions.py --repository SimonChung/yumo_editor
```

`--publish` 供工作流程建立／更新 Issue，需要 GH_TOKEN。去重依賴 `github-actions[bot]` 建立的 Issue；本機預覽有新版、需要查私人 Issues 時也需要權杖。測試涵蓋未使用工具完全不連線、實際來源缺失不能靜默略過、不接受固定基準、正式版排序、安全修補優先、去重、API 故障隔離及 digest 驗證。

共用檢查器與測試源自 codex-skills，在各儲存庫保留相同副本。設定與週期排程依各專案實際工具決定，不能直接覆蓋為其他專案的工具清單。GitHub 排程限制見[官方說明](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)。
