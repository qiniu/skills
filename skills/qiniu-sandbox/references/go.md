# Go SDK

模块为 `github.com/qiniu/go-sdk/v7`，沙箱包为 `github.com/qiniu/go-sdk/v7/sandbox`。安装及配置见 [setup.md](setup.md)。`NewClient` 返回 `(*Client, error)`，API Key 通过 `Config` 显式设置。

## 最小完整流程

在已初始化的 Go module 中保存为 `main.go`，运行 `go run .`。通过 `QINIU_SANDBOX_TEMPLATE` 指定已有模板，默认使用 `base`。

```go
package main

import (
	"cmp"
	"context"
	"errors"
	"fmt"
	"os"
	"time"

	"github.com/qiniu/go-sdk/v7/sandbox"
)

func run() (runErr error) {
	apiKey := os.Getenv("QINIU_SANDBOX_API_KEY")
	if apiKey == "" {
		return fmt.Errorf("set QINIU_SANDBOX_API_KEY")
	}
	client, err := sandbox.NewClient(&sandbox.Config{
		APIKey: apiKey, Endpoint: os.Getenv("QINIU_SANDBOX_ENDPOINT"),
	})
	if err != nil {
		return err
	}
	template := cmp.Or(os.Getenv("QINIU_SANDBOX_TEMPLATE"), "base")
	ctx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
	defer cancel()
	ttl := int32(300)
	sb, err := client.Create(ctx, sandbox.CreateParams{TemplateID: template, Timeout: &ttl})
	if err != nil {
		return fmt.Errorf("create sandbox: %w", err)
	}
	fmt.Println("sandbox:", sb.ID())
	defer func() {
		cleanupCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
		if err := sb.Kill(cleanupCtx); err != nil {
			runErr = errors.Join(runErr, fmt.Errorf("delete sandbox %s: %w", sb.ID(), err))
		} else {
			fmt.Println("sandbox deleted:", sb.ID())
		}
	}()
	if _, err := sb.WaitForReady(ctx); err != nil {
		return fmt.Errorf("wait for sandbox: %w", err)
	}
	result, err := sb.Commands().Run(ctx, `printf "hello from qiniu sandbox\n"`)
	if err != nil {
		return fmt.Errorf("run command: %w", err)
	}
	if result.ExitCode != 0 {
		return fmt.Errorf("command exited %d: %s", result.ExitCode, result.Stderr)
	}
	fmt.Print(result.Stdout)
	const path = "/home/user/skill-demo.txt"
	const content = "hello from qiniu sandbox\n"
	if _, err := sb.Files().Write(ctx, path, []byte(content)); err != nil {
		return fmt.Errorf("write file: %w", err)
	}
	text, err := sb.Files().ReadText(ctx, path)
	if err != nil {
		return fmt.Errorf("read file: %w", err)
	}
	if text != content {
		return fmt.Errorf("file content mismatch")
	}
	return nil
}

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
```

创建成功后立即注册清理，再等待就绪，使后续步骤失败时仍能清理。清理使用独立 context，避免业务 context 超时后连删除请求也无法发出。清理失败会与业务错误一并返回，程序以非零状态退出并输出 ID，调用方还需查询和处理该资源。

## 常用接口

| 任务 | 写法 |
| --- | --- |
| 连接或恢复 | `client.Connect(ctx, id, sandbox.ConnectParams{Timeout: 300})` |
| 查询信息 | `sb.GetInfo(ctx)` |
| 设置存活时间 | `sb.SetTimeout(ctx, 300*time.Second)` |
| 暂停并保存内存 | `sb.Pause(ctx)` |
| 选择暂停方式 | `sb.PauseWithParams(ctx, sandbox.PauseParams{Memory: &keepMemory})` |
| 读取二进制 | `sb.Files().Read(ctx, path)` |
| 后台执行 | `sb.Commands().Start(ctx, command)`，返回 `CommandHandle` |
| 服务域名 | `sb.GetHost(8080)`，返回不带协议的 host |

`CreateParams.Timeout` 和 `ConnectParams.Timeout` 为秒；`SetTimeout` 使用 `time.Duration`。命令 API 返回错误和命令退出码需分别检查。完整列表、分页及更多选项从 [sources.md](sources.md) 的源码入口查阅，生命周期见 [lifecycle.md](lifecycle.md)。
