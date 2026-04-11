#!/bin/bash
# 琥珀引擎 · 真实性对撞测试脚本
# 依据: AE-Web-Sync-001-V1.0 第2.3节 - 真实性对撞测试
# 功能: 独立执行开发与生产环境数据一致性验证

set -e

echo "⚡ 琥珀引擎真实性对撞测试 (核心加固项)"
echo "========================================"

# 配置
DEV_ROOT="/home/luckyelite/.openclaw/workspace/amber-engine"
PROD_ROOT="/var/www/amber-web"
PROD_URL="https://amber.googlemanager.cn:5656"  # 实际生产URL

# 1. 获取开发环境数据
echo "🔍 1. 读取开发环境数据..."
DEV_DATA_FILE="$DEV_ROOT/database/resonance_signal.json"

if [ ! -f "$DEV_DATA_FILE" ]; then
    echo "❌ 错误: 开发环境数据文件不存在: $DEV_DATA_FILE"
    exit 1
fi

DEV_SCORE=$(python3 -c "
import json
try:
    with open('$DEV_DATA_FILE', 'r') as f:
        data = json.load(f)
    score = data.get('resonance_score', 'N/A')
    # 确保是数值类型
    if isinstance(score, (int, float)):
        print(f'{score:.2f}')
    else:
        print('FORMAT_ERROR')
except json.JSONDecodeError:
    print('JSON_ERROR')
except Exception as e:
    print('READ_ERROR')
")

DEV_SIGNAL=$(python3 -c "
import json
try:
    with open('$DEV_DATA_FILE', 'r') as f:
        data = json.load(f)
    print(data.get('signal_status', 'N/A'))
except:
    print('READ_ERROR')
")

DEV_ACTION=$(python3 -c "
import json
try:
    with open('$DEV_DATA_FILE', 'r') as f:
        data = json.load(f)
    print(data.get('action', 'N/A'))
except:
    print('READ_ERROR')
")

echo "   开发环境状态:"
echo "     - 共振评分: $DEV_SCORE"
echo "     - 信号状态: $DEV_SIGNAL"
echo "     - 操作建议: $DEV_ACTION"

# 2. 获取生产环境数据
echo "🌐 2. 获取生产环境数据..."

# 检查生产环境目录
if [ ! -d "$PROD_ROOT" ]; then
    echo "❌ 错误: 生产环境目录不存在: $PROD_ROOT"
    echo "   请先运行部署脚本: ./scripts/sync/deploy_to_production.sh"
    exit 1
fi

# 尝试通过HTTP获取
PROD_SCORE="HTTP_ERROR"
PROD_SIGNAL="HTTP_ERROR"
PROD_ACTION="HTTP_ERROR"

if command -v curl &> /dev/null; then
    echo "   尝试HTTP访问: $PROD_URL"
    
    # 尝试获取API数据
    API_RESPONSE=$(curl -s -m 10 "$PROD_URL/api.php?action=get_full_data" 2>/dev/null || echo "{}")
    
    if [ "$API_RESPONSE" != "{}" ]; then
        PROD_SCORE=$(echo "$API_RESPONSE" | python3 -c "
import json, sys
try:
    data = json.loads(sys.stdin.read())
    score = data.get('resonance_score', 'N/A')
    if isinstance(score, (int, float)):
        print(f'{score:.2f}')
    else:
        print('N/A')
except:
    print('PARSE_ERROR')
")
        
        PROD_SIGNAL=$(echo "$API_RESPONSE" | python3 -c "
import json, sys
try:
    data = json.loads(sys.stdin.read())
    print(data.get('signal_status', 'N/A'))
except:
    print('PARSE_ERROR')
")
        
        PROD_ACTION=$(echo "$API_RESPONSE" | python3 -c "
import json, sys
try:
    data = json.loads(sys.stdin.read())
    print(data.get('action', 'N/A'))
except:
    print('PARSE_ERROR')
")
    else
        echo "   ⚠️  HTTP API未响应，尝试直接读取文件"
    fi
else
    echo "   ⚠️  curl未安装，跳过HTTP测试"
fi

# 如果HTTP失败，尝试直接读取生产环境文件
if [ "$PROD_SCORE" = "HTTP_ERROR" ] || [ "$PROD_SCORE" = "PARSE_ERROR" ]; then
    PROD_DATA_FILE="$PROD_ROOT/database/resonance_signal.json"
    
    if [ -L "$PROD_DATA_FILE" ]; then
        echo "   检测到软链接，读取源文件..."
        REAL_FILE=$(readlink -f "$PROD_DATA_FILE")
        PROD_DATA_FILE="$REAL_FILE"
    fi
    
    if [ -f "$PROD_DATA_FILE" ]; then
        PROD_SCORE=$(python3 -c "
import json
try:
    with open('$PROD_DATA_FILE', 'r') as f:
        data = json.load(f)
    score = data.get('resonance_score', 'N/A')
    if isinstance(score, (int, float)):
        print(f'{score:.2f}')
    else:
        print('FORMAT_ERROR')
except:
    print('READ_ERROR')
")
        
        PROD_SIGNAL=$(python3 -c "
import json
try:
    with open('$PROD_DATA_FILE', 'r') as f:
        data = json.load(f)
    print(data.get('signal_status', 'N/A'))
except:
    print('READ_ERROR')
")
        
        PROD_ACTION=$(python3 -c "
import json
try:
    with open('$PROD_DATA_FILE', 'r') as f:
        data = json.load(f)
    print(data.get('action', 'N/A'))
except:
    print('READ_ERROR')
")
    else
        echo "❌ 错误: 生产环境数据文件不存在: $PROD_DATA_FILE"
        PROD_SCORE="FILE_NOT_FOUND"
        PROD_SIGNAL="FILE_NOT_FOUND"
        PROD_ACTION="FILE_NOT_FOUND"
    fi
fi

echo "   生产环境状态:"
echo "     - 共振评分: $PROD_SCORE"
echo "     - 信号状态: $PROD_SIGNAL"
echo "     - 操作建议: $PROD_ACTION"

# 3. 对撞测试
echo "⚡ 3. 执行对撞测试..."

ERROR_COUNT=0

# 检查评分一致性
if [ "$DEV_SCORE" = "$PROD_SCORE" ]; then
    echo "   ✅ 评分一致: $DEV_SCORE"
else
    echo "   ❌ 评分不一致: 开发($DEV_SCORE) ≠ 生产($PROD_SCORE)"
    ERROR_COUNT=$((ERROR_COUNT + 1))
fi

# 检查信号状态一致性
if [ "$DEV_SIGNAL" = "$PROD_SIGNAL" ]; then
    echo "   ✅ 信号状态一致: $DEV_SIGNAL"
else
    echo "   ❌ 信号状态不一致: 开发($DEV_SIGNAL) ≠ 生产($PROD_SIGNAL)"
    ERROR_COUNT=$((ERROR_COUNT + 1))
fi

# 检查操作建议一致性
if [ "$DEV_ACTION" = "$PROD_ACTION" ]; then
    echo "   ✅ 操作建议一致: $DEV_ACTION"
else
    echo "   ❌ 操作建议不一致: 开发($DEV_ACTION) ≠ 生产($PROD_ACTION)"
    ERROR_COUNT=$((ERROR_COUNT + 1))
fi

# 4. 结果判定
echo "========================================"
if [ $ERROR_COUNT -eq 0 ]; then
    echo "🎉 真实性对撞测试: ✅ 完全通过"
    echo "   开发与生产环境数据完全一致"
    exit 0
elif [ $ERROR_COUNT -eq 1 ] && [ "$PROD_SCORE" = "FILE_NOT_FOUND" ]; then
    echo "⚠️  对撞测试: ⚠️  部分通过 (生产环境文件未找到)"
    echo "   建议: 运行部署脚本同步数据"
    exit 2
else
    echo "❌ 真实性对撞测试: ❌ 失败 ($ERROR_COUNT 项不一致)"
    echo "   [依据法典第2.3节] 触发FATAL ERROR"
    echo "   建议:"
    echo "   1. 检查生产环境部署状态"
    echo "   2. 重新运行部署脚本: ./scripts/sync/deploy_to_production.sh"
    echo "   3. 检查数据源一致性"
    exit 1
fi