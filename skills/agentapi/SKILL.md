---
name: agentapi
description: Integrate with Qiniu Cloud AgentAPI using HTTP or the Anthropic SDK. Use for AgentAPI agents, runtimes and models, execution environments, sessions, SSE events, files and task results, deployments, MCP, or skills attached to an AgentAPI agent.
---

# 七牛云 AgentAPI

先读与当前任务对应的参考资料，再编写请求或修改代码。参考资料由[七牛开发者中心](https://developer.qiniu.com/agentapi)生成，每篇都附有原文地址。查字段、必填项和响应结构时，使用[线上接口规范的本地副本](references/openapi.yaml)；需要确认最新行为时查阅原文。

| 要完成的任务 | 先读 |
| --- | --- |
| 选服务区域、准备七牛 MaaS API Key、验证鉴权 | [接入准备](references/access.md)、[API 通用约定](references/api-conventions.md) |
| 用 HTTP 或 Anthropic SDK 接入现有项目 | [通过 API 构建](references/quickstart.md) |
| 选择运行时、模型和环境 | [运行时和模型](references/agent-configuration-runtime-and-models.md)、[配置云端环境](references/execution-environments-environment.md) |
| 创建、配置和管理智能体 | [创建与管理智能体](references/agent-configuration-agent.md) |
| 提交或继续任务、消费 SSE、处理停止原因 | [创建会话](references/sessions-and-tasks-session.md)、[事件和事件流](references/sessions-and-tasks-events.md)、[会话操作](references/sessions-and-tasks-session-lifecycle.md) |
| 获取回答、下载文件并验证任务结果 | [定义结果](references/sessions-and-tasks-outcomes.md)、[附加和下载文件](references/data-and-integrations-files.md) |
| 配置 MCP、Agent Skills、Webhook、定时部署、持久记忆或自托管执行器 | [参考资料索引](references/INDEX.md) |

第一次接入时，按快速入门验证完整流程：

1. 确认目标区域和该区域可用的模型。配置 `AGENTAPI_BASE_URL` 和 `AGENTAPI_API_KEY`，HTTP 请求按文档使用 `x-api-key`。凭证从环境变量或项目已有的密钥配置读取，示例使用占位符。
2. 选用项目已有的 HTTP 客户端或受支持的 SDK。创建或复用智能体与环境，记录 API 返回的资源 ID，再用这些 ID 创建会话。使用 SDK 时，按快速入门核对 AgentAPI 扩展字段的传入方式。
3. 需要实时进度时先打开 SSE，再按会话文档发送 `user.message`，结构化输入使用 `input.parts`。按事件文档处理历史回放、事件顺序和重连。
4. 根据本轮停止原因、回答和预期文件判断结果。收到 `session.status_idle` 后还需检查 `stop_reason`，并验收用户要求的产物。
