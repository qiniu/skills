# qshell 安装指南

## 快速安装

运行 [`install.sh`](install.sh) 即可自动完成检测平台、下载、安装和配置 PATH：

```bash
bash references/install.sh
```

> **Windows 用户：** 安装脚本仅支持 macOS 和 Linux。Windows 用户请从 [GitHub Releases](https://github.com/qiniu/qshell/releases) 手动下载对应的 `.zip` 包并将 `qshell.exe` 添加到 PATH 中。

## 脚本行为说明

1. **获取版本** — 通过 GitHub API 查询 [qiniu/qshell](https://github.com/qiniu/qshell/releases) 最新 release 版本号
2. **检测平台** — 自动识别 macOS/Linux + amd64/arm64/386 架构
3. **下载** — 从 `kodo-toolbox-new.qiniu.com` 下载（需带 Referer `https://developer.qiniu.com`，脚本已内置）
4. **安装** — 解压到临时目录，将二进制移动到 `$HOME/.local/bin/qshell`（可通过 `QSHELL_INSTALL_DIR` 环境变量自定义安装路径）
5. **配置 PATH** — 如果安装目录不在 PATH 中，自动追加到 `~/.bashrc` 和 `~/.zshrc`（防重复）
6. **验证** — 执行 `qshell version` 确认安装成功

## 配置账号

安装完成后配置七牛账号：

```bash
qshell account <AccessKey> <SecretKey> <Name>
```

- `AccessKey` 和 `SecretKey`：从[七牛控制台](https://portal.qiniu.com/user/key)获取
- `Name`：自定义名称，用于本地区分多个账号

### 账号管理

```bash
qshell account          # 查看当前账号
qshell user ls          # 列出所有已配置账号
qshell user cu <Name>   # 切换账号
```

## 更新 qshell

重新执行安装脚本即可覆盖更新，会自动获取最新版本。
