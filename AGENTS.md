# 代理配置

## 驗證指令

### 後端 (Backend)
- 編譯: `go build ./...`
- 測試: `go test ./...`
- 靜態分析: `go vet ./...`

### 前端 (Frontend)
- 編譯: `npm run build` (需在 `frontend` 目錄下執行)

### Wails v3
- 開發模式: `node build/wails.mjs dev`（使用 `build/tools/go.mod`、`go.sum` 鎖定的 CLI 與已修補相依）
- 完整編譯: `task build` (需安裝 Task: `go install github.com/go-task/task/v3/cmd/task@latest`)
- 生成綁定: `node build/wails.mjs generate bindings`
- 工具鏈與依賴更新需同時驗證根模組與 `build/tools` 模組，保留原有 SBOM 阻擋門檻。
