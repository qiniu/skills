# 持久快照

快照把沙箱状态保存为可复用的模板。快照 ID 可传给创建沙箱的模板参数，从同一状态启动独立的新沙箱。本文 `sandbox`／`source` 指本次任务拥有的来源实例，`client` 为同一环境的客户端；SDK 初始化和基本清理方式沿用各语言接入参考。

## 捕获语义与参数

| 参数／结果 | 含义 |
| --- | --- |
| 来源 sandbox ID | 本次要捕获的实例，不是模板 ID |
| `memory` | 默认 true；false 只保存文件系统，从快照启动时冷启动，原进程和内存状态不保留 |
| `name` | 可选别名和标签，如 `skill-demo:v1`；创建时不能含 `/`，命名空间由账号分配 |
| 幂等键 | 每次新捕获使用新的 ASCII UUID 等唯一键；请求头 `Idempotency-Key`，长度 1–128 字节 |
| `snapshotID`／`SnapshotID` | 持久快照模板 ID，用于创建副本、查询标签和删除 |
| `names`／`Names` | 服务端返回的名称列表 |

调用前将幂等键、来源 ID 和请求体保存到任务记录。遇到断网、408 或等待超时，用原键、原来源和完全相同的请求体重试；取消客户端等待不会取消已接受的捕获。完成结果会重放，包括失败。记录在完成后保留 35 分钟，结果未知或记录可能过期时先按来源／名称查询核实，避免换键重复捕获。

文件系统快照恢复可能清理 `/tmp`，验证文件保留使用 `/home/user` 等持久路径。快照和来源实例、副本实例分别管理：销毁一个沙箱不会替代快照模板清理。

## qshell 捕获、查询、恢复、删除

```bash
qshell sandbox exec SANDBOX_ID -- sh -lc 'printf "snapshot content" > /home/user/snapshot-demo.txt'
# 生成后保存到当前任务记录，重试时复用。
CAPTURE_KEY="$(uuidgen)"
qshell sandbox snapshot create SANDBOX_ID --idempotency-key "$CAPTURE_KEY" --name skill-demo:v1 --memory=false --format json

# 读取返回的 snapshotID；按来源和名称查询，保存 NextToken。
qshell sandbox snapshot list --sandbox-id SANDBOX_ID --name skill-demo:v1 --limit 20 --format json
qshell sandbox snapshot list --sandbox-id SANDBOX_ID --name skill-demo:v1 --limit 20 --next-token NEXT_TOKEN --format json

qshell sandbox create SNAPSHOT_ID --detach --timeout 300
# 在新沙箱中核对业务文件和应用结果，随后清理该副本。
qshell sandbox exec RESTORED_SANDBOX_ID -- cat /home/user/snapshot-demo.txt
qshell sandbox kill RESTORED_SANDBOX_ID

# 快照不再需要时，删除该快照模板。
qshell sandbox template delete SNAPSHOT_ID --yes
```

CLI 列表 JSON 包含 `Items` 和 `NextToken`。每一页保留相同过滤条件，只推进游标；空游标表示遍历完成。

## Node.js：捕获与验证副本

以下片段位于 async 函数内，并已导入 `qiniu` 与 `node:crypto` 的 `randomUUID`。来源沙箱由调用方负责保留或销毁。

```javascript
const captureKey = randomUUID();
const name = `skill-demo-${captureKey}:v1`;
await sandbox.files.write('/home/user/snapshot-demo.txt', 'snapshot content');
const snapshot = await sandbox.createSnapshot({
  idempotencyKey: captureKey, name, memory: false
});
console.log('snapshot:', snapshot.snapshotID);
let restored;
try {
  restored = await qiniu.sandbox.Sandbox.create({
    client, template: snapshot.snapshotID, timeout: 300
  });
  await restored.waitForReady({ timeoutMs: 60000 });
  const text = await restored.files.readText('/home/user/snapshot-demo.txt');
  if (text !== 'snapshot content') throw new Error('Snapshot file content mismatch');
} finally {
  try {
    if (restored) await restored.kill();
  } finally {
    await client.deleteSnapshot(snapshot.snapshotID);
  }
}
```

`createSnapshot` 返回 `snapshotID`、`names`，实例封装还提供 `snapshotId`。底层 `client.createSnapshot(sandboxID, opts)` 使用同一路径。未显式传键时 Node.js SDK 会生成本次调用的键并在自动重试中复用；跨调用重试需要调用方保留的显式键。

Node.js 查询全部分页：

```javascript
const pages = sandbox.listSnapshots({ name, limit: 20 });
while (pages.hasNext) {
  for (const item of await pages.nextItems()) console.log(item.snapshotID);
}
```

`listSnapshots` 的实例封装自动限定来源沙箱；使用 `client.listSnapshotsPage({ sandboxID, name, limit, nextToken })` 可直接获得 `{ items, nextToken }`，底层 `client.listSnapshots(...)` 只返回当前页数组。

## Python：捕获与验证副本

```python
import uuid
from qiniu.services.sandbox import Sandbox

capture_key = str(uuid.uuid4())
name = 'skill-demo-{0}:v1'.format(capture_key)
sandbox.files.write('/home/user/snapshot-demo.txt', 'snapshot content')
snapshot = sandbox.create_snapshot(capture_key, name=name, memory=False)
print('snapshot:', snapshot['snapshotID'])
restored = None
try:
    restored = Sandbox.create(snapshot['snapshotID'], client=client, timeout=300)
    restored.wait_for_ready(timeout=60)
    if restored.files.read_text('/home/user/snapshot-demo.txt') != 'snapshot content':
        raise RuntimeError('Snapshot file content mismatch')
finally:
    try:
        if restored is not None:
            restored.kill()
    finally:
        client.delete_template(snapshot['snapshotID'])
```

Python 要求显式幂等键；底层入口为 `client.create_sandbox_snapshot(sandbox_id, idempotency_key, memory=None, name=None)`。返回字典，不是 Sandbox 实例。

```python
next_token = None
while True:
    page = client.list_snapshots(
        sandbox_id=sandbox.sandbox_id, name=name,
        limit=20, next_token=next_token,
    )
    for item in page['items']:
        print(item['snapshotID'])
    next_token = page['nextToken']
    if not next_token:
        break
```

Python 列表从响应 `X-Next-Token` 读取游标并包装成 `{'items': [...], 'nextToken': ...}`；最后一页 nextToken 为空。

## Go：捕获与恢复入口

Go 片段使用 `context`、`errors`、`fmt`、`time` 和 `sandbox` 包；`key` 从调用方已保存的任务记录读取。

```go
func verifySnapshot(ctx context.Context, client *sandbox.Client, source *sandbox.Sandbox, key string) (runErr error) {
	name, memory := "skill-demo-"+key+":v1", false
	const path = "/home/user/snapshot-demo.txt"
	if _, err := source.Files().Write(ctx, path, []byte("snapshot content")); err != nil {
		return err
	}
	snapshot, err := source.CreateSnapshot(ctx, sandbox.CreateSnapshotParams{
		IdempotencyKey: key, Name: &name, Memory: &memory,
	})
	if err != nil {
		return fmt.Errorf("capture snapshot: %w", err)
	}
	fmt.Println("snapshot:", snapshot.SnapshotID)
	defer func() {
		cleanupCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
		if err := client.DeleteTemplate(cleanupCtx, snapshot.SnapshotID); err != nil {
			runErr = errors.Join(runErr, fmt.Errorf("delete snapshot %s: %w", snapshot.SnapshotID, err))
		}
	}()
	ttl := int32(300)
	restored, err := client.Create(ctx, sandbox.CreateParams{TemplateID: snapshot.SnapshotID, Timeout: &ttl})
	if err != nil {
		return err
	}
	defer func() {
		cleanupCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
		if err := restored.Kill(cleanupCtx); err != nil {
			runErr = errors.Join(runErr, fmt.Errorf("delete restored sandbox %s: %w", restored.ID(), err))
		}
	}()
	if _, err := restored.WaitForReady(ctx); err != nil {
		return err
	}
	text, err := restored.Files().ReadText(ctx, path)
	if err != nil {
		return err
	}
	if text != "snapshot content" {
		return fmt.Errorf("snapshot file content mismatch")
	}
	return nil
}
```

Go 列表：

```go
func listSnapshots(ctx context.Context, client *sandbox.Client, sourceID, name string) error {
	params := &sandbox.ListSnapshotsParams{SandboxID: &sourceID, Name: &name}
	for {
		page, err := client.ListSnapshots(ctx, params)
		if err != nil {
			return err
		}
		for _, item := range page.Items {
			fmt.Println(item.SnapshotID)
		}
		if page.NextToken == "" {
			return nil
		}
		params.NextToken = &page.NextToken
	}
}
```

## 查询与清理约定

| 过滤项 | Go | Node.js | Python |
| --- | --- | --- | --- |
| 来源 | `ListSnapshotsParams.SandboxID` | `sandboxID` | `sandbox_id` |
| 名称或 ID | `Name` | `name` | `name` |
| 页大小 | `Limit *int32` | `limit` | `limit` |
| 游标 | `NextToken` | `nextToken` | `next_token` |
| 删除 | `client.DeleteTemplate(ctx, snapshotID)` | `client.deleteSnapshot(id)`／`deleteTemplate(id)` | `client.delete_template(id)` |

同名快照的新捕获需要新键；返回的快照 ID 可能仍属于同名模板的不同构建。需要长期留存时记录返回 ID、名称和标签，不在验证代码的 finally 中删除。删除模板会影响依赖该模板的后续创建，清理前核对用户要保留的快照。

快照失败时保存原键、来源 ID、请求体与错误码；结果未知时先查询原捕获，再决定复用键重试。禁止把“客户端已停止等待”当成“服务端已取消捕获”。
