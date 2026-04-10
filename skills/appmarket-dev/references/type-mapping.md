# 类型映射

JSON Schema 类型与 Terraform 类型的对应关系。

## 类型对应表

| JSON Schema 类型 | Terraform 类型 | 说明 |
|-----------------|---------------|------|
| `string` | `string` | 字符串 |
| `integer` | `number` | 整数（Terraform 无单独整数类型） |
| `number` | `number` | 数字（含小数） |
| `boolean` | `bool` | 布尔值 |
| `array` | `list(...)` 或 `set(...)` | 数组 |
| `object` | `object({...})` 或 `map(...)` | 对象 |

## 枚举处理

InputSchema 的 `enum` 对应 Terraform 的 `validation` 块：

```json
// InputSchema
{
  "properties": {
    "instance_type": {
      "type": "string",
      "enum": ["small", "medium", "large"]
    }
  }
}
```

```hcl
# Terraform
variable "instance_type" {
  type        = string
  description = "Instance type"

  validation {
    condition     = contains(["small", "medium", "large"], var.instance_type)
    error_message = "Must be small, medium, or large."
  }
}
```

## 默认值处理

```json
// InputSchema
{
  "properties": {
    "storage_size": {
      "type": "integer",
      "default": 100
    }
  }
}
```

```hcl
# Terraform
variable "storage_size" {
  type        = number
  description = "Storage size in GB"
  default     = 100
}
```