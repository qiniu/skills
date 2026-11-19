# Python SDK

依赖为 `qiniu`，入口为 `qiniu.services.sandbox`。以下代码使用 Python 3；安装和环境设置见 [setup.md](setup.md)。SDK 的命令与文件接口是同步调用。

## 最小完整流程

保存为 `sandbox_demo.py`，运行 `python sandbox_demo.py`。`QINIU_SANDBOX_TEMPLATE` 可指定已存在的模板，默认使用 `base`。

```python
import os

from qiniu.services.sandbox import Sandbox, SandboxClient


def main():
    client = SandboxClient(
        api_key=os.environ['QINIU_SANDBOX_API_KEY'],
        endpoint=os.getenv('QINIU_SANDBOX_ENDPOINT'),
    )
    sandbox = Sandbox.create(
        os.getenv('QINIU_SANDBOX_TEMPLATE', 'base'),
        client=client,
        timeout=300,
        metadata={'purpose': 'skill-demo'},
    )
    print('sandbox:', sandbox.sandbox_id)
    try:
        sandbox.wait_for_ready(timeout=60, interval=1)
        result = sandbox.commands.run('printf "hello from qiniu sandbox\\n"')
        assert result.exit_code == 0
        print(result.stdout, end='')
        path = '/home/user/skill-demo.txt'
        sandbox.files.write(path, 'hello from qiniu sandbox\n')
        assert sandbox.files.read_text(path) == 'hello from qiniu sandbox\n'
    finally:
        sandbox.kill()
        print('sandbox deleted:', sandbox.sandbox_id)


if __name__ == '__main__':
    main()
```

默认从结果检查 `exit_code`；需要非零退出时抛出异常，可设置 `throw_on_error=True`，并从 `CommandExitError` 读取命令结果。`SandboxError` 包含平台错误信息；输出错误时只保留必要字段，避免完整打印请求、环境变量或注入配置。

## 常用接口

| 任务 | 写法 |
| --- | --- |
| 连接或恢复 | `Sandbox.connect(sandbox_id, client=client, timeout=300)` |
| 查询信息 | `sandbox.get_info()` |
| 设置存活时间 | `sandbox.set_timeout(300)` |
| 暂停 | `sandbox.pause(memory=True)` |
| 恢复当前实例 | `sandbox.connect(timeout=300)` |
| 指定工作目录／环境 | `sandbox.commands.run('pwd', cwd='/home/user', envs={'MODE': 'demo'})` |
| 后台执行 | `sandbox.commands.run(command, background=True)`，返回命令句柄 |
| 读取二进制 | `sandbox.files.read(path, fmt='bytes')` |
| 写入二进制 | `sandbox.files.write(path, data)` |
| 服务域名 | `sandbox.get_host(8080)`，返回不带协议的 host |

v7.20.0 的 `Sandbox.list()` 返回分页器。用 `has_next` 和 `next_items()` 完整遍历；低层 `client.list_sandboxes()` 返回 `items` 和 `nextToken`。示例、旧方法迁移及 PyPI 旧版回退见 [列表过滤与分页](parameters.md#列表过滤与分页)。

时间参数以秒为单位。创建时的 `envs` 映射到平台的 `envVars`；SDK 参数通常使用 snake_case。生命周期与快照见 [lifecycle.md](lifecycle.md)，模板见 [templates.md](templates.md)。

进阶任务按主题读取：[进程与流式输出](commands.md)、[文件系统](filesystem.md)、[Git](git.md)、[PTY](pty.md)、[网络](network.md)、[资源挂载](resources.md)、[请求注入](injections.md)、[模板](templates.md)和[快照](snapshots.md)。先核对[语言接口差异](compatibility.md)，避免把其他 SDK 的同名方法或默认值套入当前语言。
