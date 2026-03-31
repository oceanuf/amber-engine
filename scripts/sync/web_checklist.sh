#!/bin/bash
# 琥珀引擎 · Web更新自查清单脚本
# 依据: AE-Web-Sync-001-V1.0 第四部分 - Web更新自查清单
# 功能: 自动化检查生产环境配置状态

set -e

echo "📋 琥珀引擎Web更新自查清单 (依据法典 AE-Web-Sync-001-V1.0)"
echo "=========================================================="

# 配置
DEV_ROOT="/home/luckyelite/.openclaw/workspace/amber-engine"
PROD_ROOT="/var/www/amber-web"
NGINX_CONFIG="/etc/nginx/sites-available/amber.googlemanager.cn"

TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

# 检查函数
check_item() {
    local name="$1"
    local check_cmd="$2"
    local success_msg="$3"
    local fail_msg="$4"
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    if eval "$check_cmd" > /dev/null 2>&1; then
        echo "✅ [$name] $success_msg"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        echo "❌ [$name] $fail_msg"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

check_warning() {
    local name="$1"
    local check_cmd="$2"
    local warning_msg="$3"
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    if eval "$check_cmd" > /dev/null 2>&1; then
        echo "⚠️  [$name] $warning_msg"
        WARNING_CHECKS=$((WARNING_CHECKS + 1))
        return 2
    else
        echo "✅ [$name] 正常"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    fi
}

echo "🔍 开始检查..."

# 1. 隔离性检查
echo ""
echo "🛡️  1. 隔离性检查"
check_item "隔离性" \
    "! grep -q '$DEV_ROOT/output' '$NGINX_CONFIG'" \
    "Nginx未指向开发目录" \
    "Nginx仍指向开发目录: $DEV_ROOT/output (违反隔离原则)"

check_warning "配置污染" \
    "find '$PROD_ROOT' -name '*config_dev*' -o -name '*.env' | grep -q ." \
    "发现开发配置文件在生产环境"

# 2. 数据源检查
echo ""
echo "📊 2. 数据源检查"
check_item "数据软链接" \
    "[ -L '$PROD_ROOT/database/resonance_signal.json' ]" \
    "数据文件为软链接" \
    "数据文件不是软链接或不存在"

check_item "数据可读性" \
    "[ -r '$PROD_ROOT/database/resonance_signal.json' ]" \
    "数据文件可读" \
    "数据文件不可读"

# 3. 指纹检查
echo ""
echo "🏷️  3. 指纹检查"
check_item "指纹文件" \
    "[ -f '$PROD_ROOT/version.txt' ]" \
    "版本指纹文件存在" \
    "版本指纹文件不存在"

if [ -f "$PROD_ROOT/version.txt" ]; then
    DEV_FINGERPRINT=$(cat "$DEV_ROOT/.sync_fingerprint" 2>/dev/null || echo "UNKNOWN")
    PROD_FINGERPRINT=$(grep -o "Build: [^ ]*" "$PROD_ROOT/version.txt" | cut -d' ' -f2 || echo "UNKNOWN")
    
    if [ "$DEV_FINGERPRINT" = "$PROD_FINGERPRINT" ]; then
        echo "✅ [指纹一致性] 开发($DEV_FINGERPRINT) = 生产($PROD_FINGERPRINT)"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo "❌ [指纹一致性] 开发($DEV_FINGERPRINT) ≠ 生产($PROD_FINGERPRINT)"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
fi

# 4. 对撞测试
echo ""
echo "⚡ 4. 对撞测试"
check_item "对撞脚本" \
    "[ -x '$DEV_ROOT/scripts/sync/truth_collision_test.sh' ]" \
    "对撞测试脚本可用" \
    "对撞测试脚本不可用"

# 5. 权限锁定
echo ""
echo "🔒 5. 权限锁定"
check_warning "文件权限" \
    "find '$PROD_ROOT' -type f ! -perm 644 | grep -q ." \
    "发现非644权限的文件"

check_warning "目录权限" \
    "find '$PROD_ROOT' -type d ! -perm 755 | grep -q ." \
    "发现非755权限的目录"

# 6. Nginx配置检查
echo ""
echo "🌐 6. Nginx配置检查"
check_item "Nginx配置存在" \
    "[ -f '$NGINX_CONFIG' ]" \
    "Nginx配置文件存在" \
    "Nginx配置文件不存在"

if [ -f "$NGINX_CONFIG" ]; then
    CURRENT_ROOT=$(grep -o "root [^;]*" "$NGINX_CONFIG" | head -1 | cut -d' ' -f2)
    
    if [ "$CURRENT_ROOT" = "$PROD_ROOT" ]; then
        echo "✅ [根目录配置] 正确指向生产环境: $PROD_ROOT"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo "❌ [根目录配置] 错误指向: $CURRENT_ROOT (应为: $PROD_ROOT)"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
fi

# 总结
echo ""
echo "=========================================================="
echo "📊 检查总结:"
echo "   总检查项: $TOTAL_CHECKS"
echo "   ✅ 通过: $PASSED_CHECKS"
echo "   ❌ 失败: $FAILED_CHECKS"
echo "   ⚠️  警告: $WARNING_CHECKS"
echo ""

if [ $FAILED_CHECKS -eq 0 ]; then
    if [ $WARNING_CHECKS -eq 0 ]; then
        echo "🎉 所有检查项通过！生产环境配置完美"
    else
        echo "✅ 核心检查项通过，但有 $WARNING_CHECKS 项警告"
        echo "   建议检查警告项，但不会影响系统运行"
    fi
else
    echo "❌ 发现 $FAILED_CHECKS 项关键问题需要修复"
    echo "   请根据上述检查结果进行修复"
    
    # 提供修复建议
    echo ""
    echo "🔧 修复建议:"
    if grep -q "$DEV_ROOT/output" "$NGINX_CONFIG" 2>/dev/null; then
        echo "   1. 更新Nginx配置指向生产环境:"
        echo "      sudo sed -i 's|$DEV_ROOT/output|$PROD_ROOT|g' $NGINX_CONFIG"
        echo "      sudo nginx -t && sudo systemctl reload nginx"
    fi
    
    if [ ! -f "$PROD_ROOT/version.txt" ]; then
        echo "   2. 运行部署脚本同步文件:"
        echo "      $DEV_ROOT/scripts/sync/deploy_to_production.sh"
    fi
fi

echo ""
echo "📝 依据法典 AE-Web-Sync-001-V1.0 完成检查"
exit $FAILED_CHECKS