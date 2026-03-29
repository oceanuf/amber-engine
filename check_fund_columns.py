#!/usr/bin/env python3
"""检查Tushare fund_daily接口返回的列名"""
import os
import json
import pandas as pd
import tushare as ts
import datetime

# 读取token
with open("_PRIVATE_DATA/secrets.json", "r", encoding="utf-8") as f:
    secrets = json.load(f)
    token = secrets.get("TUSHARE_TOKEN")

ts.set_token(token)
pro = ts.pro_api()

# 获取最近10天数据
end_date = datetime.datetime.now().strftime("%Y%m%d")
start_date = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%Y%m%d")

print(f"获取基金日线数据，日期范围: {start_date} 至 {end_date}")
df = pro.fund_daily(ts_code="518880.SH", start_date=start_date, end_date=end_date)

if df is not None and not df.empty:
    print(f"数据形状: {df.shape}")
    print("列名:")
    for col in df.columns:
        print(f"  '{col}'")
    
    print("\n第一行数据:")
    print(df.iloc[0])
    
    # 检查是否存在关键字段
    key_fields = ['nav', 'adj_nav', 'accum_nav', 'nav_return', 'daily_return', 'vol', 'amount']
    for field in key_fields:
        exists = field in df.columns
        print(f"{field}: {'存在' if exists else '不存在'}")
else:
    print("未获取到数据")