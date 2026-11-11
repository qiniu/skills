# AgentAPI Skill

在项目目录安装或更新七牛云 AgentAPI skill：

```sh
npx skills add qiniu/skills --skill agentapi
npx skills update agentapi
```

`SKILL.md` 提供任务步骤和参考资料入口。安装包内的 `references/` 由脚本从[七牛开发者中心](https://developer.qiniu.com/agentapi)生成，包含技术文章、原文索引和公开 OpenAPI 附件。已收录文章的无锚点链接会指向包内副本，其他链接保留线上地址。产品动态、计费说明和 Portal 操作教程可在官网查阅。

维护者在仓库根目录使用 Python 3.9 或更新版本运行：

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r skills/agentapi/scripts/requirements.txt
python skills/agentapi/scripts/sync-docs.py
python skills/agentapi/scripts/sync-docs.py --check
python -m unittest discover -s skills/agentapi/scripts
```

同步脚本在抓取和校验全部资料后才写入文件。`--check` 只比较，不写文件，有差异时退出码为 1，抓取或校验失败时为 2。提交更新前审查 `references/` 的差异。安装和使用 skill 不需要安装同步脚本的依赖。

`Sync AgentAPI skill references` 每天北京时间 09:23 在 `qiniu/skills` 默认分支运行，也可在 Actions 页面手动触发。参考资料有变化时，workflow 使用同一个分支创建或更新同步 PR，由维护者审阅合并。

同步 PR 使用仓库的 `GITHUB_TOKEN`。首次运行前，请在上游仓库的 **Settings → Actions → General → Workflow permissions** 确认已启用 **Allow GitHub Actions to create and approve pull requests**。
