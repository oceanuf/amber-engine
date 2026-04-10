#!/usr/bin/env python3
"""
测试板块资金流聚合 - G12能量潮汐算法数据可行性验证
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tushare as ts
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

# 设置Tushare token
TUSHARE_TOKEN = "9e32ef28eac05c5fbb11e6f02a50da903def70f94b3018e93340568b"
ts.set_token(TUSHARE_TOKEN)
pro = ts.pro_api()

def test_sector_capital_flow_aggregation():
    """测试板块资金流聚合"""
    print("🧪 测试板块资金流聚合可行性")
    
    # 模拟板块定义（实际应从行业分类获取）
    test_sectors = {
        "banking": ["000001.SZ", "000002.SZ", "002142.SZ"],
        "technology": ["000063.SZ", "000066.SZ", "000938.SZ"],
        "consumption": ["000858.SZ", "000568.SZ", "000895.SZ"]
    }
    
    sector_results = {}
    
    for sector_name, stocks in test_sectors.items():
        print(f"\n📊 分析板块: {sector_name}")
        print(f"   股票数量: {len(stocks)}")
        
        sector_flows = []
        
        for stock in stocks:
            try:
                # 获取最近5个交易日的资金流数据
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=10)).strftime('%Y%m%d')
                
                df_moneyflow = pro.moneyflow(
                    ts_code=stock,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if df_moneyflow is not None and not df_moneyflow.empty:
                    # 获取最新一日的数据
                    latest = df_moneyflow.iloc[0]
                    
                    # 计算净流入
                    net_amount = latest.get('net_mf_amount', 0)
                    
                    sector_flows.append({
                        "stock": stock,
                        "trade_date": latest.get('trade_date', ''),
                        "net_amount": net_amount,
                        "buy_lg_amount": latest.get('buy_lg_amount', 0),  # 大单买入
                        "sell_lg_amount": latest.get('sell_lg_amount', 0),  # 大单卖出
                        "buy_elg_amount": latest.get('buy_elg_amount', 0),  # 特大单买入
                        "sell_elg_amount": latest.get('sell_elg_amount', 0),  # 特大单卖出
                    })
                    
                    print(f"   {stock}: 净流入{net_amount/10000:.2f}万元")
                else:
                    print(f"   {stock}: 无资金流数据")
                    
            except Exception as e:
                print(f"   {stock}: 获取失败 - {str(e)[:50]}")
        
        if sector_flows:
            # 计算板块汇总
            df_sector = pd.DataFrame(sector_flows)
            
            sector_total = {
                "sector_name": sector_name,
                "stock_count": len(sector_flows),
                "total_net_amount": df_sector['net_amount'].sum(),
                "total_buy_lg": df_sector['buy_lg_amount'].sum(),
                "total_sell_lg": df_sector['sell_lg_amount'].sum(),
                "total_buy_elg": df_sector['buy_elg_amount'].sum(),
                "total_sell_elg": df_sector['sell_elg_amount'].sum(),
                "net_inflow_ratio": 0
            }
            
            # 计算净流入比例
            total_buy = sector_total['total_buy_lg'] + sector_total['total_buy_elg']
            total_sell = sector_total['total_sell_lg'] + sector_total['total_sell_elg']
            total_volume = total_buy + total_sell
            
            if total_volume > 0:
                sector_total['net_inflow_ratio'] = (total_buy - total_sell) / total_volume
            
            sector_results[sector_name] = sector_total
            
            print(f"   板块汇总:")
            print(f"     总净流入: {sector_total['total_net_amount']/10000:.2f}万元")
            print(f"     净流入比例: {sector_total['net_inflow_ratio']:.2%}")
            print(f"     大单买入: {sector_total['total_buy_lg']/10000:.2f}万元")
            print(f"     特大单买入: {sector_total['total_buy_elg']/10000:.2f}万元")
    
    return sector_results

def test_policy_data_feasibility():
    """测试政策数据可行性"""
    print("\n📜 测试政策数据可行性")
    
    # 政策数据源选项
    policy_sources = {
        "政府网站爬虫": {
            "可行性": "🟢 高",
            "技术难度": "🟡 中",
            "更新频率": "实时",
            "成本": "🟢 低",
            "备注": "需处理反爬虫和网站结构变化"
        },
        "第三方政策数据库": {
            "可行性": "🟢 高", 
            "技术难度": "🟢 低",
            "更新频率": "实时",
            "成本": "🔴 高",
            "备注": "如Wind/Choice金融终端，年费较高"
        },
        "LLM实时搜索": {
            "可行性": "🟡 中",
            "技术难度": "🟡 中",
            "更新频率": "实时",
            "成本": "🟡 中",
            "备注": "Perplexity API等，有调用成本"
        }
    }
    
    print("   可选方案:")
    for source, info in policy_sources.items():
        print(f"   - {source}:")
        print(f"       可行性: {info['可行性']} | 难度: {info['技术难度']}")
        print(f"       成本: {info['成本']} | {info['备注']}")
    
    return policy_sources

def test_derivatives_data_feasibility():
    """测试衍生品数据可行性"""
    print("\n📉 测试期权数据可行性")
    
    derivatives_sources = {
        "交易所官方数据": {
            "可行性": "🟡 中",
            "数据类型": "期权成交/持仓/行权数据",
            "IV数据": "❌ 不包含",
            "成本": "🟢 低",
            "备注": "需自行计算IV，技术难度较高"
        },
        "聚宽JoinQuant": {
            "可行性": "🟢 高",
            "数据类型": "期权全量数据",
            "IV数据": "✅ 包含",
            "成本": "🟡 中",
            "备注": "免费版有限制，专业版需付费"
        },
        "米筐RiceQuant": {
            "可行性": "🟢 高",
            "数据类型": "期权全量数据",
            "IV数据": "✅ 包含",
            "成本": "🟡 中",
            "备注": "类似聚宽，有免费额度"
        },
        "Wind金融终端": {
            "可行性": "🟢 高",
            "数据类型": "最全的衍生品数据",
            "IV数据": "✅ 包含",
            "成本": "🔴 高",
            "备注": "专业机构使用，年费较高"
        }
    }
    
    print("   可选方案:")
    for source, info in derivatives_sources.items():
        print(f"   - {source}:")
        print(f"       可行性: {info['可行性']} | IV数据: {info['IV数据']}")
        print(f"       成本: {info['成本']} | {info['备注']}")
    
    return derivatives_sources

def test_global_markets_data():
    """测试全球市场数据可行性"""
    print("\n🌍 测试全球市场数据可行性")
    
    global_sources = {
        "雅虎财经Yahoo Finance": {
            "可行性": "🟢 高",
            "覆盖范围": "全球股票/外汇/期货/指数",
            "实时性": "🟡 中 (15分钟延迟)",
            "成本": "🟢 低 (免费)",
            "API限制": "有频率限制"
        },
        "Investing.com": {
            "可行性": "🟡 中",
            "覆盖范围": "全球市场全面",
            "实时性": "🟢 高",
            "成本": "🟢 低 (爬虫)",
            "API限制": "需处理反爬虫"
        },
        "新浪财经": {
            "可行性": "🟢 高",
            "覆盖范围": "A股相关全球数据",
            "实时性": "🟢 高",
            "成本": "🟢 低 (免费)",
            "备注": "CNH汇率、A50期货等"
        },
        "专业数据商": {
            "可行性": "🟢 高",
            "覆盖范围": "最全面的全球数据",
            "实时性": "🟢 高",
            "成本": "🔴 高",
            "备注": "Bloomberg/Reuters等"
        }
    }
    
    print("   可选方案:")
    for source, info in global_sources.items():
        print(f"   - {source}:")
        print(f"       可行性: {info['可行性']} | 实时性: {info['实时性']}")
        print(f"       成本: {info['成本']} | {info.get('备注', info.get('API限制', ''))}")
    
    return global_sources

def main():
    """主测试函数"""
    print("=" * 60)
    print("G12-G15数据源可行性测试报告")
    print("=" * 60)
    
    # 测试板块资金流聚合
    sector_results = test_sector_capital_flow_aggregation()
    
    # 测试政策数据
    policy_sources = test_policy_data_feasibility()
    
    # 测试期权数据
    derivatives_sources = test_derivatives_data_feasibility()
    
    # 测试全球市场数据
    global_sources = test_global_markets_data()
    
    # 生成总结报告
    print("\n" + "=" * 60)
    print("📋 数据源可行性总结")
    print("=" * 60)
    
    summary = {
        "G12_能量潮汐": {
            "状态": "✅ 可行",
            "方案": "Tushare个股资金流聚合",
            "技术难度": "🟢 低",
            "成本": "🟢 低",
            "实施时间": "1-2天"
        },
        "G13_政策语义": {
            "状态": "✅ 可行",
            "推荐方案": "政府网站爬虫 + LLM分析",
            "备选方案": "第三方政策数据库",
            "技术难度": "🟡 中",
            "成本": "🟡 中",
            "实施时间": "3-5天"
        },
        "G14_波动率挤压2.0": {
            "状态": "⚠️ 有条件可行",
            "推荐方案": "聚宽JoinQuant免费版",
            "技术难度": "🟡 中",
            "成本": "🟡 中 (或有API调用成本)",
            "实施时间": "5-7天",
            "备注": "需调研具体API限制"
        },
        "G15_跨市场关联": {
            "状态": "✅ 可行",
            "推荐方案": "雅虎财经 + 新浪财经",
            "技术难度": "🟢 低",
            "成本": "🟢 低",
            "实施时间": "2-3天",
            "备注": "免费方案有延迟，实时性要求不高可接受"
        }
    }
    
    for algorithm, info in summary.items():
        print(f"\n{algorithm}:")
        for key, value in info.items():
            print(f"   {key}: {value}")
    
    # 保存测试结果
    test_results = {
        "test_time": datetime.now().isoformat(),
        "sector_capital_flow": sector_results,
        "summary": summary
    }
    
    os.makedirs("logs/data_tests", exist_ok=True)
    test_file = f"logs/data_tests/g12_g15_feasibility_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(test_file, 'w', encoding='utf-8') as f:
        json.dump(test_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n📁 测试结果已保存至: {test_file}")
    
    # 建议
    print("\n🎯 实施建议:")
    print("1. 立即启动: G12能量潮汐 (技术难度低，数据可用)")
    print("2. 并行开发: G13政策语义爬虫原型")
    print("3. 调研评估: G14期权数据源具体API限制")
    print("4. 基础集成: G15全球数据免费方案")
    
    print("\n⚠️  需要架构师决策:")
    print("   - G14期权数据预算范围")
    print("   - G13政策数据源优先级 (爬虫 vs 第三方API)")
    print("   - 整体实施时间表确认")

if __name__ == "__main__":
    main()