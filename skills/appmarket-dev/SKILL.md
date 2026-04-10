---
name: appmarket-dev
description: 帮助开发者创建、配置和发布七牛 AppMarket 云应用。当用户需要创建应用、发布版本、制作自定义镜像、生成 DeployMeta、编写或测试 Terraform 模块时使用。
license: MIT
compatibility: 需要 Python 3.8+、SSH 客户端、Terraform CLI，以及七牛 QINIU_ACCESS_KEY / QINIU_SECRET_KEY 环境变量。仅适用于七牛 LAS（云主机）+ AppMarket 服务。
argument-hint: "<app-id 或操作描述>"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(python3 scripts/appmarket-cli.py *)
  - Bash(python3 scripts/vm-cli.py *)
  - Bash(python3 scripts/image-cli.py *)
  - Bash(python3 scripts/tf-to-schema.py *)
  - Bash(bash scripts/tf-to-schema.sh *)
  - Bash(bash scripts/generate-deploy-meta.sh *)
  - Bash(bash scripts/bundle-module.sh *)
  - Bash(bash scripts/test-module.sh *)
  - Bash(terraform *)
  - Bash(cat *)
  - Bash(ls *)
  - Bash(jq *)
---

# AppMarket 应用开发 Skill

帮助 APP 开发者快速上架应用到七牛 AppMarket。

## 使用场景

当用户需要：
- 创建新的 AppMarket 应用
- 从 Terraform 模块生成 DeployMeta
- 发布应用版本

## 快速上架流程

### 0. 评估部署方案（必须最先完成）

**在写任何 Terraform 代码或创建 App 之前，先回答这四个问题：**

| 问题 | 可选答案 |
|------|---------|
| 服务模式？ | 长驻服务 / 一次性任务 |
| 镜像策略？ | 预装镜像 / 启动时安装 |
| 公网访问？ | 公网直接访问 / SSH 隧道 / 无需外部访问 |
| 托管方式？ | 用户自托管 (Private) / 供应商托管 (Managed) |

并确认最小部署信息已明确：

```
[ ] 入口命令（如何启动？）
[ ] 监听端口
[ ] 必需环境变量 / 密钥
[ ] 数据持久化需求
[ ] 健康检查方式
[ ] 运行用户权限
[ ] 测试验证方式
```

四个问题都有答案、清单全部打勾后，才进入步骤 1。

---

### 1. 先确定运行与镜像边界

在写 Terraform 之前，先把下面信息确认清楚：

| 项目 | 需要明确的内容 |
|------|----------------|
| 二进制来源 | 本地 build 产物 / 官方 release / 其他 |
| 启动命令 | 实际启动入口是什么 |
| 配置方式 | 配置文件路径、环境变量、CLI 参数 |
| 依赖边界 | 哪些依赖必须进镜像，哪些可在启动时注入 |
| 监听与健康检查 | 端口、健康 endpoint、就绪判断 |
| 运行权限 | root / 普通用户 / 需要哪些系统权限 |
| 镜像策略 | 预装镜像 / 启动时安装 |

**判断依据**：
- 选 **预装镜像** → 先执行步骤 2（制作镜像），再执行步骤 3（编写 Terraform）
- 选 **启动时安装** → 跳过步骤 2，直接执行步骤 3

### 2. 制作自定义镜像（仅预装镜像策略需要）

> 如果选择"启动时安装"策略，跳过此步骤直接进入步骤 3。

编写安装脚本（参考 `assets/setup-image.sh` 模板），然后一键制作：

```bash
export QINIU_ACCESS_KEY="your-ak"
export QINIU_SECRET_KEY="your-sk"

python3 scripts/image-cli.py build \
  --install-script path/to/install.sh \
  --image-name MyApp-v1.0.0 \
  --image-desc "Ubuntu 24.04 + MyApp 1.0.0"
```

脚本自动完成：创建 VM（自动选最小机型）→ SSH 执行安装脚本 → 清理环境 → 创建镜像 → 删除 VM。

> **重要**：如果应用使用官方 standalone release，安装脚本必须基于对应的官方 release 包。
> 镜像制作阶段只做安装和文件落盘，不要在镜像机上实际拉起服务；用新 VM 复现安装流程，确认文件、依赖和 service 配置后再 snapshot。

详见 [镜像制作指南](references/image-building.md)。

### 3. 编写 Terraform 模块

```
my-app/
├── main.tf           # 主资源定义（含内联 user_data 脚本）
├── variables.tf      # 输入变量（对应 InputSchema）
├── outputs.tf        # 输出定义
└── versions.tf       # Provider 版本
```

> **重要**：使用 `moduleContent` 方式发布时，`bundle-module.sh` 只打包 `*.tf` 文件。初始化脚本必须内联到 `main.tf` 的 `user_data = base64encode(<<-EOF ... EOF)` heredoc 中，**不能使用 `templatefile()` 或 `file()` 引用外部文件**。使用 `gitSource` 方式则无此限制。

详见 [Terraform 模块规范](references/terraform-module.md)。

### 4. 测试模块

```bash
# 本地验证（格式、语法、plan）
scripts/test-module.sh path/to/my-app test.tfvars

# 集成测试（需要真实凭证）
scripts/test-module.sh path/to/my-app test.tfvars --integration
```

> **注意**：本地 `terraform init` / `terraform apply` 依赖的 provider 安装方式、可用版本以及资源栈白名单，以 `qiniu/terraform-module` 仓库 README 为准；若本地验证失败，先检查 provider 版本、网络和该 README 中的白名单说明，再排查模块本身。

详见 [模块测试指南](references/module-testing.md)。

### 5. 生成并编辑 DeployMeta

```bash
# 从 Terraform 模块自动生成（InputSchema + moduleContent + 示例 Preset）
scripts/generate-deploy-meta.sh path/to/my-app
```

生成后手动检查 `deploy-meta.json`：
- **inputSchema**：确认字段类型、title、required 正确
- **inputPresets**：配置规格套餐的 `inputs`（不包含 sensitive 变量如密码、API Key）
- **regionPrices**：Private 类型 App **不需要**，应删除；Managed 类型 App 必须配置

### 6. 创建应用

```bash
python3 scripts/appmarket-cli.py create-app \
  --name "MyApp" \
  --desc "应用描述" \
  --type Private
# 输出 AppID: app-xxxxxxxxxxxx
```

或使用 Claude Code 命令：`/create-app`

### 7. 创建版本并测试

```bash
# 创建 Draft 版本
python3 scripts/appmarket-cli.py create-version \
  --app-id app-xxxxxxxxxxxx --version 1.0.0 \
  --deploy-meta path/to/deploy-meta.json

# 测试（创建真实实例验证部署，--cleanup 测完自动删除）
python3 scripts/appmarket-cli.py test-version \
  --app-id app-xxxxxxxxxxxx --version 1.0.0 \
  --region ap-northeast-1 --cleanup
```

如果测试发现问题，修改模块/DeployMeta 后用 `update-version` 更新：

```bash
# --desc 为必填参数，否则 API 返回 400
python3 scripts/appmarket-cli.py update-version \
  --app-id app-xxxxxxxxxxxx --version 1.0.0 \
  --deploy-meta path/to/deploy-meta.json \
  --desc "修复 xxx 问题"
```

或使用 Claude Code 命令：`/create-version app-xxx` → `/test-version app-xxx 1.0.0`

> **流程约定**：Draft 版本可以直接用于实例验收；只有在 Draft 通过后，才执行 `publish-version` 进入正式发布。
> Draft 版本允许通过 `update-version` 继续修改；Published 版本不可修改，只能创建新版本。
> 如果应用使用实例密码，先在模块输入层约束密码复杂度，避免把不合法密码推到 API 层才失败。

### 8. 发布版本

```bash
python3 scripts/appmarket-cli.py publish-version \
  --app-id app-xxxxxxxxxxxx --version 1.0.0 --yes
```

发布后版本不可修改，用户可购买和部署。如需变更，创建新版本号。

或使用 Claude Code 命令：`/publish-version app-xxx 1.0.0`

### 9. 版本完成标准

一个可用版本必须同时满足：

1. Terraform module 可以 `init / validate / plan`
2. 镜像来自干净 VM，且安装流程可复现
3. DeployMeta 的 `inputSchema` 与 module 变量一致
4. `inputPresets` 只暴露最终给用户的参数
5. `create-version` 后版本处于 Draft 且可创建测试实例
6. `test-version` 能创建实例并验证应用可用
7. 通过后再 `publish-version`

## 详细指南

| 主题 | 文件 |
|------|------|
| 镜像制作 | [references/image-building.md](references/image-building.md) |
| Terraform 模块规范 | [references/terraform-module.md](references/terraform-module.md) |
| 模块测试 | [references/module-testing.md](references/module-testing.md) |
| InputSchema 编写 | [references/input-schema.md](references/input-schema.md) |
| 类型映射 | [references/type-mapping.md](references/type-mapping.md) |

## DeployMeta 结构

```json
{
  "inputSchema": { /* JSON Schema，由 tf-to-schema.sh 自动生成 */ },
  "terraformModule": {
    "moduleContent": "Terraform 代码（所有 .tf 文件合并）"
  },
  "inputPresets": [
    {
      "name": "starter",
      "title": "入门版",
      "inputs": { "instance_type": "small" },
      "regionPrices": [...]
    }
  ]
}
```

> **注意**：
> - Private 类型 App 的 inputPresets **不需要 `regionPrices`**（定价由底层资源决定），但创建实例仍需账户余额充足。
> - Managed 类型 App 必须配置 `regionPrices`。
> - `generate-deploy-meta.sh` 内部调用 `assemble-deploy-meta.py` 生成的 `regionPrices` 为占位值，Private App 应将其删除。

## 自动化工具

| 工具 | 说明 |
|------|------|
| `scripts/appmarket-cli.py` | CLI 工具，封装 AppMarket API（零依赖，AK/SK 从环境变量获取） |
| `scripts/vm-cli.py` | VM 管理工具（创建/删除/列出 VM、查询机型） |
| `scripts/image-cli.py` | 镜像制作工具（一键制作：VM → 安装 → 镜像 → 删除VM；以及列出/删除镜像） |
| `scripts/generate-deploy-meta.sh` | 从 Terraform 模块生成 DeployMeta |
| `scripts/tf-to-schema.sh` | 从 variables.tf 生成 InputSchema |
| `scripts/bundle-module.sh` | 打包 Terraform 模块为 moduleContent |
| `scripts/test-module.sh` | 测试 Terraform 模块（格式、语法、plan、集成） |
| `assets/setup-image.sh` | 安装脚本模板（供 image-cli.py --install-script 使用或手动 SSH 执行） |
| `assets/deploy-meta.json` | DeployMeta 结构模板 |
