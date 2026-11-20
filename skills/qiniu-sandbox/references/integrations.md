# Agent、浏览器、MCP 与其他运行环境

集成任务先复用应用的已有依赖，确认执行模板、输入数据、所需凭据、输出形式和保留时间。基础设施部分按本 skill 的原生 SDK 操作；框架初始化代码以项目安装版本为准。

## Coding Agent 与业务 Agent

一个可验收的流程是：准备模板→挂载代码／上传输入→配置按目标限制的请求注入→执行 Agent→读取产物→清理临时实例。仓库物化和 Git helper 的区别见 [resources.md](resources.md) 与 [git.md](git.md)。

```bash
# 确认所选模板已经包含项目所需运行时与 CLI。
qshell sandbox exec SANDBOX_ID -- sh -lc 'command -v node; command -v python3'
# 在已准备好的应用目录运行用户自己的 Agent 入口。
qshell sandbox exec SANDBOX_ID --cwd /workspace/repo -- node ./agent.mjs
```

执行前确认入口文件真实存在。长任务使用 [commands.md](commands.md) 的后台句柄和输出流，将沙箱 ID／PID 与业务任务一起保存；沙箱 TTL、Agent 任务截止时间和模型请求时限分别设置。模型秘密凭据通过 [injections.md](injections.md) 提供时，核对 Agent 请求的域名、路径和模型筛选条件。

七牛维护了 [AI Agents 入口](https://developer.qiniu.com/las/13451/sandbox-agent)和 [Codex 指南](https://developer.qiniu.com/las/13453/sandbox-agent-codex)，可从那里选择相应的预装环境。使用模板前仍需在目标地域查询实际名称与权限。

## 浏览器自动化

选择已安装浏览器及其运行依赖的模板，或按 [templates.md](templates.md) 构建。控制程序可以直接在沙箱内执行 Playwright／Browser Use 应用；这样浏览器与控制端共用 localhost，不必开放调试端口。

如果控制程序位于沙箱外，明确选用 CDP 或其他 HTTP／WebSocket 协议，按浏览器的配置监听 `0.0.0.0` 并获取服务 host。将调试接口作为敏感控制服务，按 [network.md](network.md) 设置认证；确认所选框架客户端能够携带需要的请求头。以一次真实页面操作和产物验收连接，而不只检查端口开放。

## MCP 网关

原生 Node／Python 的创建参数可携带 `mcp`，并有 `getMcpUrl()`／`get_mcp_url()` helper。使用包含并配置了 MCP 网关的模板，先验证网关进程和可调用工具。URL helper 使用 50005 端口和 `/mcp` 路径；它只拼接访问地址，不会安装或启动任意 MCP 服务。

Node `getMcpToken()` 读取 `/etc/mcp-gateway/.token`（root 用户），Python `get_mcp_token()` 返回的是创建响应中的服务流量 token。两者不等价；按模板实际网关认证要求取凭据，并独立处理平台的服务访问 token。Go 此基线没有对应 MCP helper；可用原生文件／命令／服务访问接口集成已部署的网关。

接入框架时，把网关 URL 和正确的认证配置交给项目已使用的 MCP 客户端，调用工具后验收结果。不要输出网关 token、文件签名 URL 或携带凭据的服务 URL。

## Windows 与 PowerShell

七牛提供 Windows 模板和官方 [Windows／PowerShell 指南](https://developer.qiniu.com/las/13633/sandbox-windows)。该指南使用 E2B 兼容 SDK。当前原生 Go／Node／Python 的 Commands helper 固定启动 Bash，因此本 skill 的 Linux 命令示例不能直接用于 Windows。

选择官方指南中当前可用的 Windows 模板和地域，用其兼容客户端创建实例，上传 `.ps1` 和输入文件，显式调用 `powershell.exe -NoProfile -NonInteractive -File`，再下载产物并清理实例。把复杂的管道和变量逻辑放到脚本文件，避免多层引号；用 Windows 绝对路径和明确编码，并将外部工具的退出码传回调用方。此基线 Windows 创建不接受非空 resources，输入改用文件上传。模板派生的权限和 Windows 构建限制也按官方指南核对。

## SSH、私有网络和代理

| 需求 | 接入方式与边界 |
| --- | --- |
| 交互式 shell | 优先 [PTY](pty.md) 或 `qshell sandbox connect`；这两者已有沙箱认证和终端管理 |
| 必须使用 SSH 客户端 | 确认所选模板运行 sshd，且平台提供所需 TCP／WebSocket 转发方案。`getHost(22)` 生成的服务 host 不等于可直接 SSH 的原始 TCP 地址；当前原生 SDK 没有 SSH 隧道 helper |
| Tailscale／OpenVPN | 先验证模板内网络设备、所需权限、DNS／路由和出网策略；按组织现有客户端方案接入。此基线没有 VPN 专用 SDK API，也没有可直接套用的 PPIO VPN 模板约定 |
| HTTP 代理／包下载加速 | 沿用组织已有代理配置，给相关进程设置代理环境；核对内部地址、证书、访问控制和实际下载结果，不假定地域域名附带代理服务 |
| 对象存储／跨任务共享文件 | 使用 [Kodo 挂载](resources.md)，核对只读设置、对象前缀、凭据和跨实例读回；不要替换成未提供的 Volume API |

这些集成应在授权的网络与资源范围内验证。涉及权限、模板或代理变更时先把具体配置落实；无法确认的功能按 [compatibility.md](compatibility.md) 说明实际边界。
