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
| [appmarket-dev](skills/appmarket-dev/SKILL.md) | Qiniu AppMarket app development & publishing | create/version/image/deploy |

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
```

## Contributing

We welcome contributions for more Qiniu Cloud product skills. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT](LICENSE)
