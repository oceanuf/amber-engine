#!/bin/bash
# 琥珀引擎 - 数据一致性监控脚本
# 版本: v1.0.0
# 用途: 监控Web数据真实性，防止模拟数据显示问题
# 执行频率: 每小时一次 (通过Cron)

set -e

# ============================================
# 配置参数
# ============================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 路径配置
WORKSPACE_DIR="/home/luckyelite/.openclaw/workspace/amber-engine"
LOG_DIR="${WORKSPACE_DIR}/logs/monitoring"
DATA_FILE="${WORKSPACE_DIR}/database/cleaned/resonance_signal_cleaned.json"
WEB_URL="https://gemini.googlemanager.cn:10168/index.php"
TEST_URL="https://gemini.googlemanager.cn:10168/simple_test.php"

# 告警阈值
MAX_DATA_AGE_HOURS=24  # 数据最大年龄（小时）
CHECK_INTERVAL_MINUTES=60  # 检查间隔（分钟）

# ============================================
# 工具函数
# ============================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
    echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') - $1" >> "${LOG_DIR}/monitoring.log"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
    echo "[SUCCESS] $(date '+%Y-%m-%d %H:%M:%S') - $1" >> "${LOG_DIR}/monitoring.log"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
    echo "[WARNING] $(date '+%Y-%m-%d %H:%M:%S') - $1" >> "${LOG_DIR}/monitoring.log"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') - $1" >> "${LOG_DIR}/monitoring.log"
}

setup_logging() {
    # 创建日志目录
    mkdir -p "$LOG_DIR"
    
    # 设置日志文件权限
    touch "${LOG_DIR}/monitoring.log"
    touch "${LOG_DIR}/alerts.log"
    
    # 限制日志文件大小（保留最近7天）
    find "$LOG_DIR" -name "*.log" -mtime +7 -delete
}

check_data_freshness() {
    log_info "检查数据新鲜度..."
    
    if [ ! -f "$DATA_FILE" ]; then
        log_error "数据文件不存在: $DATA_FILE"
        return 1
    fi
    
    # 获取文件修改时间
    local file_mtime=$(stat -c %Y "$DATA_FILE")
    local current_time=$(date +%s)
    local age_hours=$(( (current_time - file_mtime) / 3600 ))
    
    # 提取数据中的时间戳
    local data_time=$(grep -o '"signal_time":"[^"]*"' "$DATA_FILE" | head -1 | cut -d'"' -f4)
    if [ -n "$data_time" ]; then
        local data_timestamp=$(date -d "$data_time" +%s 2>/dev/null || echo "0")
        if [ "$data_timestamp" != "0" ]; then
            local data_age_hours=$(( (current_time - data_timestamp) / 3600 ))
            log_info "数据时间: $data_time (年龄: ${data_age_hours}小时)"
        fi
    fi
    
    log_info "文件修改时间: $(date -d @$file_mtime '+%Y-%m-%d %H:%M:%S') (年龄: ${age_hours}小时)"
    
    if [ $age_hours -gt $MAX_DATA_AGE_HOURS ]; then
        log_error "数据过时: ${age_hours}小时 > ${MAX_DATA_AGE_HOURS}小时阈值"
        echo "[ALERT] 数据过时: ${age_hours}小时 | 文件: $DATA_FILE | 时间: $(date '+%Y-%m-%d %H:%M:%S')" >> "${LOG_DIR}/alerts.log"
        return 1
    else
        log_success "数据新鲜度检查通过: ${age_hours}小时"
        return 0
    fi
}

check_web_data_consistency() {
    log_info "检查Web数据一致性..."
    
    # 从数据文件提取真实评分
    local real_score=$(grep -o '"resonance_score":[0-9.]*' "$DATA_FILE" | cut -d':' -f2)
    
    if [ -z "$real_score" ]; then
        log_error "无法从数据文件提取共振评分"
        return 1
    fi
    
    log_info "数据文件共振评分: $real_score"
    
    # 从Web页面提取显示评分
    local web_content=$(curl -s -k --connect-timeout 10 "$WEB_URL" 2>/dev/null || true)
    
    if [ -z "$web_content" ]; then
        log_error "无法获取Web页面内容"
        return 1
    fi
    
    # 尝试多种方式提取评分
    local web_score=""
    
    # 方式1: 从PHP注入的数据中提取
    web_score=$(echo "$web_content" | grep -o "共振评分:[^<]*<strong[^>]*>[0-9.]*" | grep -o "[0-9.]*" | head -1)
    
    # 方式2: 从信号卡片中提取
    if [ -z "$web_score" ]; then
        web_score=$(echo "$web_content" | grep -o '<div class="score">[0-9.]*' | grep -o "[0-9.]*" | head -1)
    fi
    
    # 方式3: 使用测试页面
    if [ -z "$web_score" ]; then
        local test_content=$(curl -s -k --connect-timeout 10 "$TEST_URL" 2>/dev/null || true)
        web_score=$(echo "$test_content" | grep -o "实际显示评分: [0-9.]*" | grep -o "[0-9.]*" | head -1)
    fi
    
    if [ -z "$web_score" ]; then
        log_error "无法从Web页面提取共振评分"
        return 1
    fi
    
    log_info "Web页面共振评分: $web_score"
    
    # 比较评分
    local score_diff=$(echo "$real_score - $web_score" | bc | awk '{if($1<0) print -$1; else print $1}')
    
    if [ $(echo "$score_diff > 0.1" | bc) -eq 1 ]; then
        log_error "数据不一致: 数据文件($real_score) ≠ Web页面($web_score), 差异: $score_diff"
        echo "[ALERT] 数据不一致: 文件=$real_score, Web=$web_score, 差异=$score_diff | 时间: $(date '+%Y-%m-%d %H:%M:%S')" >> "${LOG_DIR}/alerts.log"
        return 1
    else
        log_success "Web数据一致性检查通过: $real_score ≈ $web_score (差异: $score_diff)"
        return 0
    fi
}

check_for_simulated_data() {
    log_info "检查模拟数据..."
    
    local web_content=$(curl -s -k --connect-timeout 10 "$WEB_URL" 2>/dev/null || true)
    
    if [ -z "$web_content" ]; then
        log_error "无法获取Web页面内容"
        return 1
    fi
    
    # 检查是否包含模拟数据特征
    local simulated_patterns=(
        "resonance_score: 85.5"
        "85.5分模拟数据"
        "模拟数据"
        "hardcoded.*85.5"
    )
    
    local found_simulated=false
    
    for pattern in "${simulated_patterns[@]}"; do
        if echo "$web_content" | grep -q -i "$pattern"; then
            log_error "检测到模拟数据特征: $pattern"
            found_simulated=true
        fi
    done
    
    if $found_simulated; then
        log_error "Web页面可能包含模拟数据"
        echo "[ALERT] 检测到模拟数据特征 | 时间: $(date '+%Y-%m-%d %H:%M:%S')" >> "${LOG_DIR}/alerts.log"
        return 1
    else
        log_success "模拟数据检查通过: 未发现模拟数据特征"
        return 0
    fi
}

check_php_injection() {
    log_info "检查PHP原生注入..."
    
    local web_content=$(curl -s -k --connect-timeout 10 "$WEB_URL" 2>/dev/null || true)
    
    if [ -z "$web_content" ]; then
        log_error "无法获取Web页面内容"
        return 1
    fi
    
    # 检查是否包含PHP注入特征
    local injection_patterns=(
        "PHP原生数据注入"
        "强力渗透版本"
        "resonance_signal_cleaned.json"
        "数据源:"
    )
    
    local found_injection=false
    
    for pattern in "${injection_patterns[@]}"; do
        if echo "$web_content" | grep -q "$pattern"; then
            log_info "找到PHP注入特征: $pattern"
            found_injection=true
        fi
    done
    
    if $found_injection; then
        log_success "PHP原生注入检查通过"
        return 0
    else
        log_error "未检测到PHP原生注入特征"
        echo "[ALERT] PHP原生注入特征缺失 | 时间: $(date '+%Y-%m-%d %H:%M:%S')" >> "${LOG_DIR}/alerts.log"
        return 1
    fi
}

generate_monitoring_report() {
    local status="$1"
    local checks_passed="$2"
    local total_checks="$3"
    local report_file="${LOG_DIR}/monitoring_report_$(date '+%Y%m%d_%H%M%S').json"
    
    local real_score=$(grep -o '"resonance_score":[0-9.]*' "$DATA_FILE" 2>/dev/null | cut -d':' -f2 || echo "N/A")
    local web_score=$(curl -s -k "$TEST_URL" 2>/dev/null | grep -o "实际显示评分: [0-9.]*" | grep -o "[0-9.]*" | head -1 || echo "N/A")
    
    cat > "$report_file" << EOF
{
  "monitoring_report": {
    "timestamp": "$(date '+%Y-%m-%d %H:%M:%S')",
    "status": "$status",
    "checks": {
      "passed": $checks_passed,
      "total": $total_checks,
      "success_rate": "$((checks_passed * 100 / total_checks))%"
    },
    "data": {
      "real_score": "$real_score",
      "web_score": "$web_score",
      "data_file": "$DATA_FILE",
      "data_age_hours": "$(get_data_age_hours)"
    },
    "web_status": {
      "url": "$WEB_URL",
      "accessible": "$(check_web_accessible)",
      "php_injection": "$(check_php_injection_status)"
    },
    "alerts": {
      "last_hour": $(count_alerts_last_hour),
      "today": $(count_alerts_today)
    }
  }
}
EOF
    
    log_info "监控报告生成完成: $report_file"
}

get_data_age_hours() {
    if [ -f "$DATA_FILE" ]; then
        local file_mtime=$(stat -c %Y "$DATA_FILE")
        local current_time=$(date +%s)
        echo $(( (current_time - file_mtime) / 3600 ))
    else
        echo "N/A"
    fi
}

check_web_accessible() {
    if curl -s -k --connect-timeout 5 "$WEB_URL" >/dev/null 2>&1; then
        echo "true"
    else
        echo "false"
    fi
}

check_php_injection_status() {
    local web_content=$(curl -s -k --connect-timeout 5 "$WEB_URL" 2>/dev/null || true)
    if echo "$web_content" | grep -q "PHP原生数据注入"; then
        echo "present"
    else
        echo "missing"
    fi
}

count_alerts_last_hour() {
    local one_hour_ago=$(date -d '1 hour ago' '+%Y-%m-%d %H:%M:%S')
    grep -c "\[ALERT\].*$(date '+%Y-%m-%d')" "${LOG_DIR}/alerts.log" 2>/dev/null || echo 0
}

count_alerts_today() {
    grep -c "\[ALERT\].*$(date '+%Y-%m-%d')" "${LOG_DIR}/alerts.log" 2>/dev/null || echo 0
}

send_alert() {
    local alert_message="$1"
    local alert_level="$2"
    
    # 记录到告警日志
    echo "[$alert_level] $alert_message | 时间: $(date '+%Y-%m-%d %H:%M:%S')" >> "${LOG_DIR}/alerts.log"
    
    # 这里可以添加发送邮件、钉钉、Slack等告警逻辑
    # 例如:
    # send_dingtalk_alert "$alert_message" "$alert_level"
    # send_email_alert "$alert_message" "$alert_level"
    
    log_warning "告警已记录: $alert_message"
}

# ============================================
# 主执行流程
# ============================================

main() {
    log_info "开始琥珀引擎数据一致性监控..."
    
    # 设置日志
    setup_logging
    
    # 执行检查
    local total_checks=4
    local passed_checks=0
    local failed_checks=()
    
    # 检查1: 数据新鲜度
    if check_data_freshness; then
        passed_checks=$((passed_checks+1))
    else
        failed_checks+=("数据新鲜度检查失败")
        send_alert "数据新鲜度检查失败" "ERROR"
    fi
    
    # 检查2: Web数据一致性
    if check_web_data_consistency; then
        passed_checks=$((passed_checks+1))
    else
        failed_checks+=("Web数据一致性检查失败")
        send_alert "Web数据一致性检查失败" "ERROR"
    fi
    
    # 检查3: 模拟数据检查
    if check_for_simulated_data; then
        passed_checks=$((passed_checks+1))
    else
        failed_checks+=("模拟数据检查失败")
        send_alert "检测到模拟数据特征" "CRITICAL"
    fi
    
    # 检查4: PHP注入检查
    if check_php_injection; then
        passed_checks=$((passed_checks+1))
    else
        failed_checks+=("PHP注入检查失败")
        send_alert "PHP原生注入特征缺失" "WARNING"
    fi
    
    # 生成报告
    if [ $passed_checks -eq $total_checks ]; then
        log_success "所有监控检查通过 ($passed_checks/$total_checks)"
        generate_monitoring_report "HEALTHY" "$passed_checks" "$total_checks"
        exit 0
    else
        log_error "监控检查失败: $passed_checks/$total_checks 通过"
        log_error "失败项目: ${failed_checks[*]}"
        generate_monitoring_report "UNHEALTHY" "$passed_checks" "$total_checks"
        exit 1
    fi
}

# 执行主函数
main "$@"