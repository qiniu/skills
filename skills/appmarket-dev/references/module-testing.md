# Terraform 模块测试指南

本指南介绍如何测试 AppMarket Terraform 模块，包括本地验证、集成测试、自动化测试等。

---

## 目录

- [1. 测试概述](#1-测试概述)
- [2. 本地验证](#2-本地验证)
- [3. 集成测试](#3-集成测试)
- [4. 常见问题排查](#4-常见问题排查)
- [5. 测试清单](#5-测试清单)

---

## 1. 测试概述

### 1.1 测试层次

| 测试阶段 | 目标 | 工具/方法 |
|---------|------|----------|
| **语法验证** | 确保 HCL 语法正确 | `terraform validate` |
| **静态检查** | 检查最佳实践和潜在问题 | `terraform fmt`, `tflint` |
| **本地执行** | 验证 plan 阶段资源配置正确 | `terraform plan` |
| **Draft 测试** | 在 AppMarket Draft 版本创建真实实例 | AppMarket API |
| **生产验证** | 发布后用户真实环境测试 | 用户反馈 |

### 1.2 测试环境准备

**环境变量配置**：

```bash
# 七牛云认证
export QINIU_ACCESS_KEY="your-access-key"
export QINIU_SECRET_KEY="your-secret-key"

# API 端点（可选）
export QINIU_API_ENDPOINT="https://ecs.qiniuapi.com"
```

---

## 2. 本地验证

### 2.1 格式化检查

确保代码格式符合 Terraform 标准：

```bash
cd /path/to/terraform-module

# 检查格式（只显示需要格式化的文件）
terraform fmt -check -recursive

# 自动格式化
terraform fmt -recursive
```

**预期输出**：
- 无输出表示格式正确
- 有输出则列出需要格式化的文件

### 2.2 语法验证

验证 Terraform 配置语法：

```bash
# 初始化（下载 provider）
terraform init

# 语法验证
terraform validate
```

> **注意**：本地 `terraform init` / `terraform apply` 依赖的 provider 安装方式、可用版本以及资源栈白名单，以 `qiniu/terraform-module` 仓库 README 为准；若本地验证失败，先检查 provider 版本、网络和该 README 中的白名单说明，再排查模块本身。

**预期输出**：
```
Success! The configuration is valid.
```

**常见错误**：
```
Error: Unsupported argument

  on main.tf line 10, in resource "qiniu_compute_instance" "example":
  10:   invalid_argument = "value"

An argument named "invalid_argument" is not expected here.
```

### 2.3 静态分析（可选）

使用 TFLint 检查最佳实践：

```bash
# 初始化 TFLint
tflint --init

# 执行检查
tflint
```

**检查项**：
- 未使用的变量和输出
- 硬编码的敏感信息
- 资源命名规范
- Provider 版本约束

### 2.4 生成执行计划

验证资源配置逻辑：

```bash
# 创建测试变量文件（根据实际模块的 required 变量填写）
cat > test.tfvars <<EOF
instance_type     = "ecs.c1.c2m4"
system_disk_size  = 50
root_password     = "<YourPassword>"
# ... 其他 required 变量
EOF

# 生成执行计划
terraform plan -var-file=test.tfvars

# 保存计划到文件（可选）
terraform plan -var-file=test.tfvars -out=tfplan
terraform show tfplan
```

**关键检查点**：

- [ ] 资源类型正确（`qiniu_compute_instance` 等）
- [ ] 资源依赖关系正确（`depends_on`）
- [ ] 变量替换正确（`${var.instance_name}`）
- [ ] 初始化脚本已内联到 `user_data` heredoc 中（moduleContent 模式不能用 `templatefile`）
- [ ] 敏感信息标记为 `sensitive = true`

---

## 3. 集成测试

### 3.1 创建测试实例

使用 `test-module.sh` 脚本（封装了 fmt / validate / plan，并可选 apply 集成测试）：

```bash
# 使用插件提供的测试脚本
scripts/test-module.sh path/to/terraform-module

# 或指定测试变量（注意：路径必须是绝对路径）
scripts/test-module.sh path/to/terraform-module /absolute/path/to/test.tfvars
```

> **tfvars 路径必须使用绝对路径**：`test-module.sh` 内部会 `cd` 进模块目录后再调用 `terraform`，导致相对路径失效。使用 `$(pwd)/test.tfvars` 或 `$(realpath test.tfvars)` 转换为绝对路径。

---

## 4. 常见问题排查

### 4.1 语法错误

**错误信息**：
```
Error: Unsupported block type

  on main.tf line 10:
  10: variabls "instance_name" {

Blocks of type "variabls" are not expected here. Did you mean "variable"?
```

**解决方法**：修正拼写错误 `variabls` → `variable`

### 4.2 变量未定义

**错误信息**：
```
Error: Reference to undeclared input variable

  on main.tf line 20:
  20:   name = var.instace_name

An input variable with the name "instace_name" has not been declared.
```

**解决方法**：检查变量名拼写，确保在 `variables.tf` 中已定义

### 4.3 Provider 初始化失败

**错误信息**：
```
Error: Failed to query available provider packages

Could not retrieve the list of available versions for provider hashicorp/qiniu
```

**解决方法**：
```bash
# 清理缓存
rm -rf .terraform .terraform.lock.hcl

# 重新初始化
terraform init -upgrade
```

> **本地环境额外步骤**：`hashicorp/qiniu` 无法从公网 registry 下载，需先配置 filesystem mirror（见 [Terraform 模块规范 → versions.tf 本地测试](terraform-module.md)），再运行 `terraform init`。

### 4.4 部署失败排查

**步骤**：

1. **查看实例详情和日志**：
   ```bash
   # 通过 CLI 工具查询（app-id 和 instance-id 来自 test-version 输出）
   python3 scripts/appmarket-cli.py get-instance \
     --app-id app-xxxxxxxxxxxx \
     --instance-id appi-xxxxxxxxxxxx --region ap-northeast-1
   ```

2. **检查 Terraform State**：
   ```bash
   # 查询 RFS 资源栈详情（含 Terraform outputs 和物理资源 ID）
   python3 scripts/appmarket-cli.py get-stack \
     --stack <stackName 或 stackID> --region ap-northeast-1
   ```

3. **常见部署失败原因**：
   - 镜像不存在或无权限访问
   - 实例规格在指定区域不可用
   - 配额不足（CPU、内存、磁盘）
   - user_data 脚本执行失败

---

## 5. 测试清单

### 5.1 本地测试清单

**基础验证**：
- [ ] 代码格式化 (`terraform fmt -check`)
- [ ] 语法验证 (`terraform validate`)
- [ ] 静态检查 (`tflint`)
- [ ] 执行计划生成 (`terraform plan`)

**配置检查**：
- [ ] 所有变量在 `variables.tf` 中定义
- [ ] 所有变量有合理的默认值或 description
- [ ] 敏感变量标记 `sensitive = true`
- [ ] 所有输出在 `outputs.tf` 中定义
- [ ] 输出描述清晰
- [ ] Provider 版本约束明确

**资源检查**：
- [ ] 资源命名规范（使用变量）
- [ ] 资源依赖关系正确
- [ ] 初始化脚本已内联到 user_data heredoc（moduleContent 模式）
- [ ] user_data 脚本语法正确

### 5.2 集成测试清单

**Draft 版本测试**：
- [ ] DeployMeta 生成成功
- [ ] Draft 版本创建成功
- [ ] 测试实例创建成功
- [ ] 实例状态变为 `Deployed` 或 `Running`（`Deployed` = 基础设施已就绪，`Running` = 健康检查通过）
- [ ] 所有输出正确返回（public_ip、access_url 等）

**功能验证**：
- [ ] 应用服务正常启动
- [ ] 端口监听正常
- [ ] 健康检查通过
- [ ] 初始化脚本执行成功
- [ ] 配置文件正确生效

**清理验证**：
- [ ] 测试实例成功删除
- [ ] 相关资源全部释放

---

## 相关资源

- [Terraform Testing Best Practices](https://www.terraform.io/docs/language/modules/testing-experiment.html)
- [TFLint 规则文档](https://github.com/terraform-linters/tflint/tree/master/docs/rules)
- [AppMarket API 文档](../README.md#api-端点)
- [测试脚本](../scripts/test-module.sh)
- [测试版本命令](../commands/test-version.md)
