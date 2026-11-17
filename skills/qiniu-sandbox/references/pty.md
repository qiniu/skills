# PTY 交互终端

PTY 用于交互式 shell 或需要终端的程序，包含提示符、控制字符和合并的终端输出。批处理任务优先使用 [commands.md](commands.md) 的普通命令接口。示例使用已连接的沙箱；需要保留交互状态时记录沙箱 ID 和 PID。

## 创建、输入、调整大小和结束

Node.js 在 `onData` 接收原始 Buffer，显式提供行列数：

```javascript
const terminal = await sandbox.pty.create({
  rows: 24, cols: 80, cwd: '/home/user',
  onData: data => process.stdout.write(data)
});
await sandbox.pty.resize(terminal.pid, { rows: 40, cols: 120 });
await sandbox.pty.sendInput(terminal.pid, 'printf "hello from PTY\\n"\n');
await sandbox.pty.sendInput(terminal.pid, 'exit\n');
const result = await terminal.wait();
if (result.exitCode !== 0) throw new Error('PTY exited unsuccessfully');
```

Python 通过 `wait()` 消费终端事件，当前 handle 将 PTY 输出按 UTF-8 解码并累积到最终 stdout。公共 `wait` 没有转发 PTY 输出回调；需要实时终端字节的场景应按 [兼容性边界](compatibility.md) 选用合适的 SDK。

```python
terminal = sandbox.pty.create(rows=24, cols=80, cwd='/home/user', timeout=30)
sandbox.pty.resize(terminal.pid, rows=40, cols=120)
sandbox.pty.send_stdin(terminal.pid, 'printf "hello from PTY\\n"\nexit\n')
result = terminal.wait()
print(result.stdout, end='')
if result.exit_code:
    raise RuntimeError('PTY exited {}'.format(result.exit_code))
```

Go 使用 `WithOnPtyData` 接收字节，并在 `WaitPID` 返回后发送输入：

```go
terminal, err := sb.Pty().Create(ctx, sandbox.PtySize{Rows: 24, Cols: 80},
	sandbox.WithCwd("/home/user"),
	sandbox.WithOnPtyData(func(data []byte) { _, _ = os.Stdout.Write(data) }),
)
if err != nil {
	return err
}
pid, err := terminal.WaitPID(ctx)
if err != nil {
	return err
}
if err := sb.Pty().Resize(ctx, pid, sandbox.PtySize{Rows: 40, Cols: 120}); err != nil {
	return err
}
if err := sb.Pty().SendInput(ctx, pid, []byte("printf 'hello from PTY\\n'\nexit\n")); err != nil {
	return err
}
result, err := terminal.WaitContext(ctx)
if err != nil {
	return err
}
if result.ExitCode != 0 {
	return fmt.Errorf("pty exited %d", result.ExitCode)
}
```

Go 片段位于返回 error 的函数中，需要 `os`、`fmt`。生产交互程序在终止、超时或客户端离开时，根据用户的会话保留策略停止 PTY 或断开输出连接；发生控制请求错误时保留 PID，后续可查询或显式终止。

## 方法和选项

| 任务 | Go：`sb.Pty()` | Node.js：`sandbox.pty` | Python：`sandbox.pty` |
| --- | --- | --- | --- |
| 创建 | `Create(ctx, PtySize, CommandOption...)` | `await create({rows, cols, cwd, envs, user, onData})` | `create(size=None, rows=None, cols=None, cwd=None, envs=None, user=None, timeout=None)` |
| 重连 | `Connect(ctx, pid)` | `await connect(pid, {onData, user, requestTimeoutMs})` | `connect(pid, user=None, timeout=None)` |
| 输入 | `SendInput(ctx, pid, []byte)` | `await sendInput(pid, stringOrBuffer, opts)` | `send_stdin(pid, stringOrBytes, user=None, timeout=None)`；`send_input` 为别名 |
| 调整尺寸 | `Resize(ctx, pid, PtySize)` | `await resize(pid, {rows, cols}, opts)` | `resize(pid, size=None, rows=None, cols=None, user=None, timeout=None)` |
| 等待退出 | `handle.Wait()`／`WaitContext(ctx)` | `await handle.wait()` | `handle.wait()`，从最终结果读取终端输出 |
| 杀死终端进程 | `Kill(ctx, pid)` | `await kill(pid, opts)` | `kill(pid, user=None, timeout=None)` |
| 断开输出 | `handle.Disconnect()` | `handle.disconnect()` | 当前公共 handle 未提供 disconnect 方法 |

Go 用 `sandbox.PtySize`，Python 可以用 `PtySize(rows=24, cols=80)` 或字典；Python 缺省尺寸为 24 × 80。Node.js 明确传入 `rows`／`cols`。尺寸单位是字符行列，不是像素。

Go 的 `Pty.Create` 使用 `/bin/bash -i -l`；Node.js 默认相同，但可以设置 `cmd` 和 `args`；Python 使用固定的交互 Bash。三者均设置终端 locale 和 TERM，用户提供的 envs 可覆盖默认值。运行用户和目录必须对目标程序、文件有访问权限。

## 重连与退出语义

Node.js 的重连保持实时回调：

```javascript
const terminal = await sandbox.pty.connect(savedPid, {
  onData: data => process.stdout.write(data)
});
await sandbox.pty.sendInput(savedPid, 'pwd\n');
terminal.disconnect();
```

`savedPid` 是之前记录的 PTY PID。上例只断开客户端；远端 shell 仍可能运行，需要保留会话时记录状态，需要结束时使用 `exit\n` 或 `pty.kill`。断开后的局部结果不是进程成功完成的证明。

Python 重连后在 `handle.wait` 中继续消费；Go `Pty.Connect(ctx, pid)` 没有公开回调选项，返回命令句柄，可等待最终结果，不能将它写成带 `WithOnPtyData` 参数的重载。需要重连后的实时原始字节时，按当前 SDK 能力选择实现。

EOF 应通过 PTY 输入发送 `\x04`；普通进程的 `CloseStdin` 不适用于 PTY。发送 `\x03` 是终端中断控制字符，`Kill` 是显式终止进程，两者效果由前台程序和终端设置决定。退出时检查结束结果；网络断开和读取超时不等于 shell 已终止。

## 时限与 qshell

PTY 的存活时间仍受沙箱 TTL 约束。Go 通过创建时的 context 控制流；`Pty.Create` 当前不会应用普通命令的 `WithTimeout` 计时逻辑。Node.js 的 `requestTimeoutMs`／`timeoutMs`／`timeout` 用来等待启动事件，启动后应用应自行管理交互会话时限。Python 的 `timeout` 是请求读取超时，单位为秒；不要把它当作后台 shell 必定被终止的时间。

包含 [配套 SDK 修复](sources.md#配套-sdk-修复) 的 Node.js SDK 可在 `pty.create({rows: 24, cols: 80, executionTimeoutMs: 300000})` 时交给 Envd 设置 5 分钟执行期限。断开客户端后期限继续生效；`pty.connect` 只恢复输出订阅，不接受这一选项，也不会修改原期限。需要长期保留交互会话时，在创建阶段按保留策略设置期限。

```bash
qshell sandbox connect SANDBOX_ID
```

qshell `connect` 进入交互终端并自动保持沙箱存活，适合用户主动进行终端交互。自动化任务用 SDK PTY 或普通 `exec`；qshell 的交互命令不提供完整的 PTY PID、resize 和重连管理 API。
