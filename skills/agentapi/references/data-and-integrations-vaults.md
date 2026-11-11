<!-- 由 scripts/sync-docs.py 自动生成。 -->

# 凭证管理

原文：<https://developer.qiniu.com/agentapi/13606/agentapi-data-and-integrations-vaults>

智能体配置决定使用哪些工具，Vault（保管库）决定访问第三方 MCP 服务时使用谁的身份。两者分别配置：同一智能体可以处理多个业务用户的任务，由应用在创建会话时选择对应的 `vault_ids`。

例如，应用为不同业务用户生成协作系统摘要时，应分别保存用户授权，并在每次创建会话前校验授权归属。不要把第三方令牌放进任务消息或系统提示，也不要让客户端直接决定使用哪个 Vault。

在 Portal 中，您可以从会话详情的凭证库入口查看关联的 Vault 名称、ID 和归档状态，并进入凭证库详情。任务详情显示当前配置的凭证库；运行历史则显示该次会话的关联，后续修改任务配置不会改变历史关联 ID。信息暂时不可用时，页面保留 Vault ID 并提供重试。

## 划分调用身份与业务授权

| 配置 | 负责的身份 | 应用需要控制的边界 |
| --- | --- | --- |
| MaaS API Key | 调用 AgentAPI 的账户 | 保留在应用服务端，见[接入准备](access.md) |
| 智能体的 MCP 配置 | 任务可使用的服务与工具 | 只声明任务需要的服务；声明服务器不代表已经获得第三方授权 |
| Vault 中的第三方凭证 | 访问 MCP 服务的业务用户或服务身份 | 维护用户与 Vault 的映射，创建会话前检查归属与权限 |

> 账户内的访问范围
>
> Vault 和凭证属于当前账户，账户内有权访问这些资源的 API Key 可以引用它们。`metadata` 中的业务用户 ID 只是标记，不形成用户级访问隔离。应用服务端必须校验客户端发起的任务与允许使用的 Vault，不能将 `vault_ids` 或 `external_user_id` 直接作为授权依据。

## 确定会话的访问范围

创建会话前，核对三个条件：

1. 服务地址一致。 MCP 凭证通过 `mcp_server_url` 匹配智能体配置的服务地址；没有匹配凭证时，AgentAPI 会尝试匿名连接。
2. 第三方权限满足任务。 摘要查询通常只需读取权限；发布消息等写操作需另行授权。Vault 保存令牌，不会缩小令牌在第三方系统的权限。
3. 授权属于当前任务。 根据应用服务端的用户映射选出 Vault，再将 ID 传入会话；智能体配置可以复用，用户授权不能混用。

一个会话最多引用 50 个 Vault，执行时最多匹配并注入 20 个凭证。多个 Vault 匹配同一 MCP 地址时，`vault_ids` 中第一个匹配的 Vault 优先；应避免用数组顺序掩盖重复授权配置。

## 配置并使用授权

下面的示例按“保存业务用户标识 → 添加第三方令牌 → 创建会话引用”的顺序配置授权。示例中的 Alice 是业务用户标记，不是 AgentAPI 创建的独立安全主体。

### 创建保管库并关联业务用户

为业务用户或服务身份创建 Vault，保存返回的 ID，并在应用自己的授权记录中关联该 ID。`display_name` 用于识别，`metadata` 用于检索与标记。

cURL

```bash
vault_id=$(curl --request POST "$AGENTAPI_BASE_URL/v1/vaults" \
  --header "x-api-key: $AGENTAPI_API_KEY" \
  --header "content-type: application/json" \
  --data @- <<'EOF' | jq -r '.id'
{
  "display_name": "Alice",
  "metadata": {"external_user_id": "usr_abc123"}
}
EOF
)
echo "$vault_id"  # "vlt_01ABC..."
```

Python

```python
vault = client.beta.vaults.create(
    display_name="Alice",
    metadata={"external_user_id": "usr_abc123"},
)
print(vault.id)  # "vlt_01ABC..."
```

TypeScript

```typescript
const vault = await client.beta.vaults.create({
  display_name: "Alice",
  metadata: { external_user_id: "usr_abc123" },
});
console.log(vault.id); // "vlt_01ABC..."
```

C#

```csharp
var vault = await client.Beta.Vaults.Create(new()
{
    DisplayName = "Alice",
    Metadata = new Dictionary<string, string> { ["external_user_id"] = "usr_abc123" },
});
Console.WriteLine(vault.ID); // "vlt_01ABC..."
```

Go

```go
vault, err := client.Beta.Vaults.New(ctx, anthropic.BetaVaultNewParams{
	DisplayName: "Alice",
	Metadata:    map[string]string{"external_user_id": "usr_abc123"},
})
if err != nil {
	panic(err)
}
fmt.Println(vault.ID) // "vlt_01ABC..."
```

Java

```java
var vault = client.beta().vaults().create(VaultCreateParams.builder()
    .displayName("Alice")
    .metadata(VaultCreateParams.Metadata.builder()
        .putAdditionalProperty("external_user_id", JsonValue.from("usr_abc123"))
        .build())
    .build());
IO.println(vault.id()); // "vlt_01ABC..."
```

PHP

```php
$vault = $client->beta->vaults->create(
    displayName: 'Alice',
    metadata: ['external_user_id' => 'usr_abc123'],
);
echo $vault->id . "\n"; // "vlt_01ABC..."
```

Ruby

```ruby
vault = client.beta.vaults.create(
  display_name: "Alice",
  metadata: {external_user_id: "usr_abc123"}
)
puts vault.id # "vlt_01ABC..."
```

响应返回完整的 Vault 记录：

```json
{
  "type": "vault",
  "id": "vlt_01ABC...",
  "display_name": "Alice",
  "metadata": { "external_user_id": "usr_abc123" },
  "created_at": "2026-03-18T10:00:00Z",
  "updated_at": "2026-03-18T10:00:00Z",
  "archived_at": null
}
```

### 选择第三方鉴权方式

鉴权方式由 MCP 服务决定，不由智能体模型决定：

| MCP 服务接受的授权 | 凭证类型 | 令牌维护责任 |
| --- | --- | --- |
| 业务用户通过 OAuth 授予的访问令牌 | \`mcp\_oauth\` | 应用完成授权与刷新，再更新 Vault 中的令牌 |
| 固定 API Key 或个人访问令牌，以 Bearer 方式发送 | \`static\_bearer\` | 应用根据第三方令牌有效期安排轮换 |
| 沙箱进程把密钥原样放进 \`Authorization: Bearer $变量\`，并访问预先列出的主机 | \`environment\_variable\` | 应用提供密钥和主机；AgentAPI 只在匹配的出站请求头中替换完整值 |

`mcp_oauth` 和 `static_bearer` 都以 `mcp_server_url` 匹配目标服务；`environment_variable` 以 `secret_name` 和 `networking.allowed_hosts` 限定替换范围，配置见下文“环境变量密钥”。凭证值（`token`、`access_token`、`refresh_token`、`client_secret`、`secret_value`）只写入、不在 API 响应中返回；应用应保存凭证 ID，用于后续更新或撤销。

#### 保存 OAuth 授权

下面的示例保存业务用户的访问令牌及刷新信息。保存 `refresh` 配置不会启动自动刷新：AgentAPI 当前不执行 OAuth 刷新，应用必须在令牌过期后完成刷新并更新凭证。

`refresh.token_endpoint_auth.type` 字段指定令牌刷新请求的认证方式：

- `none`：公共客户端
- `client_secret_basic`：使用客户端密钥的 HTTP Basic 身份验证
- `client_secret_post`：客户端密钥位于 POST 请求体中

cURL

```bash
credential_id=$(curl --fail-with-body -sS "$AGENTAPI_BASE_URL/v1/vaults/$vault_id/credentials" \
  -H "x-api-key: $AGENTAPI_API_KEY" \
  -H "content-type: application/json" \
  --data @- <<'EOF' | jq -r '.id'
{
  "display_name": "Alice's Slack",
  "auth": {
    "type": "mcp_oauth",
    "mcp_server_url": "https://mcp.slack.com/mcp",
    "access_token": "xoxp-...",
    "expires_at": "2099-12-31T23:59:59Z",
    "refresh": {
      "token_endpoint": "https://slack.com/api/oauth.v2.access",
      "client_id": "1234567890.0987654321",
      "scope": "channels:read chat:write",
      "refresh_token": "xoxe-1-...",
      "token_endpoint_auth": {"type": "client_secret_post", "client_secret": "abc123..."}
    }
  }
}
EOF
)
```

Python

```python
credential = client.beta.vaults.credentials.create(
    vault_id=vault.id,
    display_name="Alice's Slack",
    auth={
        "type": "mcp_oauth",
        "mcp_server_url": "https://mcp.slack.com/mcp",
        "access_token": "xoxp-...",
        "expires_at": "2099-12-31T23:59:59Z",
        "refresh": {
            "token_endpoint": "https://slack.com/api/oauth.v2.access",
            "client_id": "1234567890.0987654321",
            "scope": "channels:read chat:write",
            "refresh_token": "xoxe-1-...",
            "token_endpoint_auth": {"type": "client_secret_post", "client_secret": "abc123..."},
        },
    },
)
```

TypeScript

```typescript
const credential = await client.beta.vaults.credentials.create(vault.id, {
  display_name: "Alice's Slack",
  auth: {
    type: "mcp_oauth",
    mcp_server_url: "https://mcp.slack.com/mcp",
    access_token: "xoxp-...",
    expires_at: "2099-12-31T23:59:59Z",
    refresh: {
      token_endpoint: "https://slack.com/api/oauth.v2.access",
      client_id: "1234567890.0987654321",
      scope: "channels:read chat:write",
      refresh_token: "xoxe-1-...",
      token_endpoint_auth: {
        type: "client_secret_post",
        client_secret: "abc123...",
      },
    },
  },
});
```

C#

```csharp
var credential = await client.Beta.Vaults.Credentials.Create(vault.ID, new()
{
    DisplayName = "Alice's Slack",
    Auth = new BetaManagedAgentsMcpOAuthCreateParams
    {
        Type = BetaManagedAgentsMcpOAuthCreateParamsType.McpOAuth,
        McpServerUrl = "https://mcp.slack.com/mcp",
        AccessToken = "xoxp-...",
        ExpiresAt = DateTimeOffset.Parse("2099-12-31T23:59:59Z"),
        Refresh = new()
        {
            TokenEndpoint = "https://slack.com/api/oauth.v2.access",
            ClientID = "1234567890.0987654321",
            Scope = "channels:read chat:write",
            RefreshToken = "xoxe-1-...",
            TokenEndpointAuth = new BetaManagedAgentsTokenEndpointAuthPostParam
            {
                Type = BetaManagedAgentsTokenEndpointAuthPostParamType.ClientSecretPost,
                ClientSecret = "abc123...",
            },
        },
    },
});
```

Go

```go
credential, err := client.Beta.Vaults.Credentials.New(ctx, vault.ID, anthropic.BetaVaultCredentialNewParams{
	DisplayName: anthropic.String("Alice's Slack"),
	Auth: anthropic.BetaVaultCredentialNewParamsAuthUnion{
		OfMCPOAuth: &anthropic.BetaManagedAgentsMCPOAuthCreateParams{
			Type:         anthropic.BetaManagedAgentsMCPOAuthCreateParamsTypeMCPOAuth,
			MCPServerURL: "https://mcp.slack.com/mcp",
			AccessToken:  "xoxp-...",
			ExpiresAt:    anthropic.Time(time.Date(2099, time.December, 31, 23, 59, 59, 0, time.UTC)),
			Refresh: anthropic.BetaManagedAgentsMCPOAuthRefreshParams{
				TokenEndpoint: "https://slack.com/api/oauth.v2.access",
				ClientID:      "1234567890.0987654321",
				Scope:         anthropic.String("channels:read chat:write"),
				RefreshToken:  "xoxe-1-...",
				TokenEndpointAuth: anthropic.BetaManagedAgentsMCPOAuthRefreshParamsTokenEndpointAuthUnion{
					OfClientSecretPost: &anthropic.BetaManagedAgentsTokenEndpointAuthPostParam{
						Type:         anthropic.BetaManagedAgentsTokenEndpointAuthPostParamTypeClientSecretPost,
						ClientSecret: "abc123...",
					},
				},
			},
		},
	},
})
if err != nil {
	panic(err)
}
```

Java

```java
var credential = client.beta().vaults().credentials().create(vault.id(),
    CredentialCreateParams.builder()
        .displayName("Alice's Slack")
        .auth(BetaManagedAgentsMcpOAuthCreateParams.builder()
            .type(BetaManagedAgentsMcpOAuthCreateParams.Type.MCP_OAUTH)
            .mcpServerUrl("https://mcp.slack.com/mcp")
            .accessToken("xoxp-...")
            .expiresAt(OffsetDateTime.parse("2099-12-31T23:59:59Z"))
            .refresh(BetaManagedAgentsMcpOAuthRefreshParams.builder()
                .tokenEndpoint("https://slack.com/api/oauth.v2.access")
                .clientId("1234567890.0987654321")
                .scope("channels:read chat:write")
                .refreshToken("xoxe-1-...")
                .clientSecretPostTokenEndpointAuth("abc123...")
                .build())
            .build())
        .build());
```

PHP

```php
$credential = $client->beta->vaults->credentials->create(
    vaultID: $vault->id,
    displayName: "Alice's Slack",
    auth: ManagedAgentsMCPOAuthCreateParams::with(
        type: 'mcp_oauth',
        mcpServerURL: 'https://mcp.slack.com/mcp',
        accessToken: 'xoxp-...',
        expiresAt: new DateTimeImmutable('2099-12-31T23:59:59Z'),
        refresh: ManagedAgentsMCPOAuthRefreshParams::with(
            tokenEndpoint: 'https://slack.com/api/oauth.v2.access',
            clientID: '1234567890.0987654321',
            scope: 'channels:read chat:write',
            refreshToken: 'xoxe-1-...',
            tokenEndpointAuth: ManagedAgentsTokenEndpointAuthPostParam::with(
                type: 'client_secret_post',
                clientSecret: 'abc123...',
            ),
        ),
    ),
);
```

Ruby

```ruby
credential = client.beta.vaults.credentials.create(
  vault.id,
  display_name: "Alice's Slack",
  auth: {
    type: "mcp_oauth",
    mcp_server_url: "https://mcp.slack.com/mcp",
    access_token: "xoxp-...",
    expires_at: "2099-12-31T23:59:59Z",
    refresh: {
      token_endpoint: "https://slack.com/api/oauth.v2.access",
      client_id: "1234567890.0987654321",
      scope: "channels:read chat:write",
      refresh_token: "xoxe-1-...",
      token_endpoint_auth: {
        type: "client_secret_post",
        client_secret: "abc123..."
      }
    }
  }
)
```

#### 保存固定 Bearer 令牌

固定令牌不需要 OAuth 刷新配置。下面的示例将令牌绑定到一个 MCP 地址；如服务地址发生变化，应创建新的凭证，而非只更新令牌值。

cURL

```bash
curl --fail-with-body -sS "$AGENTAPI_BASE_URL/v1/vaults/$vault_id/credentials" \
  -H "x-api-key: $AGENTAPI_API_KEY" \
  -H "content-type: application/json" \
  --data @- <<'EOF'
{
  "display_name": "Linear API key",
  "auth": {
    "type": "static_bearer",
    "mcp_server_url": "https://mcp.linear.app/mcp",
    "token": "lin_api_your_linear_key"
  }
}
EOF
```

Python

```python
bearer_credential = client.beta.vaults.credentials.create(
    vault_id=vault.id,
    display_name="Linear API key",
    auth={
        "type": "static_bearer",
        "mcp_server_url": "https://mcp.linear.app/mcp",
        "token": "lin_api_your_linear_key",
    },
)
```

TypeScript

```typescript
const bearerCredential = await client.beta.vaults.credentials.create(vault.id, {
  display_name: "Linear API key",
  auth: {
    type: "static_bearer",
    mcp_server_url: "https://mcp.linear.app/mcp",
    token: "lin_api_your_linear_key",
  },
});
```

C#

```csharp
var bearerCredential = await client.Beta.Vaults.Credentials.Create(vault.ID, new()
{
    DisplayName = "Linear API key",
    Auth = new BetaManagedAgentsStaticBearerCreateParams
    {
        Type = BetaManagedAgentsStaticBearerCreateParamsType.StaticBearer,
        McpServerUrl = "https://mcp.linear.app/mcp",
        Token = "lin_api_your_linear_key",
    },
});
```

Go

```go
bearerCredential, err := client.Beta.Vaults.Credentials.New(ctx, vault.ID, anthropic.BetaVaultCredentialNewParams{
	DisplayName: anthropic.String("Linear API key"),
	Auth: anthropic.BetaVaultCredentialNewParamsAuthUnion{
		OfStaticBearer: &anthropic.BetaManagedAgentsStaticBearerCreateParams{
			Type:         anthropic.BetaManagedAgentsStaticBearerCreateParamsTypeStaticBearer,
			MCPServerURL: "https://mcp.linear.app/mcp",
			Token:        "lin_api_your_linear_key",
		},
	},
})
if err != nil {
	panic(err)
}
_ = bearerCredential
```

Java

```java
var bearerCredential = client.beta().vaults().credentials().create(vault.id(),
    CredentialCreateParams.builder()
        .displayName("Linear API key")
        .auth(BetaManagedAgentsStaticBearerCreateParams.builder()
            .type(BetaManagedAgentsStaticBearerCreateParams.Type.STATIC_BEARER)
            .mcpServerUrl("https://mcp.linear.app/mcp")
            .token("lin_api_your_linear_key")
            .build())
        .build());
```

PHP

```php
$bearerCredential = $client->beta->vaults->credentials->create(
    vaultID: $vault->id,
    displayName: 'Linear API key',
    auth: ManagedAgentsStaticBearerCreateParams::with(
        type: 'static_bearer',
        mcpServerURL: 'https://mcp.linear.app/mcp',
        token: 'lin_api_your_linear_key',
    ),
);
```

Ruby

```ruby
bearer_credential = client.beta.vaults.credentials.create(
  vault.id,
  display_name: "Linear API key",
  auth: {
    type: "static_bearer",
    mcp_server_url: "https://mcp.linear.app/mcp",
    token: "lin_api_your_linear_key"
  }
)
```

### 保存环境变量密钥

沙箱里的 CLI、SDK 或脚本如果把密钥原样放进 `Authorization: Bearer <密钥>`，可以用 `environment_variable` 凭证。沙箱进程只能看到占位符；真实密钥只出现在离开沙箱、且请求头完整匹配的出站请求里。自托管 worker 不接收这个占位符。

创建时必须显式指定请求头注入和有限主机。省略 `injection_location` 会返回 400。

cURL

```bash
curl --fail-with-body -sS "$AGENTAPI_BASE_URL/v1/vaults/$vault_id/credentials" \
  -H "x-api-key: $AGENTAPI_API_KEY" \
  -H "content-type: application/json" \
  --data @- <<'EOF'
{
  "display_name": "Notion API key",
  "auth": {
    "type": "environment_variable",
    "secret_name": "NOTION_API_KEY",
    "secret_value": "ntn_your-secret-here",
    "networking": {
      "type": "limited",
      "allowed_hosts": ["api.notion.com"]
    },
    "injection_location": {"header": true}
  }
}
EOF
```

响应不返回 `secret_value` 或 `mcp_server_url`。`injection_location` 固定为 `{"header": true, "body": false}`，`allowed_hosts` 返回规范化后的主机。

```json
{
  "type": "credential",
  "id": "cred_01ABC",
  "vault_id": "vlt_01ABC",
  "display_name": "Notion API key",
  "auth": {
    "type": "environment_variable",
    "secret_name": "NOTION_API_KEY",
    "networking": {
      "type": "limited",
      "allowed_hosts": ["api.notion.com"]
    },
    "injection_location": {"header": true, "body": false}
  },
  "metadata": {},
  "created_at": "2026-03-18T10:00:00Z",
  "updated_at": "2026-03-18T10:00:00Z",
  "archived_at": null
}
```

沙箱中的变量值是一个带 `agentapi_secret_` 前缀的占位符，例如 `NOTION_API_KEY=agentapi_secret_cred_01ABC`。出站到 `https://api.notion.com` 时，只有 `Authorization` 的完整值等于 `Bearer agentapi_secret_cred_01ABC`，才会替换成 `Bearer ntn_your-secret-here`。其它请求头、请求体、多出来的前后缀、大小写不同的值，以及未列出的主机，都保持原样。替换地址是 `https://<主机>`，不含路径。主机按精确匹配，`https://example.com` 不会替换发往 `https://example.com.attacker.com` 的请求。

因此客户端需要读取该环境变量，并把占位符原样放进出站请求头。变量名不决定替换哪个头。请求体、URL 或签名材料不参与替换。

替换只作用于运行时固定使用的鉴权请求头，匹配值和替换值都必须完整。环境变量凭证目前主要用于覆盖模型请求。

> 与通用环境变量注入的差异
>
> 请求体注入、不限主机、通配符、端口，以及在任意请求头中扫描占位符，都会被拒绝。凭证上的允许主机只决定替换范围，不开放网络；云端环境仍需允许访问这些主机。

约束：

- `networking.type` 只能是 `limited`。每个主机是不带协议、端口、路径和通配符的主机名或 IP，单个凭证最多 20 个。IPv6 可以写成 `[2001:db8::1]`，保存后显示为 `2001:db8::1`；更新时可以原样提交这个保存后的地址。
- `secret_name` 是环境变量名，以字母或下划线开头，只含字母、数字和下划线，长度 1 到 128。不保留任何变量名；显式配置的变量优先于运行时默认值，包括 `PATH`、`HOME` 和模型 Key。覆盖路径等进程变量也会改变运行时行为。同一 Vault 的活动凭证里按大小写区分且必须唯一，`API_TOKEN` 和 `api_token` 可以同时存在，完全相同的名称返回 409。
- `secret_name` 和 `networking` 创建后不可修改。轮换时在 `auth` 中携带 `type: "environment_variable"` 和新的 `secret_value`；省略 `auth.type` 会返回 400，无需重传名称、主机和注入位置。占位符不变，出站替换值更新。要改名称或主机，先归档再新建。归档保留名称和允许主机，清除密钥，并释放该活动名称。
- 同一会话的多个 Vault 使用相同 `secret_name` 时，按 `vault_ids` 的顺序保留第一个。
- 新增的 `secret_name` 需要运行时或 shell 重新启动后才能看到；轮换密钥不需要重启。
- 这种凭证不用于 MCP 认证，也不使用 `mcp_server_url`。

### 覆盖模型凭据

`secret_name` 只决定沙箱进程里的占位符变量名，不用于选择模型 Key。`codex` 和 `claudecode` 需要让进程改用 Vault 占位符访问模型服务主机，才会使用该凭证；否则继续使用默认模型 Key。

`native` 在凭证的允许主机与模型服务主机完全一致时使用该凭证，没有匹配时使用默认模型 Key，多条凭证同时匹配时调用失败。

创建 Vault 凭据并把 Vault 加入会话的 `vault_ids` 即可使用。凭据无效时执行失败，不会回退到默认模型 Key。模型地址和协议仍由原模型配置决定，调用 AgentAPI 仍使用已绑定的 API Key。

### 在会话中引用授权

确认业务用户有权使用前面创建的 Vault 后，将其 ID 写入会话的 `vault_ids`。示例为同一业务用户启动协作系统摘要任务：

cURL

```bash
session_id=$(curl --fail-with-body -sS $AGENTAPI_BASE_URL/v1/sessions \
  -H "x-api-key: $AGENTAPI_API_KEY" \
  -H "content-type: application/json" \
  --data @- <<EOF | jq -r '.id'
{
  "agent": {"type": "agent", "id": "$agent_id", "version": 1},
  "environment_id": "$environment_id",
  "vault_ids": ["$vault_id"],
  "title": "Alice's Slack digest"
}
EOF
)
```

Python

```python
session = client.beta.sessions.create(
    agent=agent.id,
    environment_id=environment.id,
    vault_ids=[vault.id],
    title="Alice's Slack digest",
)
```

TypeScript

```typescript
const session = await client.beta.sessions.create({
  agent: agent.id,
  environment_id: environment.id,
  vault_ids: [vault.id],
  title: "Alice's Slack digest",
});
```

C#

```csharp
var session = await client.Beta.Sessions.Create(new()
{
    Agent = agent.ID,
    EnvironmentID = environment.ID,
    VaultIds = [vault.ID],
    Title = "Alice's Slack digest",
});
```

Go

```go
session, err := client.Beta.Sessions.New(ctx, anthropic.BetaSessionNewParams{
	Agent: anthropic.BetaSessionNewParamsAgentUnion{
		OfString: anthropic.String(agent.ID),
	},
	EnvironmentID: environment.ID,
	VaultIDs:      []string{vault.ID},
	Title:         anthropic.String("Alice's Slack digest"),
})
if err != nil {
	panic(err)
}
```

Java

```java
var session = client.beta().sessions().create(SessionCreateParams.builder()
    .agent(agent.id())
    .environmentId(environment.id())
    .vaultIds(List.of(vault.id()))
    .title("Alice's Slack digest")
    .build());
```

PHP

```php
$session = $client->beta->sessions->create(
    agent: $agent->id,
    environmentID: $environment->id,
    vaultIDs: [$vault->id],
    title: "Alice's Slack digest",
);
```

Ruby

```ruby
session = client.beta.sessions.create(
  agent: agent.id,
  environment_id: environment.id,
  vault_ids: [vault.id],
  title: "Alice's Slack digest"
)
```

会话创建成功只说明配置已保存，不能证明第三方鉴权已通过。开始任务后，结合[会话事件](sessions-and-tasks-events.md)核对 MCP 调用结果：

| 现象 | 优先检查 |
| --- | --- |
| MCP 连接或调用返回鉴权错误 | 服务地址是否匹配，令牌是否过期或已被第三方撤销 |
| 可以读取但无法执行写操作 | 第三方令牌是否具有所需权限，工具配置是否允许该操作 |
| 使用了不符合预期的业务身份 | 应用选择的 Vault 是否正确，是否存在多个匹配凭证 |

## 更新授权并验证生效

凭证更新分为两类：更换令牌值时更新原凭证；变更服务或 OAuth 客户端时创建新凭证。

| 变更 | 操作 |
| --- | --- |
| 密钥值、\`display\_name\`、OAuth 刷新信息 | 更新原凭证 |
| \`mcp\_server\_url\`、\`token\_endpoint\`、\`client\_id\` 等结构性字段 | 归档旧凭证，创建新凭证 |

应用完成 OAuth 刷新或取得新令牌后，使用已保存的凭证 ID 更新。运行中的会话需要异步同步；同步完成后，后续出站请求才使用新值。

cURL

```bash
curl --fail-with-body -sS \
  "$AGENTAPI_BASE_URL/v1/vaults/$vault_id/credentials/$credential_id" \
  -H "x-api-key: $AGENTAPI_API_KEY" \
  -H "content-type: application/json" \
  --data @- <<'EOF' > /dev/null
{
  "auth": {
    "type": "mcp_oauth",
    "access_token": "xoxp-new-...",
    "expires_at": "2099-12-31T23:59:59Z",
    "refresh": {"refresh_token": "xoxe-1-new-..."}
  }
}
EOF
```

Python

```python
client.beta.vaults.credentials.update(
    credential.id,
    vault_id=vault.id,
    auth={
        "type": "mcp_oauth",
        "access_token": "xoxp-new-...",
        "expires_at": "2099-12-31T23:59:59Z",
        "refresh": {"refresh_token": "xoxe-1-new-..."},
    },
)
```

TypeScript

```typescript
await client.beta.vaults.credentials.update(credential.id, {
  vault_id: vault.id,
  auth: {
    type: "mcp_oauth",
    access_token: "xoxp-new-...",
    expires_at: "2099-12-31T23:59:59Z",
    refresh: {
      refresh_token: "xoxe-1-new-...",
    },
  },
});
```

C#

```csharp
await client.Beta.Vaults.Credentials.Update(credential.ID, new()
{
    VaultID = vault.ID,
    Auth = new BetaManagedAgentsMcpOAuthUpdateParams
    {
        Type = BetaManagedAgentsMcpOAuthUpdateParamsType.McpOAuth,
        AccessToken = "xoxp-new-...",
        ExpiresAt = DateTimeOffset.Parse("2099-12-31T23:59:59Z"),
        Refresh = new() { RefreshToken = "xoxe-1-new-..." },
    },
});
```

Go

```go
_, err = client.Beta.Vaults.Credentials.Update(ctx, credential.ID, anthropic.BetaVaultCredentialUpdateParams{
	VaultID: vault.ID,
	Auth: anthropic.BetaVaultCredentialUpdateParamsAuthUnion{
		OfMCPOAuth: &anthropic.BetaManagedAgentsMCPOAuthUpdateParams{
			Type:        anthropic.BetaManagedAgentsMCPOAuthUpdateParamsTypeMCPOAuth,
			AccessToken: anthropic.String("xoxp-new-..."),
			ExpiresAt:   anthropic.Time(time.Date(2099, time.December, 31, 23, 59, 59, 0, time.UTC)),
			Refresh: anthropic.BetaManagedAgentsMCPOAuthRefreshUpdateParams{
				RefreshToken: anthropic.String("xoxe-1-new-..."),
			},
		},
	},
})
if err != nil {
	panic(err)
}
```

Java

```java
client.beta().vaults().credentials().update(credential.id(),
    CredentialUpdateParams.builder()
        .vaultId(vault.id())
        .auth(BetaManagedAgentsMcpOAuthUpdateParams.builder()
            .type(BetaManagedAgentsMcpOAuthUpdateParams.Type.MCP_OAUTH)
            .accessToken("xoxp-new-...")
            .expiresAt(OffsetDateTime.parse("2099-12-31T23:59:59Z"))
            .refresh(BetaManagedAgentsMcpOAuthRefreshUpdateParams.builder()
                .refreshToken("xoxe-1-new-...")
                .build())
            .build())
        .build());
```

PHP

```php
$client->beta->vaults->credentials->update(
    $credential->id,
    vaultID: $vault->id,
    auth: ManagedAgentsMCPOAuthUpdateParams::with(
        type: 'mcp_oauth',
        accessToken: 'xoxp-new-...',
        expiresAt: new DateTimeImmutable('2099-12-31T23:59:59Z'),
        refresh: ManagedAgentsMCPOAuthRefreshUpdateParams::with(refreshToken: 'xoxe-1-new-...'),
    ),
);
```

Ruby

```ruby
client.beta.vaults.credentials.update(
  credential.id,
  vault_id: vault.id,
  auth: {
    type: "mcp_oauth",
    access_token: "xoxp-new-...",
    expires_at: "2099-12-31T23:59:59Z",
    refresh: {refresh_token: "xoxe-1-new-..."}
  }
)
```

### 核对同步与撤销状态

凭证轮换以及归档、删除 Vault 或凭证，都会异步同步到运行中的云端沙箱。

> 凭证同步
>
> 轮换成功仅表示新凭证已保存，运行中的沙箱需要异步同步。请在下一次会话或沙箱连接时验证新凭证，并保存轮换请求的 `X-Trace-ID` 供排障。

下表为 Vault 生命周期的 Webhook 事件，不通过会话 SSE 返回。可在 Portal 的“服务设置 → Webhook”选择订阅，接收服务的验签与可靠处理见 [Webhook 通知](data-and-integrations-webhooks.md)。未接入 Webhook 时，应用应通过资源查询核对归档或删除状态，再通过第三方服务调用验证凭证可用性。

| 事件 | 触发条件 |
| --- | --- |
| \`vault.archived\` | Vault 已归档。同时会为每个底层凭证发出一个 \`vault\_credential.archived\` 事件。 |
| \`vault.deleted\` | Vault 已删除。同时会为每个底层凭证发出一个 \`vault\_credential.deleted\` 事件。 |
| \`vault\_credential.archived\` | 凭证已归档，可能是直接归档，也可能是 vault 归档的结果。 |
| \`vault\_credential.deleted\` | 凭证已删除，可能是直接删除，也可能是 vault 删除的结果。 |
| \`vault\_credential.refresh\_failed\` | 预留事件类型；AgentAPI 当前不执行 OAuth token 自动刷新。 |

这些事件用于确认资源状态变化，不等同于第三方在线鉴权校验。AgentAPI 当前不提供 OAuth 在线校验接口，令牌可用性仍需通过实际服务访问确认。

## 停止使用并保留审计记录

业务用户撤销授权后，应用应停止为新会话选择该 Vault 或凭证，并归档或删除相应资源。归档适用于保留非敏感审计记录；删除适用于不再保留资源记录。两种操作在运行中的沙箱上生效有延迟，无法撤回已经发出的请求。

- 列出 Vault 或凭证： 分页返回，最新的在前。默认排除已归档记录；传入 `include_archived=true` 可一并返回。
- 归档 Vault： `POST /v1/vaults/{id}/archive`。同时归档其中的凭证并清除密钥，保留记录用于审计。新会话不能再引用该 Vault。
- 归档凭证： `POST /v1/vaults/{id}/credentials/{cred_id}/archive`。清除密钥负载，但保留 `mcp_server_url` 等非敏感描述信息用于审计。
- 删除 Vault 或凭证： 永久删除记录。需要保留审计信息时，请使用归档。

在 Portal 的 Vault 列表中，可以按名称或 ID 搜索，并选择活跃、已归档或全部状态。
