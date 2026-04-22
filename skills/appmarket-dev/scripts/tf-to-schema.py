#!/usr/bin/env python3
"""从 Terraform variables.tf 生成 JSON Schema（AppMarket InputSchema）。

功能：
  - 自动推断 required（无 default 的变量）
  - 提取 validation 块中的 contains() 为 enum
  - 提取 validation 块中的 >=/<= 为 minimum/maximum
  - 提取 validation 块中 length() 约束为 minLength/maxLength
  - sensitive=true 映射为 writeOnly: true
  - description 同时作为 title

用法: python3 tf-to-schema.py <variables.tf>
"""

from __future__ import annotations

import json
import re
import sys


def parse_variables(content: str) -> list[tuple[str, str]]:
    """解析 variables.tf 内容，返回 [(变量名, 块体)] 列表。"""
    variables = []
    pos = 0
    while pos < len(content):
        m = re.search(r'\bvariable\s+"([^"]+)"\s*\{', content[pos:])
        if not m:
            break
        var_name = m.group(1)
        block_start = pos + m.end()
        depth = 1
        i = block_start
        while i < len(content) and depth > 0:
            if content[i] == "{":
                depth += 1
            elif content[i] == "}":
                depth -= 1
            i += 1
        block_body = content[block_start:i - 1]
        variables.append((var_name, block_body))
        pos = i
    return variables


def extract_top_field(body: str, field: str) -> str | None:
    """提取变量块顶层字段值（跳过 validation 等嵌套块）。"""
    depth = 0
    for line in body.split("\n"):
        stripped = line.strip()
        opens = stripped.count("{")
        closes = stripped.count("}")

        if depth == 0:
            m = re.match(rf"^\s*{field}\s*=\s*(.*)", line)
            if m:
                return m.group(1).strip()

        depth += opens - closes

    return None


def tf_type_to_json(raw: str | None) -> str:
    """Terraform type -> JSON Schema type。"""
    if raw is None:
        return "string"
    raw = raw.strip()
    if raw == "string":
        return "string"
    if raw == "number":
        return "number"
    if raw == "bool":
        return "boolean"
    if raw.startswith("list") or raw.startswith("set"):
        return "array"
    if raw.startswith("map") or raw.startswith("object"):
        return "object"
    return "string"


def strip_quotes(raw: str) -> str:
    """去掉外层引号。"""
    if raw and len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ('"', "'"):
        return raw[1:-1]
    return raw


def parse_default(raw: str | None, json_type: str):
    """解析 default 值为 Python 原生类型。"""
    if raw is None:
        return None
    raw = raw.strip().rstrip(",")
    if raw == "null":
        return None
    if json_type == "boolean":
        return raw == "true"
    if json_type in ("number", "integer"):
        try:
            return float(raw) if "." in raw else int(raw)
        except ValueError:
            return None
    if json_type == "string":
        return strip_quotes(raw)
    if json_type == "array" and raw.startswith("["):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
    return strip_quotes(raw)


def extract_validation_blocks(body: str) -> list[str]:
    """提取所有 validation { ... } 块内容。"""
    blocks = []
    pos = 0
    while pos < len(body):
        vm = re.search(r"validation\s*\{", body[pos:])
        if not vm:
            break
        start = pos + vm.end()
        depth = 1
        i = start
        while i < len(body) and depth > 0:
            if body[i] == "{":
                depth += 1
            elif body[i] == "}":
                depth -= 1
            i += 1
        blocks.append(body[start:i - 1])
        pos = i
    return blocks


def extract_validation_constraints(body: str) -> dict:
    """从 validation 块提取 enum、minimum/maximum、minLength/maxLength。"""
    val_blocks = extract_validation_blocks(body)
    if not val_blocks:
        return {}

    constraints: dict = {}
    enum_items: set[str] = set()

    for val_body in val_blocks:
        # contains(["a", "b", "c"], var.xxx) -> enum
        cm = re.search(r"contains\(\s*\[([^\]]*)\]", val_body)
        if cm:
            items_raw = cm.group(1)
            items = [s.strip().strip('"').strip("'") for s in items_raw.split(",") if s.strip()]
            enum_items.update(items)

        # var.xxx >= N -> minimum
        for m in re.finditer(r"var\.\w+\s*>=\s*(\d+(?:\.\d+)?)", val_body):
            v = m.group(1)
            value = float(v) if "." in v else int(v)
            constraints["minimum"] = value if "minimum" not in constraints else max(constraints["minimum"], value)
        # var.xxx <= N -> maximum
        for m in re.finditer(r"var\.\w+\s*<=\s*(\d+(?:\.\d+)?)", val_body):
            v = m.group(1)
            value = float(v) if "." in v else int(v)
            constraints["maximum"] = value if "maximum" not in constraints else min(constraints["maximum"], value)
        # length(var.xxx) >= N -> minLength
        for m in re.finditer(r"length\(var\.\w+\)\s*>=\s*(\d+)", val_body):
            value = int(m.group(1))
            constraints["minLength"] = value if "minLength" not in constraints else max(constraints["minLength"], value)
        # length(var.xxx) <= N -> maxLength
        for m in re.finditer(r"length\(var\.\w+\)\s*<=\s*(\d+)", val_body):
            value = int(m.group(1))
            constraints["maxLength"] = value if "maxLength" not in constraints else min(constraints["maxLength"], value)

    if enum_items:
        constraints["enum"] = sorted(enum_items)

    return constraints


def build_schema(content: str) -> dict:
    """构建完整的 JSON Schema。"""
    variables = parse_variables(content)
    properties: dict = {}
    required: list[str] = []

    for var_name, body in variables:
        prop: dict = {}

        raw_type = extract_top_field(body, "type")
        json_type = tf_type_to_json(raw_type)
        prop["type"] = json_type

        raw_desc = extract_top_field(body, "description")
        if raw_desc:
            desc = strip_quotes(raw_desc)
            prop["title"] = desc
            prop["description"] = desc

        raw_default = extract_top_field(body, "default")
        if raw_default is not None:
            default_val = parse_default(raw_default, json_type)
            if default_val is not None:
                prop["default"] = default_val
        else:
            required.append(var_name)

        raw_sensitive = extract_top_field(body, "sensitive")
        if raw_sensitive and raw_sensitive.strip() == "true":
            prop["writeOnly"] = True

        constraints = extract_validation_constraints(body)
        for key in ("enum", "minimum", "maximum", "minLength", "maxLength"):
            if key in constraints:
                prop[key] = constraints[key]

        if json_type == "array" and raw_type:
            inner = re.search(r"list\((\w+)\)", raw_type)
            if inner:
                item_type = tf_type_to_json(inner.group(1))
                prop["items"] = {"type": item_type}

        properties[var_name] = prop

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def main():
    if len(sys.argv) < 2:
        print("用法: python3 tf-to-schema.py <variables.tf>", file=sys.stderr)
        sys.exit(1)

    filepath = sys.argv[1]
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    schema = build_schema(content)
    print(json.dumps(schema, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
