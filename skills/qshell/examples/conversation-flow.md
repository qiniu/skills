# Conversation Flow Examples

Typical interaction patterns between a user and an AI agent with the qshell skill.

## Example 1: Query Files in a Bucket

**User:** 列一下 my-images 里 2024 年上传的 jpg 文件

**Agent:**

```bash
qshell listbucket2 my-images -p "" -s 2024-01-01-00-00-00 -e 2024-12-31-23-59-59 -r
```

**Output:**

| Key | Size | MIME | Storage | Upload Time |
|-----|------|------|---------|-------------|
| photos/cat.jpg | 1.5 MB | image/jpeg | STANDARD | 2024-03-01 |
| photos/dog.jpg | 2.1 MB | image/jpeg | STANDARD | 2024-06-15 |
| banner.jpg | 856 KB | image/jpeg | STANDARD | 2024-09-20 |

Found 3 files, total size 4.4 MB.

---

## Example 2: Upload a File

**User:** 上传 ./dist/app.js 到 static-assets，key 用 js/app-v2.js

**Agent:**

```bash
qshell fput static-assets js/app-v2.js ./dist/app.js
```

Upload complete: `static-assets/js/app-v2.js` (128 KB)

---

## Example 3: Batch Delete with Safety Confirmation

**User:** 删除 temp-bucket 里 logs/ 前缀的所有文件

**Agent:**

> This is a destructive operation. Let me first check how many files will be affected.

```bash
qshell listbucket2 temp-bucket -p logs/ --show-fields Key,FileSize -r
```

Found 1,247 files (total 3.2 GB) under `logs/` prefix. **Deleting these files is irreversible.** Proceed?

**User:** 确认删除

**Agent:**

```bash
qshell listbucket2 temp-bucket -p logs/ --show-fields Key -o /tmp/keys-to-delete.txt
qshell batchdelete temp-bucket -i /tmp/keys-to-delete.txt -y --success-list /tmp/del-success.txt --failure-list /tmp/del-failure.txt
```

Deleted 1,247 files. Success: 1,247, Failed: 0.

---

## Example 4: CDN Refresh

**User:** 刷新这几个 URL 的 CDN 缓存：https://cdn.example.com/js/app.js 和 https://cdn.example.com/css/style.css

**Agent:**

```bash
printf 'https://cdn.example.com/js/app.js\nhttps://cdn.example.com/css/style.css' | qshell cdnrefresh
```

CDN refresh submitted for 2 URLs.

---

## Example 5: Generate Private Download Link

**User:** 给 private-bucket 里的 reports/q4-2024.pdf 生成一个私有下载链接

**Agent:**

```bash
qshell domains private-bucket
```

Bound domain: `cdn-private.example.com`

```bash
qshell privateurl "https://cdn-private.example.com/reports/q4-2024.pdf"
```

Private URL (valid for 1 hour):
```
https://cdn-private.example.com/reports/q4-2024.pdf?e=1709312400&token=xxx
```

---

## Example 6: Sandbox Management

**User:** 创建一个 Ubuntu 沙箱，超时 10 分钟

**Agent:**

```bash
qshell sandbox template list
```

| Template ID | Name |
|-------------|------|
| tmpl-abc123 | ubuntu-22.04 |
| tmpl-def456 | python-3.11 |

```bash
qshell sandbox create tmpl-abc123 -t 600
```

Sandbox `sb-xyz789` created and terminal connected. Timeout: 600s.

---

## Example 7: qshell Not Installed

**User:** 看看 my-bucket 有哪些文件

**Agent:**

```bash
qshell listbucket2 my-bucket
```

> `qshell: command not found`

qshell is not installed. Would you like me to install it automatically?

**User:** 好的

**Agent:** *(reads `references/install.md`, runs install script, then retries)*

```bash
qshell listbucket2 my-bucket
```

(outputs file list)
