# 请求注入与规则管理

七牛通过请求注入把凭据保存在沙箱外，在匹配的出站 HTTPS 请求上写入认证信息。选择内联配置用于单个沙箱，或保存规则后按 ID 引用。该机制与普通 `envs` 不同：把秘密放入环境变量会让沙箱进程读到明文。

## 配置类型与边界

| `type` | 目标／注入位置 | 主要配置 |
| --- | --- | --- |
| `openai` | 默认 `api.openai.com`，Authorization Bearer | `api_key`、可选 `base_url` |
| `anthropic` | 默认 `api.anthropic.com`，`x-api-key` | `api_key`、可选 `base_url` |
| `gemini` | 默认 `generativelanguage.googleapis.com`，`x-goog-api-key` | `api_key`、可选 `base_url` |
| `qiniu` | 默认 `api.qnaigc.com`，请求携带的 Authorization 或 `x-api-key` | `api_key`、可选 `base_url` |
| `github` | 默认匹配 `github.com`／`api.github.com` | `token`；Go 使用 `GithubInjection.Token` |
| `http` | 明确指定的 HTTPS 目标 | `base_url`、`headers`、`body` 和匹配条件 |
| `id` | 已保存规则 | `id`；Go 使用 `SandboxInjectionSpec.ByID` |

Node.js 接受 `apiKey`／`baseUrl`／`ifHeaders`／`ifQueries`／`ifBody`；Python 可以使用 `api_key`／`base_url`／`if_headers`／`if_queries`／`if_body`。二者在提交时规范化为 API 字段。Go 使用对应类型化结构，每个 union 对象只设置一种注入类型。

`base_url` 精确匹配 host；带路径时精确匹配规范化路径，尾部 `*` 表示路径前缀匹配。HTTP 类型必须提供目标。GitHub 自定义目标的 host 只能是 `github.com` 或 `api.github.com`。

`if_headers`、`if_queries` 和 `if_body` 是请求筛选条件，不是调用者授权边界；沙箱进程也能构造满足条件的请求。凭据可发送给谁，主要通过目标地址、路径和上游凭据权限限制。

## 给运行中沙箱设置 HTTP 注入

以下片段沿用已经创建的 `sandbox`／`sb`。目标地址需换成业务实际使用的 HTTPS API；服务端环境提供 `SERVICE_TOKEN`。示例只提交配置，不输出注入值。

```javascript
const injection = {
  type: 'http', baseUrl: 'https://api.example.com/v1/*',
  ifHeaders: { 'X-Sandbox-Scope': 'demo' },
  ifBody: { model: 'demo' },
  headers: { Authorization: `Bearer ${process.env.SERVICE_TOKEN}` },
  body: { api_key: process.env.SERVICE_TOKEN }
};
await sandbox.updateInjections([injection]);
```

```python
injection = {
    'type': 'http', 'base_url': 'https://api.example.com/v1/*',
    'if_headers': {'X-Sandbox-Scope': 'demo'},
    'if_body': {'model': 'demo'},
    'headers': {'Authorization': 'Bearer ' + os.environ['SERVICE_TOKEN']},
    'body': {'api_key': os.environ['SERVICE_TOKEN']},
}
sandbox.update_injections([injection])
```

```go
headers := map[string]string{"Authorization": "Bearer " + os.Getenv("SERVICE_TOKEN")}
matchHeaders := map[string]string{"X-Sandbox-Scope": "demo"}
matchBody := map[string]string{"model": "demo"}
body := map[string]string{"api_key": os.Getenv("SERVICE_TOKEN")}
injections := []sandbox.SandboxInjectionSpec{{HTTP: &sandbox.HTTPInjection{
	BaseURL: "https://api.example.com/v1/*", Headers: &headers,
	IfHeaders: &matchHeaders, IfBody: &matchBody, Body: &body,
}}}
if err := sb.UpdateInjections(ctx, injections); err != nil {
	return err
}
```

创建时使用同一配置：Node.js `Sandbox.create({ client, injections: [injection], ... })`；Python `Sandbox.create(..., injections=[injection])`；Go `CreateParams.Injections = &injections`。

运行时更新接口是**替换全部注入配置**，不是追加。调用前从应用的配置源构造完整的目标列表；传入空列表会清除注入。查询返回脱敏配置，不能把查询结果直接用于更新，否则可能把掩码当成真实凭据写回。Go 因此用不同的查询／写入类型。

| 操作 | Go | Node.js | Python |
| --- | --- | --- | --- |
| 查询 | `sb.GetInjections(ctx)` → `[]MaskedSandboxInjection` | `sandbox.getInjections()` → `{ injections }` | `sandbox.get_injections()` → `{'injections': [...]}` |
| 全量更新 | `sb.UpdateInjections(ctx, specs)` | `sandbox.updateInjections(specs)` | `sandbox.update_injections(specs)` |
| 更新实例 GitHub token | `sb.UpdateGitHubToken(ctx, token)` | `sandbox.updateGithubToken(token)` | `sandbox.update_github_token(token)` |

按单个 Git 资源轮换 token 时使用 [resources.md](resources.md) 的资源 ID 更新接口。更换服务凭据时，用新的秘密值重新构造完整配置，对目标实例提交并通过实际上游请求核对结果。

## JSON body 注入

`body` 和 `if_body` 只适用于 `type=http`，每个对象最多 20 个字段，键值均为字符串。匹配顶层 JSON 字段时区分大小写，所有条件同时满足后注入；`body` 新增或覆盖顶层字符串值。

需要处理 body 的请求必须是未压缩、最大 1 MiB 的 `application/json`。非法 JSON、不支持的请求体、已有目标字段为非字符串等情况会报错。不要把 PPIO 的 Secret 环境占位符或仅请求头替换规则套到这里；七牛的 HTTP 类型有独立的 JSON body 能力。

验证时发送带 `X-Sandbox-Scope: demo` 和 `{"model":"demo"}` 的业务请求。上游若会回显 Header 或 body，应丢弃回显内容，仅检查业务状态或状态码，避免把注入后的秘密带回日志。

## 保存规则的 CRUD

保存规则接口需要 AK／SK 的 Qiniu Mac 签名。环境配置名称见 [setup.md](setup.md)。下例为 Node.js 的完整创建、查询、更新与删除；规则名称由调用方选择，避免覆盖已有业务规则。

```javascript
const rules = new qiniu.sandbox.SandboxClient({
  endpoint: process.env.QINIU_SANDBOX_ENDPOINT,
  accessKey: process.env.QINIU_SANDBOX_ACCESS_KEY,
  secretKey: process.env.QINIU_SANDBOX_SECRET_KEY
});
const created = await rules.createInjectionRule({
  name: `skill-demo-${Date.now()}`,
  injection: { type: 'http', baseUrl: 'https://api.example.com/v1/*',
    headers: { Authorization: `Bearer ${process.env.SERVICE_TOKEN}` } }
});
const ruleID = created.ruleID || created.id;
if (!ruleID) throw new Error('Injection rule ID is unavailable');
try {
  await rules.getInjectionRule(ruleID);
  await rules.listInjectionRules();
  await rules.updateInjectionRule(ruleID, {
    name: created.name,
    injection: { type: 'http', baseUrl: 'https://api.example.com/v1/*',
      headers: { Authorization: `Bearer ${process.env.SERVICE_TOKEN_NEXT}` } }
  });
} finally {
  await rules.deleteInjectionRule(ruleID);
}
```

应用需要复用规则时保留规则并记录 ID，待引用的沙箱和业务均不再需要后再删除。更新 `injection` 时提供完整的新配置；只更新名称时可只发送 `name`。对已运行实例的生效结果，按实例配置查询及上游请求验证，不把保存规则的更新当成所有实例已收敛的证明。

| 操作 | Go 客户端 | Python 客户端 |
| --- | --- | --- |
| 创建 | `CreateInjectionRule(ctx, CreateInjectionRuleParams{Name: name, Injection: spec})` | `create_injection_rule(name=name, injection=spec)` |
| 列表 | `ListInjectionRules(ctx)` | `list_injection_rules()` |
| 详情 | `GetInjectionRule(ctx, id)` | `get_injection_rule(id)` |
| 更新 | `UpdateInjectionRule(ctx, id, UpdateInjectionRuleParams{Name: &name, Injection: &spec})` | `update_injection_rule(id, name=name, injection=spec)` |
| 删除 | `DeleteInjectionRule(ctx, id)` | `delete_injection_rule(id)` |

Go `spec` 为 `sandbox.InjectionSpec`，客户端通过 `Config.Credentials` 配置 Mac。Python 客户端通过 `access_key`／`secret_key` 配置。Python 在创建参数引用保存规则时也会切换到 Mac 鉴权，需给创建客户端准备 AK／SK。

引用形式为 Node.js／Python `{'type': 'id', 'id': ruleID}`，Go 为 `SandboxInjectionSpec{ByID: &ruleID}`。内联配置和按 ID 引用是不同 union 分支，各条规则可以分别选用。

## qshell

```bash
qshell sandbox injection-rule list
qshell sandbox injection-rule get RULE_ID
qshell sandbox injection-rule update RULE_ID --name NEW_NAME
qshell sandbox create TEMPLATE_ID --detach --injection-rule RULE_ID
qshell sandbox injection-rule delete RULE_ID
```

创建／替换配置使用 `injection-rule create|update` 的 `--type`、`--base-url`、`--api-key`、`--headers`、`--if-headers`、`--if-queries`、`--if-body`、`--body`。`--headers` 等映射参数为逗号分隔的 `key=value`，body 参数为 JSON 字符串对象。`create --inline-injection` 的单条规约以逗号分字段，规约中的 Header／Query 映射以分号分隔。涉及实际秘密时优先使用 SDK，避免 CLI 参数进入 shell 历史和进程列表。

七牛当前提供请求注入配置与规则 CRUD，没有独立 Secret／`secret_envs` 资源接口。版本与能力边界见 [compatibility.md](compatibility.md)。

来源：[Go 注入类型](https://github.com/qiniu/go-sdk/blob/master/sandbox/types_injection_rule.go)、[Node.js 注入示例](https://github.com/qiniu/nodejs-sdk/blob/master/examples/sandbox_request_injections.js)、[Python 规则示例](https://github.com/qiniu/python-sdk/blob/master/examples/sandbox_injection_rules.py)、[qshell 规则配置](https://github.com/qiniu/qshell/blob/master/docs/sandbox_injection_rule_create.md)。
