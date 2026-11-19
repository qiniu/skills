# 接口来源与维护

本技能借鉴 [PPIO Sandbox Skill](https://github.com/PPIO/ppio-skills/tree/main/skills/ppio-sandbox) 的按需参考组织方式，接口、参数与示例以七牛官方 SDK／CLI 为依据。

## 核对基线

2026-11-18 核对以下源码提交和公开安装渠道。已有项目按实际依赖版本核对类型和方法签名。

| 工具 | 源码版本 | 源码基线 | 安装渠道 |
| --- | --- | --- | --- |
| qshell | v2.22.1 | [a7e849a](https://github.com/qiniu/qshell/tree/a7e849a25a82909c83caf99e57bd53537053b16c) | [GitHub 二进制发布包](https://github.com/qiniu/qshell/releases/tag/v2.22.1) |
| Go SDK 稳定版 | v7.31.0 | [d94ab38](https://github.com/qiniu/go-sdk/tree/d94ab38cd03301662846526377d211f6da03dc74) | Go module 稳定版 |
| Go SDK 新接口 | v7.31.1-0.20261119025108-d01bf5d6d62d | [d01bf5d](https://github.com/qiniu/go-sdk/tree/d01bf5d6d62dc52f33bec22fd78e5a0ec0c0d2e7) | Go module 伪版本 |
| Node.js SDK | v8.0.0 | [a2ead37](https://github.com/qiniu/nodejs-sdk/tree/a2ead373b7a29c61440cfc4e10298ae1975147f5) | [GitHub Release](https://github.com/qiniu/nodejs-sdk/releases/tag/v8.0.0) 对应的固定源码包 |
| Python SDK | v7.20.0 | [af43f5a](https://github.com/qiniu/python-sdk/tree/af43f5afda06f48adef27a99aa1f7d777645d054) | [GitHub Release](https://github.com/qiniu/python-sdk/releases/tag/v7.20.0) 对应的固定源码包 |

## 配套 SDK 修复

以下四个 PR 均已合并。上表中 Go 的稳定标签早于 #245，Go 的新接口使用伪版本。Node 原生 Desktop 随 [nodejs-sdk#464](https://github.com/qiniu/nodejs-sdk/pull/464) 合入，v8.0.0 包含该功能。可用安装命令见 [setup.md](setup.md)。

| 工具与来源 | 配套修复的接口与行为 |
| --- | --- |
| [Go SDK #245](https://github.com/qiniu/go-sdk/pull/245) | `Client.List` 返回 `*SandboxPage{Items, NextToken}`；`TrafficAccessToken()` 可读取服务 token；PTY 重连可接收原始字节，断连立即释放等待者并保留已收到的输出；文件请求使用 Envd token，公开签名 URL 对齐 Envd 编码与 Unix 过期时间；临时 Git 认证隔离已有 credential helper |
| [Node.js SDK #463](https://github.com/qiniu/nodejs-sdk/pull/463) | `client.listSandboxes`／`listSnapshots` 返回 `{items, nextToken}`，metadata 字典保留特殊字符；文件支持 Readable 输入、端到端流式下载与 `requestTimeoutMs`，识别调用前或传输中已提前关闭的源；创建命令／PTY 时将 `executionTimeoutMs` 交给 Envd，重连不接受该选项；类型包含服务 token／`buildConfig`；临时 Git 凭据隔离、上传错误解析和文件 URL 签名已修复 |
| [Python SDK #476](https://github.com/qiniu/python-sdk/pull/476) | `client.list_sandboxes` 返回 `{'items': [...], 'nextToken': ...}`，metadata 字典保留特殊字符；PTY 支持 `on_data(bytes)` 与断连，活跃读流由读线程完成 HTTP 响应清理；临时 Git 用户名优先于已有配置，临时目录和清理使用同一进程用户；文件 URL 签名对齐 Envd，原始 Envd 请求不自动跟随重定向 |
| [qshell #469](https://github.com/qiniu/qshell/pull/469) | 列表支持 `--all`／`--next-token`；列表和批量命令共用 metadata 过滤校验；批量操作完整枚举后再执行，失败返回非零退出码。此 PR 仍依赖 Go SDK v7.30.1，未包含 Go 文件 HTTP 鉴权修复；CLI 现有 stdin／stdout 文件传输走 Commands 接口，不受该问题影响 |

新版 SDK 的低层分页重复调用同一个列表方法并回填游标。Node.js／Python 的高层分页器负责传递游标。Go 稳定版和其他旧依赖可使用 [原始 HTTP 示例](parameters.md#旧版-sdk-与原始-http-分页)。

Node.js／Python 配套修复还将 Commands／PTY 的进程选择器按 Envd Protobuf JSON 直接编码为 `process.pid` 或 `process.tag`，修复重连、输入、关闭 stdin、缩放和 kill 的 501。云端回归覆盖完整交互，PTY 测试不再把此类协议错误当作不支持而跳过；Go 的 stdin 集成用例验证真实写入、EOF 和输出。

Code Interpreter／Desktop 的兼容版本、安装命令和实测范围分别维护在 [code-interpreter.md](code-interpreter.md) 与 [desktop.md](desktop.md)。2026-11-17 已在七牛扬州环境完成解释器及桌面基础操作验证，并确认新版 E2B 的创建接口／Key 校验与当前环境存在兼容边界。升级依赖后复测实际流程；中文桌面输入与完整视觉 Agent 任务的边界见 Desktop 页。

服务端能力以[七牛沙箱实例 API](https://developer.qiniu.com/las/13480/sandbox-api-sandboxes)和实际环境为准。维护者可对照需仓库权限的[内部 OpenAPI 源文件](https://github.com/qbox/sandbox/blob/e3dfa87062481997412d505cccc2beaaffa49a06/spec/openapi-public.yml)。运行时网络更新的能力边界见 [network.md](network.md)。

产品概念参考[七牛 Sandbox 概览](https://developer.qiniu.com/las/13281/sandbox-overview)。价格、配额、地域可用性和默认模板属于动态信息，需要时查询当前文档或实际环境。

## 官方源码与文档

| 任务 | qshell | Go | Node.js | Python |
| --- | --- | --- | --- | --- |
| 生命周期、连接、状态与网络 | [命令文档](https://github.com/qiniu/qshell/tree/master/docs) | [sandbox.go](https://github.com/qiniu/go-sdk/blob/master/sandbox/sandbox.go)、[types.go](https://github.com/qiniu/go-sdk/blob/master/sandbox/types.go) | [SDK 指南](https://github.com/qiniu/nodejs-sdk/blob/master/docs/sandbox.md)、[类型](https://github.com/qiniu/nodejs-sdk/blob/master/index.d.ts) | [SDK 指南](https://github.com/qiniu/python-sdk/blob/master/examples/README-sandbox.md)、[sandbox.py](https://github.com/qiniu/python-sdk/blob/master/qiniu/services/sandbox/sandbox.py) |
| 命令、文件、Git、PTY | [exec](https://github.com/qiniu/qshell/blob/master/docs/sandbox_exec.md) | [沙箱包](https://github.com/qiniu/go-sdk/tree/master/sandbox) | [沙箱模块](https://github.com/qiniu/nodejs-sdk/tree/master/qiniu/sandbox) | [沙箱模块](https://github.com/qiniu/python-sdk/tree/master/qiniu/services/sandbox) |
| Code Interpreter | 普通脚本通过 exec；解释器用兼容 SDK | 原生包未提供专用封装 | [兼容 SDK 指南](code-interpreter.md)、[官方指南](https://developer.qiniu.com/las/13292/sandbox-code-interpreter) | 同 Node.js，使用 `e2b-code-interpreter` |
| 模板、磁盘与标签 | [构建](https://github.com/qiniu/qshell/blob/master/docs/sandbox_template_build.md)、[配置](https://github.com/qiniu/qshell/blob/master/docs/sandbox_template_config.md) | [template.go](https://github.com/qiniu/go-sdk/blob/master/sandbox/template.go) | [模板示例](https://github.com/qiniu/nodejs-sdk/blob/master/examples/sandbox_templates.js) | [模板示例](https://github.com/qiniu/python-sdk/blob/master/examples/sandbox_template_lifecycle.py) |
| 快照、幂等与分页 | [快照](https://github.com/qiniu/qshell/blob/master/docs/sandbox_snapshot.md) | [snapshot.go](https://github.com/qiniu/go-sdk/blob/master/sandbox/snapshot.go) | [快照示例](https://github.com/qiniu/nodejs-sdk/blob/master/examples/sandbox_paginator_snapshot_mcp.js) | [快照示例](https://github.com/qiniu/python-sdk/blob/master/examples/sandbox_snapshots.py) |
| Git／Kodo 资源挂载与凭据更新 | [创建参数](https://github.com/qiniu/qshell/blob/master/docs/sandbox_create.md)、[资源更新](https://github.com/qiniu/qshell/blob/master/docs/sandbox_resource_update.md) | [资源类型](https://github.com/qiniu/go-sdk/blob/master/sandbox/types.go) | [资源示例](https://github.com/qiniu/nodejs-sdk/blob/master/examples/sandbox_resources.js) | [资源类型](https://github.com/qiniu/python-sdk/blob/master/qiniu/services/sandbox/resources.py) |
| 运行时请求注入、保存的注入规则 | [注入规则](https://github.com/qiniu/qshell/blob/master/docs/sandbox_injection_rule.md) | [注入接口](https://github.com/qiniu/go-sdk/tree/master/sandbox) | [注入示例](https://github.com/qiniu/nodejs-sdk/blob/master/examples/sandbox_request_injections.js) | [注入示例](https://github.com/qiniu/python-sdk/blob/master/examples/sandbox_injection_rules.py) |

主入口已按任务路由到本地操作指引。本表用于追踪维护时的官方接口来源；使用安装版本的方法签名核对请求、鉴权和返回结构。

Desktop 还需核对 [Go Desktop](https://github.com/qiniu/go-sdk/blob/master/sandbox/desktop.go) 与 [Stream](https://github.com/qiniu/go-sdk/blob/master/sandbox/desktop_stream.go)。Windows、兼容 Desktop 和 Agent 集成见 [integrations.md](integrations.md) 与 [desktop.md](desktop.md) 的官方文档链接。语言封装与平台接口的边界集中记录在 [compatibility.md](compatibility.md)。

## 更新方式

维护本技能时，先核对四个官方仓库的发布版本，再更新受影响的参考和示例。用相应 SDK 编译或执行示例，核对创建、命令、文件、失败处理和清理行为。验证报告区分本地模拟、真实服务调用及尚未验证的环节；只有真实服务验证通过后，才能声称在线流程已通过。
