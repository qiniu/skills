---
name: miku-live
description:
  Resolve intent into Qiniu Miku Live management API action keys, validate
  parameter placement against the API catalog, and execute signed requests
  safely.
type: tool
best_for:
  - "Intent-to-action mapping for Qiniu Miku Live APIs"
scenarios:
  - "List live buckets or inspect bucket configuration"
  - "Manage streams, domains, transcoding templates, and API keys"
---

# 七牛云 Miku 快直播 API Skill

把中文请求映射为 Miku API `action_key`，再按接口总表完成归位、签名和执行。

## 速查索引

| 文件 | 用途 |
| --- | --- |
| `references/schemas.md` | 输入/输出 Schema |
| `references/interface-catalog.md` | 接口清单与参数归位 |
| `references/signing.md` | 签名与执行规则 |

## 前置条件

- 凭证优先级：请求体 `ak/sk` > 环境变量 `MIKU_LIVE_ACCESS_KEY/MIKU_LIVE_SECRET_KEY`；缺失时不做真实调用。
- 只按需读取 `references/`，不要把整份参考文档一次性展开到上下文里。

## 最小执行流程

1. 路由：有 `action` 直接执行；有 `intent` 则映射为完整 `action_key`。
2. 校验：输入/输出契约遵循 `references/schemas.md`。
3. 归位：参数归位与错误码遵循 `references/interface-catalog.md`。
4. 鉴权执行：签名与回退策略遵循 `references/signing.md`。

## 命令参考

- 输入统一使用 `action` 或 `intent`，且必须提供 `params_json`；`action` 优先。
- 执行顺序：解析 `action_key` -> 校验 schema -> 参数归位 -> 替换 Host/Path 占位符 -> 签名 -> 执行。
- 只校验、不落真实请求，或要生成代码/脚本/示例时，优先 `dry_run=true`。
- 最小输入：`{"action":"bucket-management/list_buckets","params_json":{},"dry_run":false}`。

## 意图映射

- 强制特例：“帮我获取到直播空间列表 / 直播空间有哪些 / 查询空间列表” 一律映射到 `bucket-management/list_buckets`。

| 用户意图 | action_key |
| --- | --- |
| 查看直播空间列表 | `bucket-management/list_buckets` |
| 查看或更新空间配置 | `bucket-management/get_bucket_config` / `bucket-management/update_bucket_config` |
| 创建、查询、禁播或删除流 | `stream-management/create_stream` / `stream-management/get_stream_info` / `stream-management/ban_stream` / `stream-management/delete_stream` |
| 绑定或解绑播放/推流域名 | `domain-management/bind_*` / `domain-management/unbind_*` |
| 查询统计 | `statistics/query_*` |

- 资源词决定模块：`空间/bucket -> bucket-management`；`流 -> stream-management`；`播放域名/推流域名 -> domain-management`；`证书 -> certificate-management`；`录制/截图 -> recording-management`；`转码模板 -> live-stream-transcoding-template`；`统计/日志 -> statistics`；`API Key/播放地址/推流地址 -> utilities`。
- 动作词决定前缀：`列表 -> list_*`；`详情/配置 -> get_*`；`创建 -> create_* / add_*`；`更新 -> update_* / edit_*`；`删除 -> delete_*`；`绑定/解绑 -> bind_* / unbind_*`；`启动/停止 -> start_* / stop_*`；`禁播/解禁 -> ban_* / unban_*`。
- 只在 `references/interface-catalog.md` 存在精确 `action_key` 时执行；资源类型或目标不明确时先追问；“列表/查询/看看有哪些”默认选只读接口。

## 安全规则

- 不输出完整 `sk`、证书私钥、Token、`Authorization` 头等敏感信息。
- 删除、解绑、停止、禁播等危险操作在目标不明确时先确认。
- `GET/DELETE` 默认无 body，除非接口总表显式要求。
- 参数必须严格放入 `host/path/query/body` 对应位置。

## 输出格式

- 必须返回 `resolved_action`；成功优先返回 `result`。
- 缺参时返回带位置前缀的 `missing_required`，如 `query.domain`、`host.bucket_name`、`path.stream_key`。
- dry run 显式返回 `dry_run: true`；可附带脱敏后的 `raw_response`。

## 错误处理

- 缺少 `action|intent` 或 `params_json`：直接报错并停止。
- 参数问题统一使用 `PARAM_POSITION_MISMATCH`、`UNDECLARED_PARAM`、`PARAM_VALUE_CONFLICT`。
- 缺少凭证时停止真实执行。
- 只有在未收到 HTTP 响应时才按 `signing.md` 回退语言；收到响应后直接返回。

## 交付前检查

- 当输出包含 HTML、JS、TS、React、Shell、Curl 或请求示例时，先把每个调用还原为 `action_key + params_json`。
- 交付前检查：`action_key` 存在、参数位置正确、必填项完整、query 键名大小写匹配、未声明参数未混入。
- 可执行时优先对每个调用做 `dry_run=true` 预检；任一调用失败时先修正或提示缺失信息，不直接交付。
- 默认不展开自检过程；仅在失败或用户要求时返回自检明细。
