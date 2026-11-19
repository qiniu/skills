# Code Interpreter：代码、上下文与结果

需要执行代码片段、保留变量或接收图表等结果时，使用七牛官方支持的 Code Interpreter 兼容 SDK。运行脚本文件、安装依赖和管理后台进程仍使用 [commands.md](commands.md) 的命令接口。

七牛已有解释器运行时；原生 Go／Node.js／Python `qiniu` 包当前没有 `runCode`／`run_code` 和代码上下文封装。下面的类型与方法来自 `@e2b/code-interpreter`／`e2b-code-interpreter`。Go 应用可执行脚本并读取文件产物；需要解释器上下文和富媒体结果时，通过上述兼容客户端集成。

## 依赖、模板与端点

已有项目复用兼容依赖。新项目使用下面的组合，避免基础 SDK 更新改变创建接口。

```bash
npm install --save-exact @e2b/code-interpreter@2.3.3 e2b@2.8.3
python -m pip install 'e2b-code-interpreter==2.6.0' 'e2b==2.7.0'
```

安装后用 `npm ls e2b` 或 `python -m pip show e2b` 核对基础 SDK。若 Python 兼容 SDK 在请求前检查 `e2b_` 格式，可在支持此选项的版本中设置 `E2B_VALIDATE_API_KEY=false` 或传 `validate_api_key=False`，由七牛服务端校验原始 `sk-` 密钥。若创建请求走 `POST /v2/sandboxes` 并返回 404 `method not allowed`，使用上面的兼容组合。

先按 [templates.md](templates.md) 查询目标地域的模板，确认所选模板提供 Code Interpreter／Jupyter 服务，并把其实际名称或 ID 设置为 `QINIU_SANDBOX_TEMPLATE`。普通 `base` 或自定义业务模板不保证包含解释器。依赖包的可用语言与版本由所选模板决定。

凭据沿用 [setup.md](setup.md)，兼容 SDK 使用 `E2B_*` 配置：

```bash
: "${QINIU_SANDBOX_API_KEY:?Set QINIU_SANDBOX_API_KEY}"
: "${QINIU_SANDBOX_TEMPLATE:?Select a Code Interpreter template}"
export E2B_API_KEY="$QINIU_SANDBOX_API_KEY"
export E2B_API_URL="${QINIU_SANDBOX_ENDPOINT:-https://cn-yangzhou-1-sandbox.qiniuapi.com}"
```

API Key 和 Endpoint 必须指向七牛的同一环境。兼容 SDK 会根据创建响应访问沙箱内的解释器服务；调用方不需要拼接 Jupyter 地址。

## JavaScript／TypeScript

保存为 `code-demo.mjs`，运行 `node code-demo.mjs`。输出流与最后一个表达式的结果分别处理；代码执行异常通过 `execution.error` 返回，请求失败则抛异常。

```javascript
import { Sandbox } from '@e2b/code-interpreter';

const template = process.env.QINIU_SANDBOX_TEMPLATE;
if (!template) throw new Error('Set QINIU_SANDBOX_TEMPLATE');
const sandbox = await Sandbox.create(template, { timeoutMs: 300_000 });
try {
  console.log('sandboxID:', sandbox.sandboxId);
  const execution = await sandbox.runCode('print("hello from Qiniu")\n21 * 2', {
    language: 'python', timeoutMs: 30_000, requestTimeoutMs: 40_000,
    onStdout: (output) => process.stdout.write(output.line),
    onStderr: (output) => process.stderr.write(output.line)
  });
  if (execution.error) {
    throw new Error(`${execution.error.name}: ${execution.error.value}`);
  }
  for (const result of execution.results) {
    if (result.text !== undefined) console.log(result.text);
  }
} finally {
  await sandbox.kill();
}
```

验收时应收到 stdout 中的问候和文本结果 `42`。显式记录沙箱 ID；若销毁请求失败，保留该 ID，按 [lifecycle.md](lifecycle.md) 查询并清理。

## Python

保存为 `code_demo.py`，运行 `python code_demo.py`。Python 的 TTL、执行和请求超时均以秒为单位。

```python
import os
import sys
from e2b_code_interpreter import Sandbox

template = os.environ['QINIU_SANDBOX_TEMPLATE']
sandbox = Sandbox.create(template=template, timeout=300)
try:
    print('sandboxID:', sandbox.sandbox_id)
    execution = sandbox.run_code(
        'print("hello from Qiniu")\n21 * 2',
        language='python', timeout=30, request_timeout=40,
        on_stdout=lambda output: print(output.line, end='', flush=True),
        on_stderr=lambda output: print(output.line, end='', file=sys.stderr, flush=True),
    )
    if execution.error:
        raise RuntimeError(f'{execution.error.name}: {execution.error.value}')
    for result in execution.results:
        if result.text is not None:
            print(result.text)
finally:
    sandbox.kill()
```

## 在多次执行间保留变量

同一个解释器上下文保留变量、导入和函数。需要为不同任务分离状态时，创建显式上下文，并把返回对象传给后续执行。以下片段放在上面示例的沙箱 `try` 内、`kill` 之前：

```javascript
const context = await sandbox.createCodeContext({ language: 'python' });
try {
  const setup = await sandbox.runCode('value = 40', { context });
  if (setup.error) throw new Error(setup.error.value);
  const execution = await sandbox.runCode('value + 2', { context });
  if (execution.error) throw new Error(execution.error.value);
  console.log(execution.text); // 42
} finally {
  await sandbox.removeCodeContext(context);
}
```

```python
context = sandbox.create_code_context(language='python')
try:
    setup = sandbox.run_code('value = 40', context=context)
    if setup.error:
        raise RuntimeError(setup.error.value)
    execution = sandbox.run_code('value + 2', context=context)
    if execution.error:
        raise RuntimeError(execution.error.value)
    print(execution.text)  # 42
finally:
    sandbox.remove_code_context(context)
```

| 操作 | JavaScript／TypeScript | Python |
| --- | --- | --- |
| 创建上下文 | `createCodeContext({language, cwd})` | `create_code_context(language=..., cwd=...)` |
| 使用上下文 | `runCode(code, {context})` | `run_code(code, context=context)` |
| 列举上下文 | `listCodeContexts()` | `list_code_contexts()` |
| 重启内核、清除变量 | `restartCodeContext(context)` | `restart_code_context(context)` |
| 删除上下文 | `removeCodeContext(context)` | `remove_code_context(context)` |

同次执行按 `language` 或 `context` 二选一指定。上下文分离的是解释器状态，同一沙箱中的文件、进程和网络仍属于同一环境；不同租户任务使用各自的沙箱。重启或删除上下文会丢失变量，不会替应用保存文件产物。

## 流式与富媒体结果

| 数据 | JavaScript／TypeScript | Python |
| --- | --- | --- |
| stdout／stderr 实时消息 | `onStdout`／`onStderr`，消息的 `line` | `on_stdout`／`on_stderr`，消息的 `line` |
| 展示结果实时消息 | `onResult(result)` | `on_result(result)` |
| 执行结束后的日志 | `execution.logs.stdout`／`stderr` | `execution.logs.stdout`／`stderr` |
| 执行结果集合 | `execution.results` | `execution.results` |
| 主结果文本 | `execution.text` | `execution.text` |
| 代码异常 | `execution.error` 的 `name`、`value`、`traceback` | 同左 |

每个结果可有 `text`、`html`、`png`、`jpeg` 等表示，先检查字段是否存在。PNG／JPEG 是 Base64 数据，可分别用 `Buffer.from(result.png, 'base64')` 或 `base64.b64decode(result.png)` 解码后保存；Python 先 `import base64`。用已安装绘图库产生一个小图，再验收文件格式与内容。HTML 等展示结果按应用的输出策略处理。

流回调不会替应用判定任务成功；检查执行结果中的代码异常，并单独处理创建、网络、鉴权和超时异常。日志和结果可能包含业务数据，按任务需要交付。

## 时限与故障定位

| 时限 | JavaScript／TypeScript | Python |
| --- | --- | --- |
| 沙箱 TTL，创建时设置 | `timeoutMs`（毫秒） | `timeout`（秒） |
| 单次解释器执行 | `runCode` 的 `timeoutMs` | `run_code` 的 `timeout` |
| 解释器请求等待 | `requestTimeoutMs` | `request_timeout` |

根据任务设置执行期限，并为请求返回和清理预留时间。客户端超时或断开后，先查询沙箱和业务产物；代码可能已产生副作用，重试前核对实际状态。需要终止整个临时环境时调用 `kill`。

| 现象 | 核对 |
| --- | --- |
| 创建时报模板不存在 | 同一地域查询实际模板 ID／名称及权限 |
| 普通命令可执行、runCode 连接失败 | 模板是否包含已就绪的解释器服务，所用客户端是否为 Code Interpreter SDK |
| 下一次执行找不到变量 | 沙箱和 context 是否相同、内核是否被重启／删除 |
| 请求成功但代码失败 | `execution.error` 和 stderr，核对语言、依赖和输入 |
| 没有图片结果 | 代码是否展示了图像、绘图库是否安装、结果是否包含对应 MIME 表示 |

来源：[七牛代码执行指南](https://developer.qiniu.com/las/13292/sandbox-code-interpreter)、[内部上下文回归用例（需仓库权限）](https://github.com/qbox/sandbox/blob/e3dfa87062481997412d505cccc2beaaffa49a06/tests/sdk/js-sdk/code-execution.test.ts#L121-L184)、[JS 2.3.3 发布包](https://www.npmjs.com/package/@e2b/code-interpreter/v/2.3.3)、[Python 2.6.0 发布包](https://pypi.org/project/e2b-code-interpreter/2.6.0/)。
