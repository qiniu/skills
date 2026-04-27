# MaaS 平台凭证类型与 AK/SK 签名说明

## 1. 凭证类型辨析

MaaS 平台存在两类**相互独立、用途完全不同**的凭证，混用会造成权限泄露：

### 平台管理凭证（AK / SK）

| 属性 | 说明 |
|------|------|
| 形态 | AccessKey（AK）+ SecretKey（SK），两段独立字符串 |
| 用途 | 调用平台管理接口：**日志查询、用量统计、API Key 的增删改查** |
| 鉴权方式 | HMAC-SHA1 签名，请求头格式：`Authorization: Qiniu <AK>:<EncodedSign>` |
| 权限范围 | 可操作账户下所有 API Key 和数据，**权限极高** |
| 泄露后果 | 攻击者可创建/删除全部 API Key、读取所有用量和日志记录 |
| 保管要求 | **只能在服务端/脚本中使用**，绝不能出现在客户端代码、版本控制或日志中 |

AK/SK 覆盖两类操作场景，建议使用独立凭证隔离：
- **数据读取**（日志监控、用量面板、对接 Grafana 等）：只读操作，但仍使用 AK/SK 签名
- **写操作**（创建/删除/禁用 Key、修改限额）：写操作，建议仅由授权的管理脚本持有

### 模型调用 API Key（sk-xxx）

| 属性 | 说明 |
|------|------|
| 形态 | `sk-` 开头的单段字符串，由 MaaS 平台生成 |
| 用途 | **业务代码调用 AI 模型**（OpenAI 兼容接口） |
| 鉴权方式 | 直接放入请求头：`Authorization: Bearer sk-xxxxx` |
| 权限范围 | 仅能调用 AI 模型，无法访问任何管理接口 |
| 泄露后果 | 第三方可消耗该 Key 的配额；可通过设置日/月限额控制损失上限 |
| 保管要求 | 不得硬编码在代码中，泄露后立即在平台禁用 |

### 凭证使用规则速查

```
业务代码调用 AI 模型  →  使用 API Key（sk-xxx）
                             ↓
                     Authorization: Bearer sk-xxx

管理脚本 / 告警系统 / 周报任务  →  使用 AK/SK 签名
                                        ↓
                               Authorization: Qiniu AK:sig
```

> **绝对禁止**：在业务代码（前端/移动端/服务端开放接口）中使用 AK/SK；  
> **绝对禁止**：将 AK/SK 提交到 Git 仓库或写入日志。

---

## 2. AK/SK 签名算法

> 参考官方文档：https://developer.qiniu.com/kodo/1201/access-token

### 步骤一：生成待签名原始字符串

1. 拼接 HTTP Method（大小写敏感）、空格、Path
2. 如果有 query，拼接 ? 和 query
3. 换行，拼接 Host 头（`Host: <空格>+Host`）
4. 如果有 Content-Type 头，拼接 `Content-Type: <空格>+Content-Type`
5. 如果有 `X-Qiniu-` 开头的自定义头，按 ASCII 排序后，拼接 `<Key>: <空格>+<Value>`，每个一行
6. 最后拼接两个换行符
7. 如果有 Body 且 Content-Type 不为 `application/octet-stream`，Body 也要拼接在末尾

**示例（GET 无 Body）：**
```
GET /ai/inapi/v3/apikeys
Host: api.qiniu.com

```

### 步骤二：HMAC-SHA1 签名

用 SecretKey 对上一步生成的原始字符串做 HMAC-SHA1 签名，得到二进制签名数据。

### 步骤三：URL 安全 Base64 编码

对签名结果做 URL Safe Base64 编码（将 `+` 替换为 `-`，`/` 替换为 `_`）。末尾的 `=` 填充**保留**，不要去除。

### 步骤四：拼接最终请求头

```
Authorization: Qiniu <AccessKey>:<EncodedSign>
```

---

## 3. JavaScript 示例（Node.js，服务端使用）

> 依赖内置模块 `crypto`，无需额外安装。  
> **AK/SK 通过环境变量注入，不要硬编码。**

```js
const crypto = require('crypto');
const https = require('https');

function urlsafeBase64Encode(buffer) {
  return buffer.toString('base64').replace(/\+/g, '-').replace(/\//g, '_');
}

function signQiniuAccessToken(accessKey, secretKey, method, path, host, contentType = '', xQiniuHeaders = {}, body = '') {
  let signingStr = method + ' ' + path;
  signingStr += '\nHost: ' + host;
  if (contentType) signingStr += '\nContent-Type: ' + contentType;
  const xQiniuKeys = Object.keys(xQiniuHeaders).sort();
  xQiniuKeys.forEach(key => {
    signingStr += `\n${key}: ${xQiniuHeaders[key]}`;
  });
  signingStr += '\n\n';
  if (body && contentType && contentType !== 'application/octet-stream') signingStr += body;
  const sign = crypto.createHmac('sha1', secretKey).update(signingStr).digest();
  const encodedSign = urlsafeBase64Encode(sign);
  return `${accessKey}:${encodedSign}`;
}

// AK/SK 从环境变量读取，不要直接写入代码
const ak = process.env.QINIU_ACCESS_KEY;
const sk = process.env.QINIU_SECRET_KEY;
const method = 'GET';
const path = '/ai/inapi/v3/apikeys';
const host = 'api.qiniu.com';

const token = signQiniuAccessToken(ak, sk, method, path, host);

const req = https.request({
  hostname: host,
  path: path,
  method: method,
  headers: { 'Authorization': 'Qiniu ' + token }
}, res => {
  let data = '';
  res.on('data', chunk => data += chunk);
  res.on('end', () => console.log('Response:', data));
});
req.end();
```

---

## 4. 浏览器（仅用于调试，禁止生产使用）

> **SecretKey 绝不能暴露在前端生产环境！** 以下代码仅供本地调试和学习。

```js
async function urlsafeBase64Encode(arrayBuffer) {
  const bytes = new Uint8Array(arrayBuffer);
  let str = '';
  for (let i = 0; i < bytes.length; i++) str += String.fromCharCode(bytes[i]);
  return btoa(str).replace(/\+/g, '-').replace(/\//g, '_');
}

async function signQiniuAccessTokenBrowser(accessKey, secretKey, method, path, host, contentType = '', xQiniuHeaders = {}, body = '') {
  let signingStr = method + ' ' + path;
  signingStr += '\nHost: ' + host;
  if (contentType) signingStr += '\nContent-Type: ' + contentType;
  const xQiniuKeys = Object.keys(xQiniuHeaders).sort();
  xQiniuKeys.forEach(key => {
    signingStr += `\n${key}: ${xQiniuHeaders[key]}`;
  });
  signingStr += '\n\n';
  if (body && contentType && contentType !== 'application/octet-stream') signingStr += body;
  const enc = new TextEncoder();
  const key = await window.crypto.subtle.importKey(
    'raw', enc.encode(secretKey),
    { name: 'HMAC', hash: 'SHA-1' }, false, ['sign']
  );
  const signature = await window.crypto.subtle.sign('HMAC', key, enc.encode(signingStr));
  return `${accessKey}:${await urlsafeBase64Encode(signature)}`;
}

// 仅限调试
(async () => {
  const token = await signQiniuAccessTokenBrowser('YOUR_AK', 'YOUR_SK', 'GET', '/ai/inapi/v3/apikeys', 'api.qiniu.com');
  const res = await fetch('https://api.qiniu.com/ai/inapi/v3/apikeys', {
    headers: { 'Authorization': 'Qiniu ' + token }
  });
  console.log(await res.json());
})();
```

> 再次提醒：**SK 绝不能出现在生产前端代码中。**
