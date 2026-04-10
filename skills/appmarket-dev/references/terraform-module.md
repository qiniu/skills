# Terraform 模块规范

当用户需要编写或配置 Terraform 模块时，提供以下指导。

## 快速参考

| 主题 | 参考文件 |
|------|---------|
| 变量定义 | [variables.md](references/variables.md) |
| 输出定义 | [outputs.md](references/outputs.md) |
| 资源示例 | [resources.md](references/resources.md) |
| 类型映射 | [type-mapping.md](references/type-mapping.md) |

---

## DeployMeta 完整结构

```json
{
  "inputSchema": {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["必填字段列表"],
    "properties": {
      // 参数定义
    }
  },
  "terraformModule": {
    "gitSource": {
      "repo": "https://github.com/org/terraform-module",
      "ref": "main",
      "directory": ""
    }
  },
  "inputPresets": [
    {
      "name": "规格标识",
      "title": "规格显示名称",
      "inputs": {
        // 预设参数值
      },
      "regionPrices": [
        {
          "regionIDs": ["ap-northeast-1", "cn-changshan-1"],
          "prices": [
            {
              "costPeriodUnit": "Month",
              "priceCNY": "99.00",
              "originalPriceCNY": "129.00",
              "priceUSD": "14.00",
              "originalPriceUSD": "18.00"
            }
          ]
        }
      ]
    }
  ]
}
```

---

## 核心原则

### 1. InputSchema 与 Terraform 变量对应

**关键规则：**
- ✅ **InputSchema 属性名必须与 Terraform 变量名一致**
- ✅ **敏感信息使用 `"writeOnly": true`**
- ✅ **使用 JSON Schema 标准规范**

**示例：**

InputSchema 中定义：
```json
{
  "properties": {
    "instance_type": {
      "type": "string",
      "title": "实例规格"
    },
    "root_password": {
      "type": "string",
      "title": "实例密码",
      "writeOnly": true
    }
  }
}
```

Terraform 变量对应：
```hcl
variable "instance_type" {
  type        = string
  description = "实例规格"
}

variable "root_password" {
  type        = string
  description = "实例密码"
  sensitive   = true
}
```

### 2. 敏感信息处理

**Terraform 变量：**
```hcl
variable "database_password" {
  type        = string
  description = "数据库密码"
  sensitive   = true  # 标记为敏感
}
```

**InputSchema：**
```json
{
  "database_password": {
    "type": "string",
    "title": "数据库密码",
    "writeOnly": true,  // 不在输出中显示
    "minLength": 8
  }
}
```

---

## Terraform 模块文件结构

```
terraform-module/
├── main.tf           # 主资源定义（含内联 user_data 脚本）
├── variables.tf      # 输入变量定义
├── outputs.tf        # 输出定义
├── versions.tf       # Provider 版本约束
└── locals.tf         # 局部变量（可选）
```

> **moduleContent 限制**：`bundle-module.sh` 只打包 `*.tf` 文件，不包含子目录（如 `scripts/`、`templates/`）。因此使用 `moduleContent` 方式发布时，`templatefile()` 和 `file()` 等引用外部文件的函数**不可用**，初始化脚本必须内联到 `main.tf` 的 `user_data = base64encode(<<-USERDATA ... USERDATA)` heredoc 中。使用 `gitSource` 方式则无此限制。

### 文件内容示例

#### main.tf

```hcl
resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

# ECS 实例资源
resource "qiniu_compute_instance" "app" {
  name                   = "myapp-${random_string.suffix.result}"  # name 为必填字段
  instance_type          = var.instance_type
  image_id               = var.image_id
  system_disk_size       = var.system_disk_size
  internet_max_bandwidth = var.internet_max_bandwidth
  internet_charge_type   = "PeakBandwidth"  # 峰值带宽，支持 50/100/200 Mbps

  # 初始化脚本（moduleContent 模式必须内联，不能用 templatefile）
  user_data = base64encode(<<-USERDATA
#!/bin/bash
set -euo pipefail
# 初始化逻辑...
echo "Initializing..."
USERDATA
  )

  description = "Managed by AppMarket"

  timeouts {
    create = "30m"
    delete = "30m"
  }

  lifecycle {
    ignore_changes = [user_data, instance_type, system_disk_size]
  }
}
```

> **`qiniu_compute_instance` 必知属性**：
> - `name` 是**必填字段**，API 不会自动生成；推荐用 `random_string` resource 追加后缀确保唯一性
> - 公网 IP 属性为 `public_ip_addresses[0].ipv4`（**不是** `public_ip`）
> - 务必加 `timeouts`（避免平台超时报错）和 `lifecycle.ignore_changes`（避免平台侧改动触发 drift）
> - `random` provider 需在 `versions.tf` 的 `required_providers` 中声明

#### variables.tf

```hcl
# 必填变量
variable "instance_type" {
  type        = string
  description = "ECS 实例规格"

  validation {
    condition     = can(regex("^ecs\\.", var.instance_type))
    error_message = "instance_type 必须以 'ecs.' 开头"
  }
}

variable "root_password" {
  type        = string
  description = "实例密码"
  sensitive   = true

  validation {
    condition     = length(var.root_password) >= 8
    error_message = "密码长度至少 8 个字符"
  }
}

# 可选变量
variable "system_disk_size" {
  type        = number
  description = "系统盘大小（GiB）"
  default     = 20

  validation {
    condition     = var.system_disk_size >= 10 && var.system_disk_size <= 500
    error_message = "系统盘大小必须在 10-500 GiB 之间"
  }
}

variable "internet_max_bandwidth" {
  type        = number
  description = "公网峰值带宽（Mbps），支持 50/100/200"
  default     = 100

  validation {
    condition     = contains([50, 100, 200], var.internet_max_bandwidth)
    error_message = "带宽只支持 50、100、200 Mbps"
  }
}

variable "app_name" {
  type        = string
  description = "应用名称"
  default     = "my-app"
}
```

#### outputs.tf

```hcl
output "instance_id" {
  description = "实例 ID"
  value       = qiniu_ecs_instance.app.id
}

output "public_ip" {
  description = "公网 IP 地址"
  value       = qiniu_compute_instance.app.public_ip_addresses[0].ipv4
}

output "access_url" {
  description = "应用访问地址"
  value       = "http://${qiniu_compute_instance.app.public_ip_addresses[0].ipv4}"
}

output "ssh_command" {
  description = "SSH 连接命令"
  value       = "ssh root@${qiniu_compute_instance.app.public_ip_addresses[0].ipv4}"
}
```

#### versions.tf

```hcl
terraform {
  required_version = ">= 1.0"

  required_providers {
    qiniu = {
      source  = "hashicorp/qiniu"   # 正确来源：hashicorp/qiniu，不是 qiniu/qiniu
      version = "~> 1.0.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"   # 不要写 ~> 3.6.0，平台只支持 ~> 3.0
    }
  }
}

provider "qiniu" {}    # 不要在 provider 块中硬编码 region；AppMarket 平台通过环境变量注入 region
provider "random" {}
```

> **Provider source 注意**：七牛 provider 的正确 source 是 `hashicorp/qiniu`，不是 `qiniu/qiniu`。可通过 [qiniu/terraform-module](https://github.com/qiniu/terraform-module) 仓库的 `versions.tf` 确认。
>
> **Provider 版本陷阱**：`hashicorp/random` 必须约束为 `~> 3.0`，不能写成 `~> 3.6.0`（平台仅提供 3.x 系列）。写错版本会导致 `terraform init` 失败。
>
> **本地测试 provider 安装**：本地运行 `terraform init` 时，`hashicorp/qiniu` 无法从公网下载，需配置 filesystem mirror：
> ```bash
> # 将 provider 二进制放入 mirror 目录
> mkdir -p ~/.terraform.d/plugin-mirror/registry.terraform.io/hashicorp/qiniu/1.0.0/linux_amd64/
> cp /path/to/terraform-provider-qiniu ~/.terraform.d/plugin-mirror/registry.terraform.io/hashicorp/qiniu/1.0.0/linux_amd64/
>
> # ~/.terraformrc 配置
> provider_installation {
>   filesystem_mirror {
>     path    = "/home/<user>/.terraform.d/plugin-mirror"
>     include = ["hashicorp/qiniu"]
>   }
>   direct {
>     exclude = ["hashicorp/qiniu"]
>   }
> }
> ```
> **不要在 `provider "qiniu" {}` 中硬编码 `region`**：AppMarket 运行时通过环境变量向模块注入 region，硬编码会导致跨区域部署失败。

---

## InputSchema 规范

### 基本类型映射

| JSON Schema 类型 | Terraform 类型 | 示例 |
|-----------------|---------------|------|
| `string` | `string` | `"ecs.t1.c2m4"` |
| `integer` | `number` | `20` |
| `number` | `number` | `3.14` |
| `boolean` | `bool` | `true` |
| `array` | `list` | `["a", "b"]` |
| `object` | `map` / `object` | `{"key": "value"}` |

### 常见属性定义

#### 1. 实例规格（枚举）

```json
{
  "instance_type": {
    "type": "string",
    "title": "实例规格",
    "description": "ECS 实例规格",
    "enum": [
      "ecs.t1.c2m4",
      "ecs.t1.c4m8",
      "ecs.t1.c8m16"
    ],
    "enumNames": [
      "通用型 - 2核4GB",
      "通用型 - 4核8GB",
      "通用型 - 8核16GB"
    ]
  }
}
```

#### 2. 整数范围

```json
{
  "system_disk_size": {
    "type": "integer",
    "title": "系统盘大小",
    "description": "系统盘大小（GiB）",
    "minimum": 10,
    "maximum": 500,
    "default": 20
  }
}
```

#### 3. 字符串长度和格式

```json
{
  "root_password": {
    "type": "string",
    "title": "实例密码",
    "description": "root 用户密码，至少 8 个字符",
    "minLength": 8,
    "maxLength": 30,
    "pattern": "^[a-zA-Z0-9@#$%^&*()_+=-]+$",
    "writeOnly": true
  }
}
```

#### 4. 布尔选项

```json
{
  "enable_monitoring": {
    "type": "boolean",
    "title": "启用监控",
    "description": "是否启用云监控服务",
    "default": true
  }
}
```

#### 5. 数组类型

```json
{
  "allowed_ips": {
    "type": "array",
    "title": "允许访问的 IP",
    "description": "允许 SSH 访问的 IP 地址列表",
    "items": {
      "type": "string",
      "pattern": "^\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}/\\d{1,2}$"
    },
    "default": ["0.0.0.0/0"]
  }
}
```

---

## InputPresets 规范

### 规格预设示例

> **Private 类型 App** 的 inputPresets **不需要 `regionPrices`**，定价由底层资源按量计费决定。以下示例适用于 **Managed 类型 App**。

```json
{
  "inputPresets": [
    {
      "name": "basic",
      "title": "普通版",
      "description": "适合个人开发者和小型项目",
      "inputs": {
        "instance_type": "ecs.t1.c2m4",
        "system_disk_size": 20,
        "internet_max_bandwidth": 10
      },
      "regionPrices": [
        {
          "regionIDs": ["cn-changshan-1"],
          "prices": [
            {
              "costPeriodUnit": "Month",
              "priceCNY": "79.00",
              "originalPriceCNY": "99.00"
            },
            {
              "costPeriodUnit": "Year",
              "priceCNY": "799.00",
              "originalPriceCNY": "999.00"
            }
          ]
        }
      ]
    },
    {
      "name": "pro",
      "title": "专业版",
      "description": "适合企业用户和生产环境",
      "inputs": {
        "instance_type": "ecs.t1.c4m8",
        "system_disk_size": 50,
        "internet_max_bandwidth": 20
      },
      "regionPrices": [
        {
          "regionIDs": ["cn-changshan-1"],
          "prices": [
            {
              "costPeriodUnit": "Month",
              "priceCNY": "199.00",
              "originalPriceCNY": "249.00"
            }
          ]
        }
      ]
    }
  ]
}
```

### 价格配置说明

**字段说明：**

- `costPeriodUnit`: 计费周期，支持 `Month` / `Year`
- `priceCNY`: 人民币价格（促销价）
- `originalPriceCNY`: 人民币原价
- `priceUSD`: 美元价格（可选）
- `originalPriceUSD`: 美元原价（可选）

---

## 完整示例：MySQL 数据库应用

### DeployMeta 配置

```json
{
  "inputSchema": {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["instance_type", "root_password", "database_name"],
    "properties": {
      "instance_type": {
        "type": "string",
        "title": "实例规格",
        "enum": ["ecs.t1.c2m4", "ecs.t1.c4m8", "ecs.t1.c8m16"]
      },
      "system_disk_size": {
        "type": "integer",
        "title": "系统盘大小",
        "minimum": 20,
        "maximum": 500,
        "default": 50
      },
      "root_password": {
        "type": "string",
        "title": "Root 密码",
        "minLength": 8,
        "writeOnly": true
      },
      "database_name": {
        "type": "string",
        "title": "数据库名称",
        "pattern": "^[a-zA-Z][a-zA-Z0-9_]*$",
        "default": "mydb"
      },
      "max_connections": {
        "type": "integer",
        "title": "最大连接数",
        "minimum": 100,
        "maximum": 10000,
        "default": 1000
      }
    }
  },
  "terraformModule": {
    "gitSource": {
      "repo": "https://github.com/org/terraform-mysql",
      "ref": "v1.0.0",
      "directory": ""
    }
  },
  "inputPresets": [
    {
      "name": "small",
      "title": "小型数据库",
      "inputs": {
        "instance_type": "ecs.t1.c2m4",
        "system_disk_size": 50,
        "max_connections": 500
      },
      "regionPrices": [
        {
          "regionIDs": ["cn-changshan-1"],
          "prices": [
            {
              "costPeriodUnit": "Month",
              "priceCNY": "99.00"
            }
          ]
        }
      ]
    },
    {
      "name": "medium",
      "title": "中型数据库",
      "inputs": {
        "instance_type": "ecs.t1.c4m8",
        "system_disk_size": 100,
        "max_connections": 2000
      },
      "regionPrices": [
        {
          "regionIDs": ["cn-changshan-1"],
          "prices": [
            {
              "costPeriodUnit": "Month",
              "priceCNY": "299.00"
            }
          ]
        }
      ]
    }
  ]
}
```

### Terraform 模块 (main.tf)

```hcl
resource "qiniu_compute_instance" "mysql" {
  instance_type    = var.instance_type
  image_id         = "img-mysql-8.0"
  system_disk_size = var.system_disk_size

  # moduleContent 模式：脚本必须内联
  user_data = base64encode(<<-USERDATA
#!/bin/bash
set -euo pipefail
# MySQL 初始化脚本
MYSQL_PASSWORD="${var.root_password}"
MYSQL_DB="${var.database_name}"
MAX_CONN=${var.max_connections}
# ... 初始化逻辑
USERDATA
  )

  description = "MySQL Database - Managed by AppMarket"
}
```

---

## 最佳实践

### 1. 变量验证

使用 `validation` 块确保输入合法：

```hcl
variable "instance_type" {
  type = string

  validation {
    condition     = can(regex("^ecs\\.", var.instance_type))
    error_message = "instance_type 必须以 'ecs.' 开头"
  }
}
```

### 2. 版本锁定

明确 Provider 和 Terraform 版本约束：

```hcl
terraform {
  required_version = ">= 1.0"

  required_providers {
    qiniu = {
      source  = "hashicorp/qiniu"   # 正确来源：hashicorp/qiniu，不是 qiniu/qiniu
      version = "~> 1.0.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "qiniu" {}
provider "random" {}
```

> **注意**：`hashicorp/random` 必须约束为 `~> 3.0`，不能写成 `~> 3.6.0`（平台只提供 3.x 系列）。

### 3. 不要硬编码 region

`provider "qiniu" {}` 中**不能**指定 `region`；AppMarket 平台通过环境变量将 region 注入 Terraform 运行上下文。硬编码 region 会导致跨区域部署失败，且 AppMarket 会收到未声明变量的警告。

```hcl
# ✅ 正确
provider "qiniu" {}

# ❌ 错误：不要硬编码
provider "qiniu" {
  region = "ap-northeast-1"
}
```

### 4. 区域磁盘类型差异

不同区域支持的磁盘类型不同，务必在模块中明确声明 `system_disk_type`：

```hcl
resource "qiniu_compute_instance" "app" {
  system_disk_type = "local.ssd"   # cn-hongkong-1 等区域需要 local.ssd
  system_disk_size = var.system_disk_size
  ...
}
```

> 若不指定或指定了区域不支持的磁盘类型，Terraform apply 会报 400 错误。

### 5. 敏感信息处理

```hcl
# 变量定义
variable "database_password" {
  type      = string
  sensitive = true
}

# 输出定义
output "admin_password" {
  value     = random_password.admin.result
  sensitive = true
}
```

### 4. 文档完善

README.md 必须包含：
- 模块功能说明
- 所有输入变量及其说明
- 所有输出变量及其说明
- 使用示例
- 依赖的 Provider 版本

---

## 参考资料

- [OpenTofu 语法文档](https://opentofu.org/docs/) — Terraform/OpenTofu HCL 语法、函数、内置资源参考
- [七牛云 Terraform Provider 模块示例](https://github.com/qiniu/terraform-module/) — 官方示例，包含 Provider 用法和资源定义
- [七牛云开发者文档（LAS）](https://developer.qiniu.com/las) — 云主机、镜像、实例等 API 文档
- [变量定义规范](references/variables.md)
- [输出定义规范](references/outputs.md)
- [资源定义示例](references/resources.md)
- [类型映射表](references/type-mapping.md)
