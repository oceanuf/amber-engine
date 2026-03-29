#!/usr/bin/env python3
"""调试Tushare API权限和接口问题"""
import os
import sys
import json
import pandas as pd
import tushare as ts
import datetime
import time
import traceback

# 从secrets.json读取token
token = None
try:
    with open("_PRIVATE_DATA/secrets.json", "r", encoding="utf-8") as f:
        secrets = json.load(f)
        token = secrets.get("TUSHARE_TOKEN")
except Exception as e:
    print(f"读取secrets.json失败: {e}")

if not token:
    print("❌ 未找到TUSHARE_TOKEN")
    sys.exit(1)

print(f"Token长度: {len(token)}")
ts.set_token(token)
pro = ts.pro_api()

# 创建logs目录
os.makedirs("logs", exist_ok=True)
log_file = "logs/tushare_debug.log"

def log_debug(msg):
    """记录调试信息"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(msg)

log_debug("=" * 60)
log_debug("开始Tushare API调试")

# 测试1: 检查token基本信息
log_debug("\n1. 测试Token基本信息")
try:
    # 尝试获取自己的token信息（如果有此接口）
    # 如果没有，尝试简单查询
    log_debug("Token似乎有效，尝试简单查询...")
except Exception as e:
    log_debug(f"Token测试异常: {e}")

# 测试2: 尝试不同基金代码格式
test_codes = [
    ("518880.SH", "黄金ETF - SH后缀"),
    ("518880.OF", "黄金ETF - OF后缀"),
    ("510300.SH", "沪深300ETF - SH后缀"),
    ("510300.OF", "沪深300ETF - OF后缀"),
]

end_date = datetime.datetime.now().strftime("%Y%m%d")
start_date = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%Y%m%d")

log_debug(f"\n2. 测试基金数据接口，日期范围: {start_date} 至 {end_date}")

for ts_code, description in test_codes:
    log_debug(f"\n测试 {description} ({ts_code}):")
    
    # 测试股票日线接口 (pro.daily)
    try:
        log_debug(f"  调用 pro.daily({ts_code})...")
        df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        if df is not None and not df.empty:
            log_debug(f"  ✅ pro.daily 成功: {len(df)} 条数据")
            log_debug(f"     最新日期: {df.iloc[0]['trade_date']}, 收盘价: {df.iloc[0]['close']}")
        else:
            log_debug(f"  ⚠️ pro.daily 返回空数据")
    except Exception as e:
        log_debug(f"  ❌ pro.daily 异常: {e}")
    
    time.sleep(1)  # 避免频率限制
    
    # 测试基金日线接口 (pro.fund_daily)
    try:
        log_debug(f"  调用 pro.fund_daily({ts_code})...")
        df_fund = pro.fund_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        if df_fund is not None and not df_fund.empty:
            log_debug(f"  ✅ pro.fund_daily 成功: {len(df_fund)} 条数据")
            log_debug(f"     最新日期: {df_fund.iloc[0]['trade_date']}, 净值: {df_fund.iloc[0]['adj_nav']}")
        else:
            log_debug(f"  ⚠️ pro.fund_daily 返回空数据")
    except Exception as e:
        log_debug(f"  ❌ pro.fund_daily 异常: {e}")
    
    time.sleep(1)

# 测试3: 测试宏观数据接口
log_debug("\n3. 测试宏观数据接口")
macro_tests = [
    ("shibor", "pro.shibor()", lambda: pro.shibor(start_date="20250101")),
    ("cpi", "pro.cpi()", lambda: pro.cpi(start_month="202401")),
]

for macro_name, api_call, func in macro_tests:
    try:
        log_debug(f"  调用 {api_call}...")
        df = func()
        if df is not None and not df.empty:
            log_debug(f"  ✅ {macro_name} 成功: {len(df)} 条数据")
        else:
            log_debug(f"  ⚠️ {macro_name} 返回空数据")
    except Exception as e:
        log_debug(f"  ❌ {macro_name} 异常: {e}")
    
    time.sleep(1)

# 测试4: 测试基础数据接口（股票，验证token有效）
log_debug("\n4. 测试股票数据（验证token有效性）")
try:
    df_stock = pro.daily(ts_code="000001.SZ", start_date=start_date, end_date=end_date)
    if df_stock is not None and not df_stock.empty:
        log_debug(f"  ✅ 股票数据获取成功: {len(df_stock)} 条数据")
        log_debug(f"     平安银行最新收盘价: {df_stock.iloc[0]['close']}")
    else:
        log_debug(f"  ⚠️ 股票数据返回空，可能是权限问题")
except Exception as e:
    log_debug(f"  ❌ 股票数据异常: {e}")

log_debug("\n" + "=" * 60)
log_debug("调试完成，查看详细日志请检查 logs/tushare_debug.log")

print(f"\n调试完成，日志文件: {log_file}")
with open(log_file, "r", encoding="utf-8") as f:
    print(f"最后10行日志:")
    lines = f.readlines()
    for line in lines[-10:]:
        print(line.strip())