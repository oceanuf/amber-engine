#!/usr/bin/env python3
"""
简单测试TechnicalFallback模块
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("🧪 简单测试TechnicalFallback")

# 创建测试数据
test_fund_data = {
    "fund_id": "TEST_FUND",
    "current_capital": 1000000,
    "positions": [
        {
            "ticker": "000681",
            "name": "视觉中国",
            "quantity": 4747,
            "current_price": 20.37,
            "average_cost": 21.07,
            "unrealized_pnl_pct": -0.0331,
            "entry_date": "2026-04-08",
        }
    ]
}

# 尝试导入TechnicalFallback
try:
    from scripts.arena.technical_fallback import TechnicalFallback
    print("✅ TechnicalFallback导入成功")
    
    # 测试基本功能
    fallback = TechnicalFallback(test_fund_data)
    
    # 分析持仓
    result = fallback.analyze_position(test_fund_data["positions"][0], "STABLE")
    
    print(f"📊 测试结果:")
    print(f"   标的: {result['ticker']}")
    print(f"   决策: {result['decision']}")
    print(f"   理由: {result['reason']}")
    print(f"   信心度: {result['confidence']}")
    
    # 测试整体分析
    all_result = fallback.analyze_all_positions("STABLE")
    print(f"\n📋 整体分析:")
    print(f"   持仓数: {len(all_result['recommendations'])}")
    print(f"   风险评估: {all_result['overall_risk']['level']}")
    
    print("✅ 测试通过")
    
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()