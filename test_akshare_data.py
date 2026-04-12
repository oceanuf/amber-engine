#!/usr/bin/env python3
"""
测试Akshare数据获取
"""

import akshare as ak
import pandas as pd

print("测试Akshare数据获取...")
print("=" * 60)

# 测试股票数据
test_codes = [
    ("000858", "五粮液", False),
    ("600519", "贵州茅台", False),
    ("510300", "沪深300ETF", True),
    ("159919", "沪深300ETF(深)", True)
]

for code, name, is_etf in test_codes:
    print(f"\n测试 {name}({code}):")
    
    try:
        if is_etf:
            print(f"  调用 fund_etf_hist_sina('{code}')...")
            df = ak.fund_etf_hist_sina(symbol=code)
        else:
            print(f"  调用 stock_zh_a_hist('{code}')...")
            df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
        
        if df is not None:
            print(f"  成功! 数据形状: {df.shape}")
            print(f"  列名: {df.columns.tolist()}")
            
            if not df.empty:
                print(f"  前3行数据:")
                print(df.head(3))
                
                # 检查日期和价格列
                date_cols = [col for col in df.columns if "日期" in col or "date" in col.lower()]
                price_cols = [col for col in df.columns if "收盘" in col or "close" in col.lower()]
                
                print(f"  日期列: {date_cols}")
                print(f"  价格列: {price_cols}")
                
                if date_cols and price_cols:
                    print(f"  ✅ 数据格式正确")
                else:
                    print(f"  ⚠️  数据列名不标准")
            else:
                print(f"  ⚠️  数据为空")
        else:
            print(f"  ❌ 返回None")
            
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)