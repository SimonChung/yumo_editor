# Windows 右鍵選單驗收

日期：2026-10-26。

## 實作

- NSIS 安裝時註冊 `Software\Classes\*\shell\YuMoEditor`，標籤為「以 YuMo Editor 編輯」，含應用程式圖示。依安裝範圍使用 HKLM 或 HKCU；正式安裝檔預設為全機安裝。
- 命令格式為 `"安裝路徑\yumo_editor.exe" "%1"`，支援中文與空白。只對檔案註冊，不設定副檔名關聯。`MultiSelectModel=Document` 遵循傳統選單的 15 檔限制。
- 解除安裝僅在命令仍指向本安裝位置時移除選單，避免舊安裝移除另一個位置的新命令。
- 首次啟動與後續程序的檔案路徑先排入佇列；React 訂閱事件後才取出。後續啟動將檔案送往既有視窗，沿用分頁去重、編碼與錯誤處理。

## 已驗證

- `go build ./...`、`go test ./...`、`go vet ./...`、`build.bat` 通過；完整建置包含 bindings、TypeScript／Vite、Windows 主程式及 NSIS 安裝檔。
- Go 測試涵蓋前端尚未就緒的開檔請求、第二個程序的相對路徑、中文空白路徑、空參數、重複取出防護、通知回呼及 50 個並行請求。
- 以同一份 `context_menu.nsh` 編譯暫時的 HKCU 測試工具，確認標籤、圖示及引號正確；另一個安裝位置的解除註冊保留命令，相同位置則移除成功。測試註冊已清除。
- 透過 Windows Shell 的 `YuMoEditor` verb 啟動本次建置，中文空白路徑檔案成功載入。再次啟動帶入另一檔案後，同一個程序／視窗出現兩個分頁，Markdown 預覽正常。
- 在原生編輯器修改測試 Markdown 而不儲存，再透過 Shell verb 開啟同一路徑：分頁數不增加，未儲存內容保留；按 `Ctrl+S` 後，磁碟上的原始路徑確實更新。
- 新啟動程序的原生開檔對話框右鍵選單可見正確中文標籤及 YuMo 圖示。
- 7-Zip 可解壓縮正式安裝檔，其中的主程式 SHA-256 與 `build/bin/yumo_editor.exe` 一致。

## 驗證邊界

既有 Explorer 視窗在本次暫時註冊後未顯示新項目；重新開啟資料夾視窗仍相同。未重新啟動使用者的整個 Explorer 工作階段。原生檔案對話框已確認選單顯示，Shell verb 已確認命令可用，但不能據此宣稱 Explorer 選單點擊驗收完成。

尚未在本機執行需要管理員權限的正式全機安裝／升級／解除安裝，也未取代原本安裝於 Program Files 的舊版。安裝新版並重新啟動 Explorer 後，應確認：

1. 單檔右鍵 → 顯示其他選項 → 以 YuMo Editor 編輯，可啟動並開檔。
2. 選取兩個檔案使用同一選單，兩檔均進入同一視窗；重複開啟保留未儲存修改。
3. 解除安裝後，選單消失；其他應用程式的選單與副檔名關聯不受影響。

Windows 的傳統選單行為參考 [Microsoft：Extending Shortcut Menus](https://learn.microsoft.com/en-us/windows/win32/shell/context)、[Verb Selection Model](https://learn.microsoft.com/en-us/windows/win32/shell/how-to-employ-the-verb-selection-model) 及 [Windows 11 選單說明](https://blogs.windows.com/blog/2021/07/19/extending-the-context-menu-and-share-dialog-in-windows-11/)。
