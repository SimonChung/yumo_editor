# 代理配置

## 驗證指令

### 後端 (Backend)
- 編譯: `go build ./...`
- 測試: `go test ./...`
- 靜態分析: `go vet ./...`

### 前端 (Frontend)
- 編譯: `npm run build` (需在 `frontend` 目錄下執行)

### Wails v3
- 開發模式: `wails3 dev` (若 PATH 中無指令，請使用 `%USERPROFILE%/go/bin/wails3 dev`)
- 完整編譯: `task build` (需安裝 Task: `go install github.com/go-task/task/v3/cmd/task@latest`)
- 生成綁定: `wails3 generate bindings`
