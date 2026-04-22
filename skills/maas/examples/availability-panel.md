# 可用性面板

本示例演示如何通过请求日志接口，为用户呈现 API 服务的可用性和健康状况面板。

---

## 面板目标

当用户说"帮我看下 API 的可用性""最近接口有没有报错"或"展示一下服务健康面板"时，输出：

1. **成功率 / 错误率概览**（总体及按模型分组）
2. **错误分布**（4xx 客户端错误 vs 5xx 服务端错误）
3. **近期失败请求列表**（可追溯具体错误）

---

## 数据获取步骤

### Step 1：查询近期请求总量和成功数

分两次调用日志接口，分别获取：

**查询全部请求（获取总量）：**
```
GET /ai/inapi/v3/stat/log
  ?start=2026-04-14T00:00:00+08:00
  &end=2026-04-21T23:59:59+08:00
  &page=1
  &page_size=1
```

取响应中的 `data.total` 作为总请求数。

---

**查询失败请求（获取失败量）：**
```
GET /ai/inapi/v3/stat/log
  ?start=2026-04-14T00:00:00+08:00
  &end=2026-04-21T23:59:59+08:00
  &status=failure
  &page=1
  &page_size=20
```

取 `data.total` 作为失败总数，`data.items` 作为近期失败记录列表。

**响应结构：**
```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "chatcmpl-abc123",
        "model_id": "qwen-turbo",
        "api_key": "sk-ab***c123",
        "start_time": "2026-04-20T14:23:01.000+08:00",
        "end_time": "2026-04-20T14:23:01.512+08:00",
        "server_type": "chat",
        "code": 429,
        "state": "fail",
        "errors": ["rate limit exceeded"],
        "usage": { "input": 0, "output": 0 }
      }
    ],
    "total": 47,
    "page": 1,
    "page_size": 20,
    "total_pages": 3
  },
  "message": "ok"
}
```

**关键字段说明：**
- `items[].code`：HTTP 状态码（200 = 成功；4xx = 客户端错误；5xx = 服务端错误）
- `items[].state`：请求结果，枚举值为 `success` / `fail`（注意：这是**响应字段**的值，与查询参数 `status` 的枚举值不同，`status` 参数使用 `failure`、`client_error`、`server_error`）
- `items[].errors`：错误信息列表（可能为空数组）
- `items[].id`：请求 ID，可用于查询详情

---

### Step 2（可选）：查询客户端错误和服务端错误的细分

```
GET /ai/inapi/v3/stat/log
  ?start=2026-04-14T00:00:00+08:00
  &end=2026-04-21T23:59:59+08:00
  &status=client_error
  &page=1&page_size=1
```

```
GET /ai/inapi/v3/stat/log
  ?start=2026-04-14T00:00:00+08:00
  &end=2026-04-21T23:59:59+08:00
  &status=server_error
  &page=1&page_size=1
```

分别取 `data.total` 得到 4xx 和 5xx 的请求数。

---

### Step 3（按需）：查询特定失败请求的详情

若用户想追溯某次具体失败：

```
GET /ai/inapi/v3/stat/log/detail?request_id=chatcmpl-abc123
```

**额外返回字段：**
- `cost_time.ttft`：首字节耗时（ms），响应超慢时可参考
- `cost_time.latency`：总延迟（ms）
- `user.client_ip`：请求来源 IP

---

### Step 4（按需）：按模型细分查询成功率

若需对比不同模型的可用性，可对每个模型分别查询：

```
GET /ai/inapi/v3/stat/log
  ?start=...&end=...
  &model=qwen-turbo
  &status=failure
  &page=1&page_size=1
```

---

## 面板输出格式

### 可用性概览

```
## API 可用性面板（2026-04-14 ～ 2026-04-21，近 7 天）

| 指标           | 数值         |
|---------------|-------------|
| 总请求数        | 12,843       |
| 成功请求数      | 12,796       |
| 失败请求数      | 47           |
| **整体成功率**  | **99.63%**   |
| 客户端错误（4xx）| 39           |
| 服务端错误（5xx）| 8            |
```

---

### 错误分布

```
## 失败请求错误分布

| 错误类型           | 数量 | 占总请求 |
|------------------|------|---------|
| 429 限流          | 31   | 0.24%   |
| 400 参数错误       | 8    | 0.06%   |
| 500 服务内部错误   | 6    | 0.05%   |
| 503 服务不可用     | 2    | 0.02%   |
```

---

### 近期失败请求（最多展示 20 条）

```
## 近期失败请求

| 请求 ID            | 模型        | API Key       | 时间                      | 错误码 | 错误信息             |
|-------------------|------------|--------------|--------------------------|------|---------------------|
| chatcmpl-abc123   | qwen-turbo | sk-ab***c123 | 2026-04-20 14:23:01      | 429  | rate limit exceeded  |
| chatcmpl-def456   | qwen-max   | sk-cd***d456 | 2026-04-19 09:11:42      | 500  | internal server error|
| ...               | ...        | ...          | ...                       | ...  | ...                  |

> 如需查看某次请求的完整详情（延迟、IP 来源等），请告知请求 ID。
```

---

## 完整示例对话

**用户：** 帮我看一下最近一周的 API 可用性面板

**Agent：**

> 正在查询近 7 天（2026-04-14 ～ 2026-04-21）的请求日志……

（调用 `GET /ai/inapi/v3/stat/log?start=2026-04-14T00:00:00+08:00&end=2026-04-21T23:59:59+08:00&page=1&page_size=1`，取 total = 12843）  
（调用 `GET /ai/inapi/v3/stat/log?...&status=failure&page=1&page_size=20`，取 total = 47，获取最近失败列表）  
（调用 `GET /ai/inapi/v3/stat/log?...&status=client_error&page=1&page_size=1`，取 total = 39）  
（调用 `GET /ai/inapi/v3/stat/log?...&status=server_error&page=1&page_size=1`，取 total = 8）

---

## API 可用性面板（2026-04-14 ～ 2026-04-21）

| 指标              | 数值       |
|-----------------|-----------|
| 总请求数           | 12,843    |
| 成功请求数         | 12,796    |
| 失败请求数         | 47        |
| **整体成功率**     | **99.63%** |
| 客户端错误（4xx）   | 39        |
| 服务端错误（5xx）   | 8         |

## 近期失败请求（前 20 条）

| 请求 ID          | 模型        | API Key       | 时间                 | 错误码 | 错误信息              |
|-----------------|------------|--------------|---------------------|------|--------------------|
| chatcmpl-abc123 | qwen-turbo | sk-ab***c123 | 2026-04-20 14:23:01 | 429  | rate limit exceeded |
| chatcmpl-def456 | qwen-max   | sk-cd***d456 | 2026-04-19 09:11:42 | 500  | internal server error |

> 整体可用性良好（99.63%）。主要失败原因为 429 限流（31 次），建议检查高峰期 API Key 的并发请求量或适当调高限额。
>
> 如需查看某次失败请求的完整详情，请提供请求 ID。

---

## 注意事项

- 日志接口的时间范围不超过 35 天，7 天内的面板数据实时性较好
- `server_type` 默认为 `chat`；如需查询图像生成（`image`）或视频（`video`）的可用性，需单独传参
- 图像和视频类型日志暂不支持按 `code`/`status` 过滤，如需分析需自行对 `items[].code` 做客户端聚合
- 成功率计算：`(total - failure_total) / total * 100`，当 total = 0 时展示"暂无数据"
- `errors` 字段可能为空数组，此时以 HTTP 状态码推断错误类型即可
