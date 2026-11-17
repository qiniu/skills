# 能力覆盖与接口差异

本页的限制表以 [sources.md](sources.md) 中固定的发布基线为准；同页的配套 SDK 修复表单独列出尚未作为发布包核对的变更。先确认项目依赖所属版本，再选择对应契约。SDK 封装缺口不等于服务端没有对应能力，账号与地域是否开通还需查询实际环境。

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

## 发布基线的平台 API 与语言封装

| 能力 | 此基线的实际边界 | 使用路径 |
| --- | --- | --- |
| 独立 Secret 资源 | 未提供 PPIO 的 Secret CRUD／`secret_envs` 接口 | 用七牛保存的注入规则或内联注入；按 HTTPS 匹配条件限制实际目标 |
| 独立 Volume 资源 | Node `Volume.create/list/delete` 明确返回不支持，Go／Python 也无 Sandbox Volume 管理接口 | 使用 Kodo 挂载、外部存储或快照；不承诺独立卷配额、动态挂卸载语义 |
| 生命周期事件／idle timeout | 当前公开接口无 getEvents／订阅和平台空闲回收参数 | 业务记录操作和活动时间，按约定查询状态并 Pause／Kill |
| 长时运行 | 未确认 `long_running` 元数据是七牛上限开关 | 按团队运行配额设置 TTL，需提额时按官方渠道申请 |
| 沙箱列表分页与过滤 | Go／qshell 未交付下一页游标；Node／Python 沙箱 paginator 也未读取数组响应的 `X-Next-Token`，Node `query.metadata` 编码不符合 API | 用 [原始 HTTP 遍历示例](parameters.md)读取 Header 和正确的 metadata；快照 paginator 不受影响 |
| 运行时网络更新 | Node／Python 有方法发送 `PATCH /sandboxes/{id}`，但当前公开服务端 OpenAPI 未提供该操作；Go／qshell 也无对应入口 | 在创建时落实网络配置；变更需按 [network.md](network.md) 保存数据并迁移到新沙箱 |
| Go 服务 token | Sandbox 的流量 token 私有，详情类型也未公开它 | 受限服务的 token 访问示例使用 Node／Python，或原始 API 响应 |
| 安全文件鉴权 | Go／Node 文件 HTTP 读写及三语言公开文件 URL 的签名存在与 Envd 不一致的问题 | 使用已确认包含配套文件鉴权修复的 SDK；Go 仅传绝对过期时间不足以修正签名编码 |
| Python Envd 重定向 | 请求默认跟随重定向，自定义访问 token 可能被带给其他来源 | 使用配套的禁止自动重定向修复，收到 30x 时核对端点与代理 |
| 临时 Git 凭据 | 继承的 credential helper 可能保存临时凭据；Python 文件操作还可能使用不同用户 | 使用配套凭据隔离修复；命令级回退显式清空继承 helper，见 [git.md](git.md) |
| Node 服务 token 类型 | 实例运行时保存 token，但 TypeScript 未声明该成员；waitForReady 会替换 info | 保存原始创建响应中的 token，再包装实例，见 [network.md](network.md) |
| Code Interpreter | 平台已有解释器运行时；原生 Go／Node／Python qiniu 包没有 runCode／上下文专用封装 | 使用官方支持的 `@e2b/code-interpreter`／`e2b-code-interpreter` 兼容接入，见 [code-interpreter.md](code-interpreter.md) |
| Desktop | 原生 Desktop／Stream 封装在 Go 中；原生 Node／Python qiniu 包无对应类 | Go 原生 API，或七牛官方支持的 `@e2b/desktop`／`e2b-desktop` 兼容接入 |
| Windows | 服务提供 Windows 模板，但此基线三语言 Commands helper 均启动 `/bin/bash` | 使用官方 Windows 指南的 E2B 兼容流程；不把 Linux helper 套到 Windows |
| Python Git 认证 | clone 的 username/password kwargs 未被执行层转换为 Git 认证 | 用授权的 Git 资源挂载，或在沙箱配置经核对的 credential helper |
| Python PTY | 无实时 PTY 字节回调和 disconnect helper | 当前句柄只在 wait 后提供解码后的 stdout；需要实时桌面终端时选择其他接口 |
| Go PTY 重连 | `Pty.Connect` 无输出回调选项，重连的 PTY 字节也不会进入 Stdout | 用重连句柄等待结束／终止；需要实时输出时保留创建流或更换客户端 |
| Node 命令／PTY 时限 | 流开始定时器在首个 start 事件后清除，不是完整进程执行期限 | 配套版创建时将 `executionTimeoutMs` 交给 Envd；已有进程重连不会重设期限，见 [commands.md](commands.md) |
| Node 文件 stream／请求时限 | read 的 stream 是下载缓冲完成后的包装；write 不接受通用流；read/write 未转发每次调用的 timeout | 大文件分块处理／外部存储；不要把返回 Readable 理解为端到端流式下载 |
| 模板 builder | Go 用底层构建接口；Python Template 只生成配置；Node `.build()` 仅申请构建，不启动／等待，`buildConfig` 也未声明为 TS 公共方法 | 使用文档中实际可编译的分配→启动→等待流程 |
| qshell 模板高级操作 | 没有私有 registry 凭据 flag，也没有标签修改子命令 | 使用相应 SDK 操作；CLI 的 tags 是查询 |
| MCP token helper | Node 从网关 `.token` 文件取值，Python helper 返回服务流量 token，两者不是统一凭据语义 | 按所选模板的网关认证契约取值，不把任意 helper 返回值当作网关 Bearer token |

这些差异都不应靠臆造方法名、强制类型断言或静默忽略参数掩盖。需要超出当前封装的功能时，明确使用原始公共 API、兼容 SDK 或业务层方案，并说明验证范围。
