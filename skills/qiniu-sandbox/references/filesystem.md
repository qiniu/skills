# 文件、目录、传输与监听

以下示例使用已连接的 `sandbox`；Go 使用 `sb` 和 `ctx`。文件路径是沙箱内的 POSIX 路径，本地文件路径属于调用应用所在机器。写入会覆盖同路径文件，删除和重命名前确认任务范围。

启用 Envd token 的 Go／Node 文件 HTTP 读写，以及三个 SDK 的公开签名 URL，需要先确认已包含 [配套文件鉴权修复](sources.md#配套-sdk-修复)。发布基线中的签名编码与服务端不一致，Go 默认过期时间和批量上传鉴权也有缺口；只给 URL 传绝对过期时间不能解决这些问题。

## 方法映射

| 任务 | Go：`sb.Files()` | Node.js：`sandbox.files` | Python：`sandbox.files` |
| --- | --- | --- | --- |
| 文本读取 | `ReadText(ctx, path)` → string | `await readText(path, opts)` | `read_text(path, user=None, **opts)` |
| 二进制读取 | `Read(ctx, path)` → `[]byte` | `await read(path, {format: 'bytes'})` → Buffer | `read(path, fmt='bytes')` → bytearray |
| 读取流 | `ReadStream(ctx, path)` → `io.ReadCloser`，调用方关闭 | `await read(path, {format: 'stream'})` → Readable | `read(path, fmt='stream')` → 分块迭代器 |
| 写一个文件 | `Write(ctx, path, []byte)` → `*EntryInfo` | `await write(path, data, opts)` → EntryInfo | `write(path, data, user=None, **opts)` → 文件信息 |
| 批量写入 | `WriteFiles(ctx, []sandbox.WriteEntry)` | `await writeFiles([{path, data}], opts)`，或 `write` 数组重载 | `write_files([{'path': path, 'data': data}], **opts)` |
| 元信息 | `GetInfo(ctx, path)` | `await getInfo(path, opts)` | `get_info(path, user=None, timeout=None)` |
| 列目录 | `List(ctx, path, WithDepth(n))` | `await list(path, {depth: n})` | `list(path, depth=n)` |
| 是否存在 | `Exists(ctx, path)` | `await exists(path, opts)` | `exists(path, user=None, timeout=None)` |
| 建目录 | `MakeDir(ctx, path)` | `await makeDir(path, opts)` | `make_dir(path, user=None, timeout=None)` |
| 删除 | `Remove(ctx, path)` | `await remove(path, opts)` | `remove(path, user=None, timeout=None)` |
| 重命名／移动 | `Rename(ctx, old, new)` | `await rename(old, new, opts)` | `rename(old, new, user=None, timeout=None)` |

元信息包含名称、路径、类型，以及接口返回的大小、权限、owner、group、修改时间等字段；字段的完整程度取决于读取接口。列目录默认深度为 1。`exists` 只把不存在转换为 false，鉴权和网络错误仍应处理；普通读取或写入直接执行，无需先做存在性预检查。

## 本地上传与下载

Python 支持读取对象作为上传数据，以及分块下载：

```python
with open('input.bin', 'rb') as source:
    sandbox.files.write('/home/user/input.bin', source)
with open('output.bin', 'wb') as target:
    for chunk in sandbox.files.read('/home/user/input.bin', fmt='stream'):
        target.write(chunk)
```

Node.js 发布基线的 write 只接受 string、Buffer、Uint8Array 或 ArrayBuffer，下载 stream 也先缓冲。下例适合小文件；配套修复版还支持 Readable 输入和端到端流式下载。

```javascript
const fs = require('node:fs/promises');
await sandbox.files.write('/home/user/input.bin', await fs.readFile('input.bin'));
const data = await sandbox.files.read('/home/user/input.bin', { format: 'bytes' });
await fs.writeFile('output.bin', data);
```

使用配套修复版时，Node.js 16 及以上可用 `pipeline` 传输并处理流错误：

```javascript
const fs = require('node:fs');
const { pipeline } = require('node:stream/promises');
await sandbox.files.write('/home/user/input.bin', fs.createReadStream('input.bin'), {
  requestTimeoutMs: 60000
});
const source = await sandbox.files.read('/home/user/input.bin', {
  format: 'stream', requestTimeoutMs: 60000
});
await pipeline(source, fs.createWriteStream('output.bin'));
```

上传源在正常结束前关闭，无论发生在调用前还是传输中，都会使本次上传失败并释放连接；需要重新上传时重新创建输入流。`requestTimeoutMs: 0` 显式关闭传输时限，只有任务确实需要时再使用。

配套 Python SDK 的 Envd 文件请求不自动跟随重定向；收到 30x 时按请求失败处理，避免把 Envd token 带给其他来源。排查时核对实例的 Envd 地址和代理配置，修正端点后重新请求。

Go `Write` 接受 `[]byte`；下载可使用 `ReadStream` 逐块写到本地：

```go
data, err := os.ReadFile("input.bin")
if err != nil {
	return err
}
if _, err := sb.Files().Write(ctx, "/home/user/input.bin", data); err != nil {
	return err
}
src, err := sb.Files().ReadStream(ctx, "/home/user/input.bin")
if err != nil {
	return err
}
defer src.Close()
dst, err := os.Create("output.bin")
if err != nil {
	return err
}
_, copyErr := io.Copy(dst, src)
return errors.Join(copyErr, dst.Close())
```

示例位于返回 error 的函数中，需要 `os`、`io`、`errors`。本地 `output.bin` 会被创建或截断。批量写入在 Go／Node.js 使用一次 multipart 请求；Python `write_files` 逐个调用 write，失败时可能已有部分文件写入，应根据任务检查各个目标。

## 批量文件和目录

```javascript
await sandbox.files.makeDir('/home/user/job');
await sandbox.files.writeFiles([
  { path: '/home/user/job/a.txt', data: 'a\n' },
  { path: '/home/user/job/b.txt', data: 'b\n' }
]);
const entries = await sandbox.files.list('/home/user/job', { depth: 1 });
await sandbox.files.rename('/home/user/job/a.txt', '/home/user/job/result.txt');
console.log(entries.map(entry => entry.path));
```

Go 的 `WriteEntry` 字段为 `Path`、`Data`；Python 使用字典或 `(path, data)` 元组。只删除本次任务创建、已经读取并确认不再需要的文件或目录。

## 目录事件

三个 SDK 的监听接口有不同的消费方式：

| SDK | 创建与消费 | 结束与错误 |
| --- | --- | --- |
| Go | `watch, err := sb.Files().WatchDir(ctx, path, sandbox.WithRecursive(true))`；读取 `watch.Events()` channel | `watch.Stop()`；channel 关闭后检查 `watch.Err()` |
| Node.js | `await sandbox.files.watchDir(path, onEvent, {recursive: true, onExit})`；`onEvent` 接收 `{name, type}` | `watch.stop()`；`onExit` 接收流结束信息 |
| Python | `watch = sandbox.files.watch_dir(path, recursive=True)`；主动调用 `watch.get_new_events(timeout=...)` | `watch.stop()`；支持 context manager，在退出时停止 watcher |

Node.js 的 recursive watch 需要匹配的 Envd 版本，旧模板会明确报错；按错误更新模板。Python 使用 CreateWatcher／GetWatcherEvents／RemoveWatcher 轮询 API；不能把它写成 Node.js 风格回调。

```python
with sandbox.files.watch_dir('/home/user/job') as watch:
    sandbox.files.write('/home/user/job/watched.txt', 'event\n')
    events = watch.get_new_events(timeout=10)
    for event in events:
        print(event.name, event.type)
```

Go／Node.js 通过流接收事件，持续消费期间由应用决定观察时间并停止。事件类型包括 create、write、remove、rename、chmod；监听是变更通知，业务验收还应读取目标文件。

## 签名上传／下载 URL

以下 URL 示例使用已包含配套文件鉴权修复的 SDK。URL 由已连接实例生成，权限绑定路径、操作和用户。下载使用 GET；上传使用 POST multipart/form-data，字段名为 `file`。签名 URL 是临时访问凭证，应只交给获授权的调用方。

| SDK | 下载 | 上传 |
| --- | --- | --- |
| Go | `sb.DownloadURL(path, sandbox.WithSignatureExpiration(int(time.Now().Add(5*time.Minute).Unix())))` | `sb.UploadURL(path, opts...)` |
| Node.js | `sandbox.downloadUrl(path, {signatureExpiration: 300})` | `sandbox.uploadUrl(path, {signatureExpiration: 300})` |
| Python | `sandbox.download_url(path, signature_expiration=300)` | `sandbox.upload_url(path, signature_expiration=300)` |

Node.js／Python 将小于十亿的过期值按相对秒数转换为 Unix 时间，也接受绝对 Unix 秒。Go 的 `WithSignatureExpiration` 接受绝对 Unix 秒；修复版省略此选项时默认当前时间加 300 秒。三个 SDK 的签名都遵循 Envd 的 UTF-8 SHA256、无填充标准 Base64 和 `v1_` 前缀。Go 使用 `WithFileUser(user)`；Node.js／Python 使用 `user` 指定操作用户。

Python 直接把签名 URL 交给 HTTP 客户端：

```python
import requests

url = sandbox.upload_url('/home/user/upload.txt', signature_expiration=300)
with requests.post(url, files={'file': ('upload.txt', b'uploaded\n')},
                   timeout=30, allow_redirects=False) as response:
    if not 200 <= response.status_code < 300:
        raise RuntimeError('Upload returned HTTP {}'.format(response.status_code))
with requests.get(sandbox.download_url('/home/user/upload.txt'),
                  timeout=30, allow_redirects=False) as download:
    if not 200 <= download.status_code < 300:
        raise RuntimeError('Download returned HTTP {}'.format(download.status_code))
    assert download.content == b'uploaded\n'
```

qshell 的小文件 stdin／stdout 传输见 [cli.md](cli.md)，它走 Commands 接口，不受文件 HTTP 签名问题影响；直接调用 Go 文件 HTTP 接口时仍需使用含修复的 SDK。Node.js 单文件 `write` 可指定 `useOctetStream`／`gzip`，需要 Envd ≥ 0.5.7；普通 multipart 示例不依赖这些选项。Go 使用请求 context；Python 读写的 `request_timeout` 以秒为单位，目录 RPC 使用 `timeout`。配套 Node SDK 的 `requestTimeoutMs` 以毫秒覆盖单次传输，发布基线尚未转发这一选项。跨语言迁移时对照当前方法签名。
