# 建置與打包

下列指令均從專案根目錄執行。Go、Node.js、npm、Task 與各平台的準備步驟見[開發環境需求](../README.md#開發環境需求)。Wails CLI 與 esbuild 的版本由 `build/tools/go.mod`、`build/tools/go.sum` 固定；前端安裝使用 `npm ci` 與版控中的 `frontend/package-lock.json`。

## macOS 正式 App

```sh
bash build.sh build_installer
codesign --verify --deep --strict --verbose=2 build/bin/yumo_editor.app
lipo -archs build/bin/yumo_editor.app/Contents/MacOS/yumo_editor
go version -m build/bin/yumo_editor.app/Contents/MacOS/yumo_editor
```

`bash build.sh build` 產生執行檔 `build/bin/yumo_editor`。`build_installer` 會執行 Task 的 `darwin:package`，重新產生繫結、建置前端與正式執行檔，再把圖示、`Info.plist` 和執行檔放入 `build/bin/yumo_editor.app`，最後使用 ad hoc 簽章。打包時 Wails 也會更新 `build/` 下的圖示及平台範本。要重建某次提交，可在來源乾淨的目錄打包，並用上方的 `go version -m` 核對 `vcs.revision` 和 `vcs.modified=false`。

### 製作 DMG

只有 App 時，可直接用下列範例製作拖曳安裝的 DMG。若要重建 0.3.0 含右鍵服務的版本，先掛載一份含「安裝 Finder 右鍵服務.pkg」及「安裝說明.txt」的已驗證 0.3.0 映像，再設定來源。請依 Finder 實際顯示的卷名調整路徑。

```sh
export YUMO_FINDER_MEDIA="/Volumes/YuMo Editor"
```

Finder 服務是獨立的 AppKit 服務，原始碼隨服務放在 `YuMoEditorFinder.service/Contents/Resources/FinderService.m`。目前 Git 中的 Task 只建置編輯器 App，重打包時可沿用經核對的服務安裝包。若只需 App，可用 `unset YUMO_FINDER_MEDIA` 清除上次設定的路徑。下列指令會從 App 讀取版本與架構，將新映像寫入 `build/bin/`，檔名末尾的 `App` 或 `Finder` 表示收錄的內容。

```sh
(
  set -eu
  app=build/bin/yumo_editor.app
  version=$(plutil -extract CFBundleShortVersionString raw "$app/Contents/Info.plist")
  arch=$(lipo -archs "$app/Contents/MacOS/yumo_editor")
  stage=$(mktemp -d)
  trap 'rm -rf "$stage"' EXIT

  ditto "$app" "$stage/YuMo Editor.app"
  ln -s /Applications "$stage/Applications"
  edition=App
  if [ -n "${YUMO_FINDER_MEDIA:-}" ]; then
    pkg="安裝 Finder 右鍵服務.pkg"
    (cd "$YUMO_FINDER_MEDIA" && printf '%s  %s\n' \
      '4f9d6aeffb962dfb92dad8382416cdad2cd9d5d9e4fb7e589b86acda2d4478cb' "$pkg" | shasum -a 256 -c -)
    ditto "$YUMO_FINDER_MEDIA/$pkg" "$stage/$pkg"
    ditto "$YUMO_FINDER_MEDIA/安裝說明.txt" "$stage/安裝說明.txt"
    edition=Finder
  fi

  dmg="build/bin/YuMo-Editor-$version-macOS-$arch-$edition.dmg"
  hdiutil create -format UDZO -fs HFS+ -volname "YuMo Editor" -srcfolder "$stage" "$dmg"
  hdiutil verify "$dmg"
  shasum -a 256 "$dmg"
)
```

檔案已存在時，`hdiutil create` 會停止。2026-11-19 實際交付的映像檔名與 SHA-256 見[本機交付紀錄](../docs/validation/macos-0.3.0-a73a7c3.md)；每次產生的新映像均應記錄自己的雜湊。

### 核對安裝副本

從新映像將 App 安裝至「應用程式」後，先保留該映像掛載。以下以卷名「YuMo Editor」為例，比對映像內與已安裝 App 的所有檔案，並驗證簽章和內嵌提交。成功時 `diff` 不會輸出差異。

```sh
media="/Volumes/YuMo Editor"
installed="/Applications/YuMo Editor.app"
diff -qr "$media/YuMo Editor.app" "$installed"
codesign --verify --deep --strict --verbose=2 "$installed"
go version -m "$installed/Contents/MacOS/yumo_editor"
```

退出映像後從「應用程式」啟動，用 [README 的 CSV 範例](../README.md#csv-表格預覽)檢查中文、引號內逗號與跨行欄位。交付前再以同一份執行檔驗證 SBOM，各檢查範圍與已知公告見[安全驗證紀錄](../docs/validation/macos-0.3.0-a73a7c3.md#相依與安全掃描)。

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
