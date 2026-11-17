# 命令、进程与实时输出

以下片段沿用 [语言快速入门](nodejs.md) 中已连接且就绪的 `sandbox`；Go 使用 `sb`、`ctx` 和 `sandbox` 包。调用方按任务约定保留或清理沙箱。

## 执行方式与结果

| 目标 | Go：`sb.Commands()` | Node.js：`sandbox.commands` | Python：`sandbox.commands` |
| --- | --- | --- | --- |
| 前台执行 | `Run(ctx, cmd, opts...)` | `await run(cmd, opts)` | `run(cmd, **opts)` |
| 后台启动 | `Start(ctx, cmd, opts...)` | `await run(cmd, {background: true})`，或 `start` | `run(cmd, background=True)`，或 `start` |
| 查询运行进程 | `List(ctx)` → `[]ProcessInfo` | `await list(opts)` → 数组 | `list(user=None, timeout=None)` → 列表 |
| 连接已有进程 | `Connect(ctx, pid)` → handle | `await connect(pid, opts)` → handle | `connect(pid, user=None, timeout=None)` → handle |
| 等待结果 | `handle.Wait()`／`WaitContext(ctx)` | `await handle.wait()` | `handle.wait(on_stdout=None, on_stderr=None)` |
| 发送 stdin | `SendStdin(ctx, pid, []byte)` | `await sendStdin(pid, data, opts)` | `send_stdin(pid, data, user=None, timeout=None)` |
| 发送 stdin EOF | `CloseStdin(ctx, pid)` | `await closeStdin(pid, opts)` | `close_stdin(pid, user=None, timeout=None)` |
| 终止进程 | `Kill(ctx, pid)`／`handle.Kill(ctx)` | `await kill(pid, opts)`／`handle.kill()` | `kill(pid, ...)`／`handle.kill()` |
| 断开输出连接 | `handle.Disconnect()` | `handle.disconnect()` | 当前公共 handle 未提供 disconnect 方法 |

命令通过沙箱内的 `/bin/bash -l -c` 执行，支持管道与重定向。用户输入作为数据传递时应使用环境变量或 stdin；避免拼接未转义的 shell 字符串。

结果包含 stdout、stderr、退出码及可用的错误信息。Go 为 `Stdout`／`Stderr`／`ExitCode`，Node.js 为 `stdout`／`stderr`／`exitCode`，Python 为 `stdout`／`stderr`／`exit_code`。三个 SDK 的默认流程都需要检查退出码；Node.js 可设 `throwOnError: true`，Python 可设 `throw_on_error=True`。进程存在或返回 PID 表示启动成功，最终任务结果以结束事件和退出码为准。

## 流式读取输出

Node.js 在接收事件时调用回调：

```javascript
const result = await sandbox.commands.run('printf "first\\n"; sleep 1; printf "second\\n"', {
  cwd: '/home/user',
  onStdout: chunk => process.stdout.write(chunk),
  onStderr: chunk => process.stderr.write(chunk),
  throwOnError: true
});
```

Python 前台 `run` 会持续消费事件；后台 handle 在 `wait` 时继续消费，回调接收字符串：

```python
import sys

handle = sandbox.commands.run(
    'printf "first\\n"; sleep 1; printf "second\\n"',
    background=True, timeout=30,
)
result = handle.wait(on_stdout=sys.stdout.write, on_stderr=sys.stderr.write)
if result.exit_code:
    raise RuntimeError('Command exited {}'.format(result.exit_code))
```

Go 回调接收 `[]byte`，由 SDK 事件 goroutine 调用；回调访问共享状态时由应用同步：

```go
result, err := sb.Commands().Run(ctx, `printf "first\n"; sleep 1; printf "second\n"`,
	sandbox.WithOnStdout(func(data []byte) { _, _ = os.Stdout.Write(data) }),
	sandbox.WithOnStderr(func(data []byte) { _, _ = os.Stderr.Write(data) }),
	sandbox.WithTimeout(30*time.Second),
)
if err != nil {
	return err
}
if result.ExitCode != 0 {
	return fmt.Errorf("command exited %d: %s", result.ExitCode, result.Stderr)
}
```

示例需要 `fmt`、`os`、`time`。SDK 同时累积返回结果中的输出；大量或持续日志应写入沙箱文件，再按应用需要读取或轮转。

## stdin、后台句柄与重连

Node.js 示例启动读取 stdin 的进程，写入内容并发送 EOF，再验收最终结果：

```javascript
const handle = await sandbox.commands.run('cat', { background: true, stdin: true });
await sandbox.commands.sendStdin(handle.pid, 'hello\n');
await sandbox.commands.closeStdin(handle.pid);
const result = await handle.wait();
if (result.exitCode !== 0 || result.stdout !== 'hello\n') throw new Error('stdin roundtrip failed');
```

对应的 Go 选项为 `sandbox.WithStdin()`；启动后先用 `pid, err := handle.WaitPID(ctx)` 等待 PID 分配，再发送输入。Python 使用 `stdin=True`，从 `handle.pid` 取得 PID，调用 `send_stdin` 和 `close_stdin` 后 `handle.wait()`。

记录沙箱 ID 和 PID 后，可以在后续请求中连接同一沙箱，再调用进程 `connect`。Go／Node.js 的 `disconnect` 只结束客户端输出连接；进程需要显式 `kill`。断开后的局部结果不能证明远端程序已完成；重新连接或查询进程后继续验收。Python 没有公共 disconnect 方法，应让当前读取结束，或由独立调用方按 PID 管理进程。

Go `Connect(ctx, pid)` 没有回调参数，重连后通过 `Wait` 获取结果。Node.js `connect` 可传 `onStdout`／`onStderr`；Python 在重连 handle 的 `wait` 中传回调。`CloseStdin` 用于普通进程；PTY 的输入和 EOF 见 [pty.md](pty.md)。服务端不支持 CloseStdin 时，应保留该错误并根据命令协议结束输入或显式停止进程。

## 选项和时限

| 含义 | Go | Node.js | Python |
| --- | --- | --- | --- |
| 工作目录 | `WithCwd(path)` | `cwd` | `cwd` |
| 用户 | `WithCommandUser(user)` | `user` | `user` |
| 环境变量 | `WithEnvs(map)` | `envs` | `envs` |
| 进程标签 | `WithTag(tag)` | `tag` | `tag`；connect 还支持 `tag` 选择器 |
| stdin | `WithStdin()` | `stdin: true` | `stdin=True` |
| 输出回调 | `WithOnStdout`／`WithOnStderr` | `onStdout`／`onStderr` | `on_stdout`／`on_stderr`，或 `handle.wait` 的参数 |
| 运行与等待时限 | context；`WithTimeout(time.Duration)` 约束执行流 | `timeout`／`timeoutMs`／`requestTimeoutMs` 等待启动；配套版 Start 的 `executionTimeoutMs` 由 Envd 执行 | `timeout` 以秒传到启动请求；`request_timeout` 覆盖 HTTP 读取超时，均以秒为单位 |

沙箱 TTL 与以上时限分别设置。Node.js 的启动计时器在收到进程启动事件后清除；发布基线需要应用按业务截止时间显式 kill。Python 未传进程读取时限时使用客户端超时；HTTP 超时不表示远端进程已经停止。不要用 `timeout=0` 假定所有 Python HTTP 路径都支持无限等待。

包含 [配套 SDK 修复](sources.md#配套-sdk-修复) 的 Node.js SDK 在创建进程时用 `executionTimeoutMs` 设置执行期限，单位为毫秒，0 或省略表示不设置。SDK 通过 `Connect-Timeout-Ms` 把期限交给 Envd；客户端断连或退出后，Envd 仍会在期限到达时终止启动的进程。

```javascript
const task = await sandbox.commands.run('python3 /home/user/job.py', {
  background: true,
  requestTimeoutMs: 5000,
  executionTimeoutMs: 30000
});
const result = await task.wait();
if (result.exitCode !== 0) throw new Error(`Command exited ${result.exitCode}`);
```

上例最多等待 5 秒取得启动事件，进程的 30 秒期限由 Envd 从启动阶段计时。`commands.connect` 只重新接收已有进程的输出，不接受 `executionTimeoutMs`，也不会延长或重设原期限。断开输出连接仍不代表任务完成，重连后按实际结束状态验收。

## qshell

```bash
qshell sandbox exec SANDBOX_ID -- sh -lc 'printf "hello\n"'
qshell sandbox exec SANDBOX_ID --background -- python3 -m http.server 8080 --bind 0.0.0.0
qshell sandbox exec SANDBOX_ID --cwd /home/user --env MODE=demo -- sh -lc 'printf "%s\n" "$MODE"'
```

前台 exec 实时转发输出并返回退出码；后台模式返回 PID。qshell 未提供完整的进程 list／重连／stdin 管理子命令时，使用 SDK 句柄 API。`sandbox logs` 查询平台沙箱日志，与某个进程的 stdout／stderr 是不同的数据源。
