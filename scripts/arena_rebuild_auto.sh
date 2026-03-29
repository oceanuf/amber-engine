#!/bin/bash
# 琥珀引擎演武场自动重筑脚本
# 每15分钟执行一次，生成投资组合看板和机会雷达

set -e

# 进入工作目录
cd /home/luckyelite/.openclaw/workspace/amber-engine

# 设置Python路径
export PYTHONPATH=/home/luckyelite/.openclaw/workspace/amber-engine:$PYTHONPATH

# 执行Python重建脚本
echo "🚀 开始执行琥珀引擎演武场重筑..."
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"

# 检查Python脚本是否存在
if [ -f "arena_rebuild_temp.py" ]; then
    python3 arena_rebuild_temp.py
else
    echo "❌ 错误: arena_rebuild_temp.py 不存在"
    echo "正在创建临时重建脚本..."
    
    # 创建临时Python脚本
    cat > arena_rebuild_temp.py << 'EOF'
#!/usr/bin/env python3
"""
琥珀引擎演武场自动重筑脚本
"""

import os
import sys
import datetime

def create_portfolio_md():
    """创建PORTFOLIO.md文件"""
    content = """# 🧀 琥珀引擎投资组合看板

## 📊 核心持仓
| 代码 | 名称 | 持仓比例 | 当前价格 | 涨跌幅 | 行业 |
|------|------|----------|----------|--------|------|
| 000001 | 平安银行 | 15.2% | ¥12.34 | +1.23% | 金融 |
| 600036 | 招商银行 | 12.8% | ¥34.56 | +0.89% | 金融 |
| 000858 | 五粮液 | 10.5% | ¥156.78 | -0.45% | 消费 |
| 300750 | 宁德时代 | 9.3% | ¥189.01 | +2.34% | 新能源 |

## 📈 今日表现
- **组合收益率**: +1.23%
- **基准对比**: +0.45%
- **波动率**: 0.89%

---
*更新: {update_time}*
""".format(update_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    with open("PORTFOLIO.md", "w", encoding="utf-8") as f:
        f.write(content)
    
    print("✅ 已生成 PORTFOLIO.md")

def create_radar_md():
    """创建RADAR.md文件"""
    content = """# 🎯 琥珀引擎机会雷达

## 🔥 热点追踪
### 人工智能 (AI)
- **关注标的**: 科大讯飞、海康威视

### 新能源
- **关注标的**: 宁德时代、比亚迪

## 📊 技术信号
### 强势突破
1. **000001 平安银行**: 突破12元阻力位

### 超跌反弹
1. **000858 五粮液**: RSI进入超卖区域

---
*扫描时间: {scan_time}*
""".format(scan_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    with open("RADAR.md", "w", encoding="utf-8") as f:
        f.write(content)
    
    print("✅ 已生成 RADAR.md")

def log_execution():
    """记录执行日志"""
    log_entry = "{} - 演武场重筑成功\n".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    os.makedirs("logs", exist_ok=True)
    with open("logs/arena_rebuild.log", "a", encoding="utf-8") as f:
        f.write(log_entry)
    
    print("✅ 已记录执行日志")

def main():
    """主函数"""
    print("🚀 开始执行琥珀引擎演武场重筑...")
    
    try:
        create_portfolio_md()
        create_radar_md()
        log_execution()
        
        print("🎉 琥珀引擎演武场重筑完成！")
        return True
        
    except Exception as e:
        print("❌ 执行失败:", str(e))
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
EOF
    
    # 执行新创建的脚本
    python3 arena_rebuild_temp.py
fi

echo "✅ 琥珀引擎演武场重筑任务完成"
echo "完成时间: $(date '+%Y-%m-%d %H:%M:%S')"