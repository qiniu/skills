# 环境与鉴权

## 选择工具

| 场景 | 安装 |
| --- | --- |
| 直接执行运维命令 | 下载 [qshell 最新发行包](https://github.com/qiniu/qshell/releases/latest)中与系统和架构匹配的二进制包，将 `qshell` 放入 PATH |
| Go 应用 | 在 Go module 中运行 `go get github.com/qiniu/go-sdk/v7/sandbox@latest` |
| Node.js／TypeScript 应用 | 从 [Node.js SDK 最新 Release](https://github.com/qiniu/nodejs-sdk/releases/latest)安装，见下方命令 |
| Python 应用 | 从 [Python SDK 最新 Release](https://github.com/qiniu/python-sdk/releases/latest)安装，见下方命令 |
| 解释器上下文与富媒体执行结果 | 按 [Code Interpreter 兼容 SDK](code-interpreter.md) 安装 |

有 GitHub CLI 时，以下命令直接选取各仓库的最新正式 Release。npm／PyPI 已提供项目所需接口时，也可分别使用 `npm install qiniu@latest` 和 `python -m pip install --upgrade qiniu`。

```bash
# Node.js：在项目目录执行。
node_sdk_tag="$(gh release view --repo qiniu/nodejs-sdk --json tagName --jq .tagName)" &&
  npm install --save-exact "https://codeload.github.com/qiniu/nodejs-sdk/tar.gz/refs/tags/$node_sdk_tag"
```

```bash
# Python：在空的下载目录执行。
gh release download --repo qiniu/python-sdk --pattern 'qiniu-*-py3-none-any.whl' &&
  python -m pip install ./qiniu-*-py3-none-any.whl
```

也可从发布页面下载 Python wheel 后使用同一安装命令。Node.js 可从发布页面复制正式标签，将其填入上方的 `node_sdk_tag` 后执行安装命令。

已有项目按锁定的依赖核对方法签名。旧 Go SDK 的单页签名和各语言的 HTTP 分页回退见 [parameters.md](parameters.md#列表过滤与分页)。

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

普通沙箱和模板操作使用 API Key。涉及注入规则或 Kodo 挂载时，按任务读取下列配置：

| 场景 | 凭据与示例变量 |
| --- | --- |
| SDK 管理已保存的 [注入规则](injections.md) | 使用七牛账号 AK／SK，示例从 `QINIU_SANDBOX_ACCESS_KEY`／`QINIU_SANDBOX_SECRET_KEY` 读取并显式传给客户端 |
| SDK 挂载 [Kodo 资源](resources.md) | 使用相应 bucket 的授权凭据，示例读取 `QINIU_SANDBOX_KODO_BUCKET`、`QINIU_SANDBOX_KODO_ACCESS_KEY`、`QINIU_SANDBOX_KODO_SECRET_KEY` |
| qshell 需要 AK／SK 的操作 | 优先使用当前账号，再读 `QINIU_ACCESS_KEY`／`QINIU_SECRET_KEY` |

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
