---
name: appmarket-dev
description: 帮助开发者创建、配置和发布七牛 AppMarket 云应用。当用户需要创建应用、发布版本、制作自定义镜像（含 VM 管理）、生成 DeployMeta、编写或测试 Terraform 模块时使用。
license: MIT
compatibility: 需要 Python 3.8+、SSH 客户端（ssh/scp）、sshpass、Terraform CLI，以及七牛 QINIU_ACCESS_KEY / QINIU_SECRET_KEY 环境变量。仅适用于七牛 LAS（云主机）+ AppMarket 服务。镜像制作命令（build/create-image/run-script）在启动前会自动检查 ssh/scp/sshpass 是否可用，缺失时会给出安装提示并退出。
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

**在编写安装脚本和创建 VM 之前，必须先与用户确认四个问题：**

**① 构建 VM 的 CPU / 内存规格需求**

image-cli.py 默认选择最小可用机型，但某些应用在安装/编译阶段需要较大内存或多核 CPU（如编译型语言、大模型下载等）。需要确认：

- 安装阶段是否有 CPU / 内存的最低要求？
- 安装脚本是否会在 VM 上执行耗时编译？
- 默认最小机型（通常 1C2G）是否满足需求？

确认后，通过 `--instance-type` 指定合适规格：

```bash
python3 scripts/image-cli.py build \
  --install-script path/to/install.sh \
  --image-name MyApp-v1.0.0 \
  --image-desc "Ubuntu 24.04 + MyApp 1.0.0" \
  --instance-type ecs.c1m2   # 按需指定
```

**② 构建 VM 的磁盘大小需求**

LAS 系统盘范围为 **20–500 GB**，`image-cli.py build` 默认值为 20 GB。磁盘大小直接决定镜像的 `minDisk` 约束，后续用该镜像创建实例时系统盘不能低于此值。需要确认：

- 应用安装后的磁盘占用大约是多少？
- 运行时是否有持续写入（日志、缓存、模型文件等）？
- 是否需要为未来版本预留增长空间？

> 建议：安装完成后在 VM 上用 `df -h /` 确认实际占用，在此基础上**留 20% 以上余量**后向上取整，作为 `--disk-size` 参数传入；同时在 `variables.tf` 的 `system_disk_size` 变量中设置同等的 `minimum`，确保用户创建实例时不会因磁盘过小报 400。

**③ 服务运行用户**

需要确认服务应以哪个系统用户身份运行：

| 选项 | 说明 | 注意事项 |
|------|------|---------|
| `root` | 最简单，权限最大 | 安全风险较高 |
| 专用用户（如 `appuser`） | 推荐，最小权限原则 | 若需 systemd 服务自启动，必须在安装脚本中执行 `loginctl enable-linger <username>`，否则用户未登录时服务不会随系统启动 |

> **`loginctl enable-linger` 说明**：非 root 用户的 systemd user service 默认只在该用户登录后才启动。`enable-linger` 让系统在启动时就为该用户激活 systemd session，从而支持服务自启动。

**④ 是否在镜像中配置服务自启动**

镜像中的服务启动方式影响 Terraform user_data 的设计，需要明确：

| 选项 | 说明 | 适用场景 |
|------|------|---------|
| 镜像中配置 systemd 自启 | 实例启动后服务自动运行，user_data 只注入配置文件 | 长驻服务、无需动态配置服务参数 |
| user_data 中手动启动 | user_data 写入配置后再 `systemctl start`，更灵活 | 服务启动依赖 user_data 注入的参数 |
| 不自启，手动操作 | 安装好依赖，用户 SSH 后手动启动 | 开发/调试场景 |

> **确认原则**：如果服务的配置（API Key、端口等）需要在 user_data 阶段注入，需**明确询问用户**是否希望在镜像中开启自启动，并说明风险：镜像中开启自启动时，实例首次启动时服务会在 user_data 执行前运行，可能读取到空/默认配置。用户确认接受该风险或有其他处理方案（如 user_data 中先 stop → 写配置 → start）时，方可在镜像中开启自启动。

确认后，在安装脚本和 Terraform user_data 中按约定实现。

---

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

**镜像制作完成后，`image-cli.py` 会在安装脚本同级目录自动写出构建 manifest（JSON）**，记录：基础镜像 ID/版本、构建 VM 规格、安装脚本路径及 SHA256、输出镜像 ID 及 minDisk/minCPU/minMemory 约束。

> **约定**：manifest 文件（`<image-name>-build-YYYYMMDD-HHMMSS.json`）应与安装脚本一起提交进版本控制，以便追溯镜像内容、审阅安装脚本变更、在需要时复现镜像。

**镜像验收（通过镜像创建新 VM 后必须确认）**：
- [ ] 服务进程以预期用户身份运行（`ps aux | grep <service>`）
- [ ] 若配置了自启动：重启 VM 后服务自动拉起（`systemctl status <service>` 或 `systemctl --user status <service>`）
- [ ] 若配置了自启动且为非 root 用户：确认 `loginctl show-user <username> | grep Linger` 输出 `Linger=yes`

详见 [镜像制作指南](references/image-building.md)。

### 3. 编写 Terraform 模块

> ⛔ **预装镜像策略前置检查**：开始编写 Terraform 之前，必须确认：
> - [ ] 步骤 2 已完成，已拿到真实镜像 ID（如 `image-xxxxxxxxxxxxxxxx`）
> - [ ] `image_id` 的 `default` 值使用真实镜像 ID，**不要用占位符**
>
> **如果镜像还没制作完，停在步骤 2，拿到真实镜像 ID 后再来写 Terraform。**
> 如果工作目录已有旧的 Terraform 文件，先检查 `image_id` 的 `default` 是否仍为占位符（如 `image-xxx`），是则不能继续，必须先完成镜像制作。

**在动手写代码之前，先列出具体的参数表格与用户确认：**

**步骤：**
1. 根据应用特性，拟定输入变量草案，整理成下面两张表
2. 将表格呈现给用户，明确询问是否需要调整
3. 用户确认后再编写代码，避免反复修改 `variables.tf` 导致 `deploy-meta.json` 也要跟着改

**输入变量草案（举例格式）**

| 参数 | 类型 | 是否用户可见 | 默认值 | 说明 |
|------|------|-------------|--------|------|
| `api_key` | string (sensitive) | ✅ 必填 | — | 服务 API Key |
| `root_password` | string (sensitive) | ✅ 必填 | — | 实例 root 密码（≥8 位，含字母/数字/特殊符号）|
| `model` | string | ✅ 可选 | `default-model` | 默认使用的模型 ID（用户可自行修改）|
| `instance_type` | string | 🔒 由 Preset 决定 | `ecs.t1.c2m4` | 实例规格 |
| `system_disk_size` | number | 🔒 由 Preset 决定 | `60` | 系统盘（GiB）|
| `image_id` | string | ❌ 隐藏/硬编码 | `image-xxx` | 预装镜像，不暴露给用户 |

> 图例：✅ 用户在安装界面填写 / 🔒 由 Preset 套餐控制 / ❌ 完全隐藏（variables.tf 设 default，不进 inputSchema.required）

**输出草案（举例格式）**

| 输出 | 内容 |
|------|------|
| `instance_id` | 实例 ID（运维排查用）|
| `public_ip` | 公网 IP 地址 |
| `ssh_command` | `ssh root@<ip>`（便捷连接命令）|
| `service_url` | 服务访问地址（如有 Web 界面）|
| `init_log` | 初始化日志路径 |

**确认要点：**
- `model` 等可选参数：是让用户自由填写，还是改为 Preset 枚举（下拉选择）？
- Preset 套餐数量和规格（如入门版/标准版）是否合适？
- 是否有遗漏的必填参数？

---

```
my-app/
├── main.tf           # 主资源定义（含内联 user_data 脚本）
├── variables.tf      # 输入变量（对应 InputSchema）
├── outputs.tf        # 输出定义
└── versions.tf       # Provider 版本
```

> **重要**：使用 `moduleContent` 方式发布时，`bundle-module.sh` 只打包 `*.tf` 文件。初始化脚本必须内联到 `main.tf` 的 `user_data = base64encode(<<-EOF ... EOF)` heredoc 中，**不能使用 `templatefile()` 或 `file()` 引用外部文件**。使用 `gitSource` 方式则无此限制。

详见 [Terraform 模块规范](references/terraform-module.md)。

### 4. 本地验证 Terraform 模块（必须，不可跳过）

**在生成 DeployMeta 或创建版本之前，必须先通过本地 Terraform 验证。** 跳过此步骤直接上传的模块若在 AppMarket 侧部署时才报错，排查成本极高。

```bash
cd path/to/my-app

# 1. 格式检查
terraform fmt -check -recursive

# 2. 初始化并验证语法（必须通过）
terraform init
terraform validate

# 3. 生成执行计划验证资源配置（必须能 plan 成功）
#    先准备包含所有 required 变量的 tfvars
terraform plan -var-file=test.tfvars
```

**✅ 本地验证通过检查点**（全部打勾才能继续步骤 5）：
- [ ] `terraform fmt -check` 无报错（或已格式化）
- [ ] `terraform validate` 输出 `Success! The configuration is valid.`
- [ ] `terraform plan` 能正常生成计划，resource 字段无意外报错

> **注意**：本地 `terraform init` / `terraform apply` 依赖的 provider 安装方式、可用版本以及资源栈白名单，以 `qiniu/terraform-module` 仓库 README 为准；若本地验证失败，先检查 provider 版本、网络和该 README 中的白名单说明，再排查模块本身。

```bash
# 也可使用封装脚本一步完成上述检查
# 注意：test-module.sh 内部会 cd 进模块目录，tfvars 路径必须用绝对路径
scripts/test-module.sh path/to/my-app $(pwd)/test.tfvars

# 集成测试（需要真实凭证，可选）
scripts/test-module.sh path/to/my-app $(pwd)/test.tfvars --integration
```

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

> **⚠️ 用户可见参数的评审原则（必须与用户确认）**
>
> `generate-deploy-meta.sh` 会把 `variables.tf` 中的**所有变量**都生成到 `inputSchema`，但并非所有变量都应暴露给终端用户。生成 DeployMeta 后，**必须逐一审查每个字段，并与用户确认最终的参数列表**。
>
> 判断一个变量是否应暴露给用户的依据：
> - ✅ **应暴露**：用户需要根据实际情况填写的值，如 API Key、密码、选择模型等
> - ✅ **应暴露**：可以让用户调整的规格参数，如 `instance_type`、带宽等（通过 `inputPresets` 提供选项）
> - ❌ **不应暴露**：由应用开发者固定、对用户透明的内部参数，如镜像 ID（`image_id`）、固定的 URL、内部版本号等
>
> **处理不应暴露的参数**：在 `variables.tf` 中设置 `default` 值并从 `inputSchema.required` 中移除；同时从 `inputPresets[].inputs` 中删除该字段（让 Terraform 直接用 default）。这样该参数就不会出现在 AppMarket 的安装配置界面上。

### 6. 创建应用

> ⛔ **先检查是否已有同名应用，不要重复创建。** 在执行 `create-app` 之前，必须先：
>
> ```bash
> python3 scripts/appmarket-cli.py list-apps
> ```
>
> 如果已有同名或功能相同的 App，**默认复用**——在现有 App 上创建新版本号（如 `1.1.0`、`2.0.0`）即可。如需新建，**必须先询问用户确认**，并说明已有 App 的信息（ID、名称、现有版本）。用户明确确认后方可执行 `create-app`。

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
# 创建 Draft 版本（--desc 必填，且至少 50 个字符，否则 API 返回 400）
python3 scripts/appmarket-cli.py create-version \
  --app-id app-xxxxxxxxxxxx --version 1.0.0 \
  --deploy-meta path/to/deploy-meta.json \
  --desc "初始版本，包含预装镜像和 Terraform 模块，支持香港区域部署"

# 测试（创建真实实例验证部署，--cleanup 测完自动删除）
# 注意：如果报 RFSNotEnabled [403]，说明当前区域不支持该 App 部署
# → 换其他区域重试，如 cn-hongkong-1
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
>
> **⚠️ 实例管理原则**：
> - **不要频繁创建新 App**。调试和验证阶段应在现有 App 的 Draft 版本上通过 `update-version` 反复修改，直到测试通过再考虑创建新版本或新 App。
> - **部署失败时不删除实例**。`test-version` 在部署失败时会保留实例，供人工 SSH 排查（查日志、检查 cloud-init 输出等）；排查完毕后手动调用 `delete-instance` 清理。
> - `--cleanup` 标志仅在部署**成功**后生效，失败时始终保留实例。

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
| `scripts/appmarket-cli.py` | CLI 工具，封装 AppMarket API（零依赖，AK/SK 从环境变量获取）；`wait-instance` 可在 `test-version` 超时或中断后恢复轮询 |
| `scripts/vm-cli.py` | VM 管理工具（创建/删除/列出 VM、查询机型） |
| `scripts/image-cli.py` | 镜像制作工具（一键制作：VM → 安装 → 镜像 → 删除VM；以及列出/删除镜像） |
| `scripts/generate-deploy-meta.sh` | 从 Terraform 模块生成 DeployMeta |
| `scripts/tf-to-schema.sh` | 从 variables.tf 生成 InputSchema |
| `scripts/bundle-module.sh` | 打包 Terraform 模块为 moduleContent |
| `scripts/test-module.sh` | 测试 Terraform 模块（格式、语法、plan、集成） |
| `assets/setup-image.sh` | 安装脚本模板（供 image-cli.py --install-script 使用或手动 SSH 执行） |
| `assets/deploy-meta.json` | DeployMeta 结构模板 |
