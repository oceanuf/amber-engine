#!/bin/bash
# Cron配置测试脚本
# [2614-027] 架构师指令 - 自动化调度验证

echo "=== Cron配置验证测试 ==="
echo "测试时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 1. 检查Cron服务状态
echo "1. Cron服务状态:"
if systemctl is-active cron >/dev/null 2>&1; then
    echo "   ✅ Cron服务运行正常"
else
    echo "   ❌ Cron服务未运行"
fi
echo ""

# 2. 检查当前用户的Cron配置
echo "2. 当前用户Cron配置:"
crontab -l | grep -E "(琥珀引擎|orchestrator|tushare_adapter)" | while read line; do
    echo "   📋 $line"
done
echo ""

# 3. 测试Python环境
echo "3. Python环境测试:"
PYTHON_PATH=$(which python3)
echo "   Python路径: $PYTHON_PATH"
echo "   Python版本: $(python3 --version 2>&1)"
echo ""

# 4. 测试orchestrator.py可执行性
echo "4. Orchestrator可执行性测试:"
if [ -f "scripts/orchestrator.py" ]; then
    echo "   ✅ orchestrator.py文件存在"
    # 测试导入
    if python3 -c "import sys; sys.path.insert(0, '.'); import scripts.orchestrator" 2>/dev/null; then
        echo "   ✅ orchestrator.py可正常导入"
    else
        echo "   ⚠️  orchestrator.py导入测试失败"
        python3 -c "import sys; sys.path.insert(0, '.'); import scripts.orchestrator" 2>&1 | head -5
    fi
else
    echo "   ❌ orchestrator.py文件不存在"
fi
echo ""

# 5. 测试tushare_adapter.py可执行性
echo "5. Tushare适配器可执行性测试:"
if [ -f "scripts/ingest/tushare_adapter.py" ]; then
    echo "   ✅ tushare_adapter.py文件存在"
    # 测试帮助信息
    if python3 scripts/ingest/tushare_adapter.py --help 2>&1 | grep -q "usage:"; then
        echo "   ✅ tushare_adapter.py可正常执行"
    else
        echo "   ⚠️  tushare_adapter.py执行测试失败"
        python3 scripts/ingest/tushare_adapter.py --help 2>&1 | head -3
    fi
else
    echo "   ❌ tushare_adapter.py文件不存在"
fi
echo ""

# 6. 测试日志目录
echo "6. 日志目录测试:"
LOG_DIR="logs"
if [ -d "$LOG_DIR" ]; then
    echo "   ✅ 日志目录存在: $LOG_DIR"
    # 测试写入权限
    TEST_LOG="$LOG_DIR/cron_test_$(date +%Y%m%d_%H%M%S).log"
    echo "Cron测试日志 - $(date)" > "$TEST_LOG" 2>&1
    if [ $? -eq 0 ]; then
        echo "   ✅ 日志目录可写入"
        rm "$TEST_LOG"
    else
        echo "   ❌ 日志目录不可写入"
    fi
else
    echo "   ⚠️  日志目录不存在，创建中..."
    mkdir -p "$LOG_DIR"
    if [ $? -eq 0 ]; then
        echo "   ✅ 日志目录创建成功"
    else
        echo "   ❌ 日志目录创建失败"
    fi
fi
echo ""

# 7. 模拟Cron执行测试（快速验证）
echo "7. 模拟Cron执行测试（快速验证）:"
echo "   测试命令: cd $(pwd) && timeout 5 /usr/bin/python3 scripts/orchestrator.py"
TIMEOUT_OUTPUT=$(timeout 5 python3 scripts/orchestrator.py 2>&1)
if [ $? -eq 124 ]; then
    echo "   ✅ Orchestrator启动成功（5秒超时测试通过）"
    echo "   输出摘要:"
    echo "$TIMEOUT_OUTPUT" | grep -E "\[orchestrator:(INFO|DEBUG)\]" | head -3 | sed 's/^/      /'
else
    echo "   ⚠️  Orchestrator执行结果:"
    echo "$TIMEOUT_OUTPUT" | head -5 | sed 's/^/      /'
fi
echo ""

echo "=== 测试总结 ==="
echo "Cron配置验证完成。"
echo "下次执行时间:"
echo "  - 增量同步: 工作日 18:00"
echo "  - 全量同步: 周日 18:30"
echo ""
echo "验证完成时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "测试工程师: Cheese 🧀"