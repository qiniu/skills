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
SUFFIX=""

if [ "$OS" = "darwin" ]; then
  if [ "$ARCH" = "arm64" ]; then
    SUFFIX="darwin-arm64"
  else
    SUFFIX="darwin-amd64"
  fi
elif [ "$OS" = "linux" ]; then
  if [ "$ARCH" = "x86_64" ]; then
    SUFFIX="linux-amd64"
  elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    SUFFIX="linux-arm64"
  elif [ "$ARCH" = "i386" ] || [ "$ARCH" = "i686" ]; then
    SUFFIX="linux-386"
  fi
fi

if [ -z "$SUFFIX" ]; then
  echo "Error: Unsupported platform: $OS/$ARCH" >&2
  echo "Please download manually from https://github.com/qiniu/qshell/releases" >&2
  exit 1
fi

echo "检测到平台: $SUFFIX"

# ---------- 3. 下载二进制 ----------

# 下载地址必须带 Referer，否则会被拒绝
URL="https://kodo-toolbox-new.qiniu.com/qshell-v${VERSION}-${SUFFIX}.tar.gz"
echo "正在下载: $URL"
curl -fSL -e https://developer.qiniu.com -o /tmp/qshell.tar.gz "$URL" || {
  echo "Error: Download failed: $URL" >&2
  exit 1
}

# ---------- 4. 解压并安装 ----------

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR" /tmp/qshell.tar.gz' EXIT

tar -xzf /tmp/qshell.tar.gz -C "$TMPDIR"

# 查找解压出的 qshell 二进制（可能在子目录中）
QSHELL_BIN=$(find "$TMPDIR" -maxdepth 2 -name qshell -type f 2>/dev/null | head -1)
if [ -z "$QSHELL_BIN" ]; then
  echo "Error: qshell binary not found after extraction" >&2
  exit 1
fi
chmod +x "$QSHELL_BIN"

mkdir -p "$INSTALL_DIR"
mv "$QSHELL_BIN" "$INSTALL_DIR/qshell"

# ---------- 5. 配置 PATH ----------

if ! echo "$PATH" | tr ':' '\n' | grep -qx "$INSTALL_DIR"; then
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
