#!/bin/bash
# 🕒 琥珀引擎运维调度管理器
# 功能：封装rsync同步、报告生成、权重修订的顺序指令
# 法典依据：OPERATIONS.md + 任务指令[2616-0411-P0B]
# 版本：V1.0.0

set -euo pipefail

# 配置常量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONFIG_FILE="$HOME/.amber_env"
LOG_DIR="$WORKSPACE_ROOT/logs/cron"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
LOG_FILE="$LOG_DIR/cron_${TIMESTAMP}.log"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 初始化日志
init_logging() {
    mkdir -p "$LOG_DIR"
    exec > >(tee -a "$LOG_FILE") 2>&1
    echo "=== 琥珀引擎Cron调度开始: $(date '+%Y-%m-%d %H:%M:%S') ==="
}

# 打印带颜色的消息
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查环境
check_environment() {
    log_info "检查环境配置..."
    
    # 检查工作空间
    if [[ ! -d "$WORKSPACE_ROOT" ]]; then
        log_error "工作空间不存在: $WORKSPACE_ROOT"
        exit 1
    fi
    
    # 检查配置文件
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_warning "配置文件不存在: $CONFIG_FILE"
    else
        log_info "加载环境配置: $CONFIG_FILE"
        source "$CONFIG_FILE"
    fi
    
    # 检查必需的环境变量
    if [[ -z "${GITHUB_TOKEN:-}" ]]; then
        log_warning "GITHUB_TOKEN环境变量未设置"
    fi
    
    if [[ -z "${TUSHARE_TOKEN:-}" ]]; then
        log_warning "TUSHARE_TOKEN环境变量未设置"
    fi
    
    log_info "环境检查完成"
}

# 干运行模式：仅打印命令，不执行
dry_run_mode() {
    log_info "干运行模式 - 仅显示将要执行的命令"
    
    echo "1. 加载环境: source $CONFIG_FILE"
    echo "2. 生成实战报告: cd $WORKSPACE_ROOT && python3 scripts/reporting/arena_report_generator.py"
    echo "3. 同步监控列表: cd $WORKSPACE_ROOT && python3 scripts/arena/sync_watch_list.py --mode=all"
    echo "4. 更新评委权重: cd $WORKSPACE_ROOT && python3 scripts/arena/judge_credit_updater.py"
    echo "5. GitHub同步: cd $WORKSPACE_ROOT && ./scripts/github/sync_clean.sh \"[SYNC]: Cron自动同步 $(date '+%Y-%m-%d %H:%M')\""
    echo "6. 日志归档: 将本次执行记录保存到 $LOG_FILE"
    
    log_info "干运行完成，无实际操作"
}

# 执行实战报告生成
generate_arena_report() {
    log_info "开始生成演武场实战报告..."
    
    local report_script="$WORKSPACE_ROOT/scripts/reporting/arena_report_generator.py"
    
    if [[ ! -f "$report_script" ]]; then
        log_error "报告生成器不存在: $report_script"
        return 1
    fi
    
    cd "$WORKSPACE_ROOT"
    if python3 "$report_script"; then
        log_info "实战报告生成成功"
        return 0
    else
        log_error "实战报告生成失败"
        return 1
    fi
}

# 同步监控列表
sync_watch_list() {
    log_info "开始同步监控列表..."
    
    local sync_script="$WORKSPACE_ROOT/scripts/arena/sync_watch_list.py"
    
    if [[ ! -f "$sync_script" ]]; then
        log_warning "监控列表同步脚本不存在: $sync_script"
        return 0
    fi
    
    cd "$WORKSPACE_ROOT"
    if python3 "$sync_script" --mode=all; then
        log_info "监控列表同步成功"
        return 0
    else
        log_warning "监控列表同步失败，但继续执行"
        return 0
    fi
}

# 更新评委权重
update_judge_weights() {
    log_info "开始更新评委权重..."
    
    local weight_script="$WORKSPACE_ROOT/scripts/arena/judge_credit_updater.py"
    
    if [[ ! -f "$weight_script" ]]; then
        log_warning "评委权重更新脚本不存在: $weight_script"
        return 0
    fi
    
    cd "$WORKSPACE_ROOT"
    if python3 "$weight_script"; then
        log_info "评委权重更新成功"
        return 0
    else
        log_warning "评委权重更新失败，但继续执行"
        return 0
    fi
}

# 执行GitHub同步
run_github_sync() {
    log_info "开始GitHub同步..."
    
    local sync_script="$WORKSPACE_ROOT/scripts/github/sync_clean.sh"
    
    if [[ ! -f "$sync_script" ]]; then
        log_error "GitHub同步脚本不存在: $sync_script"
        return 1
    fi
    
    cd "$WORKSPACE_ROOT"
    local commit_msg="[SYNC]: Cron自动同步 $(date '+%Y-%m-%d %H:%M')"
    if "$sync_script" "$commit_msg"; then
        log_info "GitHub同步成功"
        return 0
    else
        log_error "GitHub同步失败"
        return 1
    fi
}

# 验证指纹对撞
verify_fingerprint() {
    log_info "开始验证指纹对撞..."
    
    local verify_script="$WORKSPACE_ROOT/scripts/sync/verify_readiness.sh"
    
    if [[ ! -f "$verify_script" ]]; then
        log_warning "指纹验证脚本不存在: $verify_script"
        return 0
    fi
    
    cd "$WORKSPACE_ROOT"
    if bash "$verify_script"; then
        log_info "指纹对撞验证成功"
        return 0
    else
        log_warning "指纹对撞验证失败，但继续执行"
        return 0
    fi
}

# 主执行流程
main() {
    local dry_run=false
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                dry_run=true
                shift
                ;;
            --help|-h)
                echo "用法: $0 [--dry-run]"
                echo "  --dry-run  干运行模式，仅显示命令不执行"
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                exit 1
                ;;
        esac
    done
    
    # 初始化日志
    init_logging
    
    # 检查环境
    check_environment
    
    if [[ "$dry_run" == true ]]; then
        dry_run_mode
        exit 0
    fi
    
    log_info "开始执行Cron调度..."
    
    # 执行顺序
    local success=true
    
    # 1. 生成实战报告
    if ! generate_arena_report; then
        success=false
    fi
    
    # 2. 同步监控列表
    if ! sync_watch_list; then
        success=false
    fi
    
    # 3. 更新评委权重（可选，根据时间决定）
    local current_hour=$(date '+%H')
    if [[ "$current_hour" == "18" ]]; then
        if ! update_judge_weights; then
            success=false
        fi
    else
        log_info "非18:00时段，跳过评委权重更新"
    fi
    
    # 4. GitHub同步
    if ! run_github_sync; then
        success=false
    fi
    
    # 5. 验证指纹对撞
    if ! verify_fingerprint; then
        success=false
    fi
    
    # 总结
    if [[ "$success" == true ]]; then
        log_info "🎉 Cron调度执行完成，所有任务成功"
        echo "=== 琥珀引擎Cron调度结束: $(date '+%Y-%m-%d %H:%M:%S') ==="
        exit 0
    else
        log_error "❌ Cron调度执行完成，但有任务失败"
        echo "=== 琥珀引擎Cron调度结束（有失败）: $(date '+%Y-%m-%d %H:%M:%S') ==="
        exit 1
    fi
}

# 执行主函数
main "$@"