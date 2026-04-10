#!/bin/bash
# 从 Terraform variables.tf 生成 JSON Schema（AppMarket InputSchema）
#
# 功能：
#   - 自动推断 required（无 default 的变量）
#   - 提取 validation 块中的 contains() 为 enum
#   - 提取 validation 块中的 >=/<= 为 minimum/maximum
#   - 提取 validation 块中 length() 约束为 minLength/maxLength
#   - sensitive=true 映射为 writeOnly: true
#   - description 同时作为 title
#
# 用法: ./tf-to-schema.sh <variables.tf>

set -e

VARIABLES_FILE="${1:-variables.tf}"

if [ ! -f "$VARIABLES_FILE" ]; then
  echo "错误: 文件不存在: $VARIABLES_FILE" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$SCRIPT_DIR/tf-to-schema.py" "$VARIABLES_FILE"
