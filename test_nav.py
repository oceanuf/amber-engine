#!/usr/bin/env python3
"""
测试NAV记录器
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scripts.arena.nav_recorder import NAVRecorder

# 测试类实例化
recorder = NAVRecorder()
print("✅ NAVRecorder实例化成功")

# 测试加载virtual_fund
try:
    fund_data = recorder._load_virtual_fund()
    print(f"✅ 加载virtual_fund.json成功，持仓数量: {len(fund_data.get('positions', []))}")
except Exception as e:
    print(f"❌ 加载virtual_fund.json失败: {e}")
    sys.exit(1)

# 测试价格获取（使用回退逻辑）
test_ticker = "000681"
price, source = recorder._get_current_price(test_ticker)
print(f"✅ 价格获取测试: {test_ticker} = {price} (来源: {source})")

# 测试NAV计算
nav_data = recorder.calculate_nav()
print(f"✅ NAV计算成功:")
print(f"   日期: {nav_data['date']}")
print(f"   总资产: {nav_data['total_assets']}")
print(f"   现金: {nav_data['cash']}")
print(f"   持仓市值: {nav_data['positions_market_value']}")
print(f"   持仓数量: {nav_data['position_count']}")

# 测试CSV记录
success = recorder.record_nav(nav_data)
if success:
    print(f"✅ NAV记录成功，文件位置: {recorder.nav_history_path}")
else:
    print("❌ NAV记录失败")
    sys.exit(1)

print("\n🎉 所有测试通过！")