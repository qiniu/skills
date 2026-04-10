#!/usr/bin/env python3
"""组装 DeployMeta JSON 文件。

将 InputSchema + moduleContent + 示例 inputPresets 合并为完整的 deploy-meta.json。

用法: python3 assemble-deploy-meta.py <schema.json> <module-content-file> <output-file>
  - schema.json: tf-to-schema.py 的输出
  - module-content-file: 合并后的 .tf 文件内容（纯文本）
  - output-file: 输出的 deploy-meta.json
"""

from __future__ import annotations

import json
import sys


def generate_starter_preset(schema: dict) -> dict:
    """从 InputSchema 生成一个入门版预设。"""
    props = schema.get("properties", {})
    inputs: dict = {}
    for name, prop in props.items():
        if prop.get("writeOnly"):
            continue
        if "default" in prop:
            inputs[name] = prop["default"]
        elif "enum" in prop and prop["enum"]:
            inputs[name] = prop["enum"][0]

    return {
        "name": "starter",
        "title": "入门版",
        "description": "基础配置，适合开发测试",
        "inputs": inputs,
        "regionPrices": [
            {
                "regionIDs": ["ap-northeast-1"],
                "prices": [
                    {
                        "costPeriodUnit": "Month",
                        "priceCNY": "0.00",
                        "originalPriceCNY": "0.00",
                        "priceUSD": "0.00",
                        "originalPriceUSD": "0.00",
                    }
                ],
            }
        ],
    }


def main():
    if len(sys.argv) < 4:
        print("用法: python3 assemble-deploy-meta.py <schema.json> <module-content-file> <output-file>",
              file=sys.stderr)
        sys.exit(1)

    schema_file = sys.argv[1]
    module_file = sys.argv[2]
    output_file = sys.argv[3]

    with open(schema_file, encoding="utf-8") as f:
        schema = json.load(f)

    with open(module_file, encoding="utf-8") as f:
        module_content = f.read()

    preset = generate_starter_preset(schema)

    deploy_meta = {
        "inputSchema": schema,
        "terraformModule": {
            "moduleContent": module_content,
        },
        "inputPresets": [preset],
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(deploy_meta, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
