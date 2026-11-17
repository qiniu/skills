# 模板定义、构建和版本管理

模板保存基础环境、构建步骤、启动命令和就绪检查。普通执行任务先查询并复用模板；需要固定依赖、文件或服务启动方式时再构建。本文示例中的 `client` 沿用所选语言接入参考中已初始化的客户端；Node.js 片段在 `async` 函数内执行，Go 片段使用 `context`、`fmt` 和 `sandbox` 包。

## 选择模板和核对身份

| 操作 | Go | Node.js | Python |
| --- | --- | --- | --- |
| 默认模板 | `client.ListDefaultTemplates(ctx)` | `await client.listDefaultTemplates()` | `client.list_default_templates()` |
| 团队模板 | `client.ListTemplates(ctx, nil)` | `await client.listTemplates()` | `client.list_templates()` |
| 详情与构建记录 | `client.GetTemplate(ctx, id, nil)` | `await client.getTemplate(id)` | `client.get_template(id)` |
| 按别名解析 | `client.GetTemplateByAlias(ctx, name)` | `await client.getTemplateByAlias(name)` | `client.get_template_by_alias(name)` |

列表返回模板数组；详情包含 `templateID`、`names`、`isOwner`、`public` 和 `builds`（Go 使用导出的 CamelCase 字段）。名称用于用户选择，后续修改、日志和删除记录实际模板 ID、构建 ID。默认示例使用的 `base` 需要在当前环境可用。

`name` 是构建目标，可带标签如 `skill-demo:v1`；同名模板已存在时，v3 创建接口沿用模板 ID 并申请新构建。`fromTemplate`／`--from-template` 指定构建所用的底模板。构建前确认目标名称和归属，避免把业务模板更新到演示环境。

## qshell：从镜像或 Dockerfile 构建

```bash
qshell sandbox template list --format json
qshell sandbox template get TEMPLATE_ID
qshell sandbox template build --name skill-demo-python --from-image python:3.12-slim --wait
```

需要本地文件、固定依赖和启动服务时，在同一项目目录保存：

`Dockerfile`：

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY ./app/ /app/
RUN python -m pip install --no-cache-dir -r /app/requirements.txt
ENV PYTHONUNBUFFERED=1
```

其中 `app/requirements.txt` 是应用依赖，`app/` 中还应有 `index.html`。`qshell.sandbox.toml`：

```toml
name = "skill-demo-web:v1"
dockerfile = "./Dockerfile"
path = "."
cpu_count = 2
memory_mb = 2048
min_disk_mb = 10240
min_free_disk_mb = 1024
start_cmd = "cd /app && python -m http.server 8080 --bind 0.0.0.0"
ready_cmd = "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080')\""
```

```bash
qshell sandbox template build --wait
qshell sandbox template get skill-demo-web:v1
qshell sandbox create skill-demo-web:v1 --detach --timeout 300
```

`--wait` 等待终态并显示构建日志。没有使用 `--wait` 时，保存返回的两个 ID，再查询：

```bash
qshell sandbox template builds TEMPLATE_ID BUILD_ID
```

| 参数／配置 | 含义 |
| --- | --- |
| `--from-image`／`from_image` | 基础 Docker 镜像 |
| `--from-template`／`from_template` | 基础模板；`--template-id`／`template_id` 是同义入口 |
| `--dockerfile`／`dockerfile` | 解析 Dockerfile 中的构建指令；可叠加在指定镜像或底模板上 |
| `--path`／`path` | 本地构建上下文；COPY 源文件从这里收集，遵循 `.dockerignore` |
| `--config` | 显式指定 TOML；默认读取当前目录的 `qshell.sandbox.toml` |
| `--cpu`／`cpu_count` | vCPU 数量 |
| `--memory`／`memory_mb` | 内存，MiB |
| `--min-disk`／`min_disk_mb` | 构建后的最小总磁盘，MiB；省略或 0 不设置最小值 |
| `--min-free-disk`／`min_free_disk_mb` | 构建后的最小剩余空间，MiB；省略使用团队默认值，0 不为剩余空间额外扩容 |
| `--no-cache`／`no_cache` | 忽略构建缓存 |
| `--start-cmd`、`--ready-cmd` | 长期运行的启动命令、可结束的就绪检查 |

CLI 参数优先于配置。镜像和底模板二选一；与 Dockerfile 组合时，所选基础环境覆盖 Dockerfile 的 FROM。磁盘不会缩小，可用空间扩容是尽力而为。构建包含 COPY 时，qshell 负责文件哈希、压缩归档及上传；提交前检查上下文是否包含凭据文件。

本地脚手架命令无需云凭据，支持 `go`、`typescript`、`python`：

```bash
qshell sandbox template init --name skill-demo --language python --path ./skill-demo
qshell sandbox template config
```

## SDK：分配构建、启动、等待

三个 SDK 都提供这三个步骤。收到模板 ID／构建 ID 只说明已分配构建；只有 `ready` 表示可使用，`error` 表示构建失败。先保存 ID，再等待，客户端超时后可继续查询原构建。

### Node.js

```javascript
async function buildTemplate(client, name) {
  const config = {
    fromImage: 'python:3.12-slim',
    steps: [
      { type: 'WORKDIR', args: ['/app'] },
      { type: 'ENV', args: ['PYTHONUNBUFFERED', '1'] },
      { type: 'RUN', args: ['printf "hello from template\\n" > /app/index.html', 'root'] }
    ],
    startCmd: 'cd /app && python -m http.server 8080 --bind 0.0.0.0',
    readyCmd: 'python -c "import urllib.request; urllib.request.urlopen(\'http://127.0.0.1:8080\')"'
  };
  const created = await client.createTemplate({ name, cpuCount: 2, memoryMB: 1024 });
  console.log('template:', created.templateID, 'build:', created.buildID);
  await client.startTemplateBuild(created.templateID, created.buildID, config);
  await client.waitForBuild(created.templateID, created.buildID, {
    timeoutMs: 600000, intervalMs: 2000
  });
  return created;
}
```

当前 `Template().build(opts)` 将构建配置发给 v3 创建接口。显式控制启动和等待时，使用上面的 `createTemplate` → `startTemplateBuild` → `waitForBuild` 流程。JavaScript builder 的运行时配置位于 `buildConfig`，当前 TypeScript 声明未暴露此属性；上面的原始配置对象可同时用于 JavaScript 和 TypeScript。

### Python

```python
from qiniu.services.sandbox import Template


def build_template(client, name):
    config = (
        Template().from_image('python:3.12-slim')
        .add_step('WORKDIR', ['/app'])
        .set_env('PYTHONUNBUFFERED', '1')
        .run_cmd('printf "hello from template\\n" > /app/index.html')
        .set_start_cmd('cd /app && python -m http.server 8080 --bind 0.0.0.0')
        .set_ready_cmd('python -c "import urllib.request; urllib.request.urlopen(\'http://127.0.0.1:8080\')"')
    )
    created = client.create_template(name=name, cpuCount=2, memoryMB=1024)
    template_id, build_id = created['templateID'], created['buildID']
    print('template:', template_id, 'build:', build_id)
    client.start_template_build(template_id, build_id, **config.to_dict())
    client.wait_for_build(template_id, build_id, timeout=600, interval=2)
    return created
```

Python `Template` 生成构建配置，通过 `to_dict()` 传给客户端。客户端的构建请求使用服务端字段名，如 `fromImage`、`cpuCount`、`memoryMB`；创建模板另外接受 `min_disk_mb`、`min_free_disk_mb` 别名。

### Go

```go
func buildTemplate(ctx context.Context, client *sandbox.Client, name string) (*sandbox.TemplateCreateResponse, error) {
	created, err := client.CreateTemplate(ctx, sandbox.CreateTemplateParams{Name: &name})
	if err != nil {
		return nil, fmt.Errorf("allocate template build: %w", err)
	}
	fmt.Println("template:", created.TemplateID, "build:", created.BuildID)
	image := "python:3.12-slim"
	args := []string{`printf "hello from template\n" > /tmp/template-demo.txt`}
	steps := []sandbox.TemplateStep{{Type: "RUN", Args: &args}}
	if err := client.StartTemplateBuild(ctx, created.TemplateID, created.BuildID, sandbox.StartTemplateBuildParams{
		FromImage: &image, Steps: &steps,
	}); err != nil {
		return created, fmt.Errorf("start template build: %w", err)
	}
	if _, err := client.WaitForBuild(ctx, created.TemplateID, created.BuildID); err != nil {
		return created, fmt.Errorf("wait for template build: %w", err)
	}
	return created, nil
}
```

Go 由调用方 context 限制构建等待时间，默认每 2 秒查询一次；可传 `sandbox.WithPollInterval(...)`。构建失败或等待超时时保留返回的 `created`，用其 ID 查询日志，避免立刻再次分配构建。

### 定义步骤和私有镜像

| 定义需求 | Go `TemplateStep`／构建参数 | Node.js builder | Python builder |
| --- | --- | --- | --- |
| 镜像／已有模板 | `FromImage`／`FromTemplate` | `.fromImage(image)`／`.fromTemplate(id)` | `.from_image(image)`／`.from_template(id)` |
| 执行命令 | `{Type: "RUN", Args: &args}` | `.runCmd(cmd, { user: 'root' })` | `.run_cmd(cmd, user='root')` |
| 环境变量 | `ENV`，Args 为键、值交替 | `.setEnvs({ KEY: 'value' })` | `.set_env('KEY', 'value')` |
| 工作目录／用户 | `WORKDIR`／`USER`，Args 单项 | `.setWorkdir(path)`／`.setUser(user)` | `.add_step('WORKDIR', [path])`／`.add_step('USER', [user])` |
| 本地文件步骤 | `COPY`，配置 `FilesHash` 后启动 | `.copy(src, dest, opts)`／`.copyItems(items)` | `.copy(src, dest)` |
| 系统／语言依赖 | `RUN` 使用对应包管理器 | `.aptInstall(...)`、`.pipInstall(...)`、`.npmInstall(...)`、`.bunInstall(...)` | `.run_cmd(...)` 使用对应包管理器 |
| Git 初始内容 | `RUN` 使用 git | `.gitClone(url, path, opts)` | `.run_cmd(...)` 使用 git |
| 启动／就绪 | `StartCmd`／`ReadyCmd` | `.setStartCmd(cmd)`／`.setReadyCmd(cmd)` | `.set_start_cmd(cmd, ready_cmd=...)`／`.set_ready_cmd(cmd)` |
| 缓存 | `Force: &force`，或单步骤 `Force` | 构建配置 `force: true`；`.skipCache()` 为后续生成的步骤设置 force 标记 | 构建配置 `force=True`，或步骤 `force=True` |

执行上述包管理器、Git 和 ready 命令的前提是镜像内已有相应可执行程序。使用 `wait_for_port` 需要 `ss`／`awk`／`grep`，`wait_for_url` 需要 `curl`；也可以像示例一样用应用运行时直接检查端口或 HTTP。Python 的 `wait_for_file(path)` 检查文件，`wait_for_process(name)` 使用 pgrep，`wait_for_timeout(milliseconds)` 将毫秒换算成 sleep 秒数；等待固定时间只表示时间已到，业务就绪优先使用实际检查。Node.js／Go 可直接传 ready 命令字符串。

私有镜像认证放在启动构建的 `fromImageRegistry`，值从环境或密钥配置读取：

| 类型 | JSON 字段 |
| --- | --- |
| 通用 registry | `type: "registry"`、`username`、`password` |
| AWS ECR | `type: "aws"`、`awsAccessKeyId`、`awsSecretAccessKey`、`awsRegion` |
| GCP | `type: "gcp"`、`serviceAccountJson`（JSON 字符串） |

Node.js `.fromImage(image, { username, password })`、`.fromAWSRegistry(...)`、`.fromGCPRegistry(...)` 生成这些字段。Python `.from_image(image, credentials=registry_dict)`；Go 将同一结构 `json.Marshal` 后转为 `sandbox.FromImageRegistry`，赋给 `StartTemplateBuildParams.FromImageRegistry`。认证对象不打印、不写入模板仓库。当前 qshell 构建参数没有 registry 凭据选项，使用 SDK 配置私有镜像认证。

本地 COPY 在原始 SDK 构建流程中还需要上传文件：先计算与步骤一致的文件哈希，Go 调用 `GetTemplateFiles`、Node.js 调用 `getTemplateFiles` 取得上传信息；`present=false` 时向返回 URL PUT 对应的 gzip tar 包，再把 `filesHash` 写入 COPY 步骤。仅声明本地路径不会自动把文件放到远端。Python 当前客户端没有专用的模板文件上传入口。需要本地 Dockerfile／COPY 的常规构建，使用上面的 qshell 流程；自建上传器应复用 [qshell 的哈希与归档实现](https://github.com/qiniu/qshell/blob/master/iqshell/sandbox/template/dockerfile/upload.go)。

## 日志、重建和版本操作

| 任务 | Go | Node.js | Python |
| --- | --- | --- | --- |
| 等待构建 | `WaitForBuild(ctx, id, buildID)` | `waitForBuild(id, buildID, { timeoutMs, intervalMs })` | `wait_for_build(id, build_id, timeout=600, interval=2)` |
| 状态 | `GetTemplateBuildStatus(ctx, id, buildID, params)` | `getTemplateBuildStatus(id, buildID, opts)` | `get_template_build_status(id, build_id, **opts)` |
| 独立日志 | `GetTemplateBuildLogs(ctx, id, buildID, params)` | `getTemplateBuildLogs(id, buildID, opts)` | `get_template_build_logs(id, build_id, **opts)` |
| 已有模板申请重建 | `RebuildTemplate(ctx, id, params)` | `rebuildTemplate(id, opts)` | `rebuild_template(id, **opts)` |
| 分配标签 | `AssignTemplateTags(ctx, ManageTagsParams{Target: target, Tags: tags})` | `assignTemplateTags({ target, tags })` | `assign_template_tags(target=target, tags=tags)` |
| 查询标签 | `ListTemplateTags(ctx, id)` | `listTemplateTags(id)` | `list_template_tags(id)` |
| 删除标签 | `DeleteTemplateTags(ctx, DeleteTagsParams{Name: name, Tags: tags})` | `deleteTemplateTags({ name, tags })` | `delete_template_tags(name=name, tags=tags)` |
| 公开／私有 | `UpdateTemplate(ctx, id, UpdateTemplateParams{Public: &public})` | `updateTemplate(id, { public: value })` | `update_template(id, public=value)` |
| 删除模板 | `DeleteTemplate(ctx, id)` | `deleteTemplate(id)` | `delete_template(id)` |

`target` 是已有模板名称与标签，如 `skill-demo:v1`；分配 `tags: ['latest']` 将 latest 指向该构建。标签查询项包含 tag、buildID、createdAt；删除标签只移除名称指向，不等于删除整个模板。所有修改都限定在用户授权的目标上。

状态请求可用 `logsOffset`、`limit`、`level`；独立日志使用 `cursor`（Unix 毫秒）、`limit`、`direction`（forward／backward）、`level`、`source`（persistent／temporary）。Go 对应强类型参数中的 `LogsOffset`／`Cursor` 等字段。Python 这些客户端查询直接使用服务端 camelCase 字段。记录日志游标与已展示条目，避免把轮询中的重复日志当成重复执行。

旧重建入口返回新的 waiting build，仍需 StartTemplateBuild；Node.js／Python 的该入口使用客户端 `accessToken`／`access_token` 配置。常规同名更新优先沿用 v3 分配流程。构建结果为 error 时检查日志中的失败步骤、包源和镜像认证、COPY 内容、运行用户及 ready 命令；调整后再发起新构建。

qshell 的标签查询、可见性和删除操作：

```bash
qshell sandbox template tags TEMPLATE_ID --format json
qshell sandbox template publish TEMPLATE_ID --yes
qshell sandbox template unpublish TEMPLATE_ID --yes
qshell sandbox template delete TEMPLATE_ID --yes
```

自动化显式传目标 ID 与 `--yes`，前提是用户已授权对应操作。没有 ID 时，命令会按当前目录配置的 name 定位；核对目录和目标后再使用。模板标签分配／删除使用上表 SDK 接口。
