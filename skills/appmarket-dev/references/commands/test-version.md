# test-version

测试 AppMarket Draft 版本，创建测试实例并验证部署功能。

> **命令说明**：`/test-version` 是 Claude Code 斜杠命令的简写，底层调用的是：
> ```bash
> python3 scripts/appmarket-cli.py test-version --app-id <appID> --version <version> [options]
> ```
> 两种方式等价，本文档中的 `/test-version` 示例均可替换为上述 CLI 命令。

---

## 用法

```bash
/test-version <appID> <version> [options]
```

## 参数

| 参数 | 必需 | 说明 | 示例 |
|-----|------|------|------|
| `appID` | 是 | 应用 ID | `app-xxxxxxxxxxxx` |
| `version` | 是 | 版本号（必须是 Draft 状态） | `1.0.0`, `1.0.0-draft` |
| `--region` | 否 | 部署区域 | `ap-northeast-1`（默认） |
| `--inputs` | 否 | 输入参数 JSON 文件路径 | `test-inputs.json` |
| `--wait` | 否 | 等待实例部署完成 | 默认启用 |
| `--cleanup` | 否 | 测试完成后自动删除实例 | 默认禁用 |

---

## 快速开始

### 1. 基本测试

使用默认参数测试 Draft 版本：

```bash
/test-version app-xxxxxxxxxxxx 1.0.0
```

命令会自动：
1. 检查版本是否为 Draft 状态
2. 使用 InputSchema 中的默认值创建测试实例
3. 监控部署进度，输出实例状态和 outputs
4. 部署完成（或失败）后打印摘要；**实例不会自动删除**，需手动调用 `delete-instance` 清理，或在测试时加 `--cleanup`

### 2. 自定义参数测试

使用自定义输入参数：

```bash
# 创建输入参数文件
cat > test-inputs.json <<EOF
{
  "instance_name": "test-mysql",
  "instance_type": "ecs.c1.c2m4",
  "system_disk_size": 50,
  "mysql_username": "admin",
  "mysql_password": "<YourPassword>",
  "mysql_db_name": "testdb"
}
EOF

# 执行测试
/test-version app-xxxxxxxxxxxx 1.0.0 --inputs test-inputs.json
```

### 3. 自动清理模式

测试完成后自动删除实例：

```bash
/test-version app-xxxxxxxxxxxx 1.0.0 --cleanup
```

> **注意**：`--cleanup` 仅在部署**成功**后自动删除实例。部署失败时始终保留实例，供 SSH 进去查看 cloud-init 日志排查问题；排查完毕后用 `delete-instance` 手动清理：
> ```bash
> python3 scripts/appmarket-cli.py delete-instance \
>   --instance-id appi-xxxxxxxxxxxx --region ap-northeast-1
> ```

---

## 错误处理

### 版本不是 Draft 状态

```
✗ 错误: 版本 1.0.0 状态为 Published，只能测试 Draft 版本

建议:
  1. 创建新的 Draft 版本进行测试
  2. 或使用现有的 Draft 版本
```

### 必需参数缺失

```
✗ 错误: InputSchema 中有必需参数但未提供默认值

缺失参数:
  - mysql_password (type: string, required: true)

解决方法:
  1. 在 InputSchema 中为必需参数添加默认值
  2. 或使用 --inputs 参数提供输入文件
```

### 区域不可用

```
✗ 错误: 指定的区域 'cn-west-1' 不可用

可用区域:
  - ap-northeast-1 (亚太东北)
  - ap-southeast-1 (亚太东南 1)
  - ap-southeast-2 (亚太东南 2)
  - cn-changshan-1 (常山)
  - cn-hongkong-1 (香港)
  - cn-shaoxing-1 (绍兴)
```

### 配额不足

```
✗ 错误: 配额不足

当前配额:
  CPU: 8 核 (已用: 6 核)
  内存: 16 GB (已用: 12 GB)
  磁盘: 500 GB (已用: 450 GB)

请求配额:
  CPU: 4 核
  内存: 8 GB
  磁盘: 100 GB

建议:
  1. 删除不使用的实例释放配额
  2. 联系技术支持申请配额提升
```

### RFSNotEnabled [403]

```
Error: RFSNotEnabled [403]
```

当前区域不支持该 App 部署。处理方式：

- **换一个支持的区域**重试（见"支持区域"列表）。
- 如果所有目标区域均报此错误，说明该账号所在区域暂不支持 AppMarket，联系七牛技术支持确认。
- 如果急于上线且无法等待，可以在确认本地 `terraform validate/plan` 通过、DeployMeta 结构正确后，**由负责人确认跳过 test-version**，直接 `publish-version`。但此选项风险自担：用户部署时若失败，已是 Published 状态，只能发新版本修复。

---

## 使用场景

### 1. 测试不同规格

```bash
# 测试入门规格
cat > test-basic.json <<EOF
{
  "instance_type": "ecs.t1.c1m2",
  "system_disk_size": 20
}
EOF
/test-version app-xxx 1.0.0 --inputs test-basic.json --cleanup

# 测试标准规格
cat > test-standard.json <<EOF
{
  "instance_type": "ecs.c1.c2m4",
  "system_disk_size": 50
}
EOF
/test-version app-xxx 1.0.0 --inputs test-standard.json --cleanup

# 测试高配规格
cat > test-pro.json <<EOF
{
  "instance_type": "ecs.c1.c8m16",
  "system_disk_size": 200
}
EOF
/test-version app-xxx 1.0.0 --inputs test-pro.json --cleanup
```

### 2. 测试不同区域

```bash
# 亚太东北
/test-version app-xxx 1.0.0 --region ap-northeast-1 --cleanup

# 常山
/test-version app-xxx 1.0.0 --region cn-changshan-1 --cleanup

# 香港
/test-version app-xxx 1.0.0 --region cn-hongkong-1 --cleanup
```

### 3. 保留实例进行手动验证

```bash
# 不自动删除，手动验证功能
/test-version app-xxx 1.0.0

# 验证后手动删除
python3 scripts/appmarket-cli.py delete-instance \
  --instance-id appi-xxxxxxxxxxxx --region ap-northeast-1
```

### 4. test-version 超时或被中断后恢复

`test-version` 如果在轮询中超时或被 Ctrl-C 中断，实例仍在继续部署。此时可用 `wait-instance` 恢复轮询而无需重新部署：

```bash
python3 scripts/appmarket-cli.py wait-instance \
  --app-id app-xxxxxxxxxxxx \
  --instance-id appi-xxxxxxxxxxxx \
  --region ap-northeast-1
```

> `--timeout` 参数可调整最长等待秒数（默认 600 秒）。恢复轮询成功后，结果同 `test-version` 正常完成。

---

## 相关命令

| 命令 | 说明 |
|-----|------|
| `/create-version` | 创建新版本 |
| `/publish-version` | 发布版本 |
| 本地测试脚本 | `scripts/test-module.sh` |

---

## 相关资源

- [模块测试指南](../module-testing.md)
- [本地测试脚本](../scripts/test-module.sh)
- [AppMarket API 文档](../README.md#api-端点)
