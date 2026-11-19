#!/bin/bash
set -euo pipefail

app=$1
output_dir=$(dirname "$app")
plist="$app/Contents/Info.plist"
version=$(plutil -extract CFBundleShortVersionString raw "$plist")
executable=$(plutil -extract CFBundleExecutable raw "$plist")
arch=$(lipo -archs "$app/Contents/MacOS/$executable")

work=$(mktemp -d "$output_dir/.dmg.XXXXXXXX")
trap 'rm -rf "$work"' EXIT
volume="$work/volume"
mkdir "$volume"
ditto "$app" "$volume/YuMo Editor.app"
codesign --verify --deep --strict "$volume/YuMo Editor.app"
ln -s /Applications "$volume/Applications"

edition=App
if [[ -n "${YUMO_FINDER_MEDIA:-}" ]]; then
    pkg="安裝 Finder 右鍵服務.pkg"
    ditto "$YUMO_FINDER_MEDIA/$pkg" "$volume/$pkg"
    (cd "$volume" && printf '%s  %s\n' \
        '4f9d6aeffb962dfb92dad8382416cdad2cd9d5d9e4fb7e589b86acda2d4478cb' "$pkg" | shasum -a 256 -c -)
    ditto "$YUMO_FINDER_MEDIA/安裝說明.txt" "$volume/安裝說明.txt"
    edition=Finder
fi

dmg="$output_dir/YuMo-Editor-$version-macOS-$arch-$edition.dmg"
if [[ -e "$dmg" ]]; then
    echo "DMG already exists: $dmg" >&2
    exit 1
fi
hdiutil create -format UDZO -fs HFS+ -volname "YuMo Editor" -srcfolder "$volume" "$work/image.dmg"
hdiutil verify "$work/image.dmg"
# Publish the verified file without overwriting a concurrent build.
ln "$work/image.dmg" "$dmg"
shasum -a 256 "$dmg"
