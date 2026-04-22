# AppMarket Developer Skill

帮助开发者快速创建、配置和发布 AppMarket 云应用。

## 概述

AppMarket 是七牛云的应用市场平台，允许开发者（ISV）发布云应用供用户购买和部署。本 Skill 提供了一套命令和指导，帮助开发者完成应用的全生命周期管理。

核心文档为 `SKILL.md`，`CLAUDE.md` 是其 symlink，内容完全一致。

## 安装

### Claude Code

```bash
# 复制到项目目录，Claude Code 自动加载 CLAUDE.md
cp -r appmarket-dev /path/to/your/project/.claude/skills/
```

安装后 Agent 自动加载 `SKILL.md`，直接可用。

### VSCode / Cursor

将 `SKILL.md` 内容添加到项目的 `.cursorrules` 或 Workspace Instructions 中。

### 全局安装（Claude Code）

```bash
# 复制到用户全局目录
cp -r appmarket-dev ~/.claude/plugins/
```

## 快速开始

### 1. 制作自定义镜像（可选）

如果应用需要预装软件（数据库、中间件、官方 release、依赖等），使用 `image-cli.py` / `vm-cli.py` 一键制作：

```bash
export QINIU_ACCESS_KEY="your-ak"
export QINIU_SECRET_KEY="your-sk"

# 一键制作镜像（自动选最小机型、自动清理）
python3 scripts/image-cli.py build \
  --install-script path/to/install.sh \
  --image-name <app>-v1.0.0

# 查看可用机型
python3 scripts/vm-cli.py list-types

# 排查残留 VM
python3 scripts/vm-cli.py list-vms
```

详见 [镜像制作指南](references/image-building.md)。

### 2. 编写 Terraform 模块

参考 [Terraform 模块规范](references/terraform-module.md) 编写模块，然后测试：

```bash
# 本地测试模块
scripts/test-module.sh path/to/terraform-module

# 或指定变量文件
scripts/test-module.sh path/to/terraform-module test.tfvars

# 集成测试（需要真实凭证）
scripts/test-module.sh path/to/terraform-module test.tfvars --integration
```

> **注意**：本地 `terraform init` / `terraform apply` 依赖的 provider 安装方式、可用版本以及资源栈白名单，以 `qiniu/terraform-module` 仓库 README 为准；若本地验证失败，先检查 provider 版本、网络和该 README 中的白名单说明，再排查模块本身。

详细测试指南参考 [模块测试指南](references/module-testing.md)。

### 3. 创建应用

```bash
/create-app
```

交互式引导创建应用，需要提供：
- **应用名称**：2-60 个字符
- **应用描述**：50-10000 个字符
- **应用类型**：`Private`（用户账户部署）或 `Managed`（供应商托管）

### 4. 创建版本

```bash
/create-version app-xxxxxxxxxxxx
```

为应用创建新版本，配置：
- **Terraform 模块**：定义基础设施
- **InputSchema**：定义用户可配置参数
- **InputPresets**：定义规格套餐和价格

### 5. 测试 Draft 版本

```bash
/test-version app-xxxxxxxxxxxx 1.0.0
```

在 Draft 状态下创建测试实例验证功能，作为发布前验收；`test-version` 内部会创建 AppInstance，详见 [测试版本命令](commands/test-version.md)。

> 规则说明：Draft 版本可以通过 `update-version` 反复修改；Published 版本不可修改，只能创建新版本号。
> `update-version` 调用时 `--desc` 参数为**必填**，否则 API 返回 400。
> 如果应用使用实例密码，先在模块输入层约束密码复杂度，避免把不合法密码推到 API 层才失败。

### 6. 发布版本

```bash
/publish-version app-xxxxxxxxxxxx 1.0.0
```

发布后版本对用户可见，可以被购买和部署。

## 命令参考

| 命令 | 说明 | 参数 |
|-----|------|------|
| `/create-app` | 创建新应用 | `[name] [--type TYPE] [--desc DESC]` |
| `/create-version` | 创建应用版本 | `<appID> [version]` |
| `/test-version` | 测试 Draft 版本 | `<appID> <version> [--inputs FILE]` |
| `/publish-version` | 发布版本 | `<appID> <version>` |
| `/list-instances` | 列出实例 | `[--app-id ID]` |

也可以直接调用 `appmarket-cli.py`（完整命令集）：

| 命令 | 说明 |
|-----|------|
| `create-app` | 创建应用 |
| `update-app` | 更新应用名称/描述（`--name` / `--desc`，至少填一项） |
| `get-app` / `list-apps` | 查询应用 |
| `create-version` | 创建 Draft 版本 |
| `update-version` | 更新 Draft 版本（`--desc` **必填**） |
| `test-version` | 测试版本（创建真实实例） |
| `publish-version` | 发布版本（不可逆） |
| `get-instance` / `list-instances` / `delete-instance` | 管理实例 |

## 脚本工具

| 脚本 | 说明 | 用法 |
|-----|------|------|
| `image-cli.py` / `vm-cli.py` | 一键制作自定义镜像 | `python3 scripts/image-cli.py build --install-script FILE --image-name NAME` |
| `appmarket-cli.py` | AppMarket API 客户端 | `python3 scripts/appmarket-cli.py <command> [options]` |
| `generate-deploy-meta.sh` | 生成 DeployMeta | `scripts/generate-deploy-meta.sh <module-dir>` |
| `tf-to-schema.sh` | 生成 InputSchema | `scripts/tf-to-schema.sh <variables.tf>` |
| `bundle-module.sh` | 打包 Terraform 模块 | `scripts/bundle-module.sh <module-dir>` |
| `test-module.sh` | 测试 Terraform 模块 | `scripts/test-module.sh <module-dir> [tfvars]` |

## 开发流程

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────┐     ┌─────────────┐
│  制作镜像(可选)  │ ──▶ │  编写 TF 模块   │ ──▶ │  本地测试模块   │ ──▶ │  创建 App   │ ──▶ │  创建版本   │
│                 │     │                 │     │                 │     │             │     │   (Draft)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────┘     └─────────────┘
        │                       │                       │                      │                     │
        ▼                       ▼                       ▼                      ▼                     ▼
  创建云主机            main.tf                test-module.sh             appID            配置 DeployMeta
  安装软件 → 快照       variables.tf            terraform plan                              - Terraform 模块
  POST /v1/images       outputs.tf                                                          - InputSchema
                                                                                              - InputPresets

                                                                                                      │
                                                                                                      ▼
┌─────────────┐     ┌─────────────────┐
│  发布版本   │ ◀── │  测试 Draft 版  │
│ (Published) │     │                 │
└─────────────┘     └─────────────────┘
        │                   │
        ▼                   ▼
   用户可购买          test-version
                      创建测试实例
```

## API 端点

### App / Version 管理

| 操作 | 方法 | 端点 |
|-----|------|------|
| 创建应用 | POST | `/v1/apps/` |
| 获取应用 | GET | `/v1/apps/{appID}` |
| 更新应用 | PATCH | `/v1/apps/{appID}` |
| 列出应用 | GET | `/v1/apps/` |
| 创建版本 | POST | `/v1/apps/{appID}/versions/` |
| 获取版本 | GET | `/v1/apps/{appID}/versions/{version}` |
| 更新版本 | PUT | `/v1/apps/{appID}/versions/{version}` |
| 发布版本 | POST | `/v1/apps/{appID}/versions/{version}/publish` |
| 列出版本 | GET | `/v1/apps/{appID}/versions/` |

### Instance 管理

> **注意**：实例 API 必须使用 region 前缀域名 `{regionID}-ecs.qiniuapi.com`（如 `ap-northeast-1-ecs.qiniuapi.com`），regionID 通过 Host header 提取。

| 操作 | 方法 | 端点 |
|-----|------|------|
| 创建实例 | POST | `/v1/app-instances/` |
| 获取实例 | GET | `/v1/app-instances/{appInstanceID}` |
| 列出实例 | GET | `/v1/app-instances/` |
| 删除实例 | DELETE | `/v1/app-instances/{appInstanceID}` |
| 重试实例 | POST | `/v1/app-instances/{appInstanceID}/retry` |
| 续费实例 | POST | `/v1/app-instances/{appInstanceID}/renew` |

**API 基地址**：`https://ecs.qiniuapi.com`

**认证方式**：Qiniu 签名认证（HMAC-SHA1）

`list-instances` 支持通过 `--app-id` 过滤当前 App 的实例。

## 数据结构

### App

```json
{
  "appID": "app-xxxxxxxxxxxx",
  "name": "MySQL 数据库服务",
  "description": "企业级 MySQL 数据库服务...",
  "type": "Managed",
  "createdAt": "2024-01-01T00:00:00Z",
  "updatedAt": "2024-01-01T00:00:00Z"
}
```

### AppVersion

```json
{
  "appID": "app-xxxxxxxxxxxx",
  "version": "1.0.0",
  "description": "初始发布版本...",
  "status": "Draft",
  "deployMeta": {
    "inputSchema": {...},
    "terraformModule": {...},
    "inputPresets": [...]
  },
  "createdAt": "2024-01-01T00:00:00Z",
  "updatedAt": "2024-01-01T00:00:00Z",
  "publishedAt": null
}
```

### DeployMeta

```json
{
  "inputSchema": {
    "type": "object",
    "properties": {
      "instance_type": {
        "type": "string",
        "title": "实例规格",
        "enum": ["small", "medium", "large"]
      },
      "storage_size": {
        "type": "integer",
        "title": "存储容量(GB)",
        "minimum": 20,
        "maximum": 2000,
        "default": 100
      }
    },
    "required": ["instance_type"],
    "x-input-groups": [
      {"name": "基础配置", "inputs": ["instance_type", "storage_size"]}
    ]
  },
  "terraformModule": {
    "gitSource": {
      "repo": "https://github.com/your-org/terraform-mysql",
      "ref": "v1.0.0",
      "directory": ""
    }
  },
  "inputPresets": [
    {
      "name": "basic",
      "title": "基础版",
      "inputs": {
        "instance_type": "small",
        "storage_size": 50
      },
      "regionPrices": [
        {
          "regionIDs": ["ap-northeast-1", "cn-changshan-1"],
          "prices": [
            {
              "costPeriodUnit": "Month",
              "priceCNY": "99.00",
              "originalPriceCNY": "120.00",
              "priceUSD": "14.00",
              "originalPriceUSD": "18.00"
            },
            {
              "costPeriodUnit": "Year",
              "priceCNY": "999.00",
              "originalPriceCNY": "1200.00",
              "priceUSD": "140.00",
              "originalPriceUSD": "180.00"
            }
          ]
        }
      ]
    }
  ]
}
```

## 版本状态

| 状态 | 说明 | 可执行操作 |
|-----|------|----------|
| `Draft` | 草稿 | 修改 DeployMeta、发布、创建测试实例 |
| `Publishing` | 发布中 | 等待完成 |
| `Published` | 已发布 | 不可修改，可创建新版本 |

## 应用类型

| 类型 | 说明 | 适用场景 |
|-----|------|---------|
| `Private` | 资源部署在用户账户下 | 虚拟机、自建数据库、K8s 集群 |
| `Managed` | 资源部署在供应商账户下 | SaaS 服务、API 服务、托管服务 |

## 支持区域

| 区域 ID | 名称 |
|--------|------|
| `ap-northeast-1` | 亚太东北 |
| `ap-southeast-1` | 亚太东南 1 |
| `ap-southeast-2` | 亚太东南 2 |
| `cn-changshan-1` | 常山 |
| `cn-hongkong-1` | 香港 |
| `cn-shaoxing-1` | 绍兴 |

## 常见问题

### Q: 如何修改已发布的版本？

A: 已发布版本不可修改。需要创建新版本并发布。

### Q: 版本发布需要多长时间？

A: 通常几秒到几分钟，取决于规格数量和区域数量。

### Q: 如何测试未发布的版本？

A: Draft 状态的版本，App 所有者可以创建测试实例进行验证。

**方法 1：使用命令**（推荐）

```bash
/test-version app-xxxxxxxxxxxx 1.0.0
```

**方法 2：使用 API**

```bash
curl -X POST "https://{regionID}-ecs.qiniuapi.com/v1/app-instances/" \
  -H "Authorization: Qiniu $ACCESS_KEY:$SIGNATURE" \
  -H "Content-Type: application/json" \
  -d '{
    "appID": "app-xxxxxxxxxxxx",
    "appVersion": "1.0.0",
    "inputPresetName": "starter",
    "clientToken": "unique-idempotency-token",
    "inputs": {
      "root_password": "your-password"
    }
  }'
```

> **注意**：
> - 实例 API 必须使用 region 前缀域名 `{regionID}-ecs.qiniuapi.com`
> - 创建实例需要 `clientToken`（幂等 token，1-64 字符）和 `inputPresetName`（对应 DeployMeta 中定义的规格名称）
> - `inputs` 中**只需传 preset 未覆盖的 required 字段**（通常是密码、API Key 等 sensitive 字段），传入 preset 已有的字段会冲突
> - Private 类型 App 不需要 `regionPrices`（定价），但创建实例仍需账户余额充足

详见 [测试版本命令文档](commands/test-version.md)。

### Q: 如何构建自定义应用镜像？

A: 使用 `image-cli.py` / `vm-cli.py` 一键制作。编写安装脚本后执行 `image-cli.py build --install-script install.sh --image-name my-app-v1.0`，脚本自动完成创建 VM → SSH 安装 → 清理 → 创建镜像 → 删除 VM 全流程。详见 [镜像制作指南](references/image-building.md)。

### Q: 如何测试 Terraform 模块？

A: 使用提供的测试脚本：

```bash
# 本地验证
scripts/test-module.sh path/to/terraform-module

# 集成测试（需要真实凭证）
scripts/test-module.sh path/to/terraform-module test.tfvars --integration
```

详见 [模块测试指南](references/module-testing.md)。

### Q: InputSchema 参数名有什么要求？

A: 参数名需与 Terraform 模块中的 variable 名称完全一致。

### Q: 如何获取 AccessKey/SecretKey？

A: 登录七牛云控制台 → 个人中心 → 密钥管理。

## 相关资源

- [七牛云 Terraform Provider](https://github.com/qiniu/terraform-module/)
- [OpenTofu 语法文档](https://opentofu.org/docs/)
- [七牛云开发者文档（LAS）](https://developer.qiniu.com/las)
- [JSON Schema 规范](https://json-schema.org/)

## 开发指南

| 主题 | 文档 |
|------|------|
| 镜像构建 | [image-building.md](references/image-building.md) |
| 模块开发 | [terraform-module.md](references/terraform-module.md) |
| 模块测试 | [module-testing.md](references/module-testing.md) |
| InputSchema | [input-schema.md](references/input-schema.md) |
| 类型映射 | [type-mapping.md](references/type-mapping.md) |

## 支持

如有问题，请通过以下方式获取帮助：
- 提交 Issue
- 联系技术支持
