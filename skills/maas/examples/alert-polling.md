# 定时轮询日志接口对接告警服务

本示例演示如何定时轮询 `/inapi/v3/stat/log` 接口，检测 API 异常（高错误率、持续 5xx、限流激增等），并将告警推送到开源告警服务（以 **Alertmanager** 为例，也适用于 Grafana OnCall Webhook 等兼容格式）。

---

## 轮询策略

| 参数 | 推荐值 | 说明 |
|------|-------|------|
| 轮询间隔 | 5 分钟 | 与账单接口的最细粒度（`five_minute`）对齐 |
| 查询窗口 | 最近 10 分钟 | 覆盖 2 个轮询周期，避免遗漏边界请求 |
| page_size | 1 | 只需 `total` 字段，不关心具体记录 |

> 每次轮询时，`start` = 当前时间 − 10 分钟，`end` = 当前时间，以滚动窗口方式覆盖。

---

## 告警规则

| 规则名称 | 触发条件 | 严重度 |
|---------|---------|-------|
| `HighErrorRate` | 窗口内失败率 ≥ 10% 且总请求 ≥ 10 | `warning` |
| `CriticalErrorRate` | 窗口内失败率 ≥ 30% 且总请求 ≥ 5 | `critical` |
| `ServerErrorSpike` | 窗口内 5xx 请求数 ≥ 5 | `warning` |
| `RateLimitSpike` | 窗口内 429 请求数 ≥ 10 | `warning` |

---

## 数据获取：每轮需调用的接口

### 1. 获取总请求数

```
GET /inapi/v3/stat/log
  ?start=<now-10min>&end=<now>
  &page=1&page_size=1
```

取 `data.total` → `totalCount`

### 2. 获取失败请求数

```
GET /inapi/v3/stat/log
  ?start=<now-10min>&end=<now>
  &status=failure
  &page=1&page_size=1
```

取 `data.total` → `failCount`

### 3. 获取服务端错误数

```
GET /inapi/v3/stat/log
  ?start=<now-10min>&end=<now>
  &status=server_error
  &page=1&page_size=1
```

取 `data.total` → `serverErrorCount`

### 4. 获取限流错误数（429）

```
GET /inapi/v3/stat/log
  ?start=<now-10min>&end=<now>
  &code=429
  &page=1&page_size=1
```

取 `data.total` → `rateLimitCount`

---

## 参考实现（Node.js）

```javascript
const crypto = require('crypto');
const https = require('https');

// ── 配置 ──────────────────────────────────────────────
const QINIU_AK = process.env.QINIU_ACCESS_KEY;
const QINIU_SK = process.env.QINIU_SECRET_KEY;
const ALERTMANAGER_URL = process.env.ALERTMANAGER_URL; // e.g. http://alertmanager:9093/api/v2/alerts
const POLL_INTERVAL_MS = 5 * 60 * 1000;  // 5 分钟
const WINDOW_MINUTES = 10;                // 滑动窗口

// ── 七牛 AK/SK 签名（HMAC-SHA1 + Bearer Qiniu）
// 参考官方文档：https://developer.qiniu.com/kodo/1201/access-token
function makeAuthHeader(method, path, host) {
  // method + 空格 + path?query 在同一行，GET 无 body
  const signingStr = `${method} ${path}\nHost: ${host}\n\n`;
  const hmac = crypto.createHmac('sha1', QINIU_SK).update(signingStr).digest();
  const encodedSign = hmac.toString('base64').replace(/\+/g, '-').replace(/\//g, '_');
  return `Qiniu ${QINIU_AK}:${encodedSign}`;
}

// ── 调用日志接口 ────────────────────────────────────────
async function fetchLogTotal(params) {
  const qs = new URLSearchParams({ page: '1', page_size: '1', ...params }).toString();
  const path = `/ai/inapi/v3/stat/log?${qs}`;
  const host = 'api.qiniu.com';
  const auth = makeAuthHeader('GET', path, host);

  return new Promise((resolve, reject) => {
    const req = https.request({ host, path, method: 'GET', headers: { Authorization: auth } }, (res) => {
      let body = '';
      res.on('data', (chunk) => { body += chunk; });
      res.on('end', () => {
        if (res.statusCode !== 200) {
          reject(new Error(`HTTP ${res.statusCode}: ${body}`));
          return;
        }
        try {
          const json = JSON.parse(body);
          resolve(json?.data?.total ?? 0);
        } catch (e) {
          reject(new Error(`Parse error: ${body}`));
        }
      });
    });
    req.on('error', reject);
    req.end();
  });
}

// ── 推送告警到 Alertmanager ────────────────────────────
async function sendAlerts(alerts) {
  const body = JSON.stringify(alerts);
  const url = new URL(ALERTMANAGER_URL);
  const transport = url.protocol === 'https:' ? https : require('http');
  const defaultPort = url.protocol === 'https:' ? 443 : 80;
  return new Promise((resolve, reject) => {
    const req = transport.request({
      host: url.hostname,
      port: url.port || defaultPort,
      path: url.pathname,
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) }
    }, (res) => { res.resume(); res.on('end', resolve); });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

// ── 主轮询逻辑 ─────────────────────────────────────────
async function poll() {
  const now = new Date();
  const windowStart = new Date(now.getTime() - WINDOW_MINUTES * 60 * 1000);
  const start = windowStart.toISOString();
  const end = now.toISOString();

  const [totalCount, failCount, serverErrorCount, rateLimitCount] = await Promise.all([
    fetchLogTotal({ start, end }),
    fetchLogTotal({ start, end, status: 'failure' }),
    fetchLogTotal({ start, end, status: 'server_error' }),
    fetchLogTotal({ start, end, code: '429' }),
  ]);

  const errorRate = totalCount > 0 ? failCount / totalCount : 0;
  const alerts = [];

  const baseLabels = {
    job: 'qiniu-maas',
    instance: 'api.qiniu.com',
  };

  if (totalCount >= 5 && errorRate >= 0.3) {
    alerts.push({
      labels: { ...baseLabels, alertname: 'CriticalErrorRate', severity: 'critical' },
      annotations: {
        summary: `MaaS 错误率过高：${(errorRate * 100).toFixed(1)}%`,
        description: `近 ${WINDOW_MINUTES} 分钟内，共 ${totalCount} 次请求，失败 ${failCount} 次（${(errorRate * 100).toFixed(1)}%）`,
      },
      startsAt: now.toISOString(),
    });
  } else if (totalCount >= 10 && errorRate >= 0.1) {
    alerts.push({
      labels: { ...baseLabels, alertname: 'HighErrorRate', severity: 'warning' },
      annotations: {
        summary: `MaaS 错误率偏高：${(errorRate * 100).toFixed(1)}%`,
        description: `近 ${WINDOW_MINUTES} 分钟内，共 ${totalCount} 次请求，失败 ${failCount} 次（${(errorRate * 100).toFixed(1)}%）`,
      },
      startsAt: now.toISOString(),
    });
  }

  if (serverErrorCount >= 5) {
    alerts.push({
      labels: { ...baseLabels, alertname: 'ServerErrorSpike', severity: 'warning' },
      annotations: {
        summary: `MaaS 服务端错误激增：${serverErrorCount} 次 5xx`,
        description: `近 ${WINDOW_MINUTES} 分钟内，出现 ${serverErrorCount} 次 5xx 错误，请检查七牛 MaaS 服务状态`,
      },
      startsAt: now.toISOString(),
    });
  }

  if (rateLimitCount >= 10) {
    alerts.push({
      labels: { ...baseLabels, alertname: 'RateLimitSpike', severity: 'warning' },
      annotations: {
        summary: `MaaS 限流激增：${rateLimitCount} 次 429`,
        description: `近 ${WINDOW_MINUTES} 分钟内，出现 ${rateLimitCount} 次限流（429），建议检查各 API Key 的 RPM 配置或请求并发`,
      },
      startsAt: now.toISOString(),
    });
  }

  if (alerts.length > 0) {
    await sendAlerts(alerts);
    console.log(`[${now.toISOString()}] 推送 ${alerts.length} 条告警`);
  } else {
    console.log(`[${now.toISOString()}] 一切正常（total=${totalCount}, fail=${failCount}, 5xx=${serverErrorCount}, 429=${rateLimitCount}）`);
  }
}

// ── 启动（自调度，避免并发漂移）─────────────────────────
async function runLoop() {
  await poll().catch(console.error);
  setTimeout(runLoop, POLL_INTERVAL_MS);
}
runLoop();
```

**启动方式：**
```bash
QINIU_ACCESS_KEY=your_ak \
QINIU_SECRET_KEY=your_sk \
ALERTMANAGER_URL=http://localhost:9093/api/v2/alerts \
node alert-polling.js
```

---

## Alertmanager 接收告警格式（参考）

每次推送的 payload 为 JSON 数组：

```json
[
  {
    "labels": {
      "alertname": "HighErrorRate",
      "severity": "warning",
      "job": "qiniu-maas",
      "instance": "api.qiniu.com"
    },
    "annotations": {
      "summary": "MaaS 错误率偏高：12.3%",
      "description": "近 10 分钟内，共 120 次请求，失败 15 次（12.3%）"
    },
    "startsAt": "2026-04-21T10:05:00.000Z"
  }
]
```

此格式同样兼容 **Grafana OnCall**（Legacy Alertmanager Webhook）和其他支持 Alertmanager API v2 格式的服务。

---

## 对接其他告警服务

### Grafana OnCall（Webhook 模式）

将 `ALERTMANAGER_URL` 替换为 Grafana OnCall 提供的 Webhook 地址，payload 格式保持不变。

### 企业微信 / 钉钉 Webhook

若需对接即时通讯告警，将 `sendAlerts` 替换为以下格式：

```javascript
// 企业微信 Webhook
async function sendWechatAlert(alert) {
  const body = JSON.stringify({
    msgtype: 'markdown',
    markdown: {
      content: `## ⚠️ ${alert.labels.alertname}\n${alert.annotations.description}`
    }
  });
  // POST to https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY
}
```

---

## 运行环境建议

| 方案 | 说明 |
|------|------|
| 独立进程（Node.js） | 适合已有 Node.js 基础设施，直接 `node alert-polling.js` 运行 |
| Docker 容器 | 封装为镜像，挂载环境变量，配合 `restart: always` 保持常驻 |
| Kubernetes CronJob | 将轮询改为 CronJob，每 5 分钟触发一次，去除 `setInterval` |
| Prometheus Exporter | 将指标（errorRate、serverErrorCount 等）暴露为 `/metrics`，由 Prometheus 配合 AlertingRule 触发，不直接调用 Alertmanager |

---

## 注意事项

- 签名算法需严格遵循七牛 AK/SK 规范，`Content-Type` 为空字符串时 signingStr 中对应行也须保留（不可省略换行）
- 日志接口时间范围不超过 35 天；10 分钟滑动窗口远在限制以内
- `image` / `video` 类型日志暂不支持 `code`/`status` 过滤，上述轮询逻辑仅适用于 `server_type=chat`（默认值）
- 告警在错误消除后需要发送 `endsAt` 字段通知 Alertmanager 恢复，否则告警会持续显示（可在下一轮正常时推送 `endsAt = now`）
- 建议为轮询脚本本身配置心跳检测（如 [Healthchecks.io](https://healthchecks.io)），防止脚本静默退出导致漏报
