#!/bin/bash
# 🚨 端口自愈哨兵服务
# 功能：监控10168端口健康状态，连续失败时自动重启服务
# 法典依据：任务指令[2616-0411-P0C] 引擎架构加固与自愈哨兵实装
# 版本：V1.0.0

set -euo pipefail

# 配置常量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$WORKSPACE_ROOT/logs/sentry"
REPORT_DIR="$WORKSPACE_ROOT/logs/cron"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
LOG_FILE="$LOG_DIR/sentry_${TIMESTAMP}.log"
INCIDENT_REPORT="$REPORT_DIR/incident_${TIMESTAMP}.json"

# 监控配置
PORT=10168
HOST="localhost"
SERVICE_NAME="openclaw-gateway"  # 假设的服务名，根据实际调整
MAX_FAILURES=3
CHECK_INTERVAL=30  # 检查间隔（秒）
TIMEOUT=5  # 连接超时（秒）

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 初始化日志
init_logging() {
    mkdir -p "$LOG_DIR"
    mkdir -p "$REPORT_DIR"
    exec > >(tee -a "$LOG_FILE") 2>&1
    echo "=== 端口自愈哨兵启动: $(date '+%Y-%m-%d %H:%M:%S') ==="
}

# 打印带颜色的消息
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# 检查端口健康状态
check_port_health() {
    local host=$1
    local port=$2
    local timeout=$3
    
    # 方法1: 使用nc (netcat)
    if command -v nc &> /dev/null; then
        if nc -z -w "$timeout" "$host" "$port" &> /dev/null; then
            log_debug "端口检查通过 (nc): $host:$port"
            return 0
        fi
    fi
    
    # 方法2: 使用telnet
    if command -v telnet &> /dev/null; then
        # 简单版本，不完美但可用
        (echo "quit" | timeout "$timeout" telnet "$host" "$port" 2>&1 | grep -q "Connected") && {
            log_debug "端口检查通过 (telnet): $host:$port"
            return 0
        }
    fi
    
    # 方法3: 使用/dev/tcp (bash内置)
    if bash -c "cat < /dev/null > /dev/tcp/$host/$port" 2>/dev/null; then
        log_debug "端口检查通过 (/dev/tcp): $host:$port"
        return 0
    fi
    
    # 方法4: 使用curl (如果是HTTP服务)
    if command -v curl &> /dev/null; then
        if curl -s -o /dev/null --max-time "$timeout" "http://$host:$port/health" 2>/dev/null; then
            log_debug "端口检查通过 (curl): $host:$port"
            return 0
        fi
    fi
    
    # 所有方法都失败
    return 1
}

# 重启服务
restart_service() {
    local service_name=$1
    log_warning "尝试重启服务: $service_name"
    
    # 尝试systemctl重启
    if command -v systemctl &> /dev/null && systemctl is-enabled "$service_name" &> /dev/null; then
        log_info "使用systemctl重启服务"
        if sudo systemctl restart "$service_name"; then
            log_info "服务重启成功: $service_name"
            return 0
        else
            log_error "systemctl重启失败: $service_name"
            return 1
        fi
    fi
    
    # 尝试service命令
    if command -v service &> /dev/null; then
        log_info "使用service重启服务"
        if sudo service "$service_name" restart; then
            log_info "服务重启成功: $service_name"
            return 0
        else
            log_error "service重启失败: $service_name"
            return 1
        fi
    fi
    
    # 尝试直接kill进程并重启（最后手段）
    log_warning "使用进程重启方式"
    local pids
    pids=$(ss -tlnp 2>/dev/null | grep ":$PORT " | awk '{print $6}' | grep -oP 'pid=\K\d+' | head -1)
    
    if [[ -n "$pids" ]]; then
        log_info "杀死进程: $pids"
        if sudo kill -9 "$pids" 2>/dev/null; then
            log_info "进程已终止"
            sleep 2
            # 这里应该启动服务，但需要知道启动命令
            log_warning "需要手动配置服务启动命令"
            return 2
        else
            log_error "无法终止进程: $pids"
            return 1
        fi
    else
        log_error "未找到监听端口 $PORT 的进程"
        return 1
    fi
}

# 生成事故报告
generate_incident_report() {
    local failure_count=$1
    local incident_time=$2
    local restart_attempted=$3
    local restart_success=$4
    
    local report_data
    report_data=$(cat <<EOF
{
  "incident_id": "$(uuidgen 2>/dev/null || echo "incident_${TIMESTAMP}")",
  "timestamp": "$(date '+%Y-%m-%dT%H:%M:%S%z')",
  "port": $PORT,
  "host": "$HOST",
  "service_name": "$SERVICE_NAME",
  "failure_count": $failure_count,
  "incident_time": "$incident_time",
  "restart_attempted": $restart_attempted,
  "restart_success": $restart_success,
  "check_interval": $CHECK_INTERVAL,
  "max_failures": $MAX_FAILURES,
  "system_info": {
    "hostname": "$(hostname)",
    "uname": "$(uname -a)",
    "uptime": "$(uptime -p 2>/dev/null || echo "unknown")"
  },
  "remediation_actions": [
    {
      "action": "port_check",
      "status": "failed",
      "timestamp": "$(date '+%Y-%m-%dT%H:%M:%S%z')"
    }
  ]
}
EOF
)
    
    echo "$report_data" | jq . > "$INCIDENT_REPORT" 2>/dev/null || echo "$report_data" > "$INCIDENT_REPORT"
    log_info "事故报告已生成: $INCIDENT_REPORT"
}

# 主监控循环
monitor_loop() {
    local failure_count=0
    local incident_start_time=""
    
    log_info "开始监控端口: $HOST:$PORT"
    log_info "服务名称: $SERVICE_NAME"
    log_info "最大失败次数: $MAX_FAILURES"
    log_info "检查间隔: ${CHECK_INTERVAL}秒"
    
    while true; do
        local check_time
        check_time=$(date '+%Y-%m-%d %H:%M:%S')
        
        log_debug "检查端口 $HOST:$PORT ..."
        
        if check_port_health "$HOST" "$PORT" "$TIMEOUT"; then
            # 端口健康
            if [[ $failure_count -gt 0 ]]; then
                log_info "端口恢复健康 (连续失败: $failure_count)"
                failure_count=0
                incident_start_time=""
            fi
        else
            # 端口不健康
            failure_count=$((failure_count + 1))
            
            if [[ -z "$incident_start_time" ]]; then
                incident_start_time=$check_time
            fi
            
            log_warning "端口检查失败: $HOST:$PORT (连续失败: $failure_count/$MAX_FAILURES)"
            
            # 检查是否达到失败阈值
            if [[ $failure_count -ge $MAX_FAILURES ]]; then
                log_error "达到失败阈值 ($MAX_FAILURES)，触发自愈流程"
                
                # 生成事故报告
                generate_incident_report "$failure_count" "$incident_start_time" "true" "false"
                
                # 尝试重启服务
                local restart_attempted=true
                local restart_success=false
                
                if restart_service "$SERVICE_NAME"; then
                    restart_success=true
                    log_info "服务重启成功，重置失败计数"
                    
                    # 更新事故报告
                    generate_incident_report "$failure_count" "$incident_start_time" "$restart_attempted" "$restart_success"
                    
                    # 重置计数器
                    failure_count=0
                    incident_start_time=""
                    
                    # 等待服务启动
                    log_info "等待服务启动 (10秒)..."
                    sleep 10
                else
                    log_error "服务重启失败"
                    generate_incident_report "$failure_count" "$incident_start_time" "$restart_attempted" "$restart_success"
                    
                    # 即使重启失败，也重置计数器避免无限循环
                    failure_count=0
                    incident_start_time=""
                fi
            fi
        fi
        
        # 等待下一次检查
        sleep "$CHECK_INTERVAL"
    done
}

# 命令行参数处理
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --port)
                PORT="$2"
                shift 2
                ;;
            --host)
                HOST="$2"
                shift 2
                ;;
            --service)
                SERVICE_NAME="$2"
                shift 2
                ;;
            --max-failures)
                MAX_FAILURES="$2"
                shift 2
                ;;
            --interval)
                CHECK_INTERVAL="$2"
                shift 2
                ;;
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            --test)
                # 测试模式：只检查一次并退出
                log_info "测试模式：检查端口 $HOST:$PORT"
                if check_port_health "$HOST" "$PORT" "$TIMEOUT"; then
                    log_info "✅ 端口健康: $HOST:$PORT"
                    exit 0
                else
                    log_error "❌ 端口不健康: $HOST:$PORT"
                    exit 1
                fi
                ;;
            --dry-run)
                # 干运行模式：显示配置但不执行
                log_info "干运行模式 - 显示配置"
                echo "端口: $PORT"
                echo "主机: $HOST"
                echo "服务名: $SERVICE_NAME"
                echo "最大失败次数: $MAX_FAILURES"
                echo "检查间隔: ${CHECK_INTERVAL}秒"
                echo "超时时间: ${TIMEOUT}秒"
                echo "日志目录: $LOG_DIR"
                echo "报告目录: $REPORT_DIR"
                exit 0
                ;;
            --help)
                echo "使用说明: $0 [选项]"
                echo "选项:"
                echo "  --port PORT          监控端口 (默认: 10168)"
                echo "  --host HOST          监控主机 (默认: localhost)"
                echo "  --service NAME       服务名称 (默认: openclaw-gateway)"
                echo "  --max-failures N     最大失败次数 (默认: 3)"
                echo "  --interval SECONDS   检查间隔秒数 (默认: 30)"
                echo "  --timeout SECONDS    连接超时秒数 (默认: 5)"
                echo "  --test               测试模式：检查一次并退出"
                echo "  --dry-run            干运行模式：显示配置不执行"
                echo "  --help               显示帮助信息"
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                exit 1
                ;;
        esac
    done
}

# 主函数
main() {
    init_logging
    parse_args "$@"
    
    log_info "端口自愈哨兵启动"
    log_info "工作目录: $WORKSPACE_ROOT"
    
    # 检查必需的工具
    local missing_tools=""
    for tool in nc telnet curl ss; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools="$missing_tools $tool"
        fi
    done
    
    if [[ -n "$missing_tools" ]]; then
        log_warning "缺少工具:$missing_tools，某些检查方法可能不可用"
    fi
    
    # 检查jq（用于格式化JSON报告）
    if ! command -v jq &> /dev/null; then
        log_warning "jq未安装，事故报告将使用纯文本格式"
    fi
    
    # 启动监控循环
    monitor_loop
}

# 捕获Ctrl+C信号
trap 'log_info "接收到中断信号，停止监控"; exit 0' INT TERM

# 运行主函数
main "$@"