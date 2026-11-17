# 网络与服务鉴权

客户端配置沿用 [setup.md](setup.md)，创建和清理沿用所选语言指南。先决定出网范围、服务入站方式，再配置网络；这两种流量方向分别生效。

## 配置字段

Node.js 和 Python 的 `network` 字典使用下表中的 API 字段名，Python 不会将这些嵌套键自动转为 camelCase。

| API 字段 | Go `NetworkConfig` | 含义 |
| --- | --- | --- |
| `allowOut` | `AllowOut *[]string` | 允许的出站 IP／CIDR |
| `denyOut` | `DenyOut *[]string` | 拒绝的出站 IP／CIDR |
| `allowPublicTraffic` | `AllowPublicTraffic *bool` | 应用服务是否允许无流量 token 的请求 |
| `maskRequestHost` | `MaskRequestHost *string` | 转发给沙箱应用的 Host 掩码 |

创建选项 `allowInternetAccess`（Python：`allow_internet_access`，Go：`AllowInternetAccess *bool`）控制出站互联网访问。`secure` 控制 Envd 的命令、文件等管理接口；应用服务的公开性通过 `allowPublicTraffic` 决定。API Key、Envd token、服务流量 token 各自用于对应接口。

仅允许指定地址出网的创建配置：

```javascript
const sandbox = await qiniu.sandbox.Sandbox.create({
  client, template: 'base', timeout: 300, secure: true,
  network: {
    denyOut: ['0.0.0.0/0'], allowOut: ['1.1.1.1/32'],
    allowPublicTraffic: false
  }
});
```

```python
sandbox = Sandbox.create('base', client=client, timeout=300, secure=True,
    network={'denyOut': ['0.0.0.0/0'], 'allowOut': ['1.1.1.1/32'],
             'allowPublicTraffic': False})
```

```go
denyOut := []string{"0.0.0.0/0"}
allowOut := []string{"1.1.1.1/32"}
publicTraffic := false
params := sandbox.CreateParams{
	TemplateID: "base",
	Network: &sandbox.NetworkConfig{
		DenyOut: &denyOut, AllowOut: &allowOut, AllowPublicTraffic: &publicTraffic,
	},
}
```

创建成功后立即登记沙箱 ID 和清理逻辑。出网规则可能影响包安装、Git 或外部 API 调用；只给任务需要的目标放行。域名解析可能得到多个地址，按实际服务与平台支持的规则配置。

## 网络配置变更

将任务需要的网络规则、公共服务访问和 Host 掩码在创建时配置完整。当前公开服务端 API 未提供运行时网络更新：`/sandboxes/{sandboxID}` 仅定义 GET 和 DELETE。Node.js 的 `updateNetwork` 与 Python 的 `update_network` 虽有 SDK 封装，但它们发送的 `PATCH /sandboxes/{id}` 没有对应的公开服务端操作，不能作为可用更新流程。

现有沙箱需要变更网络时，先保存所需业务数据，再使用新的网络配置创建沙箱并恢复业务。验证新沙箱的目标可达性、应用就绪和外部访问后，按 [生命周期流程](lifecycle.md) 清理旧沙箱。

## 私有服务访问

服务应监听 `0.0.0.0`。用 `getHost(port)`／`get_host(port)`／`GetHost(port)` 取得不带协议的 host，组合成 `https://<host>`。先从沙箱内探测服务就绪，再从调用方访问。

当 `allowPublicTraffic=false` 时，外部请求需要 Header `e2b-traffic-access-token`。Node.js 和 Python 在创建返回值中保留 `trafficAccessToken`；保留该次创建响应，避免误用 API Key 或 Envd token。

Node.js 的 `waitForReady` 会用详情响应替换 `sandbox.info`，详情不含创建时的流量 token。JavaScript 可读取实例的 `sandbox.trafficAccessToken`；该成员目前未在 TypeScript 类型中声明。需要 TypeScript 接入时，在创建阶段显式保存原始响应，再包装为 Sandbox：

```javascript
const created = await client.createSandbox({
  template: 'base', timeout: 300, network: { allowPublicTraffic: false }
});
const token = created.trafficAccessToken;
const sandbox = new qiniu.sandbox.Sandbox({ client, info: created });
```

随后登记清理、等待就绪并启动所需应用。下面的请求片段放在沙箱服务已就绪、监听 8080 后以及清理之前，`token` 使用创建阶段保存的值：

```javascript
if (!token) throw new Error('Service traffic token is unavailable');
const response = await fetch(`https://${sandbox.getHost(8080)}/`, {
  headers: { 'e2b-traffic-access-token': token }
});
if (!response.ok) throw new Error(`Service returned HTTP ${response.status}`);
```

```python
import requests

token = sandbox.traffic_access_token
if not token:
    raise RuntimeError('Service traffic token is unavailable')
response = requests.get('https://' + sandbox.get_host(8080) + '/',
    headers={'e2b-traffic-access-token': token}, timeout=10)
response.raise_for_status()
```

Go 的 `Sandbox` 内部保存流量 token，但当前公开类型没有读取该值的方法；`SandboxInfo` 也不返回该字段。使用 Go 访问私有服务前，需要由能返回创建响应 token 的调用端安全交付该值。公开服务可在创建时明确设置 `AllowPublicTraffic=true`，再按应用自身的认证策略访问。

浏览器地址栏不能为任意 URL 附加该 Header。受限网页或 noVNC 需要由应用提供携带认证头的代理；将 token 保留在服务端，代理同时处理普通 HTTP 和 WebSocket。详情见 [desktop.md](desktop.md)。

## Host 与排错

`maskRequestHost` 用于让沙箱中的应用收到预期的 Host，适用于虚拟主机路由。这个字段与外部访问 URL 分开配置，先以实际应用预期的值验证请求转发。

| 现象 | 核对 |
| --- | --- |
| 沙箱内可访问、外部 401／403 | 公共流量设置、服务 token、调用方是否发送了正确 Header |
| 外部连接失败 | 监听地址、端口、服务进程和就绪检查、返回域名的可达性 |
| 返回错误站点或 Host 校验失败 | 应用的 Host 校验以及 `maskRequestHost` |
| 外部 API 或依赖安装失败 | 出网开关和 allow／deny 规则，区分 DNS、连接与远端鉴权错误 |

来源：[公开 API 定义](https://github.com/qbox/sandbox/blob/e3dfa87062481997412d505cccc2beaaffa49a06/spec/openapi-public.yml#L1840-L1878)、[Node.js Sandbox 实现](https://github.com/qiniu/nodejs-sdk/blob/master/qiniu/sandbox/sandbox.js)、[Python 客户端](https://github.com/qiniu/python-sdk/blob/master/qiniu/services/sandbox/client.py)、[Go 网络类型](https://github.com/qiniu/go-sdk/blob/master/sandbox/types.go)、[服务代理认证头](https://github.com/qbox/sandbox/blob/main/packages/client-proxy/internal/proxy/proxy.go)。
