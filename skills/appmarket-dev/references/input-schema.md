# InputSchema 编写指南

当用户需要配置 InputSchema 时，提供以下指导。

## 概述

InputSchema 使用 [JSON Schema](https://json-schema.org/) 格式定义用户可配置的参数。这些参数会传递给 Terraform 模块作为变量输入。

## 基础结构

```json
{
  "type": "object",
  "properties": {
    // 参数定义
  },
  "required": [
    // 必填参数列表
  ],
  "x-input-groups": [
    // 参数分组（AppMarket 扩展）
  ]
}
```

## 支持的数据类型

### string - 字符串

```json
{
  "instance_name": {
    "type": "string",
    "title": "实例名称",
    "description": "用于标识实例的名称",
    "minLength": 2,
    "maxLength": 64,
    "pattern": "^[a-zA-Z][a-zA-Z0-9-]*$",
    "default": "my-instance"
  }
}
```

**常用约束**：
- `minLength` / `maxLength`：长度限制
- `pattern`：正则表达式
- `enum`：枚举值
- `default`：默认值

### string (枚举)

```json
{
  "instance_type": {
    "type": "string",
    "title": "实例规格",
    "enum": ["small", "medium", "large", "xlarge"],
    "enumNames": ["小型(1C2G)", "中型(2C4G)", "大型(4C8G)", "超大(8C16G)"],
    "default": "medium",
    "description": "选择实例的计算规格"
  }
}
```

**说明**：
- `enum`：有效值列表（传递给 Terraform）
- `enumNames`：显示名称（前端展示用，与 enum 一一对应）

### integer - 整数

```json
{
  "storage_size": {
    "type": "integer",
    "title": "存储容量(GB)",
    "minimum": 20,
    "maximum": 2000,
    "default": 100,
    "description": "SSD 云盘存储容量"
  },
  "port": {
    "type": "integer",
    "title": "服务端口",
    "minimum": 1024,
    "maximum": 65535,
    "default": 3306
  }
}
```

**常用约束**：
- `minimum` / `maximum`：数值范围
- `exclusiveMinimum` / `exclusiveMaximum`：不包含边界值
- `multipleOf`：倍数约束

### number - 数字（含小数）

```json
{
  "cpu_limit": {
    "type": "number",
    "title": "CPU 限制(核)",
    "minimum": 0.5,
    "maximum": 64,
    "default": 2,
    "description": "容器 CPU 资源限制"
  }
}
```

### boolean - 布尔值

```json
{
  "backup_enabled": {
    "type": "boolean",
    "title": "启用自动备份",
    "default": true,
    "description": "是否启用每日自动备份"
  },
  "public_access": {
    "type": "boolean",
    "title": "公网访问",
    "default": false,
    "description": "是否允许公网访问"
  }
}
```

### array - 数组

```json
{
  "whitelist_ips": {
    "type": "array",
    "title": "IP 白名单",
    "items": {
      "type": "string",
      "pattern": "^\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}(/\\d{1,2})?$"
    },
    "minItems": 0,
    "maxItems": 20,
    "uniqueItems": true,
    "default": [],
    "description": "允许访问的 IP 地址或 CIDR"
  }
}
```

**常用约束**：
- `items`：数组元素的类型定义
- `minItems` / `maxItems`：数组长度限制
- `uniqueItems`：元素是否唯一

### object - 对象（嵌套配置）

```json
{
  "advanced_config": {
    "type": "object",
    "title": "高级配置",
    "properties": {
      "max_connections": {
        "type": "integer",
        "title": "最大连接数",
        "default": 1000
      },
      "timeout": {
        "type": "integer",
        "title": "超时时间(秒)",
        "default": 30
      }
    }
  }
}
```

## AppMarket 扩展字段

### x-input-groups - 参数分组

用于前端将参数分组展示：

```json
{
  "x-input-groups": [
    {
      "name": "基础配置",
      "inputs": ["instance_type", "storage_size"]
    },
    {
      "name": "网络配置",
      "inputs": ["vpc_id", "subnet_id", "public_access"]
    },
    {
      "name": "安全配置",
      "inputs": ["admin_password", "whitelist_ips"]
    },
    {
      "name": "备份配置",
      "inputs": ["backup_enabled", "backup_retention_days"]
    }
  ]
}
```

**注意**：`inputs` 中的参数名必须在 `properties` 中定义。

## 完整示例

### MySQL 服务的 InputSchema

```json
{
  "type": "object",
  "properties": {
    "instance_type": {
      "type": "string",
      "title": "实例规格",
      "enum": ["small", "medium", "large", "xlarge"],
      "enumNames": ["小型(1C2G)", "中型(2C4G)", "大型(4C8G)", "超大型(8C16G)"],
      "description": "数据库实例的计算规格"
    },
    "storage_size": {
      "type": "integer",
      "title": "存储容量(GB)",
      "minimum": 20,
      "maximum": 2000,
      "default": 100,
      "description": "SSD 云盘存储容量"
    },
    "mysql_version": {
      "type": "string",
      "title": "MySQL 版本",
      "enum": ["5.7", "8.0"],
      "default": "8.0",
      "description": "MySQL 数据库版本"
    },
    "admin_password": {
      "type": "string",
      "title": "管理员密码",
      "minLength": 8,
      "maxLength": 32,
      "pattern": "^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d).+$",
      "description": "Root 用户密码，必须包含大小写字母和数字"
    },
    "backup_enabled": {
      "type": "boolean",
      "title": "启用自动备份",
      "default": true,
      "description": "是否启用每日自动备份"
    },
    "backup_retention_days": {
      "type": "integer",
      "title": "备份保留天数",
      "minimum": 1,
      "maximum": 30,
      "default": 7,
      "description": "自动备份的保留天数"
    },
    "whitelist_ips": {
      "type": "array",
      "title": "IP 白名单",
      "items": {
        "type": "string"
      },
      "default": ["0.0.0.0/0"],
      "description": "允许访问的 IP 地址列表"
    }
  },
  "required": ["instance_type", "admin_password"],
  "x-input-groups": [
    {
      "name": "实例配置",
      "inputs": ["instance_type", "storage_size", "mysql_version"]
    },
    {
      "name": "备份配置",
      "inputs": ["backup_enabled", "backup_retention_days"]
    },
    {
      "name": "安全配置",
      "inputs": ["admin_password", "whitelist_ips"]
    }
  ]
}
```

### Redis 服务的 InputSchema

```json
{
  "type": "object",
  "properties": {
    "instance_type": {
      "type": "string",
      "title": "实例规格",
      "enum": ["1g", "2g", "4g", "8g", "16g"],
      "enumNames": ["1GB", "2GB", "4GB", "8GB", "16GB"],
      "description": "Redis 内存容量"
    },
    "redis_version": {
      "type": "string",
      "title": "Redis 版本",
      "enum": ["6.0", "7.0"],
      "default": "7.0"
    },
    "cluster_mode": {
      "type": "boolean",
      "title": "集群模式",
      "default": false,
      "description": "是否启用 Redis Cluster 模式"
    },
    "replica_count": {
      "type": "integer",
      "title": "副本数",
      "minimum": 0,
      "maximum": 5,
      "default": 1,
      "description": "只读副本数量"
    },
    "auth_password": {
      "type": "string",
      "title": "访问密码",
      "minLength": 8,
      "maxLength": 64,
      "description": "Redis 访问密码"
    }
  },
  "required": ["instance_type", "auth_password"],
  "x-input-groups": [
    {
      "name": "基础配置",
      "inputs": ["instance_type", "redis_version"]
    },
    {
      "name": "高可用配置",
      "inputs": ["cluster_mode", "replica_count"]
    },
    {
      "name": "安全配置",
      "inputs": ["auth_password"]
    }
  ]
}
```

## 与 Terraform 的关系

InputSchema 中的参数会传递给 Terraform 模块的 variables。

**命名约定**：InputSchema 的 property 名称必须与 Terraform variable 名称完全一致。

```json
// InputSchema
{
  "properties": {
    "instance_type": { "type": "string" },
    "storage_size": { "type": "integer" }
  }
}
```

```hcl
# Terraform variables.tf
variable "instance_type" {
  type        = string
  description = "Instance type"
}

variable "storage_size" {
  type        = number
  description = "Storage size in GB"
}
```

## 最佳实践

1. **必填参数最小化**：只将真正必要的参数设为 required
2. **提供合理默认值**：减少用户填写负担
3. **清晰的描述**：每个参数都应有明确的 description
4. **合理的分组**：使用 x-input-groups 将相关参数分组
5. **参数验证**：使用 pattern、minimum、maximum 等约束确保输入合法
6. **枚举优于自由输入**：对于有限选项，使用 enum 而非自由字符串
7. **密码字段复杂度**：云主机密码字段必须在 description 中告知用户，且在 Terraform `variables.tf` 中用 `precondition` 做前置校验。Qiniu API 要求密码至少满足以下 4 类中的 3 类：大写字母、小写字母、数字、特殊字符。示例合法密码：`Test@1234`。

   ```json
   "root_password": {
     "type": "string",
     "title": "实例密码",
     "minLength": 8,
     "maxLength": 32,
     "description": "云主机 root 密码，须包含大写字母、小写字母、数字、特殊字符中的至少 3 种"
   }
   ```
