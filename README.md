# Qiniu Skills

[![License: MIT](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)
[![Skills](https://img.shields.io/badge/skills-2-informational?style=flat-square)](#available-skills)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square)](CONTRIBUTING.md)

AI Skill definitions for coding agents (Claude Code, Cursor, Codex, etc.) to operate Qiniu Cloud products via natural language.

## Quick Start

```bash
# Install all skills
npx skills add qiniu/skills

# Install to a specific agent
npx skills add qiniu/skills -a claude-code

# List available skills without installing
npx skills add qiniu/skills --list
```

> Powered by the [skills.sh](https://skills.sh) open agent skills ecosystem.

## Available Skills

| Skill | Description | Commands |
|-------|-------------|----------|
| [qshell](skills/qshell/SKILL.md) | Qiniu Cloud KODO object storage CLI | 98 commands, 15 categories |
| [maas](skills/maas/SKILL.md) | 七牛云 MaaS 平台管理（API Key、用量账单、请求日志、模型市场） | REST API |

## What Can You Do

Talk to your AI agent in natural language:

- "列一下 my-bucket 里的文件" → `qshell listbucket2 my-bucket`
- "上传 test.png 到 my-bucket" → `qshell fput my-bucket test.png ./test.png`
- "创建一个沙箱" → `qshell sandbox create <template>`
- "刷新 CDN 缓存" → `qshell cdnrefresh -i <urls.txt>`
- "生成私有链接" → `qshell privateurl <URL>`
- "批量下载 logs/ 前缀的文件" → `qshell qdownload2 --bucket <Bucket> --dest-dir ./logs --prefix logs/`
- "创建一个新的 MaaS API Key" → `POST /v1/apikeys`
- "查看上个月所有 API Key 的费用和用量" → `GET /v1/statistics/bills`
- "禁用一个不再使用的 API Key" → `PUT /v1/apikeys/{id}/disable`
- "查询某个模型的价格和支持参数" → `GET /v1/models/{id}`

## Repository Structure

```
skills/
├── qshell/                       # Qiniu KODO object storage via qshell CLI
│   ├── SKILL.md                  # Skill definition (commands, intent mapping, safety rules)
│   ├── references/
│   │   ├── install.sh            # Auto-install script (platform detection + download)
│   │   └── install.md            # Install guide and account setup
│   └── examples/
│       └── conversation-flow.md  # Typical interaction examples
└── maas/                         # 七牛云 MaaS 平台管理
    ├── SKILL.md                  # Skill definition (API Key、用量账单、请求日志、模型市场)
    ├── references/
    │   ├── openapi.json          # 完整 REST API 接口定义
    │   └── aksk-token.md         # AK/SK 签名算法说明
    └── examples/
        ├── alert-polling.md      # 告警轮询示例
        ├── availability-panel.md # 可用性面板示例
        ├── usage-panel.md        # 用量面板示例
        ├── apikey-manager/       # API Key 管理示例
        └── usage-page/           # 用量页面示例
```

## Contributing

We welcome contributions for more Qiniu Cloud product skills. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT](LICENSE)
