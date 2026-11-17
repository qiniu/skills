# 状态、日志和指标

先记录沙箱 ID、模板／构建 ID、端点、时间窗口和失败操作。状态详情、平台日志、资源指标与命令 stdout／stderr 分别查询，避免把 running 解释为业务健康。

## 命令行

```bash
qshell sandbox list --state running,paused --format json
qshell sandbox logs SANDBOX_ID --level ERROR --limit 100 --format json
qshell sandbox logs SANDBOX_ID --loggers envd,proxy --follow
qshell sandbox metrics SANDBOX_ID --format json
qshell sandbox metrics SANDBOX_ID --follow
```

logs 的 `--level` 默认 INFO，显示该级别及更高级别；`--loggers` 为逗号分隔的 logger 前缀。`--follow` 持续运行，需要主动取消或等待实例结束。CLI 漂亮输出可能隐藏内部字段，关联请求时保留相关 API 的请求 ID。

## SDK 调用

沿用入门示例的 `sandbox`／`sb`，以下片段放在清理之前。指标窗口的 `start`／`end` 是 Unix 秒，日志 `start` 是 Unix 毫秒；这些原始字段不会因 JavaScript 使用 Date 而自动转换。

```javascript
const nowSeconds = Math.floor(Date.now() / 1000);
const info = await sandbox.getInfo();
const metrics = await sandbox.getMetrics({start: nowSeconds - 300, end: nowSeconds});
const logs = await sandbox.getLogs({start: Date.now() - 300000, limit: 100});
console.log(info.state, metrics.length, (logs.logEntries || logs.logs || []).length);
```

```python
import time
now_seconds = int(time.time())
info = sandbox.get_info()
metrics = sandbox.get_metrics(start=now_seconds - 300, end=now_seconds)
logs = sandbox.get_logs(start=now_seconds * 1000 - 300000, limit=100)
print(info.get('state'), len(metrics), len(logs.get('logEntries') or logs.get('logs') or []))
```

Go 使用 `sb.GetMetrics(ctx, &sandbox.GetMetricsParams{Start: &start, End: &end})`，start／end 为 int64 Unix 秒；`sb.GetLogs(ctx, &sandbox.GetLogsParams{Start: &startMillis, Limit: &limit})` 使用 int64 毫秒和 int32 条数。详情为 `sb.GetInfo(ctx)`。批量指标入口为 `client.GetSandboxesMetrics(ctx, &sandbox.GetSandboxesMetricsParams{SandboxIds: ids})`；Node 为 `client.getSandboxesMetrics(ids)`，Python 为 `client.get_sandboxes_metrics(ids)`。

| 数据 | 关键字段 | 使用方式 |
| --- | --- | --- |
| 详情 | `sandboxID`、`templateID`、`state`、`startedAt`、`endAt`、`metadata` | 核对对象、归属、TTL 和状态；Go 对应 PascalCase 字段 |
| 指标 | `cpuUsedPct`、`cpuCount`、`memUsed`、`memTotal`、`diskUsed`、`diskTotal`、`timestamp` | CPU 百分比、核数，内存／磁盘按字节 |
| 平台日志 | `logs`、`logEntries` | 原始行与结构化条目；Go 对应 `SandboxLogs.Logs`／`LogEntries` |
| 命令结果 | exit code、stdout、stderr | 应用输出与执行错误，实时输出见 [commands.md](commands.md) |

新建实例可能还没有指标；不要仅因空数组判定失败。业务健康仍以业务探测和产物验收为准。

## 故障定位顺序

1. 401／403：核对客户端使用的端点、凭据种类和资源权限；隐藏密钥。
2. 详情 404：核对 ID／区域；检查是否到期或被其他流程销毁。
3. 创建或构建未完成：查看构建状态和日志，检查启动／就绪命令，见 [templates.md](templates.md)。
4. running 但命令／文件失败：核对 Envd 域名可达性、token、用户、路径；用 health 和最小命令缩小范围。
5. 命令非零：保留退出码和必要 stderr，检查依赖、目录和输入。
6. 资源不足：读取相同时间段的指标，调整模板资源后重新验证；临时资源按原 ID 清理。

当前公开接口没有独立的沙箱生命周期 `getEvents`／事件订阅 API；文件 watcher 的事件不是平台创建／暂停事件。业务可记录已发起操作、请求 ID、时间和查询结果，恢复异步任务；接口边界见 [compatibility.md](compatibility.md)。
