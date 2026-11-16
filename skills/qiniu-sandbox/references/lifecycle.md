# 生命周期、快照与服务访问

## 选择操作

| 用户目标 | 操作和结果 |
| --- | --- |
| 延长或调整运行时间 | 使用 SDK 的 `setTimeout`／`set_timeout`／`SetTimeout`，区分沙箱 TTL 与客户端请求超时 |
| 稍后继续运行中的任务 | 暂停并保存内存；恢复后检查进程和业务状态 |
| 保存文件、下次重新启动程序 | 暂停时 `memory=false`；恢复冷启动，内存和原进程丢失 |
| 通过流量唤醒 | 创建时启用 `autoPause` 和 `autoResume.enabled`，保持内存暂停方式 |
| 保存可复用的环境状态 | 创建持久快照，记录快照 ID，再以此 ID 创建新沙箱 |
| 结束临时任务 | 销毁本次沙箱，再核对资源状态 |

`autoPauseMemory=false` 不能与启用的 `autoResume` 同用。文件系统暂停需要显式 Connect／Resume。冷启动时 `/tmp` 可能被清理，验证持久化使用 `/home/user` 等持久路径。

SDK 的 Connect 使用 v2 连接接口，连接已暂停沙箱时恢复运行；连接只延长、不缩短已有 TTL。需要主动调整到期时间时使用 SetTimeout。qshell 的 `connect` 进入交互式终端，自动化恢复使用 `resume`。

创建时配置自动暂停、流量恢复的参数：

| 工具 | 配置 |
| --- | --- |
| qshell | `--auto-pause --auto-resume` |
| Go | `CreateParams.AutoPause`、`AutoPauseMemory` 和 `AutoResume: &sandbox.AutoResumeConfig{Enabled: true}`，布尔选项使用指针 |
| Node.js | `autoPause: true, autoPauseMemory: true, autoResume: { enabled: true }` |
| Python | `auto_pause=True, auto_pause_memory=True, auto_resume={'enabled': True}` |

## 持久快照

每次新捕获生成并保存一个幂等键。网络中断、等待超时或取消后，先查询原捕获；重试使用原键、原沙箱 ID 和相同请求体。取消客户端等待不会取消服务端已接受的捕获。完成的结果会重放，包含失败；幂等记录在完成后保留 35 分钟，结果未知时先核实，避免换键重复捕获。

```bash
# 先生成并保存本次捕获的键，后续重试复用这个值。
CAPTURE_KEY="$(uuidgen)"
qshell sandbox snapshot create SANDBOX_ID --idempotency-key "$CAPTURE_KEY" --name skill-demo:v1 --memory=false --format json
qshell sandbox snapshot list --name skill-demo:v1 --format json

# 从返回的 snapshotID 创建新的沙箱，记下并管理新沙箱的 ID。
qshell sandbox create SNAPSHOT_ID --detach --timeout 300
```

生产应用将幂等键与操作记录一同保存，避免 shell 退出后丢失。快照名称为别名和可选标签，例如 `skill-demo:v1`；创建时名称不含 `/`，命名空间由账号决定。

| SDK | 创建入口 |
| --- | --- |
| Go | `sb.CreateSnapshot(ctx, sandbox.CreateSnapshotParams{IdempotencyKey: key})` |
| Node.js | `sandbox.createSnapshot({ idempotencyKey: key, name: 'skill-demo:v1', memory: false })` |
| Python | `sandbox.create_snapshot(idempotency_key=key, name='skill-demo:v1', memory=False)` |

Node.js／Python 返回值中的 `snapshotID` 可作为创建沙箱的模板参数。Go 使用 `SnapshotInfo.SnapshotID`。列表需要遍历后续分页；快照通过模板删除接口清理，删除前确认它属于本次任务且已不再需要。具体参数见 [sources.md](sources.md) 的快照参考。

## 运行和访问应用服务

1. 在沙箱中监听 `0.0.0.0`，例如 `python3 -m http.server 8080 --bind 0.0.0.0`。后台启动后，检查沙箱内就绪接口。
2. 用 SDK 的 `getHost(8080)`／`get_host(8080)`／`GetHost(8080)` 获取 host，再按访问方式组成 `https://<host>`。使用 API 返回的沙箱域名。
3. 核对创建时的网络配置。允许公共流量时，按公开服务策略访问；关闭公共流量时，按平台约定携带服务访问 token，并避免把 token 拼入日志或可分享 URL。浏览器直接访问需要考虑其携带认证头的方式。
4. 从实际调用方验证可达性和响应，再交付 URL、端口及约定的保留时间。

`secure` 控制 Envd 管理接口鉴权；`network.allowPublicTraffic` 控制应用服务的公共访问。配置应用服务访问时，应分别确认这两项设置。详细网络和鉴权接口从 [sources.md](sources.md) 查阅。
