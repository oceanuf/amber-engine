#!/usr/bin/env python3
"""
更新持仓价格脚本 - 紧急修复用
"""

import os
import sys
import json
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 今日收盘价数据
TODAY_PRICES = {
    "000681": 20.37,  # 视觉中国，-3.32%
    "600633": 12.52,  # 浙数文化，-2.79%
    "000938": 27.02   # 紫光股份，+2.12%
}

def update_fund_prices():
    """更新虚拟基金持仓价格"""
    fund_file = "database/arena/virtual_fund.json"
    
    # 加载基金数据
    with open(fund_file, 'r', encoding='utf-8') as f:
        fund_data = json.load(f)
    
    print(f"📊 更新持仓价格 (日期: 2026-04-09)")
    
    total_market_value = 0
    total_unrealized_pnl = 0
    total_cost_basis = 0
    
    # 更新每个持仓
    for position in fund_data["positions"]:
        ticker = position["ticker"]
        if ticker in TODAY_PRICES:
            new_price = TODAY_PRICES[ticker]
            old_price = position.get("current_price", 0)
            
            # 更新价格
            position["current_price"] = new_price
            
            # 计算市值和盈亏
            quantity = position["quantity"]
            average_cost = position["average_cost"]
            
            market_value = quantity * new_price
            cost_basis = quantity * average_cost
            unrealized_pnl = market_value - cost_basis
            unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0
            
            position["market_value"] = round(market_value, 2)
            position["unrealized_pnl"] = round(unrealized_pnl, 2)
            position["unrealized_pnl_pct"] = round(unrealized_pnl_pct, 2)
            
            # 累加统计
            total_market_value += market_value
            total_unrealized_pnl += unrealized_pnl
            total_cost_basis += cost_basis
            
            print(f"   {ticker} {position['name']}:")
            print(f"     价格: {old_price:.2f} → {new_price:.2f} ({((new_price-old_price)/old_price*100):.2f}%)")
            print(f"     市值: ¥{market_value:,.2f}")
            print(f"     盈亏: ¥{unrealized_pnl:,.2f} ({unrealized_pnl_pct:.2f}%)")
    
    # 更新基金总市值
    cash_balance = fund_data["current_capital"]
    total_portfolio_value = total_market_value + cash_balance
    
    # 更新绩效指标
    total_return_pct = (total_unrealized_pnl / total_cost_basis * 100) if total_cost_basis > 0 else 0
    
    fund_data["performance_metrics"]["total_return"] = round(total_return_pct / 100, 4)
    fund_data["performance_metrics"]["max_drawdown"] = max(0, -total_return_pct)  # 简化计算
    
    # 如果有盈利交易
    profitable_positions = [p for p in fund_data["positions"] if p["unrealized_pnl"] > 0]
    total_trades = len(fund_data["positions"])
    profitable_trades = len(profitable_positions)
    win_rate = profitable_trades / total_trades if total_trades > 0 else 0
    
    fund_data["performance_metrics"]["win_rate"] = round(win_rate, 4)
    fund_data["performance_metrics"]["total_trades"] = total_trades
    fund_data["performance_metrics"]["profitable_trades"] = profitable_trades
    
    # 更新最后修改时间
    fund_data["last_updated"] = datetime.now().isoformat()
    
    # 保存更新后的数据
    with open(fund_file, 'w', encoding='utf-8') as f:
        json.dump(fund_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n📈 持仓汇总:")
    print(f"   总持仓成本: ¥{total_cost_basis:,.2f}")
    print(f"   总持仓市值: ¥{total_market_value:,.2f}")
    print(f"   总浮动盈亏: ¥{total_unrealized_pnl:,.2f} ({total_return_pct:.2f}%)")
    print(f"   现金余额: ¥{cash_balance:,.2f}")
    print(f"   组合总值: ¥{total_portfolio_value:,.2f}")
    print(f"   胜率: {win_rate:.1%} ({profitable_trades}/{total_trades})")
    
    # 检查止损触发
    print(f"\n🚨 止损检查:")
    for position in fund_data["positions"]:
        ticker = position["ticker"]
        current_price = position["current_price"]
        stop_loss_price = position.get("stop_loss_price", 0)
        
        if stop_loss_price > 0 and current_price <= stop_loss_price:
            print(f"   ⚠️  {ticker} 触发止损: {current_price:.2f} ≤ {stop_loss_price:.2f}")
        else:
            print(f"   ✅ {ticker} 未触发止损: {current_price:.2f} > {stop_loss_price:.2f}")
    
    return fund_data

if __name__ == "__main__":
    print("=" * 60)
    print("💰 虚拟基金持仓价格更新 (紧急修复)")
    print("=" * 60)
    
    updated_fund = update_fund_prices()
    
    print("\n✅ 持仓价格更新完成")
    print(f"   文件: database/arena/virtual_fund.json")
    print(f"   时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")