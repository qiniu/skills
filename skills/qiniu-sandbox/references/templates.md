# 模板

模板定义基础镜像、依赖、文件、启动命令和就绪检查。先查询用户可用的模板，普通任务优先复用已有模板；需要固定依赖或启动服务时再构建。

## 查询与使用

```bash
qshell sandbox template list --format json
qshell sandbox template get TEMPLATE_ID
qshell sandbox create TEMPLATE_ID --detach --timeout 300
```

默认模板可通过 SDK 的默认模板列表接口查询。`base` 是 SDK 示例的默认模板名；选择实际环境中可用的模板。

## 使用 qshell 构建

从镜像构建：

```bash
qshell sandbox template build --name skill-demo-python --from-image python:3.12-slim --wait
```

需要安装依赖并启动服务时，在项目目录保存以下文件。

`Dockerfile`：

```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN printf 'hello from qiniu sandbox\n' > /app/index.html
```

`qshell.sandbox.toml`：

```toml
name = "skill-demo-web"
dockerfile = "./Dockerfile"
path = "."
cpu_count = 2
memory_mb = 2048
start_cmd = "cd /app && python -m http.server 8080 --bind 0.0.0.0"
ready_cmd = "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080')\""
```

```bash
qshell sandbox template build --wait
qshell sandbox template get skill-demo-web
qshell sandbox create skill-demo-web --detach --timeout 300
```

`--wait` 等待构建并显示日志。记录返回的模板 ID、构建 ID 和最终结果；构建请求已被接受时，继续查询至完成或失败。按需查询：

```bash
qshell sandbox template builds TEMPLATE_ID BUILD_ID
```

## 参数语义

- `name` 标识目标模板；同名模板已存在时沿用其 ID 并应用本次资源设置。构建前确认名称，避免覆盖用户仍在使用的模板。
- `--from-image` 选择 Docker 镜像，`--from-template` 选择底模板；`--template-id` 同样表示底模板。目标由 `--name` 指定。
- Dockerfile 可独立使用，也可叠加在所选底模板或镜像上。`--path` 是构建上下文，COPY 的文件从该目录读取。
- CLI 参数优先于 `qshell.sandbox.toml`。`--config` 显式指定配置文件；未指定时读取当前目录的配置。
- `--memory`、`--min-disk`、`--min-free-disk` 单位为 MiB。最小总磁盘和最小可用空间是两个独立要求；可用空间省略时使用团队默认值，显式 0 表示不额外为可用空间扩容，已有文件系统不会缩小。
- 启动命令启动真实工作负载，就绪检查验证工作负载已可用。检查命令本身应可结束。

## SDK 构建与更多操作

需要把构建集成到应用时，读取所选 SDK 的模板实现和示例：

| SDK | 入口与官方参考 |
| --- | --- |
| Go | `client.CreateTemplate` → `client.StartTemplateBuild` → `client.WaitForBuild`，[模板接口](https://github.com/qiniu/go-sdk/blob/master/sandbox/template.go) |
| Node.js | `qiniu.sandbox.Template()`，[模板示例](https://github.com/qiniu/nodejs-sdk/blob/master/examples/sandbox_templates.js) |
| Python | `qiniu.services.sandbox.Template`，[模板示例](https://github.com/qiniu/python-sdk/blob/master/examples/sandbox_template_lifecycle.py) |

模板发布会改变可见性，删除会移除模板；在用户指定的模板范围内操作。本次构建成功后，查询标签和构建信息可核对实际使用的版本。磁盘、标签和详细方法签名见 [sources.md](sources.md)。
