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
qshell sandbox list --all --state running,paused --metadata purpose=skill-demo --format json

# 执行命令，检查退出码以及 stdout／stderr。
qshell sandbox exec SANDBOX_ID -- sh -lc 'printf "hello from qiniu sandbox\n"'

# 将本地内容通过 stdin 写入沙箱，再读回核对。
printf 'hello from qiniu sandbox\n' | qshell sandbox exec SANDBOX_ID -- sh -lc 'cat > /home/user/skill-demo.txt'
qshell sandbox exec SANDBOX_ID -- cat /home/user/skill-demo.txt

# 任务结束后，销毁本次创建的沙箱。
qshell sandbox kill SANDBOX_ID
qshell sandbox list --all --state running,paused --metadata purpose=skill-demo --format json
```

清理后按已知 ID 调用 SDK 的详情接口确认 404／已删除状态。列表可用于辅助核对，详情接口用于确认该 ID 的状态。API 返回仍在处理中时，继续核对最终状态。实际脚本需要在创建成功并拿到 ID 后注册清理逻辑，失败时也清理本次资源；交互任务需要保留沙箱时按用户约定处理。

文件传输通过 `exec` 的 stdin／stdout 完成，适合小文件。较大文件、二进制文件和批量读写优先使用语言 SDK 的文件接口。使用 shell 重定向保存下载内容时，确认本地目标文件的覆盖范围。

## 常用操作

| 任务 | 命令 |
| --- | --- |
| 按状态查询 | `qshell sandbox list --state running,paused --format json` |
| 指定工作目录 | `qshell sandbox exec SANDBOX_ID --cwd /home/user -- pwd` |
| 设置进程环境变量 | `qshell sandbox exec SANDBOX_ID --env MODE=demo -- sh -lc 'printf "%s\n" "$MODE"'` |
| 后台启动静态服务 | `qshell sandbox exec SANDBOX_ID --background -- python3 -m http.server 8080 --bind 0.0.0.0 --directory /home/user/skill-public` |
| 查看日志 | `qshell sandbox logs SANDBOX_ID` |
| 查看指标 | `qshell sandbox metrics SANDBOX_ID` |
| 暂停并保存内存 | `qshell sandbox pause SANDBOX_ID` |
| 仅保存文件系统 | `qshell sandbox pause SANDBOX_ID --memory=false` |
| 恢复 | `qshell sandbox resume SANDBOX_ID` |

`exec` 的 `--` 后是沙箱中的命令。管道、重定向等 shell 语法应放进 `sh -lc '...'`，避免被本地 shell 提前执行。`create --env-var` 设置沙箱环境；`exec --env` 设置该命令的环境。

启动静态服务前创建 `/home/user/skill-public`，只放入获准分享的文件。后台命令返回 PID 后，再检查服务监听或就绪接口。交付访问 URL 前，按[服务访问与鉴权](network.md#私有服务访问)核对实例的公开范围。

## 分页与批量操作

qshell 默认读取一页。`--limit` 设置每页条数。有下一页时，stderr 输出 `Next token: ...`，JSON stdout 仍是数组。按相同的筛选条件回填游标，或用 `--all` 自动遍历：

```bash
qshell sandbox list -s running,paused -m 'lang=c++' --limit 20 -f json
qshell sandbox list -s running,paused -m 'lang=c++' --limit 20 --next-token 'CURSOR' -f json
qshell sandbox list -s running,paused -m 'lang=c++' --limit 20 --all -f json
```

`--all` 和 `--next-token` 互斥。列表和 `kill/pause/resume --all` 共用 metadata 校验和编码。显式传入空键、空值、重复键或格式错误的过滤条件时，命令在查询前以非零状态退出。批量操作先枚举所有匹配页、去重，再执行变更。操作前确认用户授权的资源和状态范围，本次任务的清理使用已记录的 ID。

## 范围与帮助

```bash
qshell version
qshell sandbox --help
qshell sandbox create --help
qshell sandbox exec --doc
```

模板构建见 [templates.md](templates.md)，快照见 [snapshots.md](snapshots.md)。

## 子命令索引

以下路径均接在 `qshell sandbox` 后；具体参数按主题页读取。

| 路径 | 用途 | 参考 |
| --- | --- | --- |
| `list` | 单页、游标续查或完整遍历，按 state／metadata 筛选 | [分页与批量操作](#分页与批量操作) |
| `create TEMPLATE_ID --detach` | 创建实例；env、资源、注入及到期策略 | [公共参数](parameters.md)、[资源](resources.md)、[注入](injections.md) |
| `connect ID` | 交互式终端，支持 `--user` | [PTY](pty.md) |
| `exec ID -- COMMAND` | 前台／后台执行 | [进程](commands.md) |
| `pause IDS`、`resume IDS`、`kill IDS` | 明确 ID 集合的生命周期操作 | [生命周期](lifecycle.md) |
| `logs ID`、`metrics ID` | 平台日志和采样指标，支持 follow | [观测](observability.md) |
| `template list`、`template get ID` | 查询模板 | [模板](templates.md) |
| `template init`、`template config` | 脚手架和 TOML 配置说明 | [模板](templates.md) |
| `template build`、`template builds ID BUILD_ID` | 构建及状态／日志 | [模板](templates.md) |
| `template tags ID` | 查询标签与构建 | [模板](templates.md) |
| `template publish IDS`、`template unpublish IDS` | 调整模板可见性 | [模板](templates.md) |
| `template delete IDS` | 删除模板或快照 | [模板](templates.md)、[快照](snapshots.md) |
| `snapshot create ID`、`snapshot list` | 快照捕获、筛选和游标分页 | [快照](snapshots.md) |
| `resource list ID`、`resource update ID RESOURCE_ID` | 查询挂载资源，更新 Git token | [资源](resources.md) |
| `injection-rule list`、`get ID`、`create`、`update ID`、`delete IDS` | 保存规则的完整生命周期，使用 AK／SK | [注入](injections.md) |

API Key 与 AK／SK 的配置和优先级见 [setup.md](setup.md)。实例、模板、快照和资源接口按对应鉴权方式调用；无需为了普通 API Key 沙箱操作更换 qshell 当前账号。秘密参数通过 SDK 的环境配置传入，避免把真实凭据放到命令行。
