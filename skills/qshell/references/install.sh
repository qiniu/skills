#!/usr/bin/env bash
#
# qshell 自动安装脚本
# 支持 macOS (Intel/Apple Silicon) 和 Linux (amd64/arm64/386)
# Windows 用户请从 https://github.com/qiniu/qshell/releases 手动下载
#
# 用法: bash install.sh
#

set -euo pipefail

INSTALL_DIR="${QSHELL_INSTALL_DIR:-$HOME/.local/bin}"

# ---------- 1. 获取最新版本号 ----------

echo "正在获取 qshell 最新版本..."
VERSION=$(curl -s "https://api.github.com/repos/qiniu/qshell/releases/latest" | grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/')
if [ -z "$VERSION" ]; then
  echo "Error: Failed to detect latest version. Please check https://github.com/qiniu/qshell/releases manually." >&2
  exit 1
fi
echo "最新版本: v${VERSION}"

# ---------- 2. 检测平台和架构 ----------

OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

case "${OS}-${ARCH}" in
  darwin-arm64)                SUFFIX="darwin-arm64" ;;
  darwin-x86_64)               SUFFIX="darwin-amd64" ;;
  linux-x86_64)                SUFFIX="linux-amd64" ;;
  linux-aarch64|linux-arm64)   SUFFIX="linux-arm64" ;;
  linux-i386|linux-i686)       SUFFIX="linux-386" ;;
  *)
    echo "Error: Unsupported platform: $OS/$ARCH" >&2
    echo "Please download manually from https://github.com/qiniu/qshell/releases" >&2
    exit 1
    ;;
esac

echo "检测到平台: $SUFFIX"

# ---------- 3. 下载二进制 ----------

WORK_DIR=$(mktemp -d)
trap 'rm -rf "$WORK_DIR"' EXIT

# 下载地址必须带 Referer，否则会被拒绝
URL="https://kodo-toolbox-new.qiniu.com/qshell-v${VERSION}-${SUFFIX}.tar.gz"
echo "正在下载: $URL"
curl -fSL -e https://developer.qiniu.com -o "$WORK_DIR/qshell.tar.gz" "$URL" || {
  echo "Error: Download failed: $URL" >&2
  exit 1
}

# ---------- 4. 解压并安装 ----------

tar -xzf "$WORK_DIR/qshell.tar.gz" -C "$WORK_DIR" || {
  echo "Error: Failed to extract archive. The download may be corrupt." >&2
  exit 1
}

# 查找解压出的 qshell 二进制（可能在子目录中）
QSHELL_BIN_CANDIDATES=$(find "$WORK_DIR" -maxdepth 2 -name qshell -type f -perm +111 2>/dev/null)
if [ -z "$QSHELL_BIN_CANDIDATES" ]; then
  echo "Error: qshell binary not found after extraction" >&2
  exit 1
fi
CANDIDATE_COUNT=$(echo "$QSHELL_BIN_CANDIDATES" | wc -l | tr -d ' ')
if [ "$CANDIDATE_COUNT" -ne 1 ]; then
  echo "Error: Expected to find exactly one 'qshell' executable, but found ${CANDIDATE_COUNT}." >&2
  exit 1
fi
QSHELL_BIN="$QSHELL_BIN_CANDIDATES"
chmod +x "$QSHELL_BIN"

mkdir -p "$INSTALL_DIR"
mv "$QSHELL_BIN" "$INSTALL_DIR/qshell"

# ---------- 5. 配置 PATH ----------

if ! echo "$PATH" | tr ':' '\n' | grep -qxF "$INSTALL_DIR"; then
  echo ""
  echo "$INSTALL_DIR 不在 PATH 中，正在添加..."
  for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
    if [ -f "$rc" ] && ! grep -qF "export PATH=\"$INSTALL_DIR:\$PATH\"" "$rc" 2>/dev/null; then
      echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> "$rc"
      echo "  已添加到 $rc"
    fi
  done
  export PATH="$INSTALL_DIR:$PATH"
  echo "  提示: 新终端窗口会自动生效，当前终端请执行: export PATH=\"$INSTALL_DIR:\$PATH\""
fi

# ---------- 6. 验证安装 ----------

echo ""
echo "安装完成!"
qshell version
