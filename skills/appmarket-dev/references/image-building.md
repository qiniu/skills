# 应用镜像制作指南

本指南介绍如何为 AppMarket 应用制作自定义系统镜像。LAS 的自定义镜像是云主机系统盘快照，通过「创建云主机 → 安装配置软件 → 创建自定义镜像」的方式制作。

---

## 目录

- [1. 镜像制作概述](#1-镜像制作概述)
- [2. 一键制作镜像（推荐）](#2-一键制作镜像推荐)
- [3. 编写安装脚本](#3-编写安装脚本)
- [4. 手动制作镜像](#4-手动制作镜像)
- [5. 初始化脚本开发](#5-初始化脚本开发)
- [6. 在 Terraform 模块中引用镜像](#6-在-terraform-模块中引用镜像)
- [7. 最佳实践](#7-最佳实践)

---

## 1. 镜像制作概述

### 1.1 什么是自定义镜像

LAS 自定义镜像是从**运行中的云主机实例**创建的系统盘快照。它不是 Docker 容器镜像，而是完整的操作系统磁盘镜像，包含操作系统、预装软件、配置文件等。

### 1.2 为什么需要自定义镜像

- **缩短部署时间**：预装软件避免每次实例启动时下载安装
- **保证一致性**：所有用户部署的实例使用相同的软件版本和基础配置
- **安全加固**：预配置安全策略、删除不必要的包

### 1.3 镜像与 Terraform 模块的关系

```
官方 OS 镜像 → 创建云主机 → 安装软件 → 创建自定义镜像
                                              ↓
                                    Terraform 模块引用镜像 ID
                                              ↓
                                    AppMarket 版本部署
```

- **官方镜像**：Ubuntu 24.04 LTS 等由平台提供的基础系统镜像
- **自定义镜像**：在官方镜像基础上预装应用软件后制作的镜像（类型为 `Custom`）
- **Terraform 模块**：通过 `data "qiniu_compute_images"` 查询镜像或直接引用镜像 ID

### 1.4 完整流程

```mermaid
graph TD
    A[编写安装脚本<br/>install.sh] --> B[image-cli.py build<br/>自动选最小机型]
    B --> C[创建临时 VM<br/>Ubuntu 24.04 基础镜像]
    C --> D[SSH 执行安装脚本<br/>上传 + 远程执行]
    D --> E[自动清理环境<br/>cloud-init clean 等]
    E --> F[创建自定义镜像<br/>POST /v1/images → 202]
    F --> G[等待镜像就绪<br/>Creating → Available]
    G --> H[删除临时 VM<br/>自动清理]
    H --> I[在 Terraform 模块中引用]

    style A fill:#e8f4f8
    style B fill:#e1f5e1
    style E fill:#fff4e1
    style G fill:#ffe8e1
```

---

## 2. 一键制作镜像（推荐）

使用 `scripts/vm-cli.py / scripts/image-cli.py` 自动完成全流程：创建 VM → 等待就绪 → SSH 执行安装脚本 → 清理环境 → 创建镜像 → 等待就绪 → 删除 VM。

> **重要**：如果应用有官方 standalone release，安装脚本应使用对应的官方 release 包。
> 制作镜像时只完成安装，不要实际启动服务，避免留下运行态临时文件；应用依赖、运行时和配置都应在镜像里准备好，并在干净 VM 上复现安装结果后再 snapshot。

### 2.1 前置条件

- Python 3.8+（无第三方依赖）
- `sshpass`（密码方式 SSH 连接，`apt install sshpass` / `brew install sshpass`）
- 环境变量 `QINIU_ACCESS_KEY` 和 `QINIU_SECRET_KEY`

### 2.2 基本用法

```bash
export QINIU_ACCESS_KEY="your-ak"
export QINIU_SECRET_KEY="your-sk"

# 一键制作镜像（自动选择最小可用机型）
python3 scripts/image-cli.py build \
  --install-script path/to/install.sh \
  --image-name <app>-v1.0.0 \
  --image-desc "Ubuntu 24.04 + <app> v1.0.0"
```

脚本会自动：
1. 查询最小可用机型（非 GPU，按 CPU + 内存排序）
2. 查询 Ubuntu 24.04 官方基础镜像
3. 创建临时 VM 并等待启动
4. 通过 SSH 上传并执行安装脚本
5. 执行标准清理（apt clean、cloud-init clean、删除 SSH 密钥等）
6. 创建自定义镜像并等待状态变为 `Available`
7. 删除临时 VM

### 2.3 机型选择

制作镜像时应使用**满足安装需求的最小机型**，避免镜像绑定过高的资源需求。

```bash
# 查看当前区域可用机型（按 CPU + 内存升序排列，不含 GPU）
python3 scripts/vm-cli.py list-types --region ap-northeast-1

# 按规格族过滤
python3 scripts/vm-cli.py list-types --family t1
```

不指定 `--instance-type` 时，`build` 命令会自动选择最小的可用机型。如需手动指定：

```bash
python3 scripts/image-cli.py build \
  --install-script my-install.sh \
  --image-name my-app-v1.0 \
  --instance-type ecs.t1.c2m4 \
  --disk-size 60
```

### 2.4 调试模式

使用 `--keep-vm` 保留 VM 不删除，方便 SSH 登录排查问题：

```bash
python3 scripts/image-cli.py build \
  --install-script my-install.sh \
  --image-name test --keep-vm
```

脚本会输出 VM 的 IP、密码和 SSH 命令，排查完成后手动删除：

```bash
python3 scripts/vm-cli.py delete-vm --instance-id i-xxxxx
```

### 2.5 排查残留 VM

如果脚本被强制终止导致 VM 未清理：

```bash
# 列出当前区域所有 VM
python3 scripts/vm-cli.py list-vms --region ap-northeast-1

# 删除残留 VM
python3 scripts/vm-cli.py delete-vm --instance-id i-xxxxx
```

### 2.6 完整参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--install-script` | （必需） | 安装脚本路径，将通过 SCP 上传到 VM 以 root 执行 |
| `--image-name` | （必需） | 镜像名称 |
| `--image-desc` | 自动生成 | 镜像描述 |
| `--region` | `ap-northeast-1` | 区域，自定义镜像绑定创建时的区域 |
| `--instance-type` | 自动选最小 | VM 规格，可通过 `list-types` 查看 |
| `--disk-type` | `local.ssd` | 磁盘类型（`local.ssd` 或 `cloud.ssd`） |
| `--disk-size` | `40` | 系统盘大小 GB，镜像大小 = 实际使用量 |
| `--bandwidth` | `100` | 峰值带宽 Mbps，可选 50/100/200 |
| `--base-image` | 自动查询 Ubuntu 24.04 | 基础镜像 ID |
| `--password` | 随机生成 | VM 密码 |
| `--ssh-user` | `root` | SSH 用户名 |
| `--keep-vm` | `false` | 完成后保留 VM 不删除 |

---

## 3. 编写安装脚本

安装脚本是在 VM 上以 root 身份执行的 bash 脚本，负责安装和配置应用软件。`image-cli.py` / `vm-cli.py` 会通过 SCP 上传脚本到 VM 并执行。

### 3.1 脚本模板

参考 `assets/setup-image.sh` 模板，基本结构：

```bash
#!/bin/bash
set -euo pipefail

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

# 阶段 1: 安装依赖
log "安装依赖..."
apt-get update
apt-get install -y --no-install-recommends curl wget ca-certificates

# 阶段 2: 安装应用软件（根据你的应用修改）
log "安装应用..."
# ...

# 阶段 3: 验证安装
log "验证..."
# ...

log "安装完成"
```

### 3.2 示例：应用安装脚本

参考 `assets/setup-image.sh` 模板，以下是一个典型的安装脚本结构：

```bash
#!/bin/bash
set -euo pipefail

# 安装运行时依赖（以 Node.js 为例）
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt install -y nodejs

# 安装应用及其依赖
git config --global url."https://github.com/".insteadOf ssh://git@github.com/
npm install -g --loglevel info myapp@1.0.0
rm -fv /root/.gitconfig

# 创建运行用户
useradd -m -s /bin/bash myapp
usermod -aG sudo myapp
loginctl enable-linger myapp

# 配置用户环境
sudo -u myapp bash -c 'mkdir -p ~/.myapp/data'
chmod 700 /home/myapp/.myapp
```

### 3.3 必须保留的软件

以下软件是 LAS 云主机正常运行的基础，**不能删除或禁用**：

| 软件 | 说明 |
|------|------|
| cloud-init | LAS 依赖它在实例启动时注入 user_data 初始化脚本 |
| systemd | 系统服务管理 |
| curl | HTTP 客户端，健康检查等场景需要 |
| ca-certificates | SSL 证书，HTTPS 通信需要 |
| openssh-server | SSH 远程管理 |

### 3.4 安装应用软件示例

**数据库类**：

```bash
# MySQL 8.0
sudo apt update
sudo apt install -y mysql-server mysql-client
sudo systemctl enable mysql

# PostgreSQL 16
sudo apt install -y postgresql-16 postgresql-client-16
sudo systemctl enable postgresql

# Redis 7
sudo apt install -y redis-server
sudo systemctl enable redis-server
```

**Web 服务器类**：

```bash
# Nginx
sudo apt install -y nginx
sudo systemctl enable nginx
```

**运行时类**：

```bash
# Node.js 22
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
```

### 3.5 创建应用用户（可选）

如果应用需要独立用户：

```bash
useradd -m -s /bin/bash appuser
usermod -aG sudo appuser
mkdir -p /home/appuser/.config
chmod 700 /home/appuser/.config
chown -R appuser:appuser /home/appuser
```

> **注意**：安装脚本中不需要包含清理步骤（apt clean、cloud-init clean 等），`image-cli.py` / `vm-cli.py` 会在脚本执行完成后自动执行标准清理。

---

## 4. 手动制作镜像

如果不使用 `image-cli.py` / `vm-cli.py`，也可以手动完成镜像制作。

### 4.1 创建基础云主机

**方式一：七牛云控制台（Portal）**

在控制台界面操作：**云主机** → **创建实例**，选择官方基础镜像。

**方式二：LAS API**

```
POST /v1/instances
Host: ap-northeast-1-ecs.qiniuapi.com

{
    "regionID": "ap-northeast-1",
    "imageID": "<官方镜像 ID>",
    "instanceType": "ecs.t1.c2m4",
    "systemDisk": { "diskType": "local.ssd", "size": 40 },
    "internetMaxBandwidth": 100,
    "password": "<密码>",
    "clientToken": "<UUID>",
    "names": ["image-builder"]
}
```

> **注意**：`systemDisk` 必须包含 `diskType` 字段（`local.ssd` 或 `cloud.ssd`），否则 API 返回 400 错误。

查询可用机型：`GET /v1/instance-types`，返回各机型的 CPU、内存、支持区域等信息。应选择满足需求的最小机型，避免镜像绑定过高资源需求。

### 4.2 等待 VM 就绪

轮询实例状态直到 `state`（注意不是 `status`）变为 `Running`：

```
GET /v1/instances/{instanceID}
Host: ap-northeast-1-ecs.qiniuapi.com
```

### 4.3 SSH 安装软件

```bash
ssh root@<公网IP>
# 执行安装脚本...
```

### 4.4 清理环境

制作镜像前**必须清理**以下内容：

```bash
apt-get clean && apt-get autoremove -y
rm -rf /var/lib/apt/lists/*
journalctl --vacuum-time=1d
rm -rf /tmp/* /var/tmp/*
rm -f /etc/ssh/ssh_host_*
cloud-init clean --logs
rm -f /root/.bash_history /home/*/.bash_history
```

> **关键**：`cloud-init clean` 是必须的，否则新实例不会执行 user_data 脚本。

### 4.5 创建自定义镜像

实例必须处于 **Running** 状态。API 返回 HTTP **202**（异步操作）：

```
POST /v1/images
Host: ap-northeast-1-ecs.qiniuapi.com

{
    "instanceID": "i-xxxxxxxxxxxx",
    "regionID": "ap-northeast-1",
    "name": "ubuntu-24.04-mysql-8.0",
    "description": "Ubuntu 24.04 + MySQL 8.0 预装镜像"
}

# 返回 202
{
    "imageID": "image-xxxxxxxxxxxx"
}
```

### 4.6 等待镜像就绪

轮询镜像 `state` 直到 `Available`：

```
GET /v1/images/{imageID}
Host: ap-northeast-1-ecs.qiniuapi.com
```

状态流转：`Creating` → `Available`

### 4.7 删除临时 VM

镜像就绪后删除临时 VM：

```
DELETE /v1/instances/{instanceID}
Host: ap-northeast-1-ecs.qiniuapi.com
```

### 4.8 注意事项

| 项目 | 说明 |
|------|------|
| API Host | 必须使用 region 前缀域名 `{regionID}-ecs.qiniuapi.com` |
| 实例状态字段 | API 返回的字段名是 `state`（不是 `status`） |
| systemDisk | 必须包含 `diskType`（`local.ssd` 或 `cloud.ssd`） |
| 镜像创建响应 | 返回 HTTP 202，异步操作 |
| 区域绑定 | 自定义镜像绑定创建时的 regionID，仅该区域可用 |
| 镜像大小 | 取决于系统盘实际使用量，建议控制在 10GB 以内 |

---

## 5. 初始化脚本开发

自定义镜像提供「预装环境」，但每个实例的个性化配置（密码、数据库名等）通过 Terraform `user_data` 在首次启动时注入。

### 5.1 user_data 工作原理

```
                       Terraform 模块
                            │
                    templatefile() 渲染
                            │
                    user_data 脚本
                            │
                  cloud-init 首次启动执行
                            │
                  配置密码 / 创建数据库 / 启动服务
```

Terraform 模块中的引用方式：

**方式 A：内联 heredoc（moduleContent 模式必须使用）**

```hcl
resource "qiniu_compute_instance" "mysql" {
  image_id      = local.mysql_image_id
  instance_type = var.instance_type

  user_data = base64encode(<<-USERDATA
#!/bin/bash
set -euo pipefail
MYSQL_USERNAME="${var.mysql_username}"
MYSQL_PASSWORD="${var.mysql_password}"
MYSQL_DB_NAME="${var.mysql_db_name}"
# ... 初始化逻辑
USERDATA
  )
}
```

**方式 B：templatefile（仅 gitSource 模式可用）**

```hcl
resource "qiniu_compute_instance" "mysql" {
  image_id      = local.mysql_image_id
  instance_type = var.instance_type

  user_data = base64encode(templatefile("${path.module}/scripts/init-mysql.sh", {
    mysql_username = var.mysql_username
    mysql_password = var.mysql_password
    mysql_db_name  = var.mysql_db_name
  }))
}
```

> **注意**：`bundle-module.sh` 只打包 `*.tf` 文件，不包含子目录。使用 `moduleContent` 方式发布时不能用 `templatefile()` 引用外部脚本文件。

### 5.2 初始化脚本示例（MySQL）

```bash
#!/bin/bash
set -e

# 变量由 Terraform templatefile 注入
MYSQL_USERNAME="${mysql_username}"
MYSQL_PASSWORD="${mysql_password}"
MYSQL_DB_NAME="${mysql_db_name}"

LOG_FILE="/var/log/appmarket/mysql-init.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "Starting MySQL initialization..."

# 等待 MySQL 服务就绪
for i in $(seq 1 30); do
    if mysqladmin ping -h localhost --silent 2>/dev/null; then
        log "MySQL service is ready"
        break
    fi
    if [ "$i" -eq 30 ]; then
        log "ERROR: MySQL service failed to start"
        exit 1
    fi
    sleep 2
done

# 创建管理员用户
log "Creating admin user: $MYSQL_USERNAME"
mysql -u root <<SQL
CREATE USER IF NOT EXISTS '$MYSQL_USERNAME'@'%' IDENTIFIED BY '$MYSQL_PASSWORD';
GRANT ALL PRIVILEGES ON *.* TO '$MYSQL_USERNAME'@'%' WITH GRANT OPTION;
FLUSH PRIVILEGES;
SQL

# 创建数据库
if [ -n "$MYSQL_DB_NAME" ]; then
    log "Creating database: $MYSQL_DB_NAME"
    mysql -u root <<SQL
CREATE DATABASE IF NOT EXISTS \`$MYSQL_DB_NAME\`
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON \`$MYSQL_DB_NAME\`.* TO '$MYSQL_USERNAME'@'%';
FLUSH PRIVILEGES;
SQL
fi

# 安全加固
mysql -u root <<SQL
DELETE FROM mysql.user WHERE User='';
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
DROP DATABASE IF EXISTS test;
FLUSH PRIVILEGES;
SQL

log "MySQL initialization completed"
```

### 5.3 脚本规范

| 规范 | 说明 |
|------|------|
| `set -e` | 遇错退出，避免错误被忽略 |
| 日志记录 | 关键步骤写入 `/var/log/appmarket/*.log`，便于排查 |
| 超时等待 | 服务启动等待设置合理超时（如 60 秒） |
| 幂等性 | 使用 `IF NOT EXISTS` 等，支持重复执行 |
| 敏感信息 | 密码等敏感信息**不要写入日志** |
| 路径 | 脚本放置在 `/usr/local/bin/` 或模块的 `scripts/` 目录 |

---

## 6. 在 Terraform 模块中引用镜像

### 6.1 通过 data source 动态查询（推荐）

使用 `qiniu_compute_images` data source 按条件查询镜像：

```hcl
# 查询官方 Ubuntu 24.04 镜像
data "qiniu_compute_images" "official" {
  type  = "Official"
  state = "Available"
}

locals {
  ubuntu_image_id = one([
    for item in data.qiniu_compute_images.official.items : item
    if item.os_distribution == "Ubuntu" && item.os_version == "24.04 LTS"
  ]).id
}

# 查询自定义镜像
data "qiniu_compute_images" "custom" {
  type  = "Custom"
  state = "Available"
}

locals {
  mysql_image_id = one([
    for item in data.qiniu_compute_images.custom.items : item
    if item.name == "ubuntu-24.04-mysql-8.0"
  ]).id
}
```

### 6.2 直接引用镜像 ID

```hcl
resource "qiniu_compute_instance" "app" {
  image_id      = "image-xxxxxxxxxxxx"
  instance_type = var.instance_type
  # ...
}
```

### 6.3 data source 参数

`qiniu_compute_images` 支持的过滤参数：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 是 | `Official`、`Custom`、`CustomPublic`、`CustomShared` |
| `state` | string | 否 | `Available`、`Creating`、`Deprecated` 等 |
| `region_id` | string | 否 | 不填则使用 provider 级别配置 |
| `limit` | number | 否 | 限制返回数量 |

返回的 `items` 中每个镜像包含：`id`、`name`、`os_distribution`、`os_version`、`architecture`、`state` 等字段。

---

## 7. 最佳实践

### 7.1 镜像体积优化

```bash
# 安装时使用 --no-install-recommends 减少不必要的包
sudo apt install -y --no-install-recommends mysql-server

# 安装完成后清理
sudo apt clean && sudo apt autoremove -y
sudo rm -rf /var/lib/apt/lists/*
```

### 7.2 安全加固

- 删除不必要的系统用户和服务
- 应用软件以非 root 用户运行
- 配置防火墙（ufw）仅开放必要端口
- 定期更新基础镜像（重新制作时基于最新官方镜像）

```bash
# 配置防火墙
sudo apt install -y ufw
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 3306/tcp  # MySQL
sudo ufw --force enable
```

### 7.3 验证清单

制作镜像前逐项检查：

**软件和服务**：
- [ ] 目标应用软件已安装且版本正确
- [ ] 必需软件已保留（cloud-init、curl、ca-certificates）
- [ ] 应用服务已设置开机自启（`systemctl is-enabled <service>`）
- [ ] 初始化脚本已放置且可执行

**清理**：
- [ ] apt 缓存已清理
- [ ] SSH 主机密钥已删除
- [ ] cloud-init 状态已清理
- [ ] bash 历史已清除
- [ ] 临时文件已删除
- [ ] 无敏感信息残留（密码、密钥等）

**功能验证**：
- [ ] 基于新镜像创建实例后，cloud-init 正常执行 user_data
- [ ] 应用服务正常启动
- [ ] 初始化脚本正确完成配置

---

## 8. 镜像管理常用命令

制作完成后，可用 `image-cli.py` 管理镜像生命周期。

### 查询

```bash
# 列出自定义镜像（默认 Custom 类型，全状态，带分页）
python3 scripts/image-cli.py list-images --region ap-northeast-1

# 按名称过滤
python3 scripts/image-cli.py list-images --region ap-northeast-1 --name MyApp
```

### 更新元信息

```bash
# 更新描述（最大 100 UTF8 字符）
python3 scripts/image-cli.py update-image \
  --image-id image-xxxxx \
  --region ap-northeast-1 \
  --desc "Ubuntu 24.04 + MyApp v1.0 (安装了 Node.js 22)"

# 废弃旧版本镜像（仍可使用，但不推荐）
python3 scripts/image-cli.py update-image \
  --image-id image-xxxxx \
  --region ap-northeast-1 \
  --state Deprecated

# 公开镜像（让其他账户可见）
python3 scripts/image-cli.py update-image \
  --image-id image-xxxxx \
  --region ap-northeast-1 \
  --public true
```

**可更新字段**：

| 参数 | 说明 | 约束 |
|------|------|------|
| `--name` | 镜像名称 | 只含字母/数字/-/. ，2-60 字符 |
| `--desc` | 描述 | 最大 100 UTF8 字符，超出自动截断 |
| `--state` | 状态 | `Available` / `Deprecated` / `Disabled` |
| `--public` | 是否公开 | `true` / `false` |
| `--min-cpu` | 最小 CPU 核心数 | 1-256 |
| `--min-memory` | 最小内存 GiB | 1-2048 |
| `--min-disk` | 最小磁盘 GiB | ≥ max(size, systemDiskSize) |

### 删除

```bash
# 删除镜像（状态需为 Available / Deprecated / Disabled / Failed）
python3 scripts/image-cli.py delete-image \
  --image-id image-xxxxx \
  --region ap-northeast-1
```

---

## 相关资源

- [七牛云开发者文档（LAS）](https://developer.qiniu.com/las) — 镜像 API、实例 API 等
- [七牛云 Terraform Provider 模块示例](https://github.com/qiniu/terraform-module/) — data source 用法
- [Cloud-init 文档](https://cloudinit.readthedocs.io/)
- [OpenTofu 语法文档](https://opentofu.org/docs/) — templatefile 函数等
