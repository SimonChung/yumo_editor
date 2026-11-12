# 專案實際使用工具的每週版本檢查

[GitHub Actions](https://github.com/SimonChung/yumo_editor/actions/workflows/sbom-tool-versions.yml) 每週一 UTC 01:00（台北 09:00）執行；不需開啟 Mac。也可手動 Run workflow，`dry_run` 僅預覽。排程只執行預設分支上的設定，工作分支可手動驗證。

## 本專案範圍

Go、Git、Python、Node.js、npm、Task、NSIS、Wails CLI、TypeScript、Vite、Vite React plugin。

| 工具 | 比較方式 | 實際來源 |
|---|---|---|
| Go | 專案版本 | `go.mod`, `build/tools/go.mod` |
| Git | 未固定版本，追蹤啟用後的新發布 | `.github/workflows/sbom-tool-versions.yml` |
| Python | 未固定版本，追蹤啟用後的新發布 | `.github/workflows/sbom-tool-versions.yml` |
| Node.js | 未固定版本，追蹤啟用後的新發布 | `frontend/package.json` |
| npm | 未固定版本，追蹤啟用後的新發布 | `Taskfile.yml` |
| Task | 未固定版本，追蹤啟用後的新發布 | `Taskfile.yml` |
| NSIS | 未固定版本，追蹤啟用後的新發布 | `build.bat` |
| Wails CLI | 實際固定版本 | `build/tools/go.mod` |
| TypeScript | 實際固定版本 | `frontend/package-lock.json` |
| Vite | 實際固定版本 | `frontend/package-lock.json` |
| Vite React plugin | 實際固定版本 | `frontend/package-lock.json` |

## 版本與通知規則

- Go／Trivy 沿用 `.github/sbom-tool-monitor.json`；其他工具明列於 `.github/project-tools.json`。所有工具必須有目前存在的使用來源；未列入的工具不查詢、不通知，來源消失或無法解析會失敗，不回退到假設版本。
- 固定版本直接解析腳本、Gradle wrapper、JSON 鎖檔、Go 工具模組及 monitoring lock；不執行來源程式。npm 工具以 package-lock.json 的解析版本為準，應用程式函式庫與間接依賴仍由 SBOM 管理。
- 未固定版本或浮動映像（例如 Git、Python、Docker、Node.js、JDK、Debian／Alpine）採發布追蹤：`started_at` 是啟用時間，不是安裝版本。沒有發布日期的官方索引以啟用時的 `initial_versions` 作比較；JDK 也記錄初始版本，避免資產更新時間被誤認為新版本。首次不補發既有版本通知，之後只通知新發布；不宣稱知道每台主機的實際版本。
- PostgreSQL、GitHub Actions 的主版本 alias：提醒較新主版本，以及啟用後同一主版本的新修補；不把浮動 alias 當成尚未採用既有修補。資料庫升級必須另外評估相容性，不會自動執行。
- 預設只選正式版本；Wails 已採用 beta 的專案另追蹤相同 major.minor 的 alpha／beta／RC 到正式版，並可提醒後續正式版；排除 nightly 與其他系列預覽版。Android Studio 包含 Patch 編號並只讀 Stable channel；NSIS 排除尚無發布日期的開發文件。
- 有新版才建立 GitHub Issue，指派並提及 SimonChung。安全修補先發布，標題標示「安全修補優先」，建議 24～48 小時內評估；一般更新納入每月維護。GitHub 網站／信件／行動裝置通知依個人通知設定。
- 版本與安全線索取自官方 GitHub Releases、PyPI、npm、Go、Google Android、Adoptium、Python、PostgreSQL、Alpine、Debian、GNU、NSIS 與 Docker 文件。安全線索涵蓋中間版本的 CVE／GHSA／安全修補說明；PyPI、npm、AGP 與 Wails 固定版本另查 OSV 修補資訊。JDK 以 Adoptium 官方發行作為通用 JDK 發布來源，不代表本機 JBR 品牌或版本；發行前 14 天內的 OpenJDK 官方安全公告作為優先評估線索，必須再確認版本適用性。
- 安全優先是官方發布資訊及公告的線索判斷，不是完整漏洞掃描或漏洞適用性判定。沒有公告線索時列為一般更新；來源查詢失敗或必要資料不完整時回傳非 0，不冒充沒有新版。RSS／產品更新 feed 的歷史保留範圍依上游，仍須維持每週執行。
- 開啟與已關閉 Issue 都參與去重。發布追蹤記錄通知內每個版本，較舊維護系列的新安全修補不會被較大的版本號蓋掉。後來出現新的安全證據時升級原通知，每組安全證據只留言一次；保留 Issue 與識別標記。
- 只讀檢查先完成，再依安全優先順序發布；其中一種工具失敗不會掩蓋其他工具結果。此流程不更新依賴、部署、提交或推送。真正升級時仍須固定版本／digest、測試及通過 SBOM。

## 維護與驗證

共用檢查器與測試維持各儲存庫相同副本；設定清單依各專案使用情況維護。腳本只使用 Python 標準函式庫，runner 使用內建 Python/Git，沒有新增第三方套件或 Actions。工作流程僅授予 contents: read、issues: write，暫時 Git askpass 不保存憑證，concurrency 避免同一儲存庫重複發布。

```sh
python3 -B -m unittest discover -s .github/tests -p 'test_*tool_versions.py' -v
python3 -B scripts/check_project_tool_versions.py --repository SimonChung/yumo_editor
```

`--publish` 需 GH_TOKEN；本機預覽有新版時，需要讀取私人儲存庫 Issues 的權杖進行去重。新工具先加入官方來源 adapter、測試及真實使用來源，再更新設定；不要從其他專案直接複製工具清單。移除工具時一併移除設定。

通用 Git／Python 是本儲存庫 CI 自身使用的工具，父專案因此也有週檢。OS 內建 shell／檔案工具、Codex 本體、平台 SDK 的系統函式庫、臨時一次性驗證下載與未啟用服務不列為獨立工具訂閱。

官方 API 參考：[GitHub 排程](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)、[PyPI JSON](https://docs.pypi.org/api/json/)、[Adoptium API](https://github.com/adoptium/api.adoptium.net/blob/main/docs/cookbook.adoc)、[OSV](https://google.github.io/osv.dev/api/)。
