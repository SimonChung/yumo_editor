# 代理配置

## 驗證指令

- 後端編譯: `go build ./...`
- 後端測試: `go test ./...`
- 後端靜態分析: `go vet ./...`
- 前端編譯: `npm run build` (在 `frontend` 目錄下)
- Wails v3 開發模式: `wails3 dev` (若 PATH 中無 wails3 指令，請使用 `%USERPROFILE%/go/bin/wails3 dev`)
- Wails v3 完整編譯: `task build` (需要安裝 Task: `go install github.com/go-task/task/v3/cmd/task@latest`)
- 生成 v3 綁定: `wails3 generate bindings`
