#!/usr/bin/env python3
"""
测试增强版Macro-Gold策略
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, project_root)

# 现在可以导入模块了
try:
    from scripts.synthesizer.strategies.macro_gold import MacroGoldStrategy
except ImportError as e:
    print(f"导入失败: {e}")
    print(f"Python路径: {sys.path}")
    sys.exit(1)

def test_macro_gold_strategy():
    """测试Macro-Gold策略"""
    print("=== 测试增强版Macro-Gold策略 ===")
    
    # 创建策略实例
    strategy = MacroGoldStrategy()
    
    print(f"策略名称: {strategy.name}")
    print(f"策略描述: {strategy.description}")
    print(f"所需历史天数: {strategy.get_required_history_days()}")
    print()
    
    # 测试获取利率数据
    print("1. 测试利率数据获取:")
    treasury_data = strategy.get_treasury_yield_data()
    print(f"   数据来源: {treasury_data.get('data_source', 'unknown')}")
    print(f"   数据质量: {treasury_data.get('data_quality', 'unknown')}")
    print(f"   名义利率: {treasury_data.get('nominal_yield', 'N/A')}%")
    print(f"   通胀率: {treasury_data.get('inflation_rate', 'N/A')}%")
    print(f"   实际利率: {treasury_data.get('real_yield', 'N/A')}%")
    print(f"   利率趋势: {treasury_data.get('yield_trend', 'unknown')}")
    print(f"   计算说明: {treasury_data.get('notes', 'N/A')}")
    print()
    
    # 测试分析功能（简化）
    print("2. 测试策略分析:")
    
    # 创建模拟历史数据
    history_data = {
        "ticker": "518880",
        "name": "黄金ETF",
        "history": [
            {"date": "2026-03-30", "close": 9.656},
            {"date": "2026-03-29", "close": 9.494},
            {"date": "2026-03-28", "close": 9.520},
            {"date": "2026-03-27", "close": 9.480},
            {"date": "2026-03-26", "close": 9.510},
        ]
    }
    
    try:
        result = strategy.analyze(
            ticker="518880",
            history_data=history_data,
            analysis_data=None,
            global_params=None
        )
        
        print(f"   命中: {result['hit']}")
        print(f"   得分: {result['score']:.2f}")
        print(f"   置信度: {result['confidence']:.2f}")
        print(f"   信号类型: {result['metadata'].get('signal_type', 'unknown')}")
        print(f"   数据来源: {result['metadata'].get('data_source', 'unknown')}")
        print(f"   数据质量: {result['metadata'].get('data_quality', 'unknown')}")
        print()
        
        print("   信号列表:")
        for signal in result['signals']:
            print(f"     - {signal}")
        
        print()
        print("   元数据:")
        for key, value in result['metadata'].items():
            if key not in ['signal_type', 'data_source', 'data_quality']:
                print(f"     - {key}: {value}")
                
    except Exception as e:
        print(f"   分析失败: {e}")
    
    print()
    print("=== 测试完成 ===")

if __name__ == "__main__":
    test_macro_gold_strategy()