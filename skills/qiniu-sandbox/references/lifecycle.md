# 生命周期与长期任务

创建、连接和列表参数见 [parameters.md](parameters.md)，持久快照见 [snapshots.md](snapshots.md)，网络唤醒与服务认证见 [network.md](network.md)。

## 状态与操作

| 用户目标 | 操作和结果 |
| --- | --- |
| 调整运行时间 | SetTimeout，设置从现在起的存活时间，受团队配额约束 |
| 保留运行中的进程 | 暂停并保存内存；Connect 后核对进程和业务状态 |
| 保留文件，下次重启程序 | 暂停时 `memory=false`；恢复冷启动，内存和原进程丢失 |
| 通过流量恢复 | 创建时启用自动暂停、内存暂停和 `autoResume.enabled` |
| 复用环境状态创建新实例 | 创建持久快照；以快照 ID 创建新的沙箱 |
| 完成临时任务 | Kill 本次 ID，然后查询确认终态 |

列表状态为 `running`／`paused`。Kill 后资源可能表现为详情 404 或从列表移除；记录实际结果。暂停／恢复请求完成后，再核对实例与业务状态。

## 暂停与恢复

| 工具 | 内存暂停 | 文件系统暂停 | 显式恢复 |
| --- | --- | --- | --- |
| qshell | `sandbox pause ID` | `sandbox pause ID --memory=false` | `sandbox resume ID` |
| Go | `sb.Pause(ctx)` | `sb.PauseWithParams(ctx, sandbox.PauseParams{Memory: &keepMemory})`，`keepMemory=false` | `client.Connect(ctx, id, sandbox.ConnectParams{Timeout: 300})` |
| Node.js | `sandbox.pause({memory: true})` | `sandbox.pause({memory: false})` | `sandbox.connect({timeout: 300})` |
| Python | `sandbox.pause(memory=True)` | `sandbox.pause(memory=False)` | `sandbox.connect(timeout=300)` |

Connect v2 只延长、不缩短已有 TTL。qshell `connect` 进入交互式终端，自动化恢复用 `resume`。连接既有实例后由用户决定保留时间，任务结束不自动销毁其他任务的资源。

## 到期策略

| 工具 | 创建选项 |
| --- | --- |
| qshell | `--auto-pause --auto-resume`；仅文件系统使用 `--auto-pause --auto-pause-memory=false` |
| Go | `AutoPause *bool`、`AutoPauseMemory *bool`、`AutoResume: &sandbox.AutoResumeConfig{Enabled: true}` |
| Node.js | `autoPause: true, autoPauseMemory: true, autoResume: {enabled: true}` |
| Python | `auto_pause=True, auto_pause_memory=True, auto_resume={'enabled': True}` |

文件系统暂停不能与流量自动恢复组合。冷启动时 `/tmp` 可能被清理；验证持久化使用 `/home/user` 等持久路径，并重启应用进程。超出沙箱生命周期仍需保存的数据写入 Kodo／业务存储，或保存为快照。

## 调整 TTL 与 Refresh

| 工具 | 接口 | 单位与含义 |
| --- | --- | --- |
| Go | `sb.SetTimeout(ctx, 300*time.Second)` | `time.Duration`，至少 1 秒 |
| Node.js | `sandbox.setTimeout(300)`／`sandbox.setTimeout({timeoutMs: 300000})` | 数值形式为秒，选项形式可用毫秒 |
| Python | `sandbox.set_timeout(300)` | 秒 |
| Go | `sb.Refresh(ctx, sandbox.RefreshParams{Duration: &seconds})` | `seconds` 为 int；延长请求 |
| Node.js | `sandbox.refresh({duration: 300})` | duration 为秒 |
| Python | `sandbox.refresh(duration=300)` | duration 为秒 |

SetTimeout 可能缩短剩余时间，Connect 不会。Refresh 与 SetTimeout 是不同操作；修改后查询 `endAt`／`EndAt`，确认实际到期时间。

## 长期运行与空闲回收

七牛官方[生命周期说明](https://developer.qiniu.com/las/13284/sandbox-lifecycle)列出了默认时长和团队运行上限，较长时长需按账号权限申请。以当前配置和服务端错误为准；PPIO 的 `long_running` 元数据不是此基线已确认的七牛运行上限开关。

长期服务保存沙箱 ID、模板、端点、到期时间和业务归属。在授权保留期内调用 SetTimeout／Refresh，重连后查询进程；句柄等待、输出和终止见 [commands.md](commands.md)。实例到期后从外部数据或快照恢复任务，避免只用控制进程内存中的 PID 保存任务状态。

此基线公开 SDK／API 未提供 PPIO 式 `idle_timeout` 回收接口。需要空闲回收时，由业务记录最后活动时间，在自己定义的空闲条件成立后对确定的 ID 调用 Pause／Kill；不要把普通 metadata 当作已生效的空闲策略。差异见 [compatibility.md](compatibility.md)。
