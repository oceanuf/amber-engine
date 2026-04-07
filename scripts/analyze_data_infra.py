#!/usr/bin/env python3
"""
数据基础设施板块分析脚本
获取相关ETF和个股的实时行情，分析投资价值
"""

import akshare as ak
import pandas as pd
import json
import datetime
from typing import Dict, List, Any, Optional

def get_etf_list() -> List[Dict[str, Any]]:
    """获取数据基础设施相关ETF列表"""
    etfs = [
        {"code": "515050.SH", "name": "华夏中证5G通信主题ETF", "category": "5G/通信基础设施"},
        {"code": "515070.SH", "name": "易方达中证人工智能ETF", "category": "AI/算力基础设施"},
        {"code": "515250.SH", "name": "富国中证信息安全ETF", "category": "网络安全"},
        {"code": "515400.SH", "name": "富国中证大数据产业ETF", "category": "大数据基础设施"},
        {"code": "159995.SZ", "name": "华夏国证半导体芯片ETF", "category": "芯片/算力基础"},
        {"code": "512480.SH", "name": "国联安中证全指半导体ETF", "category": "半导体基础设施"},
    ]
    return etfs

def get_stock_list() -> List[Dict[str, Any]]:
    """获取数据基础设施相关个股列表"""
    stocks = [
        # 服务器/云计算
        {"code": "000977.SZ", "name": "浪潮信息", "category": "服务器"},
        {"code": "603019.SH", "name": "中科曙光", "category": "高性能计算"},
        {"code": "000938.SZ", "name": "紫光股份", "category": "云计算基础设施"},
        {"code": "600536.SH", "name": "中国软件", "category": "基础软件"},
        
        # 网络安全
        {"code": "002439.SZ", "name": "启明星辰", "category": "网络安全"},
        {"code": "300369.SZ", "name": "绿盟科技", "category": "网络安全"},
        {"code": "300454.SZ", "name": "深信服", "category": "网络安全/云计算"},
        {"code": "688201.SH", "name": "信安世纪", "category": "网络安全"},
        
        # 数据中心
        {"code": "300383.SZ", "name": "光环新网", "category": "数据中心"},
        {"code": "603881.SH", "name": "数据港", "category": "数据中心"},
        {"code": "000815.SZ", "name": "美利云", "category": "数据中心"},
        
        # 数据交易/流通
        {"code": "600633.SH", "name": "浙数文化", "category": "数据交易（浙江大数据交易中心）"},
        {"code": "300229.SZ", "name": "拓尔思", "category": "数据服务"},
        {"code": "300170.SZ", "name": "汉得信息", "category": "企业数据服务"},
        
        # 算力基础设施
        {"code": "688256.SH", "name": "寒武纪", "category": "AI芯片"},
        {"code": "688041.SH", "name": "海光信息", "category": "CPU/DCU"},
        {"code": "002049.SZ", "name": "紫光国微", "category": "安全芯片"},
        
        # 基础软件/数据库
        {"code": "600588.SH", "name": "用友网络", "category": "企业软件"},
        {"code": "002410.SZ", "name": "广联达", "category": "建筑数据"},
    ]
    return stocks

def get_real_time_quotes(codes: List[str]) -> Optional[pd.DataFrame]:
    """获取实时行情数据"""
    try:
        # 获取所有A股实时行情
        spot_df = ak.stock_zh_a_spot_em()
        
        # 过滤出我们关心的代码
        # 注意：akshare返回的代码格式是"000977"，不带后缀
        codes_no_suffix = [code.split('.')[0] for code in codes]
        filtered_df = spot_df[spot_df['代码'].isin(codes_no_suffix)].copy()
        
        return filtered_df
    except Exception as e:
        print(f"获取实时行情失败: {e}")
        return None

def get_etf_real_time() -> Optional[pd.DataFrame]:
    """获取ETF实时行情"""
    try:
        # 获取ETF实时行情
        etf_spot = ak.fund_etf_spot_em()
        return etf_spot
    except Exception as e:
        print(f"获取ETF行情失败: {e}")
        return None

def analyze_data_infrastructure():
    """分析数据基础设施板块"""
    print("=" * 80)
    print("数据基础设施板块分析报告")
    print(f"生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 获取ETF列表
    etfs = get_etf_list()
    etf_codes = [etf['code'] for etf in etfs]
    
    # 获取个股列表
    stocks = get_stock_list()
    stock_codes = [stock['code'] for stock in stocks]
    
    print("\n📊 一、数据基础设施相关ETF")
    print("-" * 80)
    
    # 获取ETF行情
    etf_quotes = get_etf_real_time()
    if etf_quotes is not None:
        for etf in etfs:
            code_no_suffix = etf['code'].split('.')[0]
            etf_data = etf_quotes[etf_quotes['代码'] == code_no_suffix]
            if not etf_data.empty:
                row = etf_data.iloc[0]
                print(f"代码: {etf['code']}")
                print(f"名称: {etf['name']}")
                print(f"分类: {etf['category']}")
                print(f"最新价: {row.get('最新价', 'N/A')}")
                print(f"涨跌幅: {row.get('涨跌幅', 'N/A')}%")
                print(f"成交额: {row.get('成交额', 'N/A')}")
                print(f"换手率: {row.get('换手率', 'N/A')}%")
                print("-" * 40)
            else:
                print(f"⚠️  未找到ETF数据: {etf['code']} {etf['name']}")
    else:
        print("❌ 无法获取ETF行情数据")
    
    print("\n📈 二、数据基础设施相关个股")
    print("-" * 80)
    
    # 获取个股行情
    stock_quotes = get_real_time_quotes(stock_codes)
    if stock_quotes is not None:
        # 按分类分组显示
        categories = {}
        for stock in stocks:
            cat = stock['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(stock)
        
        for category, cat_stocks in categories.items():
            print(f"\n🔹 {category}:")
            for stock in cat_stocks:
                code_no_suffix = stock['code'].split('.')[0]
                stock_data = stock_quotes[stock_quotes['代码'] == code_no_suffix]
                if not stock_data.empty:
                    row = stock_data.iloc[0]
                    change_pct = float(str(row.get('涨跌幅', '0')).replace('%', ''))
                    change_symbol = "↑" if change_pct > 0 else "↓" if change_pct < 0 else "→"
                    
                    print(f"  {stock['code']} {stock['name']:10} "
                          f"最新: {row.get('最新价', 'N/A'):>6} "
                          f"{change_symbol}{abs(change_pct):>5.2f}% "
                          f"市值: {row.get('总市值', 'N/A'):>10} "
                          f"PE(TTM): {row.get('市盈率-动态', 'N/A'):>6}")
                else:
                    print(f"  ⚠️ {stock['code']} {stock['name']} - 数据缺失")
    else:
        print("❌ 无法获取个股行情数据")
    
    print("\n🎯 三、投资建议摘要")
    print("-" * 80)
    print("基于'数据要素×'三年行动计划（2024-2026）政策利好:")
    print("1. 📍 优先关注: 数据交易平台、数据中心、云计算基础设施")
    print("2. 🔒 安全边际: 网络安全、数据安全板块受益于合规需求")
    print("3. ⚡ 成长潜力: AI算力、芯片等算力基础设施")
    print("4. 📊 估值注意: 部分标的估值较高，建议分批配置")
    
    # 生成探针输入数据
    probe_input = {
        "analysis_time": datetime.datetime.now().isoformat(),
        "theme": "数据基础设施",
        "etfs": etfs,
        "stocks": stocks,
        "policy_background": {
            "plan": "数据要素×三年行动计划（2024-2026）",
            "target_year": 2026,
            "key_metrics": "打造300+典型应用场景，数据产业年均增速>20%"
        }
    }
    
    # 保存探针输入数据
    output_file = "database/probe/data_infrastructure_input.json"
    import os
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(probe_input, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 探针输入数据已保存至: {output_file}")
    print("🔍 可将此文件交给探针模块进行DNA提取和相似性分析")
    
    print("\n" + "=" * 80)
    print("分析完成。建议结合技术面和基本面进一步筛选标的。")
    print("=" * 80)

if __name__ == "__main__":
    analyze_data_infrastructure()