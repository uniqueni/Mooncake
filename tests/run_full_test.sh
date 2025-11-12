#!/bin/bash
################################################################################
# vLLM + LMCache + Mooncake 完整测试自动化脚本
#
# 这个脚本会自动执行以下操作：
# 1. 检查环境和依赖
# 2. 启动 Mooncake Master（可选）
# 3. 启动 Decoder 节点（可选）
# 4. 启动 Prefiller 节点（可选）
# 5. 启动 Proxy Server（可选）
# 6. 运行缓存效果测试
# 7. 生成测试报告
# 8. 清理环境（可选）
################################################################################

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/test_config.yaml"
OUTPUT_DIR="${SCRIPT_DIR}/test_results"
REPORT_DIR="${SCRIPT_DIR}/reports"

# 测试参数
TEST_SCENARIOS="high_reuse medium_reuse low_reuse"
TEST_ROUNDS=2
CONCURRENCY=""

# 服务控制标志
START_MOONCAKE=false
START_DECODER=false
START_PREFILLER=false
START_PROXY=false
CLEANUP_AFTER_TEST=false

# 日志文件
LOG_DIR="${SCRIPT_DIR}/logs"
MOONCAKE_LOG="${LOG_DIR}/mooncake_master.log"
DECODER_LOG="${LOG_DIR}/decoder.log"
PREFILLER_LOG="${LOG_DIR}/prefiller.log"
PROXY_LOG="${LOG_DIR}/proxy.log"

################################################################################
# 辅助函数
################################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "命令 '$1' 未找到，请先安装"
        return 1
    fi
    return 0
}

check_python_package() {
    python3 -c "import $1" 2>/dev/null
    if [ $? -ne 0 ]; then
        log_error "Python 包 '$1' 未安装"
        return 1
    fi
    return 0
}

wait_for_service() {
    local host=$1
    local port=$2
    local max_wait=$3
    local waited=0

    log_info "等待服务 ${host}:${port} 启动..."

    while [ $waited -lt $max_wait ]; do
        if nc -z "$host" "$port" 2>/dev/null; then
            log_success "服务 ${host}:${port} 已就绪"
            return 0
        fi
        sleep 1
        waited=$((waited + 1))
    done

    log_error "服务 ${host}:${port} 在 ${max_wait} 秒内未启动"
    return 1
}

################################################################################
# 环境检查
################################################################################

check_environment() {
    log_info "检查环境和依赖..."

    # 检查必需命令
    local required_commands=("python3" "curl" "nc")
    for cmd in "${required_commands[@]}"; do
        if ! check_command "$cmd"; then
            return 1
        fi
    done

    # 检查 Python 包
    local required_packages=("yaml" "openai")
    for pkg in "${required_packages[@]}"; do
        if ! check_python_package "$pkg"; then
            log_warning "请运行: pip install $pkg"
            return 1
        fi
    done

    # 检查配置文件
    if [ ! -f "$CONFIG_FILE" ]; then
        log_error "配置文件不存在: $CONFIG_FILE"
        return 1
    fi

    # 检查测试脚本
    if [ ! -f "${SCRIPT_DIR}/test_vllm_lmcache_mooncake.py" ]; then
        log_error "测试脚本不存在: ${SCRIPT_DIR}/test_vllm_lmcache_mooncake.py"
        return 1
    fi

    log_success "环境检查通过"
    return 0
}

################################################################################
# 服务启动函数
################################################################################

start_mooncake_master() {
    log_info "启动 Mooncake Master..."

    # 从配置文件读取参数（这里使用默认值，实际应该从 YAML 读取）
    local master_port=50052
    local metrics_port=9004
    local metadata_port=8080

    mkdir -p "$LOG_DIR"

    # 启动 Mooncake Master
    nohup mooncake_master \
        -port "$master_port" \
        -max_threads 64 \
        -metrics_port "$metrics_port" \
        --enable_http_metadata_server=true \
        --http_metadata_server_host=0.0.0.0 \
        --http_metadata_server_port="$metadata_port" \
        > "$MOONCAKE_LOG" 2>&1 &

    local pid=$!
    echo "$pid" > "${LOG_DIR}/mooncake_master.pid"

    # 等待服务启动
    if wait_for_service "localhost" "$master_port" 30; then
        log_success "Mooncake Master 已启动 (PID: $pid)"
        return 0
    else
        log_error "Mooncake Master 启动失败"
        return 1
    fi
}

start_decoder() {
    log_info "启动 Decoder 节点..."
    log_warning "请手动启动 Decoder 节点，或设置自动启动逻辑"
    # TODO: 添加 vLLM Decoder 启动逻辑
    return 0
}

start_prefiller() {
    log_info "启动 Prefiller 节点..."
    log_warning "请手动启动 Prefiller 节点，或设置自动启动逻辑"
    # TODO: 添加 vLLM Prefiller 启动逻辑
    return 0
}

start_proxy() {
    log_info "启动 Proxy Server..."
    log_warning "请手动启动 Proxy Server，或设置自动启动逻辑"
    # TODO: 添加 Proxy Server 启动逻辑
    return 0
}

################################################################################
# 测试执行
################################################################################

run_tests() {
    log_info "开始运行测试..."

    mkdir -p "$OUTPUT_DIR"

    local test_cmd="python3 ${SCRIPT_DIR}/test_vllm_lmcache_mooncake.py"
    test_cmd="$test_cmd --config $CONFIG_FILE"
    test_cmd="$test_cmd --scenarios $TEST_SCENARIOS"
    test_cmd="$test_cmd --rounds $TEST_ROUNDS"
    test_cmd="$test_cmd --output-dir $OUTPUT_DIR"

    if [ -n "$CONCURRENCY" ]; then
        test_cmd="$test_cmd --concurrency $CONCURRENCY"
    fi

    log_info "执行命令: $test_cmd"

    if $test_cmd; then
        log_success "测试执行成功"
        return 0
    else
        log_error "测试执行失败"
        return 1
    fi
}

################################################################################
# 报告生成
################################################################################

generate_reports() {
    log_info "生成测试报告..."

    mkdir -p "$REPORT_DIR"

    # 查找最新的统计文件
    local latest_stats=$(ls -t "${OUTPUT_DIR}"/stats_*.json 2>/dev/null | head -1)
    local latest_results=$(ls -t "${OUTPUT_DIR}"/results_*.json 2>/dev/null | head -1)

    if [ -z "$latest_stats" ]; then
        log_error "未找到统计文件"
        return 1
    fi

    log_info "使用统计文件: $latest_stats"

    local report_cmd="python3 ${SCRIPT_DIR}/generate_report.py"
    report_cmd="$report_cmd --stats $latest_stats"

    if [ -n "$latest_results" ]; then
        report_cmd="$report_cmd --results $latest_results"
    fi

    report_cmd="$report_cmd --output-dir $REPORT_DIR"
    report_cmd="$report_cmd --format both"

    # 如果安装了 matplotlib，生成图表
    if check_python_package "matplotlib"; then
        report_cmd="$report_cmd --generate-charts"
    fi

    log_info "执行命令: $report_cmd"

    if $report_cmd; then
        log_success "报告生成成功"
        log_info "报告位置: $REPORT_DIR"

        # 列出生成的报告文件
        if [ -f "${REPORT_DIR}/report.html" ]; then
            log_success "HTML 报告: ${REPORT_DIR}/report.html"
        fi
        if [ -f "${REPORT_DIR}/report.md" ]; then
            log_success "Markdown 报告: ${REPORT_DIR}/report.md"
        fi

        return 0
    else
        log_error "报告生成失败"
        return 1
    fi
}

################################################################################
# 清理函数
################################################################################

cleanup() {
    log_info "清理环境..."

    # 停止 Mooncake Master
    if [ -f "${LOG_DIR}/mooncake_master.pid" ]; then
        local pid=$(cat "${LOG_DIR}/mooncake_master.pid")
        if ps -p "$pid" > /dev/null 2>&1; then
            log_info "停止 Mooncake Master (PID: $pid)"
            kill "$pid" 2>/dev/null || true
            rm -f "${LOG_DIR}/mooncake_master.pid"
        fi
    fi

    # TODO: 停止其他服务

    log_success "清理完成"
}

################################################################################
# 显示使用帮助
################################################################################

show_usage() {
    cat << EOF
用法: $0 [选项]

选项:
    -h, --help              显示此帮助信息
    -c, --config FILE       指定配置文件 (默认: test_config.yaml)
    -s, --scenarios LIST    要测试的场景列表 (默认: high_reuse medium_reuse low_reuse)
    -r, --rounds N          每个场景测试轮数 (默认: 2)
    -n, --concurrency N     并发请求数限制
    -o, --output DIR        结果输出目录 (默认: test_results)
    --report-dir DIR        报告输出目录 (默认: reports)

    --start-mooncake        自动启动 Mooncake Master
    --start-decoder         自动启动 Decoder 节点
    --start-prefiller       自动启动 Prefiller 节点
    --start-proxy           自动启动 Proxy Server
    --start-all             启动所有服务

    --cleanup               测试后清理环境
    --skip-test             跳过测试，只生成报告

示例:
    # 基本测试（假设服务已启动）
    $0

    # 启动所有服务并运行测试
    $0 --start-all --cleanup

    # 只运行特定场景
    $0 --scenarios "high_reuse long_context" --rounds 3

    # 使用自定义配置
    $0 --config my_config.yaml --output my_results

EOF
}

################################################################################
# 参数解析
################################################################################

SKIP_TEST=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -s|--scenarios)
            TEST_SCENARIOS="$2"
            shift 2
            ;;
        -r|--rounds)
            TEST_ROUNDS="$2"
            shift 2
            ;;
        -n|--concurrency)
            CONCURRENCY="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --report-dir)
            REPORT_DIR="$2"
            shift 2
            ;;
        --start-mooncake)
            START_MOONCAKE=true
            shift
            ;;
        --start-decoder)
            START_DECODER=true
            shift
            ;;
        --start-prefiller)
            START_PREFILLER=true
            shift
            ;;
        --start-proxy)
            START_PROXY=true
            shift
            ;;
        --start-all)
            START_MOONCAKE=true
            START_DECODER=true
            START_PREFILLER=true
            START_PROXY=true
            shift
            ;;
        --cleanup)
            CLEANUP_AFTER_TEST=true
            shift
            ;;
        --skip-test)
            SKIP_TEST=true
            shift
            ;;
        *)
            log_error "未知选项: $1"
            show_usage
            exit 1
            ;;
    esac
done

################################################################################
# 主流程
################################################################################

main() {
    echo "================================================================================"
    echo "          vLLM + LMCache + Mooncake 缓存效果测试 - 自动化脚本"
    echo "================================================================================"
    echo ""

    # 1. 环境检查
    if ! check_environment; then
        log_error "环境检查失败，退出"
        exit 1
    fi

    # 2. 启动服务
    if $START_MOONCAKE; then
        if ! start_mooncake_master; then
            log_error "Mooncake Master 启动失败，退出"
            exit 1
        fi
    fi

    if $START_DECODER; then
        start_decoder
    fi

    if $START_PREFILLER; then
        start_prefiller
    fi

    if $START_PROXY; then
        start_proxy
    fi

    # 3. 运行测试
    if ! $SKIP_TEST; then
        if ! run_tests; then
            log_error "测试失败"
            if $CLEANUP_AFTER_TEST; then
                cleanup
            fi
            exit 1
        fi
    fi

    # 4. 生成报告
    if ! generate_reports; then
        log_warning "报告生成失败，但测试已完成"
    fi

    # 5. 清理
    if $CLEANUP_AFTER_TEST; then
        cleanup
    fi

    echo ""
    echo "================================================================================"
    log_success "所有任务完成！"
    echo "================================================================================"
    echo ""
    echo "📊 测试结果: $OUTPUT_DIR"
    echo "📄 测试报告: $REPORT_DIR"
    echo "📝 日志文件: $LOG_DIR"
    echo ""
}

# 捕获 Ctrl+C 并清理
trap cleanup INT TERM

# 运行主流程
main

exit 0
