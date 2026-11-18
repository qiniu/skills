# 创建、连接和公共参数

先用所选语言的入门参考初始化 `client`；以下 SDK 片段沿用该客户端。区域与凭据见 [setup.md](setup.md)，运行时子模块的参数见各主题页。

## 创建参数

| 目标 | Go `CreateParams` | Node.js `Sandbox.create` | Python `Sandbox.create` | 含义 |
| --- | --- | --- | --- | --- |
| 模板 | `TemplateID` | `template`／`templateID` | 首个 `template` 参数 | 模板 ID、名称或快照 ID；显式指定以便复现 |
| 存活时间 | `Timeout *int32` | `timeout`／`timeoutMs` | `timeout` | Go／Python 和 Node 的 `timeout` 为秒，`timeoutMs` 为毫秒 |
| 环境变量 | `EnvVars *map[string]string` | `envs`／`envVars` | `envs` | 创建时注入进程环境，秘密访问优先评估请求注入 |
| 元数据 | `Metadata *Metadata` | `metadata` | `metadata` | 字符串键值；用于业务标识和列表筛选 |
| 自动暂停 | `AutoPause *bool` | `autoPause` | `auto_pause` | 到期选择暂停；未传时保留服务端默认值 |
| 暂停内存 | `AutoPauseMemory *bool` | `autoPauseMemory` | `auto_pause_memory` | false 为文件系统暂停；不能同时启用自动恢复 |
| 流量恢复 | `AutoResume *AutoResumeConfig` | `autoResume: {enabled: true}` | `auto_resume={'enabled': True}` | 见 [lifecycle.md](lifecycle.md) |
| Envd 鉴权 | `Secure *bool` | `secure` | `secure` | 管理接口的认证，与应用服务公共访问分开 |
| 出网 | `AllowInternetAccess *bool` | `allowInternetAccess` | `allow_internet_access` | 访问互联网开关 |
| 网络 | `Network *NetworkConfig` | `network` | `network` | 字段见 [network.md](network.md) |
| 注入配置 | `Injections *[]SandboxInjectionSpec` | `injections` | `injections` | 内联或保存规则引用，见 [injections.md](injections.md) |
| 挂载资源 | `Resources *[]SandboxResourceSpec` | `resources` | `resources` | 启动前物化的 Git／Kodo 资源，见 [resources.md](resources.md) |
| 创建幂等键 | `IdempotencyKey` | `idempotencyKey` | `idempotency_key` | SDK 默认自动生成；同次不确定请求手动重试时复用原键和请求体 |

Go 的可选指针区分“未传”与 false／0。任意选项不会自动变成有效的服务端配置。MCP、Windows 和其他语言差异见 [integrations.md](integrations.md) 与 [compatibility.md](compatibility.md)。

## 连接和查询

| 操作 | Go | Node.js | Python |
| --- | --- | --- | --- |
| 创建 | `client.Create(ctx, params)` | `Sandbox.create({client, ...options})` | `Sandbox.create(template, client=client, **options)` |
| 连接已有 ID | `client.Connect(ctx, id, ConnectParams{Timeout: 300})` | `Sandbox.connect(id, {client, timeout: 300})` | `Sandbox.connect(id, client=client, timeout=300)` |
| 就绪等待 | `sb.WaitForReady(ctx)` | `sandbox.waitForReady({timeoutMs: 60000})` | `sandbox.wait_for_ready(timeout=60)` |
| 查询详情 | `sb.GetInfo(ctx)` | `sandbox.getInfo()` | `sandbox.get_info()` |
| 查询列表 | `client.List(ctx, &ListParams{...})` | `Sandbox.list({client, query: {...}, limit: 100})` | `Sandbox.list(client=client, query={...}, limit=100)` |

Connect v2 在暂停时恢复沙箱，并只延长 TTL。Go `ConnectParams.Timeout=0` 使用服务端默认的 300 秒；Node／Python 省略时同样使用服务端默认值。创建返回实例后立即注册清理，再进行就绪等待。Go／Node 的等待检查控制面 running；Python 检查 Envd health。后续命令、文件和业务就绪仍需按实际结果验收。

## 列表过滤与分页

`GET /v2/sandboxes` 的正文是数组，下一页游标在响应头 `X-Next-Token` 中。请求参数为 `state`（逗号分隔）、`template`、`metadata`、`limit`、`nextToken`。`metadata` 先分别对每个键和值做百分号编码，再组成并编码内部 query，最后交给 HTTP 客户端编码外层参数。服务端会先解码整个 metadata，再拆分和解码键值；少一层会把 `a+b` 变成 `a b`，或让包含 `&`、`=`、`%` 的筛选值报错。

源码基线的列表封装没有完整交付响应头游标，Node 的 `query.metadata` 还会编码为 `metadata[app]`。包含 [配套 SDK 修复](sources.md#配套-sdk-修复) 后，Node／Python 接受原始 metadata 字典并完成所需编码；Go 的 `ListParams.Metadata` 仍由调用方提供已编码的内部 query。下面的原始 HTTP 流程可用于源码基线和配套版本，普通 `nextToken` 直接交给 HTTP 客户端编码一次。

Node.js 18+，沿用 SDK 客户端的 `endpoint` 和入门配置的环境变量：

```javascript
const listApiKey = process.env.QINIU_SANDBOX_API_KEY;
if (!listApiKey) throw new Error('Set QINIU_SANDBOX_API_KEY');
const filters = {app: 'reporting', branch: 'feat/a&b=1+2%'};
const metadata = new URLSearchParams(Object.entries(filters).map(([key, value]) => [
  encodeURIComponent(key), encodeURIComponent(value)
])).toString();
let nextToken;
do {
  const url = new URL(client.endpoint + '/v2/sandboxes');
  url.searchParams.set('state', 'running,paused');
  url.searchParams.set('metadata', metadata);
  url.searchParams.set('limit', '100');
  if (nextToken) url.searchParams.set('nextToken', nextToken);
  const response = await fetch(url, {
    headers: {'X-API-Key': listApiKey},
    signal: AbortSignal.timeout(30000)
  });
  if (!response.ok) throw new Error(`List sandboxes returned HTTP ${response.status}`);
  const items = await response.json();
  for (const item of items) console.log(item.sandboxID);
  nextToken = response.headers.get('X-Next-Token');
} while (nextToken);
```

Python，沿用 `client.endpoint`，使用相同的 API Key：

```python
import os
from urllib.parse import quote, urlencode
import requests

filters = {'app': 'reporting', 'branch': 'feat/a&b=1+2%'}
metadata = urlencode({quote(key, safe=''): quote(value, safe='')
                      for key, value in filters.items()})
params = {'state': 'running,paused', 'metadata': metadata, 'limit': 100}
while True:
    response = requests.get(client.endpoint + '/v2/sandboxes', params=params,
                            headers={'X-API-Key': os.environ['QINIU_SANDBOX_API_KEY']},
                            timeout=30)
    response.raise_for_status()
    for item in response.json():
        print(item['sandboxID'])
    next_token = response.headers.get('X-Next-Token')
    if not next_token:
        break
    params['nextToken'] = next_token
```

Go 可使用下面的函数，传入与 `sandbox.Config` 相同的端点、API Key 和 HTTPClient。需要导入 `context`、`encoding/json`、`fmt`、`net/http`、`net/url` 和 `strings`。

```go
func listSandboxIDs(ctx context.Context, hc *http.Client, endpoint, apiKey string) ([]string, error) {
	filters := url.Values{}
	for key, value := range map[string]string{"app": "reporting", "branch": "feat/a&b=1+2%"} {
		filters.Set(url.QueryEscape(key), url.QueryEscape(value))
	}
	metadata := filters.Encode()
	var ids []string
	cursor := ""
	for {
		u, err := url.Parse(strings.TrimRight(endpoint, "/") + "/v2/sandboxes")
		if err != nil {
			return nil, err
		}
		q := u.Query()
		q.Set("state", "running,paused")
		q.Set("metadata", metadata)
		q.Set("limit", "100")
		if cursor != "" {
			q.Set("nextToken", cursor)
		}
		u.RawQuery = q.Encode()
		req, err := http.NewRequestWithContext(ctx, http.MethodGet, u.String(), nil)
		if err != nil {
			return nil, err
		}
		req.Header.Set("X-API-Key", apiKey)
		resp, err := hc.Do(req)
		if err != nil {
			return nil, err
		}
		if resp.StatusCode != http.StatusOK {
			resp.Body.Close()
			return nil, fmt.Errorf("list sandboxes: HTTP %d", resp.StatusCode)
		}
		var items []struct {
			SandboxID string `json:"sandboxID"`
		}
		err = json.NewDecoder(resp.Body).Decode(&items)
		resp.Body.Close()
		if err != nil {
			return nil, err
		}
		for _, item := range items {
			ids = append(ids, item.SandboxID)
		}
		cursor = resp.Header.Get("X-Next-Token")
		if cursor == "" {
			return ids, nil
		}
	}
}
```

Go 使用配套 SDK 的 `client.List` 时，将上例的 `metadata` 传给 `ListParams.Metadata`；不要把已编码的值再传给 Node／Python 的 metadata 字典入口。批量修改／清理前先完成查询并保存明确的资源 ID 集合，避免边翻页边改变筛选集合；qshell 的限制见 [cli.md](cli.md)。

## 请求选项与时间单位

| 范围 | Go | Node.js | Python |
| --- | --- | --- | --- |
| API 端点 | `Config.Endpoint` | `SandboxClient({endpoint})` | `SandboxClient(endpoint=...)` |
| HTTP 客户端 | `Config.HTTPClient` | `httpAgent`／`httpsAgent` | `session`，requests Session |
| API 请求时限 | context 和 HTTPClient | 客户端 `timeout` 是 urllib 时限（毫秒） | 客户端 `timeout` 为 requests 时限（秒），默认 30 |
| 自动重试 | `Config.RetryMax *int` | `maxRetries` | `max_retries` |
| 重试环境变量 | `SANDBOX_RETRY_MAX` | 同左 | 同左 |
| 进程／文件时限 | context／方法 options | `requestTimeoutMs` 等待启动；配套版创建命令／PTY 时用 `executionTimeoutMs` 设置 Envd 执行期限，文件传输也支持 `requestTimeoutMs`，见主题页 | 对应 `timeout`／`request_timeout`，见主题页 |

重试次数默认 5，0 禁用；并非每个接口都走自动重试。不要给命令套上创建请求的重试策略，命令可能已经产生业务副作用。

## 返回值与错误

- Go 的 API 方法返回结果与 `error`，`APIError` 包含 `StatusCode`、`Reqid`、`Code` 和 `Message`。命令结果还需检查 `ExitCode`。
- Node／Python 控制面错误带响应／data，命令默认返回非零退出结果；`throwOnError`／`throw_on_error` 才启用 `CommandExitError`，见 [commands.md](commands.md)。
- 详情、资源与注入查询可能包含 token 或脱敏配置。只打印必要字段；脱敏配置不能作为包含真实凭据的新请求直接回写。
