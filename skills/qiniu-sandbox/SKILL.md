---
name: qiniu-sandbox
description: >-
  Build and troubleshoot Qiniu Cloud Sandbox workflows with qshell or the
  Qiniu Go, Node.js/TypeScript, and Python SDKs. Use for creating sandboxes,
  running commands, reading and writing sandbox files, managing lifecycle,
  building templates, taking snapshots, or configuring sandbox service access.
---

# 七牛云 Sandbox

使用七牛 Sandbox 为应用或 AI Agent 提供隔离的代码执行环境。根据用户的语言和已有项目，选择 qshell、Go、Node.js／TypeScript 或 Python；沿用项目的依赖、端点和凭据配置。

## 操作流程

1. 明确目标：操作已有沙箱，还是创建沙箱；使用哪个模板；执行什么命令；文件输入和预期结果是什么。查询资源时记录实际返回的 ID。
2. 首次接入或遇到鉴权、安装问题时，读取[环境与鉴权](references/setup.md)。按下表读取所选工具的参考，只加载当前任务需要的文件。
3. 创建沙箱后记录 ID，等待就绪再执行命令或文件操作。分别检查 API 返回、命令退出码和业务产物；后台进程返回 PID 只表示已启动。
4. 为临时任务设置有限的存活时间，在 `finally`／`defer` 中清理本次创建的资源。用户需要保留服务或暂停续用时，按约定保留，并交付资源 ID 和后续操作。
5. 汇报所用工具、沙箱 ID、执行结果及资源最终状态。遇到错误时保留操作、阶段、ID 和可用的请求 ID，隐藏凭据。

## 按任务读取

| 任务 | 参考 |
| --- | --- |
| 安装、版本、API Key、端点、常见错误 | [setup.md](references/setup.md) |
| 用命令行管理沙箱、执行命令、传输文件 | [cli.md](references/cli.md) |
| 使用 Go SDK 编写应用 | [go.md](references/go.md) |
| 使用 Node.js／TypeScript SDK 编写应用 | [nodejs.md](references/nodejs.md) |
| 使用 Python SDK 编写应用 | [python.md](references/python.md) |
| 暂停、恢复、超时、快照和服务访问 | [lifecycle.md](references/lifecycle.md) |
| 选择模板、构建环境、启动命令与就绪检查 | [templates.md](references/templates.md) |
| 查询更多 API、资源挂载、请求注入或核对接口变化 | [sources.md](references/sources.md) |

## 关键约定

- qshell 自动化创建使用 `--detach`。交互式 `create`／`connect` 会进入终端；需要交互时再选择这些模式。
- 沙箱存活时间、命令执行时限和 HTTP 请求超时分别设置。Node.js 的 `timeout` 为秒，`timeoutMs` 为毫秒；Go 的创建参数为秒，`SetTimeout` 接受 `time.Duration`。
- 沙箱 API Key 用于平台 API，Envd token 用于沙箱内的命令／文件接口，服务访问 token 用于沙箱中的应用服务。由 SDK 处理 Envd 鉴权，凭据从服务端环境或密钥配置读取。
- 暂停方式、快照恢复和服务访问有独立语义，操作前读取生命周期参考。销毁、覆盖文件、删除模板和调整模板可见性应落实到用户授权的具体资源；清理只针对本次任务创建的资源。
- 查询、诊断任务按只读范围执行。示例中的创建、构建和删除操作用于用户已要求的实际任务；安装技能本身不会创建云资源。
