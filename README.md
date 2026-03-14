# Qiniu Skills

AI Skill 定义文件集合，为 AI 编程助手（如 Claude Code、Cursor 等）提供七牛云产品的操作能力，实现自然语言驱动的云资源管理。

## 目录结构

```
skills/
└── qshell/                    # qshell CLI 操作七牛云 KODO 对象存储
    ├── SKILL.md               # 主 Skill 定义文件（命令速查、意图映射、安全规则、输出格式等）
    └── references/
        └── install.md         # 安装指南（自动检测平台并下载安装 qshell）
```

## 已收录 Skills

| Skill | 说明 | 命令数 |
|-------|------|--------|
| [qshell](skills/qshell/SKILL.md) | 七牛云 KODO 对象存储 CLI 操作 | 98 个命令，15 大类 |

## 使用方式

将对应的 `skills/<name>/` 目录配置到 AI 编程助手的 Skill 搜索路径中，助手即可根据自然语言意图自动调用相关命令。

### 示例

- "列一下 my-bucket 里的文件" → `qshell listbucket2 my-bucket`
- "上传 test.png 到 my-bucket" → `qshell fput my-bucket test.png ./test.png`
- "创建一个沙箱" → `qshell sandbox create <template>`
- "刷新 CDN 缓存" → `qshell cdnrefresh -i <urls.txt>`

## 贡献

欢迎为更多七牛云产品添加 AI Skill 定义。每个 Skill 应包含：

1. `SKILL.md` — 主定义文件，包含 YAML frontmatter、命令速查、意图映射、安全规则和输出格式
2. `references/` — 辅助参考文档（如安装指南、配置说明等）

## License

[MIT](LICENSE)
