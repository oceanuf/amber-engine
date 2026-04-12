#!/usr/bin/env python3
"""
股票诊断技能续写部分 - 报告生成
"""

import os
import sys
import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.skills.stock_advisor import StockAdvisorSkill

def generate_full_report():
    """生成完整报告示例"""
    skill = StockAdvisorSkill()
    
    # 测试语义识别
    test_cases = [
        "分析000858五粮液",
        "510300怎么样",
        "看看贵州茅台600519",
        "评价159919",
        "000858怎么样"
    ]
    
    for text in test_cases:
        print(f"\n测试: {text}")
        stock_info = skill.extract_stock_info(text)
        if stock_info:
            print(f"  识别结果: {stock_info}")
            
            # 获取数据
            df = skill.get_stock_data(stock_info)
            if df is not None and len(df) > 0:
                print(f"  数据获取: 成功 ({len(df)} 条)")
                
                # 计算胜率
                current_price = df["close"].iloc[-1] if len(df) > 0 else 0
                win_rate_30d = skill.calculate_win_rate(df, 30)
                win_rate_60d = skill.calculate_win_rate(df, 60)
                win_rate_90d = skill.calculate_win_rate(df, 90)
                
                # 生成交易建议
                trading_advice = skill.generate_trading_advice(df, current_price)
                
                # 组装分析结果
                analysis_results = {
                    "rating": "谨慎乐观" if win_rate_30d["win_rate"] > 50 else "谨慎",
                    "win_rate_30d": win_rate_30d,
                    "win_rate_60d": win_rate_60d,
                    "win_rate_90d": win_rate_90d,
                    "trading_advice": trading_advice,
                    "data_points": len(df),
                    "data_recency": "今日" if df["date"].iloc[-1].date() == datetime.datetime.now().date() else "历史"
                }
                
                print(f"  30天胜率: {win_rate_30d['win_rate']}%")
                print(f"  交易建议: {trading_advice['action']}")
                
                # 生成报告
                report = skill.generate_report(stock_info, analysis_results)
                
                # 保存报告
                output_dir = "stock-analytics"
                os.makedirs(output_dir, exist_ok=True)
                
                code_clean = stock_info["code"].replace(".", "")
                output_path = os.path.join(output_dir, f"{code_clean}.md")
                
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(report)
                
                print(f"  报告保存: {output_path}")
            else:
                print(f"  数据获取: 失败")
        else:
            print(f"  识别失败")

if __name__ == "__main__":
    generate_full_report()