# 能力覆盖与接口差异

先按 [setup.md](setup.md#选择工具)安装依赖，并核对项目锁定版本的方法签名。账号权限、模板和地域可用性查询实际环境。

## 主题覆盖

| 任务 | 本地指引 |
| --- | --- |
| 创建／连接／列表／公共参数 | [parameters.md](parameters.md)、三语言入门页、[cli.md](cli.md) |
| 代码片段／解释器上下文／流式与富媒体结果 | [code-interpreter.md](code-interpreter.md) |
| 暂停／恢复／超时／长期任务 | [lifecycle.md](lifecycle.md) |
| 前后台进程／流式输出／stdin／重连 | [commands.md](commands.md) |
| 文件／目录／批量／watch／签名传输 | [filesystem.md](filesystem.md) |
| Git／交互式终端 | [git.md](git.md)、[pty.md](pty.md) |
| 模板定义／构建／就绪／标签／删除 | [templates.md](templates.md) |
| 快照创建／查询／恢复／清理 | [snapshots.md](snapshots.md) |
| 网络／服务访问／Envd 鉴权 | [network.md](network.md) |
| 请求注入／保存规则／凭据轮换 | [injections.md](injections.md) |
| Git 与 Kodo 挂载／持久数据 | [resources.md](resources.md) |
| Desktop／VNC／Computer Use | [desktop.md](desktop.md) |
| 日志／指标／故障定位 | [observability.md](observability.md) |
| 地域／接入配置 | [setup.md](setup.md) |
| Agent／浏览器／MCP／Windows／SSH／VPN | [integrations.md](integrations.md) |

## 平台 API 与语言封装

| 能力 | 接口行为 | 使用路径 |
| --- | --- | --- |
| 独立 Secret 资源 | 未提供 PPIO 的 Secret CRUD／`secret_envs` 接口 | 用七牛保存的注入规则或内联注入；按 HTTPS 匹配条件限制实际目标 |
| 独立 Volume 资源 | Node `Volume.create/list/delete` 明确返回不支持，Go／Python 也无 Sandbox Volume 管理接口 | 使用 Kodo 挂载、外部存储或快照；不承诺独立卷配额、动态挂卸载语义 |
| 生命周期事件／idle timeout | 当前公开接口无 getEvents／订阅和平台空闲回收参数 | 业务记录操作和活动时间，按约定查询状态并 Pause／Kill |
| 长时运行 | 未确认 `long_running` 元数据是七牛上限开关 | 按团队运行配额设置 TTL，需提额时按官方渠道申请 |
| 沙箱列表分页与过滤 | qshell 和 Go／Node.js／Python SDK 均支持续页 | [SDK 分页与旧版 HTTP 示例](parameters.md#列表过滤与分页) |
| 运行时网络更新 | Node／Python 有方法发送 `PATCH /sandboxes/{id}`，但当前公开服务端 OpenAPI 未提供该操作；Go／qshell 也无对应入口 | 在创建时落实网络配置；变更需按 [network.md](network.md) 保存数据并迁移到新沙箱 |
| Go 服务 token | `TrafficAccessToken()` | 旧版缺少访问器时从创建响应读取流量 token |
| 安全文件鉴权 | 通过 Envd token 访问文件，或按路径签名 | [文件鉴权与签名示例](filesystem.md#签名上传下载-url) |
| Python Envd 重定向 | Envd 请求禁止自动跳转 | 收到 30x 时核对端点和代理 |
| 临时 Git 凭据 | 新版显式临时凭据隔离已有 helper | 见 [Git 认证](git.md#凭据和语言差异) |
| Node 服务 token 类型 | SDK 保留实例流量 token 并提供类型 | 旧版可从创建响应保存 token，见 [network.md](network.md) |
| Code Interpreter | 平台已有解释器运行时；原生 Go／Node／Python qiniu 包没有 runCode／上下文专用封装 | 使用官方支持的 `@e2b/code-interpreter`／`e2b-code-interpreter` 兼容接入，见 [code-interpreter.md](code-interpreter.md) |
| Desktop | Go 和 Node.js提供原生 Desktop 与 noVNC | 使用 [Go／Node 原生指引](desktop.md)。Node.js 也可使用 `@e2b/desktop`，Python 使用 `e2b-desktop` |
| Windows | 服务提供 Windows 模板，但三语言 Commands helper 均启动 `/bin/bash` | 使用官方 Windows 指南的 E2B 兼容流程；不把 Linux helper 套到 Windows |
| Python Git 认证 | clone 支持显式临时凭据 | 显式用户名优先于 Git 配置，clone 移除 URL 旧凭据 |
| Python PTY | 支持 `on_data(bytes)` 和 `disconnect()` | [PTY 回调和重连](pty.md) |
| Go PTY 重连 | 支持带回调重连和断连释放等待者 | 参见 [PTY 重连示例](pty.md) |
| Node 命令／PTY 时限 | 在创建时将 `executionTimeoutMs` 交给 Envd | 重连沿用已有进程期限，见 [commands.md](commands.md) |
| Node 文件 stream／请求时限 | 支持端到端流式传输和完整请求时限 | [文件读取、上传和时限](filesystem.md) |
| 模板 builder | Go 用底层构建接口，Python Template 生成配置，Node.js 声明 `buildConfig` | 按 SDK 的分配、启动和等待步骤执行，见 [templates.md](templates.md) |
| qshell 模板高级操作 | 没有私有 registry 凭据 flag，也没有标签修改子命令 | 使用相应 SDK 操作；CLI 的 tags 是查询 |
| MCP token helper | Node 从网关 `.token` 文件取值，Python helper 返回服务流量 token，两者不是统一凭据语义 | 按所选模板的网关认证契约取值，不把任意 helper 返回值当作网关 Bearer token |

这些差异都不应靠臆造方法名、强制类型断言或静默忽略参数掩盖。需要超出当前封装的功能时，明确使用原始公共 API、兼容 SDK 或业务层方案，并说明验证范围。
