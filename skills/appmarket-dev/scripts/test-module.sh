#!/bin/bash
# Terraform 模块测试脚本
# 用法: ./test-module.sh <module-dir> [tfvars-file] [--integration]

set -e

# ============================================================================
# 配置和参数解析
# ============================================================================

MODULE_DIR="${1:-.}"
TFVARS_FILE="${2:-}"
RUN_INTEGRATION_TEST=false
INIT_LOG="$(mktemp /tmp/terraform-init.XXXXXX.log)"
PLAN_LOG="$(mktemp /tmp/terraform-plan.XXXXXX.log)"
trap 'rm -f "$INIT_LOG" "$PLAN_LOG"' EXIT

# 解析命令行参数
for arg in "$@"; do
  case $arg in
    --integration)
      RUN_INTEGRATION_TEST=true
      shift
      ;;
  esac
done

# 检查模块目录
if [ ! -d "$MODULE_DIR" ]; then
  echo "错误: 模块目录不存在: $MODULE_DIR" >&2
  exit 1
fi

cd "$MODULE_DIR"

# ============================================================================
# 日志函数
# ============================================================================

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

log_success() {
    echo "✓ [$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

log_error() {
    echo "✗ [$(date +'%Y-%m-%d %H:%M:%S')] $*" >&2
}

log_section() {
    echo ""
    echo "=========================================="
    echo "$*"
    echo "=========================================="
}

# ============================================================================
# 环境检查
# ============================================================================

check_prerequisites() {
    log_section "检查前置依赖"

    # 检查 Terraform
    if ! command -v terraform &> /dev/null; then
        log_error "Terraform 未安装"
        log "请访问 https://www.terraform.io/downloads 安装 Terraform"
        exit 1
    fi
    log_success "Terraform $(terraform version | head -n1 | awk '{print $2}')"

    # 检查 TFLint（可选）
    if command -v tflint &> /dev/null; then
        log_success "TFLint $(tflint --version | head -n1 | awk '{print $3}')"
    else
        log "TFLint 未安装（可选），跳过静态检查"
    fi

    # 检查必需文件
    local required_files=("main.tf" "variables.tf" "outputs.tf")
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            log_error "必需文件不存在: $file"
            exit 1
        fi
    done
    log_success "必需文件检查通过"
}

# ============================================================================
# 格式化检查
# ============================================================================

test_format() {
    log_section "格式化检查"

    if terraform fmt -check -recursive; then
        log_success "代码格式正确"
        return 0
    else
        log_error "代码格式不符合规范"
        log "运行 'terraform fmt -recursive' 自动格式化"
        return 1
    fi
}

# ============================================================================
# 语法验证
# ============================================================================

test_validate() {
    log_section "语法验证"

    # 初始化
    log "初始化 Terraform..."
    if terraform init -upgrade -input=false > "$INIT_LOG" 2>&1; then
        log_success "初始化成功"
    else
        log_error "初始化失败"
        cat "$INIT_LOG"
        return 1
    fi

    # 验证
    log "验证配置文件..."
    if terraform validate; then
        log_success "语法验证通过"
        return 0
    else
        log_error "语法验证失败"
        return 1
    fi
}

# ============================================================================
# 静态检查（TFLint）
# ============================================================================

test_lint() {
    log_section "静态检查"

    if ! command -v tflint &> /dev/null; then
        log "TFLint 未安装，跳过静态检查"
        return 0
    fi

    log "初始化 TFLint..."
    tflint --init > /dev/null 2>&1 || true

    log "执行静态检查..."
    if tflint; then
        log_success "静态检查通过"
        return 0
    else
        log_error "静态检查发现问题"
        return 1
    fi
}

# ============================================================================
# 生成执行计划
# ============================================================================

test_plan() {
    log_section "生成执行计划"

    local plan_args=()

    # 如果提供了 tfvars 文件
    if [ -n "$TFVARS_FILE" ]; then
        if [ ! -f "$TFVARS_FILE" ]; then
            log_error "变量文件不存在: $TFVARS_FILE"
            return 1
        fi
        log "使用变量文件: $TFVARS_FILE"
        plan_args+=("-var-file=$TFVARS_FILE")
    else
        # 尝试查找测试变量文件
        local test_vars_files=(
            "test.tfvars"
            "test/fixtures/basic.tfvars"
            "examples/basic.tfvars"
        )
        for vars_file in "${test_vars_files[@]}"; do
            if [ -f "$vars_file" ]; then
                log "找到测试变量文件: $vars_file"
                plan_args+=("-var-file=$vars_file")
                break
            fi
        done
    fi

    log "生成执行计划..."
    if terraform plan -input=false "${plan_args[@]}" -out=tfplan > "$PLAN_LOG" 2>&1; then
        log_success "执行计划生成成功"

        # 显示计划摘要
        echo ""
        terraform show -no-color tfplan | grep -A 20 "Terraform will perform"
        echo ""

        return 0
    else
        log_error "执行计划生成失败"
        cat "$PLAN_LOG"
        return 1
    fi
}

# ============================================================================
# 集成测试（可选）
# ============================================================================

test_integration() {
    log_section "集成测试"

    if [ "$RUN_INTEGRATION_TEST" != "true" ]; then
        log "跳过集成测试（使用 --integration 启用）"
        return 0
    fi

    # 检查认证信息
    if [ -z "$QINIU_ACCESS_KEY" ] || [ -z "$QINIU_SECRET_KEY" ]; then
        log_error "集成测试需要设置环境变量："
        log "  export QINIU_ACCESS_KEY=<your-access-key>"
        log "  export QINIU_SECRET_KEY=<your-secret-key>"
        return 1
    fi

    log "开始部署测试实例..."
    if terraform apply -auto-approve tfplan; then
        log_success "实例部署成功"
    else
        log_error "实例部署失败"
        return 1
    fi

    # 显示输出
    log "实例输出："
    terraform output

    # 等待用户确认后销毁
    echo ""
    read -p "是否销毁测试实例？[Y/n] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        log "销毁测试实例..."
        if terraform destroy -auto-approve; then
            log_success "实例销毁成功"
        else
            log_error "实例销毁失败，请手动清理资源"
            return 1
        fi
    else
        log "保留测试实例，请稍后手动销毁"
    fi

    return 0
}

# ============================================================================
# 清理临时文件
# ============================================================================

cleanup() {
    log_section "清理临时文件"

    rm -f tfplan /tmp/terraform-*.log
    log_success "临时文件已清理"
}

# ============================================================================
# 主函数
# ============================================================================

main() {
    local exit_code=0

    log_section "Terraform 模块测试"
    log "模块目录: $MODULE_DIR"
    log "变量文件: ${TFVARS_FILE:-自动检测}"
    log "集成测试: ${RUN_INTEGRATION_TEST}"

    # 检查前置依赖
    check_prerequisites || exit_code=$?

    # 格式化检查
    test_format || exit_code=$?

    # 语法验证
    test_validate || exit_code=$?

    # 静态检查
    test_lint || exit_code=$?

    # 生成执行计划
    test_plan || exit_code=$?

    # 集成测试（可选）
    if [ "$exit_code" -eq 0 ]; then
        test_integration || exit_code=$?
    fi

    # 清理
    cleanup

    # 总结
    log_section "测试总结"
    if [ "$exit_code" -eq 0 ]; then
        log_success "所有测试通过 ✓"
        echo ""
        echo "下一步："
        echo "  1. 使用 scripts/generate-deploy-meta.sh 生成 DeployMeta"
        echo "  2. 创建 AppMarket Draft 版本"
        echo "  3. 使用 /test-version 命令测试 Draft 版本"
        echo "  4. 发布版本"
    else
        log_error "测试失败，请修复问题后重试 ✗"
    fi

    exit $exit_code
}

# 运行主函数
main
