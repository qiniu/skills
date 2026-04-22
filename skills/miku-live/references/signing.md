# Miku 鉴权与执行参考

输入统一使用 `action`（或 `intent` 映射）与 `params_json`；输出按 `schemas.md`。

## 鉴权核心规则

- 鉴权字段：请求体 `ak`、`sk` 或环境变量 `MIKU_LIVE_ACCESS_KEY`、`MIKU_LIVE_SECRET_KEY`；请求体优先。
- 签名算法：`HMAC-SHA1` + `Base64URL`；`Authorization` 格式：`Qiniu <AK>:<SIGN>`。
- `Base64URL` 仅替换 `+ -> -`、`/ -> _`，`=` 必须保留。
- 接口 `domain` 含占位符时，必须先替换为最终 Host 再签名（例如 `<bucket_name>`）。
- `sign_data` 构造与一致性检查见下方“签名生成详单”。

## 自动执行策略

1. 解析输入：优先 `action`；仅有 `intent` 时先映射为完整 `action_key`，并写入 `resolved_action`。
2. 按 `references/schemas.md` 校验输入。
3. 参数归位按 `references/interface-catalog.md` 执行。
4. 先替换 Host/Path 占位符，再生成 `sign_data` 并签名。
5. 按语言优先级执行：`curl -> javascript -> nodejs -> go -> java -> php`。
6. 用户提供 `preferred_languages` 时先按用户顺序，之后补齐默认顺序。
7. 仅在“未收到 HTTP 响应”时回退语言；已收到 HTTP 响应则直接返回。
8. `max_attempts` 为总尝试上限（含首个执行与回退）；达到上限后立即停止并返回最后一次错误。

## 回退触发条件

- 运行时不存在（命令/编译器/依赖缺失）
- 模板渲染失败
- 请求发送失败（连接、超时、TLS）

## 签名生成详单

1. 根据 `action_key` 命中接口行，先替换 host/path 占位符，再按接口清单组装最终的 `method`、`host`、`path`、`query`、`body`。  
2. `PATH_WITH_QUERY` 规则：有 query 就拼 `path?query`，没有 query 就只用 `path`。  
3. `sign_data` 一句话概括：`<METHOD> <PATH_WITH_QUERY>\nHost: <HOST>[ \nContent-Type: application/json]\n\n[<BODY_JSON>]`。  
4. 这里的关键只有两点：无 body 时结尾仍然是 `\n\n`；有 body 时 `BODY_JSON` 紧跟在这一个空行后面，等价于 `...\n\n<BODY_JSON>`。  
5. `BODY_JSON` 必须与真实发送的请求体完全一致，不能在签名前后改字段顺序、空白字符或格式。  
6. 用 `MIKU_LIVE_SECRET_KEY`（或请求体 `sk`）对 `sign_data` 做 `HMAC-SHA1`，再做 `Base64URL`（仅 `+ -> -`、`/ -> _`，`=` 保留），最后生成 `Authorization: Qiniu <AK>:<SIGN>`。  
7. 发送前检查：请求里的 `method/host/path+query/body` 必须和 `sign_data` 完全一致，否则按签名错误处理。  
