# 建置與打包

下列指令均從專案根目錄執行。Go、Node.js、npm、Task 與各平台的準備步驟見[開發環境需求](../README.md#開發環境需求)。Wails CLI 與 esbuild 的版本由 `build/tools/go.mod`、`build/tools/go.sum` 固定；前端安裝使用 `npm ci` 與版控中的 `frontend/package-lock.json`。

## macOS 正式 App

```sh
bash build.sh build_installer
codesign --verify --deep --strict --verbose=2 build/bin/yumo_editor.app
lipo -archs build/bin/yumo_editor.app/Contents/MacOS/yumo_editor
go version -m build/bin/yumo_editor.app/Contents/MacOS/yumo_editor
```

`bash build.sh build` 產生執行檔 `build/bin/yumo_editor`。`build_installer` 會執行 Task 的 `darwin:package`，重新產生繫結、建置前端與正式執行檔，再把圖示、`Info.plist` 和執行檔放入 `build/bin/yumo_editor.app`，最後使用 ad hoc 簽章。打包時會讀取版控中的 `build/darwin/Info.plist`，只在 App 內的副本設定執行檔名與正式版權署名。Wails 從 `build/appicon.png` 直接將圖示產生在 App 的 `Contents/Resources/`。這個流程保留 macOS、Windows 的來源檔，也不建立 `build/ios/`。

### 製作 DMG

從專案根目錄執行下列指令，會先建置並簽署正式 App，再產生可拖曳到「應用程式」安裝的 DMG。完成後會驗證映像並印出 SHA-256。

```sh
bash build.sh dmg
```

預設產物為 `build/bin/YuMo-Editor-<版本>-macOS-<架構>-App.dmg`。要包含 Finder 右鍵服務，先掛載含「安裝 Finder 右鍵服務.pkg」及「安裝說明.txt」的已驗證 0.3.0 映像，再以實際卷名指定來源。

```sh
YUMO_FINDER_MEDIA="/Volumes/YuMo Editor" bash build.sh dmg
```

此模式會核對服務安裝包的 SHA-256，將安裝包與說明一併放入檔名以 `-Finder.dmg` 結尾的映像。服務原始碼隨服務放在 `YuMoEditorFinder.service/Contents/Resources/FinderService.m`。兩種模式都保留已存在的同名 DMG，重建前可將先前映像改名或移到其他位置。[5c4198f Finder 版 DMG 安裝與開檔紀錄](../docs/validation/macos-0.3.0-5c4198f.md)

從乾淨的 checkout 打包後，可用以下指令檢查工作目錄。第一行應無輸出，第二行應成功退出。

```sh
git status --porcelain=v1 --untracked-files=all
test ! -e build/ios
```

### 核對安裝副本

從新映像將 App 安裝至「應用程式」後，先保留該映像掛載。以下以卷名「YuMo Editor」為例，比對映像內與已安裝 App 的所有檔案，並驗證簽章和內嵌提交。成功時 `diff` 不會輸出差異。

```sh
media="/Volumes/YuMo Editor"
installed="/Applications/YuMo Editor.app"
diff -qr "$media/YuMo Editor.app" "$installed"
codesign --verify --deep --strict --verbose=2 "$installed"
go version -m "$installed/Contents/MacOS/yumo_editor"
```

退出映像後從「應用程式」啟動，用 [README 的 CSV 範例](../README.md#csv-表格預覽)檢查中文、引號內逗號與跨行欄位。交付前再以同一份執行檔驗證 SBOM，各檢查範圍與已知公告見[安全驗證紀錄](../docs/validation/macos-0.3.0-5c4198f.md#相依與安全掃描)。

## Windows

執行 `build.bat` 產生 `build/bin/yumo_editor.exe` 與 `build/bin/yumo_editor-amd64-installer.exe`。完整安裝、開發與清理指令見[專案 README](../README.md#建置與驗證)。

| 路徑 | 用途 |
| --- | --- |
| `build/windows/icon.ico`、`info.json`、`wails.exe.manifest` | 執行檔圖示、版本資訊與應用程式 manifest。圖示來源是 `build/appicon.png`。 |
| `build/windows/installer/project.nsi` | 正式 NSIS 安裝檔入口；Task 用專案鎖定的 Wails CLI 產生並封裝 Microsoft WebView2 bootstrapper。 |
| `build/windows/installer/wails_tools.nsh` | 正式安裝檔引用的 Wails 3.1.0 輔助檔。`build/windows/nsis/` 為另一組範本。 |
| `build/windows/installer/context_menu.nsh` | 安裝及移除「以 YuMo Editor 編輯」檔案選單；Windows 11 的入口在「顯示其他選項」。 |

這些安裝腳本與中繼資料受版本控制，更新 Wails 平台資產時應保留專案自訂的選單與安裝邏輯。

## 建置目錄與清理

`build/darwin/Info.plist` 供正式 App 使用，`Info.dev.plist` 供開發使用；`icons.icns` 由圖示來源產生。`build/bin/` 放置各平台的建置產物，本機原始驗證報告存放於其下的 `verification/`。`task clean` 會移除整個 `build/bin/`、`frontend/dist/` 與 Windows syso；執行前請先將要保留的 DMG、報告與備份移出該目錄。`task clean:all` 另清除 `frontend/node_modules/`，兩種清理都保留 `frontend/package-lock.json`。
