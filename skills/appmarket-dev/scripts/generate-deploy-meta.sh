#!/bin/bash
# 从 Terraform 模块生成 DeployMeta
#
# 功能：
#   - 打包 .tf 文件为 moduleContent
#   - 调用 tf-to-schema 生成 InputSchema
#   - 生成包含示例 inputPresets 的 DeployMeta（价格为占位符）
#
# 用法: ./generate-deploy-meta.sh <terraform-module-dir> [output-file]

set -e

MODULE_DIR="${1:-.}"
OUTPUT_FILE="${2:-deploy-meta.json}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ ! -d "$MODULE_DIR" ]; then
  echo "错误: 目录不存在: $MODULE_DIR" >&2
  exit 1
fi

# 检查必要文件
for f in main.tf variables.tf; do
  if [ ! -f "$MODULE_DIR/$f" ]; then
    echo "错误: 缺少文件: $MODULE_DIR/$f" >&2
    exit 1
  fi
done

echo "正在处理 Terraform 模块: $MODULE_DIR"

# 1. 合并所有 .tf 文件
echo "  -> 打包 Terraform 文件..."
WORK_DIR=$(mktemp -d)
trap 'rm -rf "$WORK_DIR"' EXIT
cat "$MODULE_DIR"/*.tf > "$WORK_DIR/module-content.txt" 2>/dev/null

# 2. 生成 InputSchema
echo "  -> 生成 InputSchema..."
"$SCRIPT_DIR/tf-to-schema.sh" "$MODULE_DIR/variables.tf" > "$WORK_DIR/schema.json"

# 3. 组装 DeployMeta
echo "  -> 组装 DeployMeta..."
python3 "$SCRIPT_DIR/assemble-deploy-meta.py" "$WORK_DIR/schema.json" "$WORK_DIR/module-content.txt" "$OUTPUT_FILE"

echo "已生成: $OUTPUT_FILE"
echo ""
echo "注意:"
echo "  - Private 类型 App：请删除 inputPresets 中的 regionPrices 字段（不需要定价）。"
echo "  - Managed 类型 App：请将 regionPrices 中的价格修改为实际价格，并将 regionIDs 改为有效区域。"
echo "  - 可用区域: ap-northeast-1, ap-southeast-1, ap-southeast-2, cn-changshan-1, cn-hongkong-1, cn-shaoxing-1"
echo "  - 可添加更多规格（standard、pro 等）。"
