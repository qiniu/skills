# 七牛云管理凭证（Access Token）生成说明

> 参考官方文档：https://developer.qiniu.com/kodo/1201/access-token

## 1. 管理凭证简介

七牛云管理凭证（Access Token）用于对资源管理类 API 请求进行鉴权。所有敏感操作（如资源删除、移动、复制、查询等）都必须在 HTTP 请求头部携带合法的 Authorization 字段，否则会返回 401 认证失败。

## 2. 签名算法步骤

### 步骤一：生成待签名原始字符串

1. 拼接 HTTP Method（大小写敏感）、空格、Path
2. 如果有 query，拼接 ? 和 query
3. 换行，拼接 Host 头（Host: <空格>+Host）
4. 如果有 Content-Type 头，拼接 Content-Type: <空格>+Content-Type
5. 如果有 X-Qiniu- 开头的自定义头，按 ASCII 排序后，拼接 <Key>: <空格>+<Value>，每个一行
6. 最后拼接两个换行符
7. 如果有 Body 且 Content-Type 不为 application/octet-stream，Body 也要拼接在末尾

**示例：**
```
POST /move/bmV3ZG9jczpmaW5kX21hbi50eHQ=/bmV3ZG9jczpmaW5kLm1hbi50eHQ=
Host: rs.qiniu.com

```

### 步骤二：HMAC-SHA1 签名

用 SecretKey 对上一步生成的原始字符串做 HMAC-SHA1 签名，得到二进制签名数据。

### 步骤三：URL 安全 Base64 编码

对签名结果做 URL Safe Base64 编码（将 + 替换为 -，/ 替换为 _）。末尾的 `=` 填充**保留**，不要去除。

### 步骤四：拼接 AccessKey 和签名

用英文冒号 : 连接 AccessKey 和编码后的签名，得到最终的 Access Token。

**最终 HTTP 请求头：**
```
Authorization: Qiniu <AccessKey>:<encodedSign>
```

## 3. 注意事项
- 所有签名步骤必须严格遵循官方算法说明。
- X-Qiniu- 开头的自定义头部需排序并格式化。
- 推荐直接使用七牛云官方 SDK 生成管理凭证，避免手动拼接出错。
- 详细规则和特殊场景请查阅[官方文档](https://developer.qiniu.com/kodo/1201/access-token)。

## 5. JavaScript 示例代码（以获取 apikeys 接口为例）

> 依赖说明：
> - 需在 Node.js 环境下运行。
> - 依赖内置模块 `crypto`，无需额外安装。

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

// 示例参数
const ak = 'YOUR_ACCESS_KEY';
const sk = 'YOUR_SECRET_KEY';
const method = 'GET';
const path = '/ai/inapi/v3/apikeys';
const host = 'api.qiniu.com';
const contentType = '';
const body = '';

const token = signQiniuAccessToken(ak, sk, method, path, host, contentType, {}, body);

const options = {
  hostname: host,
  path: path,
  method: method,
  headers: {
    'Authorization': 'Qiniu ' + token
  }
};

const req = https.request(options, res => {
  let data = '';
  res.on('data', chunk => data += chunk);
  res.on('end', () => console.log('Response:', data));
});
req.end();
```

## 6. 纯前端（浏览器）方案（以获取 apikeys 接口为例）

> 依赖说明：
> - 仅需现代浏览器（支持 Web Crypto API）。
> - 无需额外安装第三方库。

> 注意：**SecretKey 绝不能暴露在前端生产环境！**以下代码仅用于学习和测试。

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
    'raw',
    enc.encode(secretKey),
    { name: 'HMAC', hash: 'SHA-1' },
    false,
    ['sign']
  );
  const signature = await window.crypto.subtle.sign('HMAC', key, enc.encode(signingStr));
  const encodedSign = await urlsafeBase64Encode(signature);
  return `${accessKey}:${encodedSign}`;
}

// 示例用法
(async () => {
  const ak = 'YOUR_ACCESS_KEY';
  const sk = 'YOUR_SECRET_KEY';
  const method = 'GET';
  const path = '/ai/inapi/v3/apikeys';
  const host = 'api.qiniu.com';
  const contentType = '';
  const body = '';

  const token = await signQiniuAccessTokenBrowser(ak, sk, method, path, host, contentType, {}, body);

  fetch('https://api.qiniu.com/ai/inapi/v3/apikeys', {
    method: 'GET',
    headers: {
      'Authorization': 'Qiniu ' + token
    }
  })
    .then(res => res.json())
    .then(data => console.log('Response:', data));
})();
```

> 再次提醒：**SecretKey 绝不能暴露在前端生产环境！**
