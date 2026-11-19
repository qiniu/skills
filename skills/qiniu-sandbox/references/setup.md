# 环境与鉴权

## 选择工具

| 场景 | 安装／依赖 | 安装来源 |
| --- | --- | --- |
| 直接执行运维命令 | 下载 [qshell 最新发行包](https://github.com/qiniu/qshell/releases/latest)，将 `qshell` 放入 PATH | 已核对 v2.22.1 |
| Go 应用，沿用稳定版签名 | `go get github.com/qiniu/go-sdk/v7@v7.31.0` | Go module 稳定版 |
| Go 应用，需要新版分页和鉴权 | `go get github.com/qiniu/go-sdk/v7@v7.31.1-0.20261119025108-d01bf5d6d62d` | 已合并提交对应的 Go 伪版本 |
| Node.js／TypeScript 应用 | `npm install --save-exact https://codeload.github.com/qiniu/nodejs-sdk/tar.gz/a2ead373b7a29c61440cfc4e10298ae1975147f5` | GitHub v8.0.0 固定源码 |
| Python 应用 | `python -m pip install 'qiniu @ https://codeload.github.com/qiniu/python-sdk/tar.gz/af43f5afda06f48adef27a99aa1f7d777645d054'` | GitHub v7.20.0 固定源码 |
| 解释器上下文与富媒体执行结果 | [Code Interpreter 兼容 SDK](code-interpreter.md) | 版本见主题页 |

截至 2026-11-19，公开 npm 的 `qiniu` 最新为 7.15.2，缺少 Sandbox 模块。PyPI 最新为 7.18.0，已有 Sandbox 模块，可用 `python -m pip install 'qiniu==7.18.0'` 安装旧版。等所需版本进入包仓库后，可以改用该渠道对应的版本号。在已有项目中沿用当前依赖，若要升级则先核对 [接口迁移和源码基线](sources.md)。

Go 稳定版 `List` 返回切片，伪版本返回含 `Items` 和 `NextToken` 的页对象。两种签名及旧版 HTTP 分页见 [parameters.md](parameters.md#列表过滤与分页)。

## 凭据与端点

本技能的原生 SDK 示例统一从 `QINIU_SANDBOX_API_KEY` 读取 API Key，并显式传给客户端；端点从可选的 `QINIU_SANDBOX_ENDPOINT` 读取。Code Interpreter／Desktop 兼容 SDK 的 `E2B_*` 配置按各自主题页映射到七牛端点。通过用户已有的环境或密钥管理方式提供值，避免把密钥写进代码、命令参数、日志和版本控制。

客户端默认端点为 `https://cn-yangzhou-1-sandbox.qiniuapi.com`。已有项目配置了其他环境时，沿用其端点，并确认模板、沙箱和凭据属于该环境。

七牛[Windows 沙箱指南](https://developer.qiniu.com/las/13633/sandbox-windows)已列出扬州 `https://cn-yangzhou-1-sandbox.qiniuapi.com` 和达拉斯 `https://us-south-1-sandbox.qiniuapi.com`。这是已核对的端点示例，具体模板和地域可用性以当前环境为准；切换地域后重新查询模板。不要把 PPIO 的 `PPIO_DOMAIN` 或地域名传给七牛客户端。

qshell 原生使用 `QINIU_API_KEY`、`QINIU_SANDBOX_API_URL`，可这样复用上述配置：

```bash
: "${QINIU_SANDBOX_API_KEY:?Set QINIU_SANDBOX_API_KEY}"
export QINIU_API_KEY="$QINIU_SANDBOX_API_KEY"
if [ -n "${QINIU_SANDBOX_ENDPOINT:-}" ]; then
  export QINIU_SANDBOX_API_URL="$QINIU_SANDBOX_ENDPOINT"
fi
```

qshell 也接受 `E2B_API_KEY`／`E2B_API_URL`，同类 `QINIU_*` 配置优先。Go SDK 的 `Config.APIKey` 需要显式赋值；Node.js 客户端自动读取 `QINIU_SANDBOX_API_KEY`；Python 客户端依次读取 `QINIU_SANDBOX_API_KEY`、`QINIU_API_KEY`、`E2B_API_KEY`。SDK 示例中的显式配置让不同语言使用同一份环境设置。

普通沙箱和模板操作使用 API Key。管理保存的注入规则需要 AK／SK；Kodo 挂载还需按所选 SDK 的资源配置提供对应凭据。只有任务涉及这些功能时，才读取 [sources.md](sources.md) 中的资源和注入参考。qshell 的 AK／SK 优先取当前账号，再取 `QINIU_ACCESS_KEY`／`QINIU_SECRET_KEY`。

## 常见错误

| 现象 | 下一步 |
| --- | --- |
| 命令不存在、模块导入失败、方法或 flag 不存在 | 核对安装位置、依赖版本以及 `qshell sandbox <command> --help`，再选择对应版本的接口 |
| 401／403 | 核对当前工具实际使用的凭据、端点和资源权限；报告状态码和请求 ID，隐藏认证头 |
| 模板或沙箱不存在 | 在同一环境查询实际 ID；检查资源归属和沙箱是否已超时；模板查询见 [templates.md](templates.md) |
| 创建成功但命令／文件请求失败 | 核对就绪状态、沙箱域名的可达性和 Envd 鉴权；保存 ID，检查日志和指标 |
| 命令失败 | 查看退出码和 stderr，核对工作目录、运行用户、依赖及文件路径 |
| 请求超时、断网，结果未知 | 先用已记录的 ID 查询；创建和快照重试应复用原幂等键及请求体，避免重复创建资源 |

诊断时只输出必要字段。关闭会打印认证头、环境变量或注入内容的调试输出。
