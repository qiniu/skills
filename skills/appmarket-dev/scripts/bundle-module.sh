#!/bin/bash
# 打包 Terraform 模块为单个 moduleContent 字符串
# 用法: ./bundle-module.sh <terraform-module-dir>

set -e

MODULE_DIR="${1:-.}"

if [ ! -d "$MODULE_DIR" ]; then
  echo "错误: 目录不存在: $MODULE_DIR" >&2
  exit 1
fi

# 合并所有 .tf 文件，添加分隔注释
for f in "$MODULE_DIR"/*.tf; do
  if [ -f "$f" ]; then
    filename=$(basename "$f")
    echo "# === $filename ==="
    cat "$f"
    echo ""
  fi
done
