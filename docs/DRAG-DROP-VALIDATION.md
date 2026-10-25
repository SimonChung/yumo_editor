# 檔案總管拖放功能與驗收

更新日期：2026-10-25。可將 Windows 檔案總管中的一個或多個檔案拖到玉墨編輯區，直接開啟、編輯並以 `Ctrl+S` 儲存。重複拖入已開啟的檔案會切換到該分頁，不覆蓋尚未儲存的內容；目錄、二進位或讀取失敗的檔案不建立空分頁，顯示錯誤後繼續處理其餘有效檔案。Markdown、SVG 與編碼處理沿用現有功能。

## 本次真實任務

由本機 LangGraph 控制台執行真實 Codex，未提供修改清單，系統自行選出桌面入口、前端開檔邏輯與 README 三個檔案。任務 `0e3f9186-5698-416f-ae9a-38c0add36720` 經兩輪、9 個工作完成：首輪保持原碼，獨立驗收 14 fail／2 pass 且 Reviewer 拒絕；第二輪依回饋修正，16 項全過並通過獨立審查。

第二輪程式落盤後曾中斷 worker 與控制程序；generation 2 保留原候選內容及 Codex session，最後保存 14 個 checkpoints 和 10 份代次證據。差異檔先套在獨立副本重驗，再套回本專案；Go build/test/vet、前端 production build、Windows 主程式與 NSIS 安裝檔建置均成功。沒有變更套件版本、既有測試或生成綁定。

16 項前端行為驗收使用實際 React 元件與模擬 Wails I/O 邊界，涵蓋多檔、中文空白路徑、重複與競態、未儲存內容保護、錯誤後繼續、儲存編碼、預覽及事件清理。這與真正的 Explorer／OLE 操作分開記錄：**Windows 原生操作已通過**：使用者從檔案總管拖入四檔並確認全部開啟，代理接續核對四分頁、中文空白路徑、Big5 偵測及 Markdown／SVG 預覽；修改 UTF-8 與 Big5 文字後按 Ctrl+S，磁碟位元組與原編碼一致，UTF-8 關閉後從原生對話框重開也保留內容。跨應用程式拖曳由使用者操作，其餘由代理核對。重複拖入、競態與錯誤後繼續仍以自動元件測試為證據，未逐項重做原生操作。

完整腳本、固定測試、模型工作、scope、SHA256 及逐階段 log 保存於本機控制台專案：

- `C:\Users\Simon\Documents\ChatGPT\LangGraph\docs\VERIFICATION-YUMO-DRAG-2026-10-25.md`
- `C:\Users\Simon\Documents\ChatGPT\LangGraph\docs\evidence\yumo-drag-2026-10-25\`
- `C:\Users\Simon\Documents\ChatGPT\LangGraph\scripts\yumo-validation\`

## Windows 手動回歸檢查表

1. 啟動本次建置的 `build/bin/yumo_editor.exe`。
2. 從檔案總管一起拖入中文空白路徑文字檔、Markdown、SVG 及 Big5 文字檔，核對四個分頁、內容與預覽。
3. 修改文字檔但先不儲存，再拖入同一檔案，確認只切換分頁且保留未儲存內容。
4. 按 `Ctrl+S`，從磁碟核對原路徑內容已更新；重新開啟仍相同。
5. 混入目錄或二進位檔，確認錯誤可辨識，且其餘有效檔案仍可開啟。

本次已完成第 1、2、4 項；第 3、5 項有固定自動元件測試覆蓋，未額外執行原生拖曳。

目前沒有宣稱 macOS／Linux 的原生拖放或全新 Windows 的安裝／解除安裝已通過。驗收文件為交付時補充，與模型產出的三檔 patch 分開記錄。
