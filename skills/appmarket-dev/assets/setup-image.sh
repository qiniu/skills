#!/bin/bash
# AppMarket 镜像安装脚本模板
#
# 使用说明：
#   1. 复制此模板并修改「安装应用软件」部分为你的应用安装命令
#   2. 配合 image-cli.py 命令使用：
#        python3 scripts/image-cli.py build \
#          --install-script my-install.sh \
#          --image-name my-app-v1.0
#   3. 也可以手动 SSH 到 VM 上以 root 执行此脚本
#
# 注意事项：
#   - 脚本在远程 VM 上以 root 身份执行
#   - cloud-init 必须保留，不能删除或禁用
#   - 环境清理（apt clean、cloud-init clean 等）由 image-cli.py 统一处理，
#     此脚本只需关注软件安装和配置
#   - 如需手动制作镜像，清理步骤参考 skills/image-building.md

set -euo pipefail

# ============================================================================
# 应用配置 — 请替换为你的应用信息
# ============================================================================

APP_NAME="<APP_NAME>"
APP_VERSION="<APP_VERSION>"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

# ============================================================================
# 阶段 1: 系统更新和基础软件
# ============================================================================

log "阶段 1/3: 系统更新和基础软件..."
apt-get update
apt-get install -y --no-install-recommends curl wget ca-certificates gnupg

# ============================================================================
# 阶段 2: 安装应用软件
# ============================================================================
# TODO: 根据你的应用修改以下命令

log "阶段 2/3: 安装应用软件..."

# --- MySQL 示例（取消注释并按需修改） ---
# apt-get install -y --no-install-recommends mysql-server mysql-client
# systemctl enable mysql

# --- PostgreSQL 示例 ---
# apt-get install -y --no-install-recommends postgresql-16 postgresql-client-16
# systemctl enable postgresql

# --- Redis 示例 ---
# apt-get install -y --no-install-recommends redis-server
# systemctl enable redis-server

# --- Nginx 示例 ---
# apt-get install -y --no-install-recommends nginx
# systemctl enable nginx

# --- Node.js 示例 ---
# curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
# apt install -y nodejs

# --- 放置配置文件示例 ---
# cat > /etc/mysql/conf.d/appmarket.cnf << 'EOF'
# [mysqld]
# bind-address = 0.0.0.0
# max_connections = 200
# character-set-server = utf8mb4
# collation-server = utf8mb4_unicode_ci
# EOF

# --- 创建应用用户示例 ---
# useradd -m -s /bin/bash appuser
# usermod -aG sudo appuser
# mkdir -p /home/appuser/.config
# chmod 700 /home/appuser/.config
# chown -R appuser:appuser /home/appuser

# --- 配置日志轮转 ---
mkdir -p /var/log/appmarket
cat > /etc/logrotate.d/appmarket << 'EOF'
/var/log/appmarket/*.log {
    daily
    missingok
    rotate 14
    compress
    notifempty
}
EOF

# ============================================================================
# 阶段 3: 验证安装
# ============================================================================

log "阶段 3/3: 验证安装..."

# TODO: 添加你的验证命令
# mysql --version
# nginx -v
# node -v

log "安装完成: $APP_NAME $APP_VERSION"
