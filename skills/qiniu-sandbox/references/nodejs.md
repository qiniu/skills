# Node.js／TypeScript SDK

依赖为 `qiniu`，入口为 `qiniu.sandbox.SandboxClient` 和 `qiniu.sandbox.Sandbox`。安装与环境设置见 [setup.md](setup.md)。TypeScript 可以使用 `import * as qiniu from 'qiniu'`，接口类型随 SDK 提供。

需要截图、键鼠或 noVNC 时，使用 [Node.js 原生 Desktop 指引](desktop.md#nodejs-原生-desktop)。

## 最小完整流程

以下示例使用 Node.js 18 或更新版本。将代码保存为 `sandbox-demo.cjs`，运行 `node sandbox-demo.cjs`。`QINIU_SANDBOX_TEMPLATE` 可指定已存在的模板，默认使用 `base`。

```javascript
const assert = require('node:assert/strict');
const qiniu = require('qiniu');

async function main() {
  const apiKey = process.env.QINIU_SANDBOX_API_KEY;
  if (!apiKey) throw new Error('Set QINIU_SANDBOX_API_KEY');
  const client = new qiniu.sandbox.SandboxClient({
    apiKey,
    endpoint: process.env.QINIU_SANDBOX_ENDPOINT
  });
  const sandbox = await qiniu.sandbox.Sandbox.create({
    client,
    template: process.env.QINIU_SANDBOX_TEMPLATE || 'base',
    timeout: 300,
    metadata: { purpose: 'skill-demo' }
  });
  console.log('sandbox:', sandbox.sandboxID);
  try {
    await sandbox.waitForReady({ timeoutMs: 60000, intervalMs: 1000 });
    const result = await sandbox.commands.run('printf "hello from qiniu sandbox\\n"');
    assert.equal(result.exitCode, 0);
    process.stdout.write(result.stdout);
    const path = '/home/user/skill-demo.txt';
    await sandbox.files.write(path, 'hello from qiniu sandbox\n');
    assert.equal(await sandbox.files.readText(path), 'hello from qiniu sandbox\n');
  } finally {
    try {
      await sandbox.kill();
      console.log('sandbox deleted:', sandbox.sandboxID);
    } catch (error) {
      console.error(`Failed to delete sandbox ${sandbox.sandboxID}: ${error.message}`);
      process.exitCode = 1;
    }
  }
}

main().catch(err => {
  console.error(err.message);
  process.exitCode = 1;
});
```

默认从结果检查 `exitCode`；需要非零退出时抛出异常，可设置 `throwOnError: true`，并从 `CommandExitError` 读取命令结果。清理失败时保留 ID 并报告失败，继续查询资源状态。

## 常用接口

| 任务 | 写法 |
| --- | --- |
| 连接或恢复已有沙箱 | `await qiniu.sandbox.Sandbox.connect(id, { client, timeout: 300 })` |
| 查询信息 | `await sandbox.getInfo()` |
| 设置存活时间 | `await sandbox.setTimeout(300)`，单位为秒 |
| 暂停 | `await sandbox.pause({ memory: true })` |
| 执行时设置环境／目录 | `await sandbox.commands.run('pwd', { cwd: '/home/user', envs: { MODE: 'demo' } })` |
| 后台执行 | `await sandbox.commands.run(command, { background: true })`，返回命令句柄 |
| 读取二进制 | `await sandbox.files.read(path, { format: 'bytes' })` |
| 写入二进制 | `await sandbox.files.write(path, buffer)` |
| 服务域名 | `sandbox.getHost(8080)`，返回不带协议的 host |

`Sandbox.list()` 返回分页器。用 `hasNext` 和 `nextItems()` 完整遍历；低层 `client.listSandboxes()` 返回 `{ items, nextToken }`。示例及旧版回退见 [列表过滤与分页](parameters.md#列表过滤与分页)。

设置沙箱存活时间时，`timeout` 为秒，`timeoutMs` 为毫秒，选用其中一个即可。`SandboxClient({ timeout })` 的 HTTP 请求超时为毫秒。生命周期与快照见 [lifecycle.md](lifecycle.md)，模板见 [templates.md](templates.md)。

进阶任务按主题读取：[进程与流式输出](commands.md)、[文件系统](filesystem.md)、[Git](git.md)、[PTY](pty.md)、[网络](network.md)、[资源挂载](resources.md)、[请求注入](injections.md)、[模板](templates.md)和[快照](snapshots.md)。先核对[语言接口差异](compatibility.md)，避免把其他 SDK 的同名方法或默认值套入当前语言。
