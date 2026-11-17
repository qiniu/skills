# Git 与 Kodo 资源挂载

资源通过创建参数 `resources` 配置，平台在沙箱启动前将资源放到指定绝对路径。资源挂载适用于启动时准备仓库或数据；需要在运行中操作普通 Git 仓库时读取 [git.md](git.md)。

## 资源规约

Node.js／Python 的资源对象使用 API 字段名：

| 类型 | 字段 | 含义 |
| --- | --- | --- |
| `github_repository` | `url`、`mount_path`、`authorization_token` | 仓库 URL、沙箱内绝对路径、该仓库自己的访问 token |
| `kodo` | `bucket`、`mount_path` | 已存在的 Kodo bucket 和挂载路径 |
| `kodo` 可选 | `prefix`、`read_only` | 限制对象前缀、请求只读挂载 |
| `kodo` 可选 | `access_key`、`secret_key` | 该资源独立的 Kodo 凭据，二者一同提供 |

每个 GitHub 资源独立携带 token；多个仓库可用不同凭据。Kodo 资源显式提供完整 AK／SK 时，创建请求可使用 Sandbox API Key；省略资源凭据时，SDK 从客户端的 Qiniu Mac 凭据签名并提供访问凭据。Go 使用 `Config.Credentials`，Node.js 使用 `mac` 或 `accessKey`／`secretKey`，Python 使用 `mac` 或 `access_key`／`secret_key`。

查询结果只包含资源 ID 和配置，服务端隐藏凭据。资源 ID 与沙箱 ID、仓库 URL、挂载路径分别使用，更新时采用查询到的 `resource_id`。

## 创建仓库资源并轮换凭据

以下 Node.js 示例沿用已有 `qiniu`、`client`，由服务端环境提供仓库地址和本次／下一次 token。新 token 应具备目标仓库所需权限。

```javascript
const sandbox = await qiniu.sandbox.Sandbox.create({
  client, template: 'base', timeout: 300,
  resources: [{
    type: 'github_repository', url: process.env.GIT_REPO_URL,
    mount_path: '/workspace/repo', authorization_token: process.env.GITHUB_TOKEN
  }]
});
console.log('sandbox:', sandbox.sandboxID);
try {
  await sandbox.waitForReady({ timeoutMs: 60000 });
  const result = await sandbox.commands.run('test -d /workspace/repo/.git');
  if (result.exitCode !== 0) throw new Error('Repository is unavailable');
  const { resources } = await sandbox.getResources();
  const repo = resources.find(item => item.type === 'github_repository');
  if (!repo) throw new Error('Repository resource is unavailable');
  await sandbox.updateGitRepositoryResourceToken(repo.resource_id, process.env.GITHUB_TOKEN_NEXT);
} finally {
  await sandbox.kill();
}
```

轮换针对运行中该资源立即生效。它更新平台管理的凭据，不会执行 Git pull 或自动推送本地更改。仓库修改需按 [git.md](git.md) 明确提交和推送；销毁前保存需要的成果。

Go 与 Python 的创建规约：

```go
token := os.Getenv("GITHUB_TOKEN")
resources := []sandbox.SandboxResourceSpec{{GitRepository: &sandbox.GitRepositoryResource{
	Type: sandbox.GitRepositoryTypeGithub,
	URL: os.Getenv("GIT_REPO_URL"), MountPath: "/workspace/repo", AuthorizationToken: &token,
}}}
params := sandbox.CreateParams{TemplateID: "base", Resources: &resources}
```

```python
from qiniu.services.sandbox import GitRepositoryResource

resource = GitRepositoryResource(os.environ['GIT_REPO_URL'], '/workspace/repo',
    authorization_token=os.environ['GITHUB_TOKEN'])
sandbox = Sandbox.create('base', client=client, timeout=300, resources=[resource])
```

## Kodo 跨沙箱复用

下面的 Python 示例要求 Sandbox API Key 客户端 `client`，以及具备指定测试前缀读写权限的 Kodo AK／SK。它写入独立测试对象、销毁第一个沙箱、在第二个沙箱读取并移除该测试对象。保留业务数据时按用户约定保留对象。

```python
import os
import uuid
from qiniu.services.sandbox import KodoResource, Sandbox

resource = KodoResource(
    bucket=os.environ['QINIU_SANDBOX_KODO_BUCKET'], mount_path='/mnt/data',
    prefix='skill-demo/', read_only=False,
    access_key=os.environ['QINIU_SANDBOX_KODO_ACCESS_KEY'],
    secret_key=os.environ['QINIU_SANDBOX_KODO_SECRET_KEY'])
path = '/mnt/data/probe-' + uuid.uuid4().hex + '.txt'

first = Sandbox.create('base', client=client, timeout=300, resources=[resource])
try:
    first.wait_for_ready()
    first.files.write(path, 'persistent data\n')
finally:
    first.kill()

second = Sandbox.create('base', client=client, timeout=300, resources=[resource])
try:
    second.wait_for_ready()
    assert second.files.read_text(path) == 'persistent data\n'
    second.files.remove(path)
finally:
    second.kill()
```

Kodo 数据保存在 bucket 中，沙箱销毁与对象删除是两项操作。验证完成后在 Kodo 侧核对测试对象已删除。挂载使用对象存储资源，应用应按所需文件操作验证语义；不能据此假定本地块设备或任意文件系统的完整行为。

Go／Node.js 对应的 Kodo 字段：

```go
ak, sk := os.Getenv("QINIU_SANDBOX_KODO_ACCESS_KEY"), os.Getenv("QINIU_SANDBOX_KODO_SECRET_KEY")
readOnly := true
resources := []sandbox.SandboxResourceSpec{{Kodo: &sandbox.KodoResource{
	Bucket: os.Getenv("QINIU_SANDBOX_KODO_BUCKET"), MountPath: "/mnt/data",
	ReadOnly: &readOnly, AccessKey: &ak, SecretKey: &sk,
}}}
params := sandbox.CreateParams{TemplateID: "base", Resources: &resources}
```

```javascript
const resources = [{
  type: 'kodo', bucket: process.env.QINIU_SANDBOX_KODO_BUCKET,
  mount_path: '/mnt/data', prefix: 'datasets/', read_only: true,
  access_key: process.env.QINIU_SANDBOX_KODO_ACCESS_KEY,
  secret_key: process.env.QINIU_SANDBOX_KODO_SECRET_KEY
}];
```

## 查询与更新入口

| 操作 | Go | Node.js | Python |
| --- | --- | --- | --- |
| 列出实例资源 | `sb.GetResources(ctx)` → `[]SandboxResourceInfo` | `sandbox.getResources()` → `{ resources }` | `sandbox.get_resources()` → `{'resources': [...]}` |
| 按资源 ID 更新 Git token | `sb.UpdateGitRepositoryResourceToken(ctx, id, token)` | `sandbox.updateGitRepositoryResourceToken(id, token)` | `sandbox.update_git_repository_resource_token(id, token)` |

Go 的资源结果通过 `GitRepository`／`Kodo` 指针区分类型，ID 为对应对象的 `ResourceID`。PATCH 当前仅更新 GitHub 资源的 `authorization_token`，Kodo 的 bucket、路径和凭据应在创建时确定。

qshell：

```bash
qshell sandbox create TEMPLATE_ID --detach --resource 'type=kodo,bucket=BUCKET,mount-path=/mnt/data,prefix=datasets/,read-only=true'
qshell sandbox resource list SANDBOX_ID --format json
```

CLI 创建 Git 资源使用 `--resource 'type=github_repository,url=URL,mount-path=/workspace/repo,token=TOKEN'`；更新使用 `sandbox resource update SANDBOX_ID RESOURCE_ID --token TOKEN`。真实 token 放入 CLI 参数会出现在进程参数中，自动化优先使用服务端 SDK。

## Volume 边界

当前七牛 Sandbox OpenAPI 资源为 GitHub 仓库和 Kodo 挂载，没有独立 Volume 的创建、配额扩容、动态挂卸载、删除接口。Node.js 导出的 `Volume` 类是兼容入口，`create`／`list`／`delete` 均返回 `NotImplementedError`。需要持久数据时使用上面的 Kodo 资源流程；资源生命周期按 bucket／对象管理。

来源：[Go 资源类型](https://github.com/qiniu/go-sdk/blob/master/sandbox/types_resource.go)、[Node.js 资源示例](https://github.com/qiniu/nodejs-sdk/blob/master/examples/sandbox_resources.js)、[Python 资源类型](https://github.com/qiniu/python-sdk/blob/master/qiniu/services/sandbox/resources.py)、[Volume 兼容入口](https://github.com/qiniu/nodejs-sdk/blob/master/qiniu/sandbox/volume.js)。
