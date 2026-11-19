# 0.3.0 Release 附件下載與 SHA-256 核對紀錄

2026-11-19 04:16 UTC 從 GitHub 完整下載以下四個附件，全部回傳 HTTP 200。從下載內容計算的 SHA-256 及位元組數皆與 GitHub Release 回報的值相符。[0.3.0 Release](https://github.com/SimonChung/yumo_editor/releases/tag/0.3.0)

| 附件 | 下載連結 | 位元組數 | 實測 SHA-256 |
| --- | --- | ---: | --- |
| Windows x64 安裝檔 | [yumo_editor-amd64-installer.exe](https://github.com/SimonChung/yumo_editor/releases/download/0.3.0/yumo_editor-amd64-installer.exe) | 6,897,830 | `b14c66d57367d44d47494ce0cb1bdd3d4ccdb6a5081c5d4b7c576daf41641404` |
| Windows 執行檔 SBOM | [windows-0.3.0-amd64-314d4d6-app.cdx.json](https://github.com/SimonChung/yumo_editor/releases/download/0.3.0/windows-0.3.0-amd64-314d4d6-app.cdx.json) | 9,301 | `2ae26be394e12decf157dbece2bd485e51c53c651e1bfb7b850cdd3cae0cb030` |
| macOS arm64 Finder 版 DMG | [YuMo-Editor-0.3.0-macOS-arm64.dmg](https://github.com/SimonChung/yumo_editor/releases/download/0.3.0/YuMo-Editor-0.3.0-macOS-arm64.dmg) | 6,802,315 | `c127e255244b4343276cb103fad34f2311368836871b6bc84bec6c0a756f730d` |
| macOS 執行檔 SBOM | [macos-0.3.0-5c4198f-app.cdx.json](https://github.com/SimonChung/yumo_editor/releases/download/0.3.0/macos-0.3.0-5c4198f-app.cdx.json) | 6,583 | `885b7ff06af7d5263fbdc12165d974519a542da3e3ee39f483589d2653e5dc1d` |

Windows x64 安裝檔的建置提交為 `314d4d6`，macOS Finder 版 DMG 的建置提交為 `5c4198f`。兩個安裝檔的 SHA-256 均與各平台的驗證紀錄相符，兩份 SBOM 也分別與專案收錄的檔案逐位元組相同。[Windows 驗證紀錄](windows-0.3.0-amd64-314d4d6.md) · [macOS 驗證紀錄](macos-0.3.0-5c4198f.md)
