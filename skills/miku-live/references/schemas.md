# Miku Schema 参考

统一契约：输入使用 `action`（或 `intent` 映射）与 `params_json`，输出至少包含 `resolved_action`。

## 输入契约（Request）

- `action` 与 `intent` 至少提供一个。
- `params_json` 是唯一参数容器，且必填；无参数时传 `{}`。
- `ak`/`sk` 可选，传入时覆盖环境变量 `MIKU_LIVE_ACCESS_KEY`/`MIKU_LIVE_SECRET_KEY`。
- `dry_run` 默认 `false`；`topk` 默认 `5`（最小 `1`）。
- `max_attempts` 为总尝试上限（含首个执行与回退），默认 `5`（最小 `1`）。
- 不允许额外字段（`additionalProperties=false`）。

```json
{
  "type": "object",
  "properties": {
    "action": { "type": "string" },
    "intent": { "type": "string" },
    "params_json": { "type": "object" },
    "ak": { "type": "string" },
    "sk": { "type": "string" },
    "dry_run": { "type": "boolean", "default": false },
    "topk": { "type": "integer", "minimum": 1, "default": 5 },
    "preferred_languages": { "type": "array", "items": { "type": "string", "enum": ["curl", "javascript", "nodejs", "go", "java", "php"] } },
    "timeout_seconds": { "type": "integer", "minimum": 1, "default": 30 },
    "max_attempts": { "type": "integer", "minimum": 1, "default": 5 }
  },
  "required": ["params_json"],
  "anyOf": [{ "required": ["action"] }, { "required": ["intent"] }],
  "additionalProperties": false
}
```

## 输出契约（Response）

- 必须返回 `resolved_action`（完整 `<module>/<name>`）。
- 缺参时优先返回 `missing_required`（`body.xxx/query.xxx/host.xxx/path.xxx`）。
- 允许扩展字段（`additionalProperties=true`）。

```json
{
  "type": "object",
  "properties": {
    "resolved_action": { "type": "string" },
    "result": { "type": "object" },
    "missing_required": { "type": "array", "items": { "type": "string" } },
    "raw_response": { "type": "string", "description": "HTTP <status>: <body>" },
    "dry_run": { "type": "boolean" },
    "error": { "type": "string" }
  },
  "required": ["resolved_action"],
  "additionalProperties": true
}
```

## 最小示例

请求：`{"action":"bucket-management/list_buckets","params_json":{}}`

响应：`{"resolved_action":"bucket-management/list_buckets","result":{"buckets":[]}}`
