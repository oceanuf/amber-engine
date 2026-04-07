#!/usr/bin/env python3
"""
使用Tushare获取股票实时价格
"""

import os
import sys
import json
import tushare as ts
import pandas as pd
from datetime import datetime

# 加载密钥
secrets_path = "_PRIVATE_DATA/secrets.json"
if os.path.exists(secrets_path):
    with open(secrets_path, 'r', encoding='utf-8') as f:
        secrets = json.load(f)
    token = secrets.get("TUSHARE_TOKEN")
else:
    token = os.environ.get("TUSHARE_TOKEN")

if not token:
    print("❌ 未找到Tushare令牌")
    sys.exit(1)

# 设置token
ts.set_token(token)
pro = ts.pro_api()

# 数据基础设施相关标的
stocks = [
    # 服务器/云计算
    ("000977.SZ", "浪潮信息"),
    ("603019.SH", "中科曙光"),
    ("000938.SZ", "紫光股份"),
    
    # 网络安全
    ("002439.SZ", "启明星辰"),
    ("300369.SZ", "绿盟科技"),
    ("300454.SZ", "深信服"),
    
    # 数据中心
    ("300383.SZ", "光环新网"),
    ("603881.SH", "数据港"),
    
    # 数据交易
    ("600633.SH", "浙数文化"),
    
    # 算力基础设施
    ("688256.SH", "寒武纪"),
    ("688041.SH", "海光信息"),
]

def get_realtime_prices():
    """获取实时价格"""
    print("📊 数据基础设施板块个股实时行情")
    print("=" * 80)
    print(f"查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    results = []
    
    for code, name in stocks:
        try:
            # 使用日线数据获取最新价格（实时行情需要权限）
            df = pro.daily(ts_code=code, start_date='20260401', end_date='20260407')
            if not df.empty:
                latest = df.iloc[0]
                close_price = latest['close']
                pct_chg = latest['pct_chg']  # 涨跌幅
                
                # 获取基础信息
                try:
                    df_basic = pro.stock_basic(ts_code=code)
                    if not df_basic.empty:
                        industry = df_basic.iloc[0]['industry']
                        market_cap = df_basic.iloc[0]['total_mv'] / 10000  # 转换为亿元
                    else:
                        industry = "N/A"
                        market_cap = "N/A"
                except:
                    industry = "N/A"
                    market_cap = "N/A"
                
                results.append({
                    'code': code,
                    'name': name,
                    'price': close_price,
                    'change_pct': pct_chg,
                    'industry': industry,
                    'market_cap': market_cap
                })
                
                print(f"{code} {name:10} 收盘价: {close_price:>7.2f} 涨跌幅: {pct_chg:>6.2f}% 行业: {industry:10} 市值: {market_cap if isinstance(market_cap, str) else f'{market_cap:,.0f}亿'}")
            else:
                print(f"⚠️  {code} {name} - 无数据")
        except Exception as e:
            print(f"❌ {code} {name} - 查询失败: {str(e)[:50]}")
    
    return results

def get_etf_info():
    """获取ETF信息"""
    print("\n📈 数据基础设施相关ETF")
    print("-" * 80)
    
    etfs = [
        ("515050.SH", "华夏中证5G通信主题ETF"),
        ("515070.SH", "易方达中证人工智能ETF"),
        ("515250.SH", "富国中证信息安全ETF"),
        ("515400.SH", "富国中证大数据产业ETF"),
        ("159995.SZ", "华夏国证半导体芯片ETF"),
        ("512480.SH", "国联安中证全指半导体ETF"),
    ]
    
    for code, name in etfs:
        try:
            df = pro.fund_daily(ts_code=code, start_date='20260401', end_date='20260407')
            if not df.empty:
                latest = df.iloc[0]
                nav = latest['nav']  # 单位净值
                nav_date = latest['nav_date']  # 净值日期
                print(f"{code} {name:20} 单位净值: {nav:>7.3f} 净值日期: {nav_date}")
            else:
                print(f"⚠️  {code} {name} - 无净值数据")
        except Exception as e:
            print(f"❌ {code} {name} - 查询失败: {str(e)[:50]}")

def main():
    print("🔍 数据基础设施板块分析 - 探针试金石")
    print("=" * 80)
    
    # 检查Tushare连接
    try:
        # 测试连接
        df = pro.trade_cal(exchange='SSE', start_date='20260401', end_date='20260407')
        print("✅ Tushare API连接正常")
    except Exception as e:
        print(f"❌ Tushare连接失败: {e}")
        return
    
    # 获取个股数据
    stock_results = get_realtime_prices()
    
    # 获取ETF数据
    get_etf_info()
    
    # 分析总结
    print("\n🎯 探针分析建议")
    print("=" * 80)
    print("基于'数据要素×'政策红利，建议探针重点关注:")
    print("1. 🔍 **数据交易平台**: 浙数文化(600633) - 参与浙江大数据交易中心")
    print("2. 🖥️ **云计算基础设施**: 浪潮信息(000977)、中科曙光(603019)")
    print("3. 🔒 **网络安全**: 启明星辰(002439)、绿盟科技(300369)")
    print("4. ⚡ **算力芯片**: 寒武纪(688256)、海光信息(688041)")
    print("5. 📊 **ETF配置**: 515070(人工智能)、515250(信息安全)、515400(大数据)")
    
    # 生成探针输入文件
    probe_data = {
        "theme": "数据基础设施",
        "analysis_time": datetime.now().isoformat(),
        "policy_background": "数据要素×三年行动计划（2024-2026）",
        "key_stocks": stock_results,
        "recommended_etfs": [
            {"code": "515050.SH", "name": "华夏中证5G通信主题ETF", "category": "通信基础设施"},
            {"code": "515070.SH", "name": "易方达中证人工智能ETF", "category": "AI算力"},
            {"code": "515250.SH", "name": "富国中证信息安全ETF", "category": "网络安全"},
            {"code": "515400.SH", "name": "富国中证大数据产业ETF", "category": "大数据"},
        ],
        "probe_instructions": "分析这些标的的业务构成，寻找更多数据基础设施相关公司"
    }
    
    output_file = "database/probe/data_infra_probe_input.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(probe_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 探针输入文件已保存: {output_file}")
    print("🚀 可将此文件作为'试金石'交给探针模块进行深度分析")
    print("=" * 80)

if __name__ == "__main__":
    main()