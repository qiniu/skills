# Qiniu Skills

[![License: MIT](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)
[![Skills](https://img.shields.io/badge/skills-4-informational?style=flat-square)](#available-skills)
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
| [appmarket-dev](skills/appmarket-dev/SKILL.md) | Qiniu AppMarket app development & publishing | create/version/image/deploy |
| [maas](skills/maas/SKILL.md) | Qiniu MaaS platform management: request log query, usage statistics, API Key lifecycle | REST API |
| [miku-live](skills/miku-live/SKILL.md) | Intent resolution, parameter validation, and signed execution for Qiniu Miku Live management APIs | 40+ action keys across buckets, streams, domains, certificates, recording, relay, statistics, and API keys |

## What Can You Do

Talk to your AI agent in natural language:

- "列一下 my-bucket 里的文件" → `qshell listbucket2 my-bucket`
- "上传 test.png 到 my-bucket" → `qshell fput my-bucket test.png ./test.png`
- "创建一个沙箱" → `qshell sandbox create <template>`
- "刷新 CDN 缓存" → `qshell cdnrefresh -i <urls.txt>`
- "生成私有链接" → `qshell privateurl <URL>`
- "批量下载 logs/ 前缀的文件" → `qshell qdownload2 --bucket <Bucket> --dest-dir ./logs --prefix logs/`
- "帮我在 AppMarket 上架一个 MySQL 应用" → runs `appmarket-dev` skill
- "创建 AppMarket 应用版本并测试" → `appmarket-cli.py create-version / test-version`
- "查看近 7 天接口成功率，是否有 5xx 异常" → maas skill 查询请求日志
- "生成本月各模型 Token 消耗报表" → maas skill 查询用量统计
- "创建一个新 API Key 并设置月度限额" → maas skill 管理 API Key
- "某次失败请求的错误原因是什么" → maas skill 查询日志详情
- "帮我获取到直播空间列表" → `bucket-management/list_buckets`
- "禁播 bucket-a 里的 stream-1" → `stream-management/ban_stream`
- "给 bucket-a 绑定播放域名 live.example.com" → `domain-management/bind_downstream_domain`
- "创建一个转推任务" → `pub-relay/create_pub_task`

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
└── appmarket-dev/                # Qiniu AppMarket app development & publishing
    ├── SKILL.md                  # Skill definition
    ├── README.md                 # Usage guide
    ├── assets/                   # Templates (deploy-meta, setup-image)
    ├── scripts/                  # CLI tools (appmarket-cli, vm-cli, image-cli, tf-to-schema)
    └── references/               # Guides (terraform-module, image-building, testing, etc.)
└── maas/                         # Qiniu MaaS platform management
    ├── SKILL.md                  # Skill definition (request logs, usage stats, API Key management)
    ├── references/
    │   ├── openapi.json          # Full REST API specification
    │   └── aksk-token.md         # AK/SK signing algorithm and credential types
    └── examples/
        ├── alert-polling.md      # Alert polling reference implementation
        ├── availability-panel.md # Availability panel output template
        └── usage-panel.md        # Usage panel output template
└── miku-live/                    # Qiniu Miku Live API mapping and execution guidance
    ├── SKILL.md                  # Skill definition (intent mapping, safety rules, output contract)
    └── references/
        ├── interface-catalog.md  # Action catalog and parameter placement
        ├── schemas.md            # Unified request/response contract
        └── signing.md            # Signing and execution details
```

## Contributing

We welcome contributions for more Qiniu Cloud product skills. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT](LICENSE)
