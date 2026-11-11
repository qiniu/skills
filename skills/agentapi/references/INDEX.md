# AgentAPI 任务文档索引

按当前任务选择需要读的页面。具体字段、示例和限制以对应的七牛开发者中心页面为准。

## 选接入方式并跑通首个任务

| 当前任务 | 官网文档 |
| --- | --- |
| 判断 AgentAPI 是否适合任务，理解智能体、环境和会话之间的关系 | [产品概述](https://developer.qiniu.com/agentapi/13584/agentapi-overview) · [基本概念](https://developer.qiniu.com/agentapi/13583/agentapi-concepts) |
| 确认服务地域、准备 API Key 和模型 | [接入准备](https://developer.qiniu.com/agentapi/13585/agentapi-access) |
| 在控制台配置和测试智能体，再把验证后的配置用到代码中 | [在 Portal 中构建](https://developer.qiniu.com/agentapi/13586/agentapi-portal) |
| 在应用中用 HTTP 或 SDK 跑通一次任务 | [通过 API 构建](https://developer.qiniu.com/agentapi/13587/agentapi-quickstart) |
| 选择运行时、模型或云端环境，确认软件和网络条件 | [运行时和模型](https://developer.qiniu.com/agentapi/13589/agentapi-agent-configuration-runtime-and-models) · [配置云端环境](https://developer.qiniu.com/agentapi/13608/agentapi-execution-environments-environment) · [云端沙箱参考](https://developer.qiniu.com/agentapi/13609/agentapi-execution-environments-cloud-environments) |

## 提交任务、显示进度和验收结果

| 当前任务 | 官网文档 |
| --- | --- |
| 创建或更新智能体，管理可复用配置 | [创建与管理智能体](https://developer.qiniu.com/agentapi/13590/agentapi-agent-configuration-agent) |
| 创建会话、继续任务或中断执行 | [创建会话](https://developer.qiniu.com/agentapi/13596/agentapi-sessions-and-tasks-session) · [会话操作](https://developer.qiniu.com/agentapi/13598/agentapi-sessions-and-tasks-session-lifecycle) |
| 接收实时进度、回传工具结果或判断停止原因 | [事件和事件流](https://developer.qiniu.com/agentapi/13597/agentapi-sessions-and-tasks-events) |
| 上传任务输入、获取文件或定义结果验收条件 | [附加和下载文件](https://developer.qiniu.com/agentapi/13602/agentapi-data-and-integrations-files) · [定义结果](https://developer.qiniu.com/agentapi/13599/agentapi-sessions-and-tasks-outcomes) |

## 接入工具和业务数据

| 当前任务 | 官网文档 |
| --- | --- |
| 配置内置工具或接入应用执行的自定义工具 | [工具](https://developer.qiniu.com/agentapi/13591/agentapi-agent-configuration-tools) |
| 连接远程 MCP，管理凭证或配置工具确认 | [MCP 连接器](https://developer.qiniu.com/agentapi/13592/agentapi-agent-configuration-mcp) · [凭证管理](https://developer.qiniu.com/agentapi/13606/agentapi-data-and-integrations-vaults) · [权限策略](https://developer.qiniu.com/agentapi/13593/agentapi-agent-configuration-permissions) |
| 复用业务规范或跨会话资料 | [Agent Skills](https://developer.qiniu.com/agentapi/13594/agentapi-agent-configuration-skills) · [构建持久记忆](https://developer.qiniu.com/agentapi/13603/agentapi-data-and-integrations-memory) |
| 给代码审查助手访问 GitHub 仓库的能力 | [访问 GitHub](https://developer.qiniu.com/agentapi/13604/agentapi-data-and-integrations-github) · [代码审查案例](https://developer.qiniu.com/agentapi/13627/code-review-assistant) |

## 定期运行、接收通知和访问内网

| 当前任务 | 官网文档 |
| --- | --- |
| 定时核对订单、生成日报或查看定时运行记录 | [定时部署](https://developer.qiniu.com/agentapi/13600/agentapi-sessions-and-tasks-scheduled-deployments) · [运营任务案例](https://developer.qiniu.com/agentapi/13629/handle-operational-tasks-with-scheduled-tasks) |
| 让应用在后台接收通知并验证签名 | [Webhook 通知](https://developer.qiniu.com/agentapi/13605/agentapi-data-and-integrations-webhooks) |
| 把文件和命令执行放在自有基础设施，并确认隔离与数据流 | [自托管执行器](https://developer.qiniu.com/agentapi/13614/agentapi-execution-environments-self-hosted) · [自托管安全责任](https://developer.qiniu.com/agentapi/13615/agentapi-execution-environments-self-hosted-security) · [内网运维案例](https://developer.qiniu.com/agentapi/13628/sre-intelligent-o-m) |

## 核对接口或迁移现有应用

| 当前任务 | 官网文档 |
| --- | --- |
| 核对鉴权、分页、错误或请求和响应字段，下载 OpenAPI YAML | [API 通用约定](https://developer.qiniu.com/agentapi/13618/agentapi-api-conventions) · [OpenAPI 规范](https://developer.qiniu.com/agentapi/13619/agentapi-openapi) |
| 查找当前语言的 SDK 安装方式 | [SDK 下载](https://developer.qiniu.com/agentapi/13620/agentapi-sdk-download) |
| 从现有智能体应用迁移 | [迁移到 AgentAPI](https://developer.qiniu.com/agentapi/13617/agentapi-migration) |
