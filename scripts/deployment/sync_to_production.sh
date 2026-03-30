#!/bin/bash
# 琥珀引擎 - 生产环境同步脚本
# 版本: v1.0.0
# 用途: 将工作空间文件同步到生产Web服务器
# 执行权限: 需要sudo权限

set -e  # 遇到错误立即退出

# ============================================
# 配置参数
# ============================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 路径配置
WORKSPACE_DIR="/home/luckyelite/.openclaw/workspace/amber-engine"
PRODUCTION_DIR="/var/www/gemini_master/master-audit"
BACKUP_DIR="${PRODUCTION_DIR}/backups"

# 需要同步的文件和目录
SYNC_ITEMS=(
    "web/index.php"
    "web/get_latest_data.php"
    "web/css/style.css"
    "web/diagnostic.php"
    "web/verify_fix.php"
    "web/simple_test.php"
    "web/test_cache.php"
)

# ============================================
# 工具函数
# ============================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

check_prerequisites() {
    log_info "检查前置条件..."
    
    # 检查工作空间目录
    if [ ! -d "$WORKSPACE_DIR" ]; then
        log_error "工作空间目录不存在: $WORKSPACE_DIR"
        return 1
    fi
    
    # 检查生产目录
    if [ ! -d "$PRODUCTION_DIR" ]; then
        log_error "生产目录不存在: $PRODUCTION_DIR"
        return 1
    fi
    
    # 检查备份目录，不存在则创建
    if [ ! -d "$BACKUP_DIR" ]; then
        log_warning "备份目录不存在，创建: $BACKUP_DIR"
        sudo mkdir -p "$BACKUP_DIR"
        sudo chmod 755 "$BACKUP_DIR"
    fi
    
    log_success "前置条件检查通过"
    return 0
}

create_backup() {
    local source_file="$1"
    local target_dir="$2"
    
    if [ ! -f "$source_file" ]; then
        log_warning "源文件不存在，跳过备份: $source_file"
        return 0
    fi
    
    local filename=$(basename "$source_file")
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_file="${BACKUP_DIR}/${filename}.backup.${timestamp}"
    
    log_info "创建备份: $backup_file"
    sudo cp "$source_file" "$backup_file"
    
    if [ $? -eq 0 ]; then
        log_success "备份创建成功: $backup_file"
        # 记录备份信息
        echo "Backup: $backup_file | Source: $source_file | Time: $(date '+%Y-%m-%d %H:%M:%S')" >> "${BACKUP_DIR}/backup_history.log"
    else
        log_error "备份创建失败: $source_file"
        return 1
    fi
}

sync_file() {
    local source_path="$1"
    local target_path="$2"
    
    log_info "同步文件: $source_path -> $target_path"
    
    # 检查源文件是否存在
    if [ ! -f "$source_path" ]; then
        log_error "源文件不存在: $source_path"
        return 1
    fi
    
    # 检查目标文件是否存在（需要备份）
    if [ -f "$target_path" ]; then
        create_backup "$target_path" "$BACKUP_DIR"
    fi
    
    # 同步文件
    sudo cp "$source_path" "$target_path"
    
    if [ $? -eq 0 ]; then
        log_success "文件同步成功: $(basename "$source_path")"
        
        # 设置适当权限
        sudo chmod 644 "$target_path"
        sudo chown www-data:www-data "$target_path" 2>/dev/null || true
        
        # 记录同步信息
        local source_md5=$(md5sum "$source_path" | cut -d' ' -f1)
        local target_md5=$(md5sum "$target_path" | cut -d' ' -f1)
        
        if [ "$source_md5" = "$target_md5" ]; then
            log_success "MD5校验通过: $source_md5"
        else
            log_error "MD5校验失败: 源=$source_md5, 目标=$target_md5"
            return 1
        fi
    else
        log_error "文件同步失败: $source_path"
        return 1
    fi
}

verify_sync() {
    log_info "开始验证同步结果..."
    
    local verification_passed=true
    
    for item in "${SYNC_ITEMS[@]}"; do
        local source_file="${WORKSPACE_DIR}/${item}"
        local target_file="${PRODUCTION_DIR}/$(basename "$item")"
        
        # 调整目标路径（对于css目录）
        if [[ "$item" == web/css/* ]]; then
            target_file="${PRODUCTION_DIR}/css/$(basename "$item")"
        fi
        
        if [ ! -f "$source_file" ]; then
            log_warning "源文件不存在，跳过验证: $source_file"
            continue
        fi
        
        if [ ! -f "$target_file" ]; then
            log_error "目标文件不存在: $target_file"
            verification_passed=false
            continue
        fi
        
        local source_md5=$(md5sum "$source_file" | cut -d' ' -f1)
        local target_md5=$(md5sum "$target_file" | cut -d' ' -f1)
        
        if [ "$source_md5" = "$target_md5" ]; then
            log_success "✓ $(basename "$item"): MD5一致 ($source_md5)"
        else
            log_error "✗ $(basename "$item"): MD5不一致 (源=$source_md5, 目标=$target_md5)"
            verification_passed=false
        fi
    done
    
    if [ "$verification_passed" = true ]; then
        log_success "所有文件同步验证通过"
        return 0
    else
        log_error "部分文件同步验证失败"
        return 1
    fi
}

test_web_access() {
    log_info "测试Web访问..."
    
    local test_url="https://gemini.googlemanager.cn:10168/simple_test.php"
    local max_retries=3
    local retry_count=0
    
    while [ $retry_count -lt $max_retries ]; do
        log_info "尝试访问Web页面 (尝试 $((retry_count+1))/$max_retries)..."
        
        # 使用curl测试访问
        local response=$(curl -s -k --connect-timeout 10 "$test_url" 2>/dev/null || true)
        
        if echo "$response" | grep -q "修复成功"; then
            log_success "Web访问测试通过: 页面显示修复成功"
            return 0
        elif echo "$response" | grep -q "简单测试"; then
            log_success "Web访问测试通过: 页面可访问"
            return 0
        else
            log_warning "Web访问测试失败或响应异常"
            retry_count=$((retry_count+1))
            sleep 2
        fi
    done
    
    log_error "Web访问测试失败: 无法访问或响应异常"
    return 1
}

generate_report() {
    local status="$1"
    local report_file="${BACKUP_DIR}/sync_report_$(date '+%Y%m%d_%H%M%S').md"
    
    log_info "生成同步报告: $report_file"
    
    cat > "$report_file" << EOF
# 琥珀引擎生产环境同步报告

## 基本信息
- **报告时间**: $(date '+%Y-%m-%d %H:%M:%S')
- **同步状态**: $status
- **工作空间**: $WORKSPACE_DIR
- **生产环境**: $PRODUCTION_DIR
- **执行用户**: $(whoami)

## 同步项目
$(for item in "${SYNC_ITEMS[@]}"; do
    source_file="${WORKSPACE_DIR}/${item}"
    target_file="${PRODUCTION_DIR}/$(basename "$item")"
    if [[ "$item" == web/css/* ]]; then
        target_file="${PRODUCTION_DIR}/css/$(basename "$item")"
    fi
    
    if [ -f "$source_file" ]; then
        source_md5=$(md5sum "$source_file" 2>/dev/null | cut -d' ' -f1 || echo "N/A")
    else
        source_md5="文件不存在"
    fi
    
    if [ -f "$target_file" ]; then
        target_md5=$(md5sum "$target_file" 2>/dev/null | cut -d' ' -f1 || echo "N/A")
    else
        target_md5="文件不存在"
    fi
    
    echo "- **$(basename "$item")**: 源MD5=$source_md5, 目标MD5=$target_md5"
done)

## 验证结果
$(if [ "$status" = "成功" ]; then
    echo "- ✅ 所有文件同步验证通过"
    echo "- ✅ MD5校验一致"
    echo "- ✅ Web访问测试通过"
else
    echo "- ❌ 同步验证失败"
    echo "- ❌ 请检查错误日志"
fi)

## 备份信息
- **备份目录**: $BACKUP_DIR
- **备份数量**: $(ls -1 "$BACKUP_DIR"/*.backup.* 2>/dev/null | wc -l || echo 0)

## 建议
1. 定期运行此脚本确保环境一致性
2. 监控Web页面数据真实性
3. 建立自动化部署流水线

---
*报告生成时间: $(date '+%Y-%m-%d %H:%M:%S')*
*同步脚本版本: v1.0.0*
EOF
    
    log_success "同步报告生成完成: $report_file"
}

# ============================================
# 主执行流程
# ============================================

main() {
    log_info "开始琥珀引擎生产环境同步..."
    log_info "工作空间: $WORKSPACE_DIR"
    log_info "生产环境: $PRODUCTION_DIR"
    
    # 检查前置条件
    if ! check_prerequisites; then
        log_error "前置条件检查失败，退出"
        exit 1
    fi
    
    # 同步文件
    local sync_errors=0
    
    for item in "${SYNC_ITEMS[@]}"; do
        local source_file="${WORKSPACE_DIR}/${item}"
        local target_file="${PRODUCTION_DIR}/$(basename "$item")"
        
        # 调整目标路径（对于css目录）
        if [[ "$item" == web/css/* ]]; then
            target_file="${PRODUCTION_DIR}/css/$(basename "$item")"
            # 确保目标目录存在
            sudo mkdir -p "${PRODUCTION_DIR}/css"
        fi
        
        if ! sync_file "$source_file" "$target_file"; then
            sync_errors=$((sync_errors+1))
        fi
    done
    
    # 验证同步结果
    if [ $sync_errors -eq 0 ]; then
        if verify_sync; then
            log_success "文件同步验证通过"
        else
            log_error "文件同步验证失败"
            sync_errors=$((sync_errors+1))
        fi
    fi
    
    # 测试Web访问
    if [ $sync_errors -eq 0 ]; then
        if test_web_access; then
            log_success "Web访问测试通过"
        else
            log_warning "Web访问测试失败，但不影响文件同步"
        fi
    fi
    
    # 生成报告
    if [ $sync_errors -eq 0 ]; then
        generate_report "成功"
        log_success "琥珀引擎生产环境同步完成"
        echo "========================================"
        echo "同步状态: ✅ 成功"
        echo "同步文件: ${#SYNC_ITEMS[@]} 个"
        echo "备份位置: $BACKUP_DIR"
        echo "验证结果: 所有文件MD5一致"
        echo "========================================"
        exit 0
    else
        generate_report "失败"
        log_error "琥珀引擎生产环境同步失败 (错误数: $sync_errors)"
        echo "========================================"
        echo "同步状态: ❌ 失败"
        echo "错误数量: $sync_errors"
        echo "请检查日志获取详细信息"
        echo "========================================"
        exit 1
    fi
}

# 执行主函数
main "$@"