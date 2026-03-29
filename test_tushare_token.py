#!/usr/bin/env python3
"""测试Tushare Token有效性"""
import os
import sys
import tushare as ts

# 从环境变量或secrets文件读取token
token = os.environ.get("TUSHARE_TOKEN")
if not token:
    # 尝试从secrets.json读取
    import json
    try:
        with open("_PRIVATE_DATA/secrets.json", "r", encoding="utf-8") as f:
            secrets = json.load(f)
            token = secrets.get("TUSHARE_TOKEN")
    except:
        pass

print(f"Token: {'已设置' if token else '未设置'}")
if token:
    print(f"Token长度: {len(token)}")
    # 测试token
    try:
        ts.set_token(token)
        pro = ts.pro_api()
        print("✅ Tushare Pro API 初始化成功")
        
        # 测试简单查询
        print("测试查询黄金ETF (518880.SH) 最近5天数据...")
        df = pro.daily(ts_code="518880.SH", start_date="20260320", end_date="20260329")
        if df is not None and not df.empty:
            print(f"✅ 成功获取 {len(df)} 条真实数据")
            print(df[['trade_date', 'close', 'vol']].head())
        else:
            print("⚠️ 获取真实数据失败，可能Token无效或网络问题")
            
    except Exception as e:
        print(f"❌ Tushare API错误: {e}")
        import traceback
        traceback.print_exc()
else:
    print("❌ 未找到TUSHARE_TOKEN")