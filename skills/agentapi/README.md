# AgentAPI Skill

在项目目录安装或更新七牛云 AgentAPI skill。

```sh
npx skills add qiniu/skills --skill agentapi
npx skills update agentapi
```

[SKILL.md](SKILL.md) 帮助 agent 根据任务选择 Portal 或 API、运行时和执行环境。[任务文档索引](references/INDEX.md) 指向七牛开发者中心的具体页面，包括「在 Portal 中构建」。Agent 可以按任务查阅最新的接口规范、示例和产品说明。

`Check AgentAPI documentation links` 每天北京时间 09:23 在 `qiniu/skills` 默认分支检查索引链接，也可在 Actions 页面手动触发。发现失效或重定向的链接时，运行日志会列出对应的 URL 和行号。维护者也可以在仓库根目录运行同一检查。

```sh
python3 .github/scripts/check-agentapi-doc-links.py
```
