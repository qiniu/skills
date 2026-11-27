# Qiniu Skills

[English](README.md) | 简体中文

[![License: MIT](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)
[![Skills](https://img.shields.io/badge/skills-7-informational?style=flat-square)](#可用技能)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square)](CONTRIBUTING.md)

面向编程智能体（Claude Code、Cursor、Codex 等）的 AI 技能定义，让你通过自然语言操作七牛云产品。

## 快速开始

```bash
# 安装全部技能
npx skills add qiniu/skills

# 安装到指定智能体
npx skills add qiniu/skills -a claude-code

# 仅安装 AgentAPI 技能
npx skills add qiniu/skills --skill agentapi

# 仅安装 Sandbox 技能
npx skills add qiniu/skills --skill qiniu-sandbox

# 列出可用技能，不执行安装
npx skills add qiniu/skills --list
```

> 基于 [skills.sh](https://skills.sh) 开放智能体技能生态。

## 可用技能

| 技能 | 说明 | 命令 / 接口 |
|-------|-------------|----------|
| [qshell](skills/qshell/SKILL.md) | 七牛云 KODO 对象存储命令行工具 | 98 个命令，15 个分类 |
| [qiniu-sandbox](skills/qiniu-sandbox/SKILL.md) | 七牛云 Sandbox 的生命周期、进程、文件、Git/PTY、模板、快照、资源挂载、注入、代码解释和桌面自动化 | qshell, Go, Node.js/TypeScript, Python |
| [appmarket-dev](skills/appmarket-dev/SKILL.md) | 七牛云 AppMarket 应用开发与发布 | create/version/image/deploy |
| [maas](skills/maas/SKILL.md) | 七牛云 MaaS 平台管理：请求日志查询、用量统计和 API Key 生命周期管理 | REST API |
| [miku-live](skills/miku-live/SKILL.md) | 七牛云 Miku Live 管理 API 的意图解析、参数校验与签名执行 | 40 多个操作键，覆盖直播空间、流、域名、证书、录制、转推、统计和 API Key |
| [xfetch-web](skills/xfetch-web/SKILL.md) | 通过七牛 xfetch 抓取并抽取网页内容 | markdown/json/html |
| [agentapi](skills/agentapi/SKILL.md) | 选择合适的七牛云 AgentAPI 接入方式，通过 Portal 或 API 构建应用 | 运行时、会话、SSE 事件和任务结果 |

如需 AgentAPI 技能的使用帮助或反馈，请前往 [AgentAPI 社区](skills/agentapi/README.md#交流与反馈)。

## 使用示例

用自然语言向你的 AI 智能体描述需求：

- "列一下 my-bucket 里的文件" → `qshell listbucket2 my-bucket`
- "上传 test.png 到 my-bucket" → `qshell fput my-bucket test.png ./test.png`
- "创建一个沙箱并执行 Python 代码" → `qiniu-sandbox` 技能，选择 qshell 或项目所用的 SDK
- "刷新 CDN 缓存" → `qshell cdnrefresh -i <urls.txt>`
- "生成私有链接" → `qshell privateurl <URL>`
- "批量下载 logs/ 前缀的文件" → `qshell qdownload2 --bucket <Bucket> --dest-dir ./logs --prefix logs/`
- "帮我在 AppMarket 上架一个 MySQL 应用" → 调用 `appmarket-dev` 技能
- "创建 AppMarket 应用版本并测试" → `appmarket-cli.py create-version / test-version`
- "查看近 7 天接口成功率，是否有 5xx 异常" → maas 技能查询请求日志
- "生成本月各模型 Token 消耗报表" → maas 技能查询用量统计
- "创建一个新 API Key 并设置月度限额" → maas 技能管理 API Key
- "某次失败请求的错误原因是什么" → maas 技能查询日志详情
- "帮我获取到直播空间列表" → `bucket-management/list_buckets`
- "禁播 bucket-a 里的 stream-1" → `stream-management/ban_stream`
- "给 bucket-a 绑定播放域名 live.example.com" → `domain-management/bind_downstream_domain`
- "读取 https://example.com/page 的页面内容" → xfetch-web 技能调用 Qiniu xfetch
- "把本地 Agent 项目迁移到七牛 AgentAPI" → agentapi 技能查看项目配置，选择 HTTP 接口或 Anthropic SDK 接入
- "用 AgentAPI 做一个代码审查助手" → agentapi 技能根据工具链和仓库权限选择运行时，并给出接入方案
- "这个需求该用 AgentAPI 还是直接调用模型 API？" → agentapi 技能根据工具调用、交互轮次和交付方式判断是否适合 AgentAPI

## 仓库结构

```
skills/
├── qiniu-sandbox/                # 通过 qshell 和各语言 SDK 操作七牛云 Sandbox
│   ├── SKILL.md                  # 工作流程与任务路由
│   └── references/               # 任务指南、SDK 示例、API 差异与资料来源
├── qshell/                       # 通过 qshell CLI 操作七牛云 KODO 对象存储
│   ├── SKILL.md                  # 技能定义（命令、意图映射、安全规则）
│   ├── references/
│   │   ├── install.sh            # 自动安装脚本（平台检测与下载）
│   │   └── install.md            # 安装指南与账号配置
│   └── examples/
│       └── conversation-flow.md  # 典型交互示例
├── appmarket-dev/                # 七牛云 AppMarket 应用开发与发布
│   ├── SKILL.md                  # 技能定义
│   ├── README.md                 # 使用指南
│   ├── assets/                   # 模板（deploy-meta、setup-image）
│   ├── scripts/                  # 命令行工具（appmarket-cli、vm-cli、image-cli、tf-to-schema）
│   └── references/               # 指南（Terraform 模块、镜像构建、测试等）
├── maas/                         # 七牛云 MaaS 平台管理
│   ├── SKILL.md                  # 技能定义（请求日志、用量统计、API Key 管理）
│   ├── references/
│   │   ├── openapi.json          # 完整 REST API 规范
│   │   └── aksk-token.md         # AK/SK 签名算法与凭证类型
│   └── examples/
│       ├── alert-polling.md      # 告警轮询参考实现
│       ├── availability-panel.md # 可用性面板输出模板
│       └── usage-panel.md        # 用量面板输出模板
├── miku-live/                    # 七牛云 Miku Live API 映射与执行指南
│   ├── SKILL.md                  # 技能定义（意图映射、安全规则、输出约定）
│   └── references/
│       ├── interface-catalog.md  # 操作目录与参数位置
│       ├── schemas.md            # 统一请求与响应约定
│       └── signing.md            # 签名与执行细节
├── xfetch-web/                   # 七牛 xfetch 网页抓取与内容抽取
│   ├── SKILL.md                  # 技能定义
│   └── scripts/
│       └── xfetch.py             # 路径式 xfetch API 辅助脚本
└── agentapi/                     # 七牛云 AgentAPI 接入与故障排查指南
    ├── SKILL.md                  # 技能定义（运行时与环境选择、会话与 SSE、验证）
    ├── README.md                 # 安装指南与社区二维码
    ├── assets/
    │   └── developer-community.jpg
    └── references/
        └── INDEX.md              # 从七牛云开发者中心自动同步的文档索引
```

## 参与贡献

欢迎贡献更多七牛云产品技能。贡献指南请参阅 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

[MIT](LICENSE)
