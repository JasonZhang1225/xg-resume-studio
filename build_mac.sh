#!/usr/bin/env bash
# 构建 macOS 版：PyInstaller 生成 .app（pywebview 独立窗口），再用 hdiutil 打成 .dmg。
# 用法：./build_mac.sh [版本号]，默认 1.1.0。
# 使用当前激活的 Python（如 conda activate xg-resume 后运行）；也可用 PY=/path/to/python 指定。
set -euo pipefail
cd "$(dirname "$0")"

VERSION="${1:-1.1.0}"
APP_NAME="滴鱼简历助手"
PY="${PY:-python}"

if ! "$PY" -c "import fastapi, webview" >/dev/null 2>&1; then
  echo "[ERROR] 依赖未安装。先运行: conda create -n xg-resume python=3.12 && conda activate xg-resume && pip install -r requirements.txt"
  exit 1
fi

"$PY" -m pip show pyinstaller >/dev/null 2>&1 || "$PY" -m pip install pyinstaller

echo "[1/2] Building ${APP_NAME}.app ..."
"$PY" -m PyInstaller --noconfirm --clean --windowed --name "$APP_NAME" desktop.py \
  --osx-bundle-identifier com.xg.resume-studio \
  --add-data "templates:templates" \
  --add-data "static:static" \
  --add-data "resume_templates:resume_templates" \
  --add-data "docs/CHANGELOG.md:docs" \
  --collect-all rapidocr_onnxruntime \
  --collect-all onnxruntime \
  --collect-all pypdfium2 \
  --exclude-module pytest \
  --exclude-module ruff

# 写入版本号（Finder「显示简介」可见）
PLIST="dist/${APP_NAME}.app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString ${VERSION}" "$PLIST"
/usr/libexec/PlistBuddy -c "Add :CFBundleVersion string ${VERSION}" "$PLIST" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Set :CFBundleVersion ${VERSION}" "$PLIST"
# 修改 Info.plist 后重新 ad-hoc 签名，否则 Apple Silicon 上会提示"已损坏"
codesign --force --deep --sign - "dist/${APP_NAME}.app"

echo "[2/2] Building DMG ..."
STAGE="build/dmg"
rm -rf "$STAGE" && mkdir -p "$STAGE"
cp -R "dist/${APP_NAME}.app" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
mkdir -p dist-installer
DMG="dist-installer/XG-Resume-Studio-${VERSION}-macos-$(uname -m).dmg"
rm -f "$DMG"
hdiutil create -volname "XG Resume Studio" -srcfolder "$STAGE" -ov -format UDZO "$DMG"

echo
echo "Done: $DMG"
echo "数据保存在 ~/Library/Application Support/XG Resume Studio/data"
