# 接口来源与维护

本技能借鉴 [PPIO Sandbox Skill](https://github.com/PPIO/ppio-skills/tree/main/skills/ppio-sandbox) 的按需参考组织方式，接口、参数与示例以七牛官方 SDK／CLI 为依据。

## 核对基线

2026-11-16 核对以下源码版本。链接固定到对应提交，便于复核。接入已有项目时仍应检查项目实际安装的版本；遇到接口差异，从官方仓库的对应版本继续查阅。

| 工具 | 版本 | 源码基线 |
| --- | --- | --- |
| qshell | v2.21.2 | [ab37568](https://github.com/qiniu/qshell/tree/ab37568bd6fe71218f62dd15b62b03d581dfa7a6) |
| Go SDK | v7.31.0 | [d94ab38](https://github.com/qiniu/go-sdk/tree/d94ab38cd03301662846526377d211f6da03dc74) |
| Node.js SDK | v7.15.6 | [f0b4989](https://github.com/qiniu/nodejs-sdk/tree/f0b4989a63ab70c7236a3bfc2a6a51eb594f5de9) |
| Python SDK | v7.19.0 | [26d426e](https://github.com/qiniu/python-sdk/tree/26d426e2d6c67f68a2980828bab5bae611a42545) |

产品概念参考[七牛 Sandbox 概览](https://developer.qiniu.com/las/13281/sandbox-overview)。价格、配额、地域可用性和默认模板属于动态信息，需要时查询当前文档或实际环境。

## 官方源码与文档

| 任务 | qshell | Go | Node.js | Python |
| --- | --- | --- | --- | --- |
| 生命周期、连接、状态与网络 | [命令文档](https://github.com/qiniu/qshell/tree/master/docs) | [sandbox.go](https://github.com/qiniu/go-sdk/blob/master/sandbox/sandbox.go)、[types.go](https://github.com/qiniu/go-sdk/blob/master/sandbox/types.go) | [SDK 指南](https://github.com/qiniu/nodejs-sdk/blob/master/docs/sandbox.md)、[类型](https://github.com/qiniu/nodejs-sdk/blob/master/index.d.ts) | [SDK 指南](https://github.com/qiniu/python-sdk/blob/master/examples/README-sandbox.md)、[sandbox.py](https://github.com/qiniu/python-sdk/blob/master/qiniu/services/sandbox/sandbox.py) |
| 命令、文件、Git、PTY | [exec](https://github.com/qiniu/qshell/blob/master/docs/sandbox_exec.md) | [沙箱包](https://github.com/qiniu/go-sdk/tree/master/sandbox) | [沙箱模块](https://github.com/qiniu/nodejs-sdk/tree/master/qiniu/sandbox) | [沙箱模块](https://github.com/qiniu/python-sdk/tree/master/qiniu/services/sandbox) |
| 模板、磁盘与标签 | [构建](https://github.com/qiniu/qshell/blob/master/docs/sandbox_template_build.md)、[配置](https://github.com/qiniu/qshell/blob/master/docs/sandbox_template_config.md) | [template.go](https://github.com/qiniu/go-sdk/blob/master/sandbox/template.go) | [模板示例](https://github.com/qiniu/nodejs-sdk/blob/master/examples/sandbox_templates.js) | [模板示例](https://github.com/qiniu/python-sdk/blob/master/examples/sandbox_template_lifecycle.py) |
| 快照、幂等与分页 | [快照](https://github.com/qiniu/qshell/blob/master/docs/sandbox_snapshot.md) | [snapshot.go](https://github.com/qiniu/go-sdk/blob/master/sandbox/snapshot.go) | [快照示例](https://github.com/qiniu/nodejs-sdk/blob/master/examples/sandbox_paginator_snapshot_mcp.js) | [快照示例](https://github.com/qiniu/python-sdk/blob/master/examples/sandbox_snapshots.py) |
| Git／Kodo 资源挂载与凭据更新 | [创建参数](https://github.com/qiniu/qshell/blob/master/docs/sandbox_create.md)、[资源更新](https://github.com/qiniu/qshell/blob/master/docs/sandbox_resource_update.md) | [资源类型](https://github.com/qiniu/go-sdk/blob/master/sandbox/types.go) | [资源示例](https://github.com/qiniu/nodejs-sdk/blob/master/examples/sandbox_resources.js) | [资源类型](https://github.com/qiniu/python-sdk/blob/master/qiniu/services/sandbox/resources.py) |
| 运行时请求注入、保存的注入规则 | [注入规则](https://github.com/qiniu/qshell/blob/master/docs/sandbox_injection_rule.md) | [注入接口](https://github.com/qiniu/go-sdk/tree/master/sandbox) | [注入示例](https://github.com/qiniu/nodejs-sdk/blob/master/examples/sandbox_request_injections.js) | [注入示例](https://github.com/qiniu/python-sdk/blob/master/examples/sandbox_injection_rules.py) |

主入口已按任务路由到本地操作指引。本表用于追踪维护时的官方接口来源；使用安装版本的方法签名核对请求、鉴权和返回结构。

Desktop 还需核对 [Go Desktop](https://github.com/qiniu/go-sdk/blob/master/sandbox/desktop.go) 与 [Stream](https://github.com/qiniu/go-sdk/blob/master/sandbox/desktop_stream.go)。Windows、兼容 Desktop 和 Agent 集成见 [integrations.md](integrations.md) 与 [desktop.md](desktop.md) 的官方文档链接。语言封装与平台接口的边界集中记录在 [compatibility.md](compatibility.md)。

## 更新方式

维护本技能时，先核对四个官方仓库的发布版本，再更新受影响的参考和示例。用相应 SDK 编译或执行示例，核对创建、命令、文件、失败处理和清理行为。验证报告区分本地模拟、真实服务调用及尚未验证的环节；只有真实服务验证通过后，才能声称在线流程已通过。
