# 接口来源与维护

本技能借鉴 [PPIO Sandbox Skill](https://github.com/PPIO/ppio-skills/tree/main/skills/ppio-sandbox) 的按需参考组织方式，接口、参数与示例以七牛官方 SDK／CLI 为依据。

## 安装与兼容性

从 [环境与鉴权](setup.md#选择工具)选择官方发布渠道。已有项目按锁定的依赖核对类型和方法签名；查找各语言封装差异见 [compatibility.md](compatibility.md)。

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

维护本技能时，先核对四个官方仓库的发布版本，再更新受影响的参考和示例。用相应 SDK 编译或执行示例，核对创建、命令、文件、失败处理和清理行为。在维护 PR 中记录所用版本、发布渠道、本地检查和云端验证结果。
