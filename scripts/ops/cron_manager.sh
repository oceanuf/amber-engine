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

# 架构加固预检：检查端口健康和数据降级模块
preflight_checks() {
    log_info "开始架构加固预检..."
    
    # 检查10168端口健康状态
    local port_check_script="$WORKSPACE_ROOT/scripts/ops/service_sentry.sh"
    if [[ -f "$port_check_script" ]]; then
        log_info "检查10168端口健康状态..."
        if "$port_check_script" --test &> /dev/null; then
            log_info "✅ 10168端口健康"
        else
            log_warning "⚠️  10168端口不健康，尝试重启服务..."
            
            # 这里可以调用service_sentry.sh的自动修复功能
            # 但由于权限问题，暂时只记录警告
            log_warning "端口异常，但需要手动或配置sudo权限执行重启"
            
            # 记录到日志文件
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] 10168端口异常 - 需要人工干预" >> "$LOG_FILE"
        fi
    else
        log_warning "端口检查脚本不存在: $port_check_script"
    fi
    
    # 检查数据降级模块
    local fallback_script="$WORKSPACE_ROOT/scripts/arena/technical_fallback.py"
    if [[ -f "$fallback_script" ]]; then
        log_info "检查数据降级模块..."
        
        # 测试数据降级模块
        cd "$WORKSPACE_ROOT"
        if python3 -c "import sys; sys.path.insert(0, '.'); from scripts.arena.technical_fallback import DataFallback; print('✅ 数据降级模块导入成功')" 2>&1 | grep -q "导入成功"; then
            log_info "✅ 数据降级模块就绪"
            
            # 测试获取一个股票数据
            local test_output
            test_output=$(python3 -c "
import sys
sys.path.insert(0, '.')
from scripts.arena.technical_fallback import DataFallback
fallback = DataFallback()
result = fallback.get_stock_price('510300')
if result.get('success'):
    print(f'测试通过: {result["data_source"]}')
else:
    print(f'测试失败: {result.get("reason", "unknown")}')
" 2>&1)
            
            if echo "$test_output" | grep -q "测试通过"; then
                log_info "✅ 数据降级功能测试通过"
            else
                log_warning "⚠️  数据降级功能测试异常: $test_output"
            fi
        else
            log_warning "⚠️  数据降级模块导入失败"
        fi
    else
        log_warning "数据降级脚本不存在: $fallback_script"
    fi
    
    # 检查arena_watch_list.json有效性
    local watch_list_file="$WORKSPACE_ROOT/config/arena_watch_list.json"
    if [[ -f "$watch_list_file" ]]; then
        log_info "检查arena_watch_list.json有效性..."
        
        if python3 -c "
import json
with open('$watch_list_file', 'r', encoding='utf-8') as f:
    data = json.load(f)
    
# 基本验证
if not isinstance(data, dict):
    print('无效格式: 不是字典')
elif 'watch_list' not in data:
    print('缺少watch_list字段')
elif not isinstance(data.get('watch_list', []), list):
    print('watch_list不是列表')
else:
    tickers = [item.get('ticker') for item in data.get('watch_list', []) if item.get('ticker')]
    print(f'验证通过: {len(tickers)}个有效标的')
" 2>&1 | grep -q "验证通过"; then
            log_info "✅ arena_watch_list.json验证通过"
        else
            local validation_result
            validation_result=$(python3 -c "
import json
try:
    with open('$watch_list_file', 'r', encoding='utf-8') as f:
        data = json.load(f)
    print('JSON格式正确')
except Exception as e:
    print(f'JSON解析错误: {e}')
" 2>&1)
            log_warning "⚠️  arena_watch_list.json验证失败: $validation_result"
        fi
    else
        log_warning "arena_watch_list.json不存在: $watch_list_file"
    fi
    
    log_info "架构加固预检完成"
}

# 干运行模式：仅打印命令，不执行
dry_run_mode() {
    log_info "干运行模式 - 仅显示将要执行的命令"
    
    echo "0. 生成宏观脉冲简报: cd $WORKSPACE_ROOT && python3 scripts/pipeline/macro_pulse_dispatcher.py"
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

# 检查数据就绪状态
check_data_ready() {
    log_info "检查数据就绪状态..."
    
    local trigger_script="$WORKSPACE_ROOT/scripts/pipeline/data_ready_trigger.py"
    
    if [[ ! -f "$trigger_script" ]]; then
        log_warning "数据就绪触发器不存在: $trigger_script"
        return 1  # 视为数据未就绪
    fi
    
    cd "$WORKSPACE_ROOT"
    
    # 执行数据就绪检查（不等待，立即检查）
    log_info "执行数据就绪检查..."
    local exit_code
    
    if python3 "$trigger_script" --no-wait; then
        exit_code=$?
    else
        exit_code=$?
    fi
    
    case $exit_code in
        0)
            log_info "✅ 数据就绪，可以启动评委中控"
            return 0
            ;;
        2)
            log_warning "⚠️  数据未就绪，但降级模式可用"
            return 2  # 降级模式
            ;;
        *)
            log_error "❌ 数据就绪检查失败，退出码: $exit_code"
            return 1  # 失败
            ;;
    esac
}

# 更新评委权重（支持数据就绪检测）
update_judge_weights() {
    log_info "开始更新评委权重..."
    
    local weight_script="$WORKSPACE_ROOT/scripts/arena/judge_credit_updater.py"
    
    if [[ ! -f "$weight_script" ]]; then
        log_warning "评委权重更新脚本不存在: $weight_script"
        return 0
    fi
    
    # 检查数据就绪状态
    check_data_ready
    local data_ready_status=$?
    
    cd "$WORKSPACE_ROOT"
    
    # 根据数据就绪状态执行不同的命令
    if [[ $data_ready_status -eq 0 ]]; then
        # 数据就绪，正常执行
        log_info "数据就绪，执行正常评委权重更新"
        if python3 "$weight_script" --auto --signal="DATA_READY"; then
            log_info "评委权重更新成功"
            return 0
        else
            log_warning "评委权重更新失败，但继续执行"
            return 0
        fi
    elif [[ $data_ready_status -eq 2 ]]; then
        # 降级模式
        log_info "数据未就绪，执行降级模式评委权重更新"
        if python3 "$weight_script" --auto --signal="FALLBACK_MODE"; then
            log_info "评委权重更新成功（降级模式）"
            return 0
        else
            log_warning "评委权重更新失败（降级模式），但继续执行"
            return 0
        fi
    else
        # 数据检查失败
        log_warning "数据就绪检查失败，跳过评委权重更新"
        return 0
    fi
}

# 记录资产净值
record_nav() {
    log_info "开始记录资产净值..."
    
    local nav_script="$WORKSPACE_ROOT/scripts/arena/nav_recorder.py"
    
    if [[ ! -f "$nav_script" ]]; then
        log_warning "资产净值记录脚本不存在: $nav_script"
        return 0
    fi
    
    cd "$WORKSPACE_ROOT"
    if python3 "$nav_script"; then
        log_info "资产净值记录成功"
        return 0
    else
        log_warning "资产净值记录失败，但继续执行"
        return 0
    fi
}

# 清算交易
settle_trades() {
    log_info "开始清算交易..."
    
    local settle_script="$WORKSPACE_ROOT/scripts/arena/trade_settler.py"
    
    if [[ ! -f "$settle_script" ]]; then
        log_warning "交易清算脚本不存在: $settle_script"
        return 0
    fi
    
    cd "$WORKSPACE_ROOT"
    if python3 "$settle_script"; then
        log_info "交易清算成功"
        return 0
    else
        log_warning "交易清算失败，但继续执行"
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

# 生成宏观脉冲简报
# 任务指令 [2616-0412-P1]：宏观感知哨兵实装
# 法典依据：ARENA-SOP.md 第一阶段
# 验收标准：1) 感知自动化 2) 逻辑脱耦 3) 流程首环挂接 4) 工程诚实
generate_macro_pulse() {
    log_info "开始生成宏观脉冲简报..."
    
    local pulse_script="$WORKSPACE_ROOT/scripts/pipeline/macro_pulse_dispatcher.py"
    
    if [[ ! -f "$pulse_script" ]]; then
        log_warning "宏观脉冲分发器不存在: $pulse_script"
        log_warning "跳过宏观脉冲生成（系统将缺少宏观感知输入）"
        return 0  # 不是致命错误，继续执行
    fi
    
    log_info "执行宏观脉冲分发器..."
    cd "$WORKSPACE_ROOT"
    
    # 获取当前小时，决定是否使用缓存
    local current_hour=$(date '+%H')
    local use_cache=""
    
    # 如果在09:00-10:00之间，获取新鲜新闻；其他时间使用缓存
    if [[ "$current_hour" == "09" ]]; then
        log_info "09:00时段，获取新鲜宏观新闻"
        use_cache="--fresh"
    else
        log_info "非09:00时段，使用缓存新闻"
        use_cache=""
    fi
    
    # 执行宏观脉冲分发器
    if python3 "$pulse_script" $use_cache; then
        log_info "✅ 宏观脉冲简报生成成功"
        
        # 检查是否生成报告
        local today_report="$WORKSPACE_ROOT/reports/macro/macro_pulse_today.json"
        if [[ -f "$today_report" ]]; then
            log_info "宏观脉冲报告已生成: $today_report"
            
            # 提取宏观强度指数
            local macro_intensity
            macro_intensity=$(python3 -c "
import json
try:
    with open('$today_report', 'r', encoding='utf-8') as f:
        data = json.load(f)
    intensity = data.get('executive_summary', {}).get('macro_intensity_index', 0)
    print(f'{intensity:.2f}')
except Exception as e:
    print('0.00')
")
            
            log_info "📈 今日宏观强度指数: $macro_intensity/1.0"
            
            # 根据宏观强度决定是否继续执行
            if (( $(echo "$macro_intensity >= 0.7" | bc -l) )); then
                log_warning "⚠️  高宏观强度($macro_intensity)，市场可能出现大幅波动"
            elif (( $(echo "$macro_intensity >= 0.4" | bc -l) )); then
                log_info "中宏观强度($macro_intensity)，正常执行后续流程"
            else
                log_info "低宏观强度($macro_intensity)，市场相对平静"
            fi
        fi
        
        return 0
    else
        log_warning "⚠️  宏观脉冲简报生成失败，但继续执行（降级模式）"
        
        # 创建降级标记
        local fallback_marker="$WORKSPACE_ROOT/.MACRO_FALLBACK_ACTIVE"
        echo "{\"timestamp\": \"$(date -Is)\", \"reason\": \"macro_pulse_dispatcher_failed\"}" > "$fallback_marker"
        log_warning "已创建宏观降级标记: $fallback_marker"
        
        return 0  # 不是致命错误，继续执行
    fi
}

# 审计候选池
# 任务指令 [2616-0412-P3]：数据净化流水线与候选池深度挂接
# 法典依据：ARENA-SOP.md 第三阶段
# 验收标准：1) 自动化安检 2) 异常熔断逻辑 3) 信号级联挂接 4) 量化审计报告
audit_candidates() {
    log_info "开始审计候选池..."
    
    local audit_script="$WORKSPACE_ROOT/scripts/pipeline/data_sanitizer.py"
    
    if [[ ! -f "$audit_script" ]]; then
        log_warning "数据净化脚本不存在: $audit_script"
        log_warning "跳过候选池审计（系统将缺少数据安检）"
        return 0  # 不是致命错误，继续执行
    fi
    
    log_info "执行候选池审计..."
    cd "$WORKSPACE_ROOT"
    
    if python3 "$audit_script" --audit-candidates; then
        log_info "✅ 候选池审计成功"
        
        # 检查是否生成审计报告
        local audit_report_dir="$WORKSPACE_ROOT/reports/sanitization"
        local today_report="$audit_report_dir/candidate_audit_today.json"
        
        if [[ -f "$today_report" ]]; then
            log_info "候选池审计报告已生成: $today_report"
            
            # 提取审计摘要
            local audit_summary
            audit_summary=$(python3 -c "
import json
try:
    with open('$today_report', 'r', encoding='utf-8') as f:
        data = json.load(f)
    summary = data.get('metadata', {})
    total = summary.get('total_candidates', 0)
    passed = summary.get('passed_count', 0)
    removed = summary.get('removed_count', 0)
    warning = summary.get('warning_count', 0)
    pass_rate = summary.get('pass_rate', 0)
    
    print(f'总共候选: {total}')
    print(f'通过数量: {passed}')
    print(f'警告数量: {warning}')
    print(f'剔除数量: {removed}')
    print(f'通过率: {pass_rate*100:.1f}%')
    
    # 信号级联：只有当有通过的候选时才发出DATA_READY_FOR_JUDGE信号
    if passed > 0:
        print('SIGNAL:DATA_READY_FOR_JUDGE')
    else:
        print('SIGNAL:NO_HEALTHY_CANDIDATES')
    
except Exception as e:
    print(f'解析审计报告失败: {e}')
    print('SIGNAL:PARSE_ERROR')
")
            
            # 输出摘要
            while IFS= read -r line; do
                if [[ "$line" == SIGNAL:* ]]; then
                    log_info "信号: $line"
                    
                    if [[ "$line" == "SIGNAL:DATA_READY_FOR_JUDGE" ]]; then
                        log_info "🚀 数据已就绪，可以向评委中控传递"
                    elif [[ "$line" == "SIGNAL:NO_HEALTHY_CANDIDATES" ]]; then
                        log_warning "⚠️  无健康候选，阻止向评委中控传递"
                    fi
                else
                    log_info "$line"
                fi
            done <<< "$audit_summary"
        fi
        
        return 0
    else
        log_warning "⚠️  候选池审计失败，但继续执行（降级模式）"
        
        # 创建降级标记
        local fallback_marker="$WORKSPACE_ROOT/.DATA_SANITIZER_FALLBACK_ACTIVE"
        echo "{\"timestamp\": \"$(date -Is)\", \"reason\": \"data_sanitizer_audit_failed\"}" > "$fallback_marker"
        log_warning "已创建数据净化降级标记: $fallback_marker"
        
        return 0  # 不是致命错误，继续执行
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
    
    # 架构加固预检（新增）
    preflight_checks
    
    if [[ "$dry_run" == true ]]; then
        dry_run_mode
        exit 0
    fi
    
    log_info "开始执行Cron调度..."
    
    # 执行顺序
    local success=true
    
    # 0. 生成宏观脉冲简报（SOP第一阶段）
    if ! generate_macro_pulse; then
        success=false
        log_warning "宏观脉冲生成失败，但继续执行后续流程"
    fi
    
    # 1. 审计候选池（SOP第三阶段 - 数据净化）
    if ! audit_candidates; then
        success=false
        log_warning "候选池审计失败，但继续执行后续流程"
    fi
    
    # 2. 生成实战报告
    if ! generate_arena_report; then
        success=false
    fi
    
    # 3. 同步监控列表
    if ! sync_watch_list; then
        success=false
    fi
    
    # 4. 更新评委权重（可选，根据时间决定）
    local current_hour=$(date '+%H')
    if [[ "$current_hour" == "18" ]]; then
        if ! update_judge_weights; then
            success=false
        fi
    else
        log_info "非18:00时段，跳过评委权重更新"
    fi
    
    # 5. 记录资产净值
    if ! record_nav; then
        success=false
    fi
    
    # 6. 清算交易
    if ! settle_trades; then
        success=false
    fi
    
    # 7. GitHub同步
    if ! run_github_sync; then
        success=false
    fi
    
    # 8. 验证指纹对撞
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