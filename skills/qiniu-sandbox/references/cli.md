# qshell

完成 [setup.md](setup.md) 中的环境配置。命令组为 `qshell sandbox`，别名为 `qshell sbx`。自动化创建使用 `--detach`；全局 `-d` 的含义是调试输出。

## 创建、执行、文件操作与清理

先选择实际可用的模板：

```bash
qshell sandbox template list --format json
```

以下命令中的 `TEMPLATE_ID`、`SANDBOX_ID` 应替换为本次操作的实际值。分步执行，读取上一条结果后再继续。

```bash
# 创建并记录返回的沙箱 ID；存活时间为 300 秒。
qshell sandbox create TEMPLATE_ID --detach --timeout 300 --metadata purpose=skill-demo

# 查询本次沙箱状态；进入 running 后再执行任务。
qshell sandbox list --state running,paused --metadata purpose=skill-demo --format json

# 执行命令，检查退出码以及 stdout／stderr。
qshell sandbox exec SANDBOX_ID -- sh -lc 'printf "hello from qiniu sandbox\n"'

# 将本地内容通过 stdin 写入沙箱，再读回核对。
printf 'hello from qiniu sandbox\n' | qshell sandbox exec SANDBOX_ID -- sh -lc 'cat > /home/user/skill-demo.txt'
qshell sandbox exec SANDBOX_ID -- cat /home/user/skill-demo.txt

# 任务结束后，销毁本次创建的沙箱。
qshell sandbox kill SANDBOX_ID
qshell sandbox list --state running,paused --metadata purpose=skill-demo --format json
```

最后一次查询应确认该 ID 已不在结果中。API 返回仍在处理中时，继续核对最终状态。实际脚本需要在创建成功并拿到 ID 后注册清理逻辑，失败时也清理本次资源；交互任务需要保留沙箱时按用户约定处理。

文件传输通过 `exec` 的 stdin／stdout 完成，适合小文件。较大文件、二进制文件和批量读写优先使用语言 SDK 的文件接口。使用 shell 重定向保存下载内容时，确认本地目标文件的覆盖范围。

## 常用操作

| 任务 | 命令 |
| --- | --- |
| 按状态查询 | `qshell sandbox list --state running,paused --format json` |
| 指定工作目录 | `qshell sandbox exec SANDBOX_ID --cwd /home/user -- pwd` |
| 设置进程环境变量 | `qshell sandbox exec SANDBOX_ID --env MODE=demo -- sh -lc 'printf "%s\n" "$MODE"'` |
| 后台启动服务 | `qshell sandbox exec SANDBOX_ID --background -- python3 -m http.server 8080 --bind 0.0.0.0` |
| 查看日志 | `qshell sandbox logs SANDBOX_ID` |
| 查看指标 | `qshell sandbox metrics SANDBOX_ID` |
| 暂停并保存内存 | `qshell sandbox pause SANDBOX_ID` |
| 仅保存文件系统 | `qshell sandbox pause SANDBOX_ID --memory=false` |
| 恢复 | `qshell sandbox resume SANDBOX_ID` |

`exec` 的 `--` 后是沙箱中的命令。管道、重定向等 shell 语法应放进 `sh -lc '...'`，避免被本地 shell 提前执行。`create --env-var` 设置沙箱环境；`exec --env` 设置该命令的环境。

后台命令返回 PID 后，再检查服务监听或就绪接口。需要交付外部访问 URL 时读取 [lifecycle.md](lifecycle.md)。

## 范围与帮助

`kill`、`pause`、`resume` 支持多个 ID 和 `--all`。批量操作前明确用户授权的资源范围和状态筛选；本次任务的清理使用已记录的 ID。

```bash
qshell version
qshell sandbox --help
qshell sandbox create --help
qshell sandbox exec --doc
```

模板构建见 [templates.md](templates.md)，快照见 [lifecycle.md](lifecycle.md)。
