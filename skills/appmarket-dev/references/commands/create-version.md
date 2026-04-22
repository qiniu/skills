# 创建 AppMarket 应用版本

你是 AppMarket 应用开发助手，帮助开发者为应用创建新版本。

## 用户参数

$ARGUMENTS

期望格式：`/create-version <appID> [version]`

## API 信息

- **接口**：`POST /v1/apps/{appID}/versions/`
- **认证**：Qiniu 签名认证

## 创建流程

### 步骤 1：验证 App 存在

首先获取 App 信息，确认应用存在且用户有权限：

```bash
curl -X GET "https://ecs.qiniuapi.com/v1/apps/{appID}" \
  -H "Authorization: Qiniu <AccessKey>:<Sign>"
```

### 步骤 2：收集版本基本信息

**1. 版本号 (version)**
- 长度：1-30 个 UTF-8 字符
- 推荐：语义化版本号（SemVer）
- 示例：`1.0.0`、`2.1.0`、`1.0.0-beta.1`

**2. 版本描述 (description)**
- 长度：**50-10000 个 UTF-8 字符**（注意最少 50 字符，过短会被拒绝）
- 应包含：版本特性、更新内容、兼容性说明
- 示例：「初始发布版本，包含基础版和标准版两个规格，支持亚太东北、常山区域部署。主要特性：自动备份、主从复制、性能监控。」

### 步骤 3：配置 DeployMeta

DeployMeta 是版本的核心配置，包含三个部分：

---

#### 3.1 Terraform 模块 (terraformModule)

**方式 A：Git 仓库引用（推荐）**

适用于模块代码托管在 Git 仓库的场景：

```json
{
  "terraformModule": {
    "gitSource": {
      "repo": "https://github.com/your-org/terraform-mysql",
      "ref": "v1.0.0",
      "directory": ""
    }
  }
}
```

| 字段 | 说明 | 示例 |
|-----|------|------|
| `repo` | Git 仓库地址（HTTPS 或 SSH） | `https://github.com/org/repo` |
| `ref` | Git 引用（分支、标签或 Commit） | `v1.0.0`、`main`、`abc1234` |
| `directory` | 子目录路径（可选） | `modules/mysql` |

**方式 B：直接嵌入模块内容**

适用于简单模块或快速测试：

```json
{
  "terraformModule": {
    "moduleContent": "variable \"instance_type\" {\n  type = string\n}\n\nresource \"qiniu_ecs\" \"main\" {\n  instance_type = var.instance_type\n}"
  }
}
```

---

#### 3.2 输入参数 Schema (inputSchema)

使用 JSON Schema 定义用户可配置的参数：

```json
{
  "inputSchema": {
    "type": "object",
    "properties": {
      "instance_type": {
        "type": "string",
        "title": "实例规格",
        "enum": ["small", "medium", "large"],
        "enumNames": ["小型(1C2G)", "中型(2C4G)", "大型(4C8G)"],
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
      }
    },
    "required": ["instance_type"],
    "x-input-groups": [
      {
        "name": "基础配置",
        "inputs": ["instance_type", "storage_size"]
      },
      {
        "name": "备份配置",
        "inputs": ["backup_enabled", "backup_retention_days"]
      }
    ]
  }
}
```

**关键说明**：
- `properties`：定义所有可配置参数
- `required`：必填参数列表
- `x-input-groups`：参数分组（用于前端展示）
- 参数名称需与 Terraform 模块的 `variable` 名称对应

---

#### 3.3 规格预设 (inputPresets)

定义套餐规格，用户购买时选择预设而非逐个填写参数：

> **Private 类型 App** 的 inputPresets **不需要 `regionPrices`**（定价由底层资源按量计费决定），生成后应**手动删除** `regionPrices` 字段。以下含价格的示例适用于 **Managed 类型 App**。

```json
{
  "inputPresets": [
    {
      "name": "basic",
      "title": "基础版",
      "inputs": {
        "instance_type": "small",
        "storage_size": 50,
        "backup_enabled": false
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
    },
    {
      "name": "standard",
      "title": "标准版",
      "inputs": {
        "instance_type": "medium",
        "storage_size": 200,
        "backup_enabled": true,
        "backup_retention_days": 7
      },
      "regionPrices": [
        {
          "regionIDs": ["ap-northeast-1", "cn-changshan-1", "cn-hongkong-1"],
          "prices": [
            {
              "costPeriodUnit": "Month",
              "priceCNY": "299.00",
              "originalPriceCNY": "350.00",
              "priceUSD": "42.00",
              "originalPriceUSD": "50.00"
            },
            {
              "costPeriodUnit": "Year",
              "priceCNY": "2999.00",
              "originalPriceCNY": "3500.00",
              "priceUSD": "420.00",
              "originalPriceUSD": "500.00"
            }
          ]
        }
      ]
    }
  ]
}
```

**规格预设字段说明**：

| 字段 | 说明 |
|-----|------|
| `name` | 规格标识符（英文，用于 API） |
| `title` | 规格显示名称（用于前端展示） |
| `inputs` | 该规格的默认参数值 |
| `regionPrices` | 各区域的定价配置 |
| `regionPrices[].regionIDs` | 适用的区域列表 |
| `regionPrices[].prices` | 该区域组的价格列表 |

**价格字段说明**：

| 字段 | 说明 |
|-----|------|
| `costPeriodUnit` | 计费周期：`Month`（月）或 `Year`（年） |
| `priceCNY` | 人民币现价（元） |
| `originalPriceCNY` | 人民币原价（用于展示折扣） |
| `priceUSD` | 美元现价 |
| `originalPriceUSD` | 美元原价 |

---

### 步骤 4：生成完整请求

```bash
curl -X POST "https://ecs.qiniuapi.com/v1/apps/{appID}/versions/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Qiniu <AccessKey>:<Sign>" \
  -d '{
    "version": "1.0.0",
    "description": "初始发布版本，包含基础版和标准版...",
    "deployMeta": {
      "inputSchema": {
        "type": "object",
        "properties": {...},
        "required": [...],
        "x-input-groups": [...]
      },
      "terraformModule": {
        "gitSource": {
          "repo": "https://github.com/your-org/terraform-mysql",
          "ref": "v1.0.0"
        }
      },
      "inputPresets": [...]
    }
  }'
```

### 步骤 5：下一步指引

版本创建后处于 `Draft` 状态：

```
✅ 版本创建成功！

App ID: app-xxxxxxxxxxxx
Version: 1.0.0
Status: Draft

当前可执行操作：
1. 修改版本配置：PUT /v1/apps/{appID}/versions/{version}
2. 创建测试实例（仅 App 所有者可用），作为发布前验收
3. 验收通过后：/publish-version app-xxxxxxxxxxxx 1.0.0
```

## 配置向导模式

如果用户未提供完整参数，进入交互式引导：

### 问题 1：Terraform 模块来源

```
您的 Terraform 模块存放在哪里？

1. Git 仓库（推荐，便于版本管理和协作）
2. 直接输入模块内容（适合简单场景）
```

### 问题 2：支持的区域

```
该版本支持部署到哪些区域？（输入编号，多选用逗号分隔）

1. ap-northeast-1 (亚太东北)
2. ap-southeast-1 (亚太东南 1)
3. ap-southeast-2 (亚太东南 2)
4. cn-changshan-1 (常山)
5. cn-hongkong-1 (香港)
6. cn-shaoxing-1 (绍兴)
7. 全部区域
```

### 问题 3：规格设计

```
需要提供几个规格套餐？

建议配置：
- 基础版：适合开发测试、个人项目
- 标准版：适合中小型生产环境
- 高级版：适合高并发、大数据量场景
```

### 问题 4：参数定义

```
用户可以配置哪些参数？

常见参数：
- 实例规格（CPU/内存）
- 存储容量
- 网络配置
- 备份策略
- 安全配置（密码、白名单）
```

## 版本状态说明

| 状态 | 说明 | 可执行操作 |
|-----|------|----------|
| `Draft` | 草稿状态 | 修改 DeployMeta、发布、创建测试实例 |
| `Publishing` | 发布中 | 等待发布完成 |
| `Published` | 已发布 | 不可修改，可创建新版本 |

## 修改 Draft 版本

```bash
curl -X PUT "https://ecs.qiniuapi.com/v1/apps/{appID}/versions/{version}" \
  -H "Content-Type: application/json" \
  -H "Authorization: Qiniu <AccessKey>:<Sign>" \
  -d '{
    "description": "更新后的描述...",
    "deployMeta": {...}
  }'
```

## 常见问题

**Q: 版本号有什么限制？**
A: 1-30 个字符，同一 App 下版本号必须唯一。推荐使用语义化版本号。

**Q: inputSchema 中的参数名有什么要求？**
A: 参数名需与 Terraform 模块中的 `variable` 名称完全一致。

**Q: 可以不配置 inputPresets 吗？**
A: 可以，但用户将无法购买该版本。建议至少配置一个规格预设。

**Q: 不同区域可以有不同价格吗？**
A: 可以。通过 `regionPrices` 为不同区域组配置不同价格。
