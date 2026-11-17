# 沙箱内 Git

Git helper 调用沙箱中安装的 `git`。它适合在运行中的沙箱内检查和修改工作副本；创建沙箱时由平台挂载 Git 仓库资源是另一个入口，挂载规则和资源凭据按资源指引处理。以下示例沿用已连接的 `sandbox`；Go 使用 `sb`、`ctx` 和 `sandbox` 包。

## 克隆和检查

Python 的公开仓库流程：

```python
result = sandbox.git.clone(
    'https://github.com/qiniu/go-sdk.git',
    path='/home/user/go-sdk', depth=1, branch='master',
    throw_on_error=True,
)
status = sandbox.git.status('/home/user/go-sdk')
print(status.current_branch, status.is_clean)
```

下列私库认证使用已包含 [配套凭据隔离修复](sources.md#配套-sdk-修复) 的 SDK。Node.js 的 HTTPS 私库认证同时传入用户名和 token，使用当前进程环境中的凭据：

```javascript
const result = await sandbox.git.clone(process.env.GIT_REPO_URL, {
  path: '/home/user/repo',
  depth: 1,
  username: process.env.GIT_USERNAME,
  password: process.env.GITHUB_TOKEN,
  envs: { GIT_TERMINAL_PROMPT: '0' },
  throwOnError: true
});
const status = await sandbox.git.status('/home/user/repo', { throwOnError: true });
console.log(status.currentBranch, status.changedFiles, status.untrackedFiles);
```

Go 对应的私库入口：

```go
result, err := sb.Git().Clone(ctx, os.Getenv("GIT_REPO_URL"), &sandbox.CloneOptions{
	Path: "/home/user/repo", Depth: 1,
	Username: os.Getenv("GIT_USERNAME"), Password: os.Getenv("GITHUB_TOKEN"),
})
if err != nil {
	return err
}
if result.ExitCode != 0 {
	return fmt.Errorf("git clone exited %d", result.ExitCode)
}
status, err := sb.Git().Status(ctx, "/home/user/repo", nil)
if err != nil {
	return err
}
fmt.Println(status.CurrentBranch, status.IsClean())
```

Go 片段位于返回 error 的函数中，需要 `os`、`fmt`。为 `GIT_REPO_URL`、`GIT_USERNAME` 和 `GITHUB_TOKEN` 提供已有授权凭据。私有认证支持和敏感数据处理有语言差异，见下文。

## 操作映射

下表中的 `path` 为仓库绝对路径，`opts` 为该语言的选项；修改工作副本和推送按用户授权的分支、文件和远程仓库执行。

| 任务 | Go：`sb.Git()` | Node.js：`sandbox.git` | Python：`sandbox.git` |
| --- | --- | --- | --- |
| 初始化 | `Init(ctx, path, *InitOptions)` | `await init(path, {initialBranch})` | `init(path, initial_branch=...)` |
| 状态 | `Status(ctx, path, *GitOptions)` | `await status(path, opts)` | `status(path, **opts)` |
| 分支列表 | `Branches(ctx, path, opts)` | `await branches(path, opts)` | `branches(path, **opts)` |
| 新建并切换分支 | `CreateBranch(ctx, path, branch, opts)` | `await createBranch(path, branch, opts)` | `create_branch(path, name, start_point=None)` |
| 切换已有分支 | `CheckoutBranch(ctx, path, branch, opts)` | `await checkoutBranch(path, branch, opts)` | `checkout_branch(path, name, create=False)` |
| 删除分支 | `DeleteBranch(ctx, path, branch, *DeleteBranchOptions)` | `await deleteBranch(path, branch, {force: false})` | `delete_branch(path, name, force=False)` |
| 暂存指定文件 | `Add(ctx, path, &AddOptions{Files: []string{...}})` | `await add(path, {files: [...]})` | `add(path, files=[...])` |
| 提交 | `Commit(ctx, path, message, *CommitOptions)` | `await commit(path, message, opts)` | `commit(path, message, author_name=None, author_email=None)` |
| 拉取 | `Pull(ctx, path, *PullOptions)` | `await pull(path, {remote, branch, ...opts})` | `pull(path, remote=None, branch=None, **opts)` |
| 推送 | `Push(ctx, path, *PushOptions)` | `await push(path, {remote, branch, ...opts})` | `push(path, remote=None, branch=None, set_upstream=True, **opts)` |
| 添加 remote | `RemoteAdd(ctx, path, name, url, *RemoteAddOptions)` | `await remoteAdd(path, name, url, opts)` | `remote_add(path, name, url, **opts)` |
| 查询 remote | `RemoteGet(ctx, path, name, opts)` | `await remoteGet(path, name, opts)` | `remote_get(path, name='origin', **opts)` |
| 设置配置 | `SetConfig(ctx, key, value, *ConfigOptions)` | `await setConfig(key, value, {scope, path})` | `set_config(key, value, scope='local', path=path)` |
| 读取配置 | `GetConfig(ctx, key, *ConfigOptions)` | `await getConfig(key, {scope, path})` | `get_config(key, scope='local', path=path)` |
| reset | `Reset(ctx, path, *ResetOptions)` | `await reset(path, {mode, target, paths})` | `reset(path, target=None, mode=None, **opts)` |
| restore | `Restore(ctx, path, *RestoreOptions)` | `await restore(path, {paths, staged, source})` | `restore(path, paths=None, staged=False, source=None, **opts)` |

Go 返回的 `GitStatus` 和 Python 状态对象包含当前分支、upstream、ahead／behind 和文件状态；Node.js 当前状态结果为 `currentBranch`、`changedFiles`、`untrackedFiles` 和原始 stdout。不要跨语言假定状态结果字段完全相同。

查询 remote 时，Go `RemoteGet` 和 Node.js `remoteGet` 返回 URL 字符串；Python `remote_get` 返回命令结果，检查 `exit_code` 后从 `stdout.strip()` 读取 URL。

Go 通用 `GitOptions` 提供 `Envs`、`User`、`Cwd`、`Timeout time.Duration`；Node.js／Python 使用命令选项，例如 `cwd`、`user`、`envs` 和输出回调。Go 的 Git 调用会把非零退出转换为错误；Node.js 默认要检查 `exitCode`，可设置 `throwOnError: true`。Python `status` 会对失败抛错，其他操作按返回结果或 `throw_on_error=True` 检查。

## 本地提交流程

先检查状态并明确文件列表，再设置仓库级作者信息、创建分支、暂存和提交：

```python
repo = '/home/user/repo'
status = sandbox.git.status(repo)
sandbox.git.configure_user(repo, 'Sandbox Bot', 'sandbox@example.com', throw_on_error=True)
sandbox.git.create_branch(repo, 'sandbox/task', throw_on_error=True)
sandbox.git.add(repo, files=['result.txt'], throw_on_error=True)
sandbox.git.commit(repo, 'Add task result', throw_on_error=True)
```

该片段假设 `result.txt` 已按任务生成，`sandbox/task` 尚不存在；提交只修改沙箱中的仓库。推送前核对授权目标，可用 `remote_get` 查询对应 URL。Node.js 使用 `configureUser(repo, name, email, {scope: 'local'})`；Go 使用 `ConfigureUser(ctx, name, email, &sandbox.ConfigOptions{Scope: sandbox.GitConfigScopeLocal, Path: repo})`。

## 凭据和语言差异

- 配套修复版对显式临时凭据使用命令级 `credential.helper=` 隔离已有 helper，避免已有 store／cache 保存本次凭据；未传临时认证参数的普通调用继续使用项目原配置。Node.js 用临时 helper 和进程环境传入凭据，Go 的 clone 默认在结束后移除 origin URL 凭据；显式 `DangerouslyStoreCredentials` 会保留它，push／pull 的临时 remote 凭据在操作后恢复。
- 配套 Python `Git.clone` 接受 `username`、`password` 和 `user`；clone／pull／push 的私有临时目录、askpass 上传、命令及清理均使用同一用户。前台结束后清理；后台操作保留句柄并调用 `wait()`，使凭据文件在操作完成后清理。
- 发布基线尚未包含这些隔离修复，且 Python clone 没有实现凭据参数。需要在该基线上克隆私库时，使用授权的 Git 资源挂载，或下面显式清空继承 helper 的命令流程。

配套 Python SDK 的私库调用：

```python
import os

result = sandbox.git.clone(
    os.environ['GIT_REPO_URL'], path='/home/user/repo',
    username=os.environ['GIT_USERNAME'], password=os.environ['GITHUB_TOKEN'],
    user='user', throw_on_error=True,
)
```

命令级回退把 token 放入本次沙箱进程环境，只用于用户已授权向沙箱提供凭据的任务：

```python
import os

command = '''git -c credential.helper= -c 'credential.helper=!f() { printf "username=%s\\npassword=%s\\n" "$GIT_USERNAME" "$GIT_PASSWORD"; }; f' clone --depth 1 "$GIT_REPO_URL" /home/user/repo'''
result = sandbox.commands.run(command, envs={
    'GIT_TERMINAL_PROMPT': '0',
    'GIT_USERNAME': os.environ['GIT_USERNAME'],
    'GIT_PASSWORD': os.environ['GITHUB_TOKEN'],
    'GIT_REPO_URL': os.environ['GIT_REPO_URL'],
}, throw_on_error=True)
```

持久认证是显式选择的另一种凭据生命周期：

| SDK | 入口 | 持久化内容与清理 |
| --- | --- | --- |
| Go | `DangerouslyAuthenticate(ctx, &AuthenticateOptions{Username, Password, Host, Protocol})` | 设置用户级 `credential.helper=store`，通过 `git credential approve` 保存凭据；默认 Host 为 github.com，Protocol 为 https。结束后按同一 host／username 调用 `git credential reject`，并恢复任务前的 helper 配置 |
| Node.js | `await dangerouslyAuthenticate(path, remote, username, password, opts)` | 将带凭据的 URL 写入该仓库 `.git/config` 的 remote；结束后用已记录的不含凭据的 URL 恢复对应 remote |
| Python | `dangerously_authenticate(username, password, host='github.com', protocol='https', **opts)` | 使用用户级 credential store，清理同 Go 的凭据记录与 helper 配置 |

只修改本次任务配置，保留已有账号配置。优先使用单次操作的临时认证。返回错误、日志或 remote URL 中可能含敏感信息，输出前只保留必要信息。

## reset、restore 和默认值

`reset --hard`、工作区 restore、强制删除分支会丢弃改动或引用，先核对用户要求的具体范围。路径级取消暂存可使用 Node.js `reset(path, {paths: ['result.txt']})`、Python `reset(path, paths=['result.txt'])`、Go `ResetOptions{Paths: []string{"result.txt"}}`；有路径时不混用重置模式。

Go `Add` 无文件列表且 `All=nil` 时默认暂存全部；Node.js／Python 没给文件列表时通常暂存 `.`。因此示例显式列出文件。Python `delete_branch` 的默认 `force=True`，需要保留未合并分支时显式传 `force=False`；Go／Node.js 的默认强制行为不同，也应明确选项。

Go 默认 `PushOptions.SetUpstream=nil` 和 Python `set_upstream=True` 会尝试配置 upstream；Node.js push 只使用给定 remote／branch，首次设 upstream 可通过 `commands.run('git push --set-upstream ...')`，按实际仓库名和分支正确引用参数。缺少 upstream 的 pull 应选择明确 remote 和 branch，避免反复执行同一个失败命令。

qshell 没有独立的沙箱 Git helper 命令组；可通过 `qshell sandbox exec SANDBOX_ID -- git -C /home/user/repo status --short --branch` 查询。凭据型操作使用 SDK 或平台资源配置，避免把 token 放在 CLI 参数里。

2026-11-17 云端回归在新建的七牛沙箱内启动了隔离的 HTTPS Git 服务，使用测试专用账号验证 Go／Node.js／Python 的认证 clone、commit、push 和 pull。匿名请求被拒绝，推送后的远端文件内容正确，remote 未残留凭据，预设的 credential store 未保存临时密码；测试沙箱已清理。这验证了 SDK 的私库交互与凭据隔离，未验证外部 Git 托管平台的账号权限或组织策略。
