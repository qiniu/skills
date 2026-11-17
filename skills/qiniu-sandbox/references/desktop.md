# Desktop 与 Computer Use

`desktop` 是带 Xfce、Xvfb 和桌面自动化工具的预构建沙箱模板。先确认所用地域已发布该模板。Go 使用七牛原生 Desktop 封装；Node.js／Python 可按[官方 Desktop 指南](https://developer.qiniu.com/las/13576/sandbox-desktop)使用 E2B 兼容 Desktop SDK 接入七牛端点。

## Go：创建、截图和操作

以下函数使用已配置的 `*sandbox.Client`。保存的 `desktop.png` 是本次任务产物；真实截图可能包含用户数据，按任务的交付范围处理。

```go
func captureDesktop(ctx context.Context, client *sandbox.Client) (runErr error) {
	ttl := int32(300)
	desktop, err := client.CreateDesktop(ctx, sandbox.DesktopCreateParams{
		CreateParams: sandbox.CreateParams{Timeout: &ttl},
		Resolution: sandbox.ScreenSize{Width: 1024, Height: 768},
	})
	if err != nil {
		return err
	}
	defer func() {
		cleanupCtx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
		defer cancel()
		runErr = errors.Join(runErr, desktop.Kill(cleanupCtx))
	}()
	if err := desktop.Open(ctx, "https://www.qiniu.com"); err != nil {
		return err
	}
	if err := desktop.Wait(ctx, 3*time.Second); err != nil {
		return err
	}
	pngData, err := desktop.Screenshot(ctx)
	if err != nil {
		return err
	}
	return os.WriteFile("desktop.png", pngData, 0o600)
}
```

导入 `context`、`errors`、`os`、`time` 和 `github.com/qiniu/go-sdk/v7/sandbox`。`CreateDesktop` 默认模板为 `desktop`，默认分辨率 1024 × 768、DPI 96、Display `:0`；它创建沙箱、等待就绪并启动图形桌面。中途失败时 SDK 尽力清理已创建的沙箱。

包装已有沙箱使用 `sandbox.NewDesktop(sb, sandbox.DesktopOptions{})`，之后显式 `desktop.Start(ctx)`；包装动作本身不启动桌面。底模板需具备 Xvfb、Xfce、xdotool 和截图工具。

## Go 操作表

| 目标 | 方法与参数 |
| --- | --- |
| 屏幕／光标 | `ScreenSize(ctx)` → `ScreenSize`；`CursorPosition(ctx)` → `Point` |
| 移动鼠标 | `MoveMouse(ctx, Point{X: x, Y: y})` |
| 单击／双击 | `Click(ctx, MouseButtonLeft, &point)`；`DoubleClick(ctx, &point)`；point 为 nil 时使用当前位置 |
| 右键／按下／松开 | `Click(ctx, MouseButtonRight, &point)`；`MouseDown(ctx, button)`；`MouseUp(ctx, button)` |
| 拖动／滚动 | `Drag(ctx, from, to)`；`Scroll(ctx, ScrollDirectionDown, amount)` |
| 输入文字 | `TypeText(ctx, text, nil)`；可通过 `TypeTextOptions` 设置 Unicode 分块大小及字符间隔 |
| 按键 | `Press(ctx, "ctrl", "l")`、`Press(ctx, "enter")` |
| 打开／启动程序 | `Open(ctx, pathOrURL)`；`Launch(ctx, application, args...)` |
| 窗口 | `ActiveWindowID(ctx)`、`ApplicationWindows(ctx, application)`、`WindowTitle(ctx, id)` |
| 等待／截图 | `Wait(ctx, duration)`；`Screenshot(ctx)` → PNG `[]byte` |

坐标以实际桌面分辨率为准；给视觉模型的截图和动作坐标使用同一坐标系。模型返回动作后校验类型、坐标和输入范围，再调用 SDK。业务循环设置明确的任务完成条件、最大步数和时限；结束时释放沙箱。

桌面命令非零退出会返回 `DesktopCommandError`，包含操作名及 `CommandResult`。截图在沙箱中使用临时文件，SDK 读取后移除；应用仍需在销毁前保存需要的文件或录制结果。

## Go：noVNC

对于已有 `desktop`：

```go
stream := desktop.Stream()
if err := stream.Start(ctx, nil); err != nil {
	return err
}
viewURL, err := stream.URL(&sandbox.DesktopStreamURLOptions{ViewOnly: true})
if err != nil {
	return err
}
authKey, err := stream.AuthKey()
if err != nil {
	return err
}
```

`viewURL` 默认不包含密码；通过应用的已鉴权响应安全交付 URL 和 `authKey`，不要写入日志。需要把密码带入 URL 时，调用方明确设置 `DesktopStreamURLOptions.AuthKey`；此时整个 URL 按凭据处理。

| 设置／操作 | 语义 |
| --- | --- |
| `DesktopStreamOptions.VNCPort`／`WebPort` | 默认 5900／6080，端口不能相同 |
| `RequireAuth` | `nil` 默认开启随机 VNC 密码；使用 `*bool` 显式配置 |
| `WindowID` | 只共享指定 X11 窗口 |
| URL 的 `AutoConnect`／`ViewOnly`／`Resize` | 自动连接默认开启；缩放为 `scale`（默认）、`off` 或 `remote` |
| `Stop(ctx)` | 停止 VNC 和 noVNC，清除本地密码状态；不销毁沙箱 |

一次桌面只运行一个流，切换窗口流前先停止旧流。交互结束先调用 `Stop`，任务结束再 `Kill`。无论哪一步失败，都记录实际状态并完成剩余资源清理。

VNC 密码和平台的服务流量 token 是两层鉴权。关闭公共流量时，浏览器还需要能携带平台 Header 的 HTTP／WebSocket 代理；原理见 [network.md](network.md)。仅关闭浏览器页签不会停止桌面流或沙箱。

## JavaScript／Python 兼容接入

七牛原生 `qiniu` Node.js／Python 包当前没有 Desktop 类；以下是官方提供的兼容 SDK 路线，包名和时间单位与原生 SDK 分开使用。配置 `E2B_API_KEY` 和 `E2B_API_URL` 为七牛对应地域端点。

安装 `@e2b/desktop` 后，TypeScript：

```typescript
import { Sandbox as DesktopSandbox } from '@e2b/desktop';
const session = await DesktopSandbox.create('desktop', { timeoutMs: 300_000 });
try {
  const image = await session.screenshot();
  // 将 image 交给业务侧保存或视觉模型。
} finally {
  await session.kill();
}
```

安装 `e2b-desktop` 后，Python：

```python
from e2b_desktop import Sandbox as DesktopSandbox
session = DesktopSandbox.create(template='desktop', timeout=300)
try:
    image = session.screenshot()
finally:
    session.kill()
```

兼容 SDK 的鼠标、输入和流服务方法按其安装版本及官方指南核对，不调用不存在的 `qiniu.sandbox.Desktop`。详见 [compatibility.md](compatibility.md)。

来源：[Go Desktop](https://github.com/qiniu/go-sdk/blob/master/sandbox/desktop.go)、[Go noVNC](https://github.com/qiniu/go-sdk/blob/master/sandbox/desktop_stream.go)、[七牛 Desktop 官方指南](https://developer.qiniu.com/las/13576/sandbox-desktop)。
