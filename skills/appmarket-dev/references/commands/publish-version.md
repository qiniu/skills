# 发布 AppMarket 应用版本

你是 AppMarket 应用开发助手，帮助开发者发布应用版本。

## 用户参数

$ARGUMENTS

期望格式：`/publish-version <appID> <version>`

## API 信息

- **接口**：`POST /v1/apps/{appID}/versions/{version}/publish`
- **认证**：Qiniu 签名认证

## 发布流程

### 步骤 1：获取版本信息

发布前，获取并展示版本详情供用户确认：

```bash
curl -X GET "https://ecs.qiniuapi.com/v1/apps/{appID}/versions/{version}" \
  -H "Authorization: Qiniu <AccessKey>:<Sign>"
```

### 步骤 2：展示确认信息

以清晰格式展示版本配置：

```
═══════════════════════════════════════════
        版本发布确认
═══════════════════════════════════════════

App ID:      app-xxxxxxxxxxxx
版本号:      1.0.0
当前状态:    Draft
版本描述:    初始发布版本...

───────────────────────────────────────────
Terraform 模块
───────────────────────────────────────────
来源:        Git 仓库
仓库地址:    https://github.com/your-org/terraform-mysql
Git Ref:     v1.0.0

───────────────────────────────────────────
规格配置 (共 2 个)
───────────────────────────────────────────
┌──────────┬────────┬─────────────┬─────────────┐
│ 规格     │ 名称   │ 月价格(CNY) │ 年价格(CNY) │
├──────────┼────────┼─────────────┼─────────────┤
│ basic    │ 基础版 │ ¥99         │ ¥999        │
│ standard │ 标准版 │ ¥299        │ ¥2999       │
└──────────┴────────┴─────────────┴─────────────┘

───────────────────────────────────────────
支持区域
───────────────────────────────────────────
• ap-northeast-1 (亚太东北)
• cn-changshan-1 (常山)

═══════════════════════════════════════════
```

### 步骤 3：发布前检查清单

提醒用户确认以下事项：

```
📋 发布前检查清单：

[ ] Terraform 模块已在目标区域测试通过
[ ] InputSchema 参数定义完整且正确
[ ] Managed App：所有规格预设的价格已配置；Private App：已移除 regionPrices
[ ] 支持的区域列表已确认
[ ] 版本描述准确清晰（>= 50 字符）

⚠️  重要提醒：
• 发布后版本配置将被锁定，无法修改
• 如需更改，必须创建新版本
• 建议先使用 Draft 版本创建测试实例验证
```

### 步骤 4：执行发布

用户确认后，执行发布：

```bash
curl -X POST "https://ecs.qiniuapi.com/v1/apps/{appID}/versions/{version}/publish" \
  -H "Authorization: Qiniu <AccessKey>:<Sign>"
```

**成功响应** (HTTP 200)：无响应体

### 步骤 5：查询发布状态

发布是异步过程，需要轮询状态：

```bash
# 查询版本状态
curl -X GET "https://ecs.qiniuapi.com/v1/apps/{appID}/versions/{version}" \
  -H "Authorization: Qiniu <AccessKey>:<Sign>"
```

**状态流转**：
```
Draft → Publishing → Published
              ↓
        (失败时保持 Publishing，需排查)
```

### 步骤 6：发布结果

**发布成功**：
```
✅ 版本发布成功！

App ID:      app-xxxxxxxxxxxx
Version:     1.0.0
Status:      Published
发布时间:    2024-01-15T10:30:00Z

该版本现已对用户可见，可以被购买和部署。

后续操作：
• 查看版本详情：GET /v1/apps/{appID}/versions/{version}
• 创建新版本：/create-version app-xxxxxxxxxxxx
• 查看实例列表：GET /v1/app-instances/?appID={appID}
```

**发布中**：
```
⏳ 版本正在发布中...

App ID:      app-xxxxxxxxxxxx
Version:     1.0.0
Status:      Publishing

系统正在生成价格表，请稍候...
可使用以下命令查询状态：

curl -X GET "https://ecs.qiniuapi.com/v1/apps/{appID}/versions/{version}" \
  -H "Authorization: Qiniu <AccessKey>:<Sign>"
```

## 发布失败处理

如果版本长时间停留在 `Publishing` 状态：

1. **检查价格配置**：确保所有规格的价格配置完整
2. **检查区域有效性**：确保 regionIDs 中的区域都是有效的
3. **联系支持**：如果问题持续，请联系平台技术支持

## 快速示例

```bash
# 发布指定版本
/publish-version app-xxxxxxxxxxxx 1.0.0

# 发布前先查看版本详情
curl -X GET "https://ecs.qiniuapi.com/v1/apps/app-xxxxxxxxxxxx/versions/1.0.0" \
  -H "Authorization: Qiniu <AccessKey>:<Sign>"
```

## 发布后注意事项

### 1. 版本不可变

已发布版本的以下内容无法修改：
- 版本号
- DeployMeta（inputSchema、terraformModule、inputPresets）
- 价格配置

如需更改，必须创建新版本。

### 2. 实例升级

用户已创建的实例不会自动升级到新版本。需要：
- 用户主动选择升级
- 或在新版本中提供升级路径说明

### 3. 版本下线

目前不支持下线已发布版本。如需停止销售：
- 将价格设置为极高值（不推荐）
- 联系平台进行下线处理

## 常见问题

**Q: 发布需要多长时间？**
A: 通常几秒到几分钟，取决于规格数量和区域数量。

**Q: 发布失败会有什么影响？**
A: 版本会保持 `Publishing` 状态，不会影响已有版本。可以修复问题后重试。

**Q: 可以同时发布多个版本吗？**
A: 可以，不同版本的发布互不影响。

**Q: 发布后如何撤销？**
A: 不支持撤销。如果发现问题，请尽快创建修复版本。
