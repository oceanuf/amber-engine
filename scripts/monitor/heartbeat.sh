#!/bin/bash
#
# 琥珀引擎心跳监控脚本
# 监控 orchestrator 调度器是否正常执行
# 符合 [2614-092号] 指令要求：若超过 70 分钟未更新，自动发送高亮红色告警
#

set -e

# 配置
LOG_FILE="logs/cron_orchestrator.log"
CHECK_INTERVAL_MINUTES=60  # 每小时检查一次
WARNING_THRESHOLD_MINUTES=70
ALERT_COLOR_RED='\033[1;31m'
ALERT_COLOR_RESET='\033[0m'
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
SCRIPT_NAME=$(basename "$0")

# 工作目录切换到项目根目录
cd "$(dirname "$0")/../.." || {
    echo "❌ 无法切换到项目根目录"
    exit 1
}

# 检查日志文件是否存在
if [ ! -f "$LOG_FILE" ]; then
    echo -e "${ALERT_COLOR_RED}🚨 [$TIMESTAMP] $SCRIPT_NAME: 警告 - 日志文件不存在: $LOG_FILE${ALERT_COLOR_RESET}"
    echo "   创建空日志文件..."
    mkdir -p "$(dirname "$LOG_FILE")"
    touch "$LOG_FILE"
    exit 0
fi

# 获取日志文件最后修改时间（分钟）
current_time=$(date +%s)
file_mtime=$(stat -c %Y "$LOG_FILE")
minutes_since_update=$(( (current_time - file_mtime) / 60 ))

# 输出状态信息
echo "[$TIMESTAMP] $SCRIPT_NAME: 心跳检查"
echo "   日志文件: $LOG_FILE"
echo "   最后修改: $(date -d @$file_mtime '+%Y-%m-%d %H:%M:%S')"
echo "   已过去: $minutes_since_update 分钟"
echo "   阈值: $WARNING_THRESHOLD_MINUTES 分钟"

# 检查最近日志中的API错误 (只检查最近30分钟)
api_error_patterns=("TUSHARE_API_ERROR" "AUTH_FAIL" "NET_TIMEOUT" "INSUFFICIENT_DATA" "SCHEMA_MISMATCH")
error_found=false
error_messages=()
recent_minutes=30  # 只检查最近30分钟的错误
recent_timestamp=$(date -d "$recent_minutes minutes ago" '+%Y-%m-%d %H:%M')

# 检查最近30分钟的日志
if [ -f "$LOG_FILE" ]; then
    # 提取最近30分钟的日志内容
    recent_log=$(awk -v threshold="$recent_timestamp" '
        BEGIN {found=0} 
        /^\[20[0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]/ {
            timestamp=substr($1,2) " " substr($2,1,5)
            if (timestamp >= threshold) found=1
            else found=0
        }
        found {print}
    ' "$LOG_FILE")
    
    # 在最近日志中搜索错误模式
    for pattern in "${api_error_patterns[@]}"; do
        echo "$recent_log" | grep -q "$pattern" 2>/dev/null
        if [ $? -eq 0 ]; then
            # 获取最近匹配的行
            error_line=$(echo "$recent_log" | grep "$pattern" | tail -1)
            # 过滤掉DEBUG级别的网络超时（模拟数据）
            if [[ ! "$error_line" =~ "DEBUG.*模拟网络超时" ]]; then
                error_messages+=("$error_line")
                error_found=true
            fi
        fi
    done
fi

# 检查是否超过阈值
if [ $minutes_since_update -ge $WARNING_THRESHOLD_MINUTES ]; then
    echo -e "${ALERT_COLOR_RED}🚨 [$TIMESTAMP] $SCRIPT_NAME: 紧急告警 - orchestrator 已停止 ${minutes_since_update} 分钟！${ALERT_COLOR_RESET}"
    echo -e "${ALERT_COLOR_RED}   最后执行时间: $(date -d @$file_mtime '+%Y-%m-%d %H:%M:%S')${ALERT_COLOR_RESET}"
    echo -e "${ALERT_COLOR_RED}   当前时间: $(date '+%Y-%m-%d %H:%M:%S')${ALERT_COLOR_RESET}"
    echo -e "${ALERT_COLOR_RED}   超过阈值: $((minutes_since_update - WARNING_THRESHOLD_MINUTES)) 分钟${ALERT_COLOR_RESET}"
    
    # 检查Cron服务状态
    if systemctl is-active cron >/dev/null 2>&1; then
        echo -e "${ALERT_COLOR_RED}   Cron服务状态: 运行中${ALERT_COLOR_RESET}"
    else
        echo -e "${ALERT_COLOR_RED}   Cron服务状态: 停止${ALERT_COLOR_RESET}"
    fi
    
    # 检查最近日志内容
    echo -e "${ALERT_COLOR_RED}   最近日志片段:${ALERT_COLOR_RESET}"
    tail -5 "$LOG_FILE" | while IFS= read -r line; do
        echo -e "${ALERT_COLOR_RED}     $line${ALERT_COLOR_RESET}"
    done
    
    # 建议操作
    echo -e "${ALERT_COLOR_RED}   建议立即检查:${ALERT_COLOR_RESET}"
    echo -e "${ALERT_COLOR_RED}     1. 检查Cron配置: crontab -l | grep orchestrator${ALERT_COLOR_RESET}"
    echo -e "${ALERT_COLOR_RED}     2. 手动测试调度器: python3 scripts/orchestrator.py --test${ALERT_COLOR_RESET}"
    echo -e "${ALERT_COLOR_RED}     3. 检查脚本权限: ls -la scripts/orchestrator.py${ALERT_COLOR_RESET}"
    
    # 退出码非零表示告警
    exit 1
fi

# 检查API错误
if [ "$error_found" = true ]; then
    echo -e "${ALERT_COLOR_RED}🚨 [$TIMESTAMP] $SCRIPT_NAME: API错误检测 - 发现 ${#error_messages[@]} 个API错误！${ALERT_COLOR_RESET}"
    echo -e "${ALERT_COLOR_RED}   最后修改时间: $(date -d @$file_mtime '+%Y-%m-%d %H:%M:%S')${ALERT_COLOR_RESET}"
    echo -e "${ALERT_COLOR_RED}   错误模式: ${api_error_patterns[*]}${ALERT_COLOR_RESET}"
    
    # 显示错误消息
    echo -e "${ALERT_COLOR_RED}   最近错误:${ALERT_COLOR_RESET}"
    for error_msg in "${error_messages[@]}"; do
        echo -e "${ALERT_COLOR_RED}     $error_msg${ALERT_COLOR_RESET}"
    done
    
    echo -e "${ALERT_COLOR_RED}   建议立即检查:${ALERT_COLOR_RESET}"
    echo -e "${ALERT_COLOR_RED}     1. 检查Tushare Token是否有效${ALERT_COLOR_RESET}"
    echo -e "${ALERT_COLOR_RED}     2. 检查网络连接${ALERT_COLOR_RESET}"
    echo -e "${ALERT_COLOR_RED}     3. 查看详细日志: tail -50 $LOG_FILE${ALERT_COLOR_RESET}"
    
    # 退出码非零表示告警
    exit 1
fi

# 一切正常
echo "✅ [$TIMESTAMP] $SCRIPT_NAME: 心跳正常 - orchestrator 在 ${minutes_since_update} 分钟前执行"
exit 0