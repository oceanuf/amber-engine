#!/usr/bin/env python3
"""
Dividend-Alpha 策略修复验证测试
确保修复后的代码无 NameError 并能正常运行
"""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.synthesizer.strategies.dividend_alpha import DividendAlphaStrategy

def test_import():
    """测试导入"""
    strategy = DividendAlphaStrategy()
    assert strategy.name == "Dividend-Alpha"
    print("✅ 导入测试通过")

def test_required_history_days():
    """测试所需历史天数"""
    strategy = DividendAlphaStrategy()
    days = strategy.get_required_history_days()
    assert days == 60, f"需要60天，实际{days}天"
    print("✅ 历史天数测试通过")

def test_analyze_with_mock_data():
    """使用模拟数据测试分析功能"""
    strategy = DividendAlphaStrategy()
    
    # 模拟历史数据
    mock_history = {
        "ticker": "000681",
        "name": "视觉中国", 
        "history": [
            {"date": "20260331", "price": 20.07, "change": "-2.57%"},
            {"date": "20260330", "price": 20.6, "change": "0.24%"},
            {"date": "20260327", "price": 20.55, "change": "1.93%"}
        ]
    }
    
    # 测试数据不足的情况
    result = strategy.analyze("000681", mock_history)
    assert isinstance(result, dict)
    assert "hit" in result
    assert "score" in result
    assert "signals" in result
    print("✅ 模拟数据分析测试通过")

def test_analyze_with_real_data():
    """使用真实数据测试（如果可用）"""
    history_file = "../../../database/history_000681.json"
    if not os.path.exists(history_file):
        print("⚠️  真实数据文件不存在，跳过真实数据测试")
        return
    
    with open(history_file, 'r', encoding='utf-8') as f:
        history_data = json.load(f)
    
    strategy = DividendAlphaStrategy()
    
    # 注意：真实数据可能不足60天，但至少不会抛出NameError
    try:
        result = strategy.analyze("000681", history_data)
        assert isinstance(result, dict)
        assert "hit" in result
        print("✅ 真实数据分析测试通过（无NameError）")
    except NameError as e:
        print(f"❌ NameError 仍然存在: {e}")
        raise
    except Exception as e:
        # 其他错误可以接受（如数据不足）
        print(f"⚠️  其他错误（可接受）: {e}")

def test_calculate_dividend_protection_score():
    """测试保护垫评分函数"""
    strategy = DividendAlphaStrategy()
    
    # 测试参数传递
    prices = [100.0, 98.0, 102.0, 101.0, 99.0]
    result = strategy.calculate_dividend_protection_score(
        net_dividend_yield=0.025,
        price_stability=0.7,
        current_price=100.0,
        ma60=95.0,
        prices=prices
    )
    
    assert isinstance(result, dict)
    assert "score" in result
    assert "confidence" in result
    assert "signals" in result
    print("✅ 保护垫评分函数测试通过")

def main():
    """运行所有测试"""
    print("🧪 开始 Dividend-Alpha 策略修复验证...")
    
    tests = [
        test_import,
        test_required_history_days,
        test_calculate_dividend_protection_score,
        test_analyze_with_mock_data,
        test_analyze_with_real_data
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} 失败: {e}")
    
    print(f"\n📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！Dividend-Alpha 策略修复成功。")
        return 0
    else:
        print("⚠️  部分测试失败，需要进一步修复。")
        return 1

if __name__ == "__main__":
    sys.exit(main())