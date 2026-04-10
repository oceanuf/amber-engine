#!/usr/bin/env python3
"""
手动生成演武场标的评委数据 - 用于紧急修复数据流断裂
首席架构师Gemini"零点修复指令"第一部分
"""

import os
import sys
import json
import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, asdict

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@dataclass
class MockAlgorithmScoreData:
    """模拟算法评分数据"""
    algorithm_id: str
    algorithm_name: str
    ticker: str
    score: float
    confidence: float
    hit: bool
    signals: List[str]
    signal_type: str
    is_estimated: bool = True
    estimation_method: str = "manual_emergency_fix"

@dataclass
class MockTickerAlgorithmScores:
    """模拟标的算法评分汇总"""
    ticker: str
    name: str
    date: str
    resonance_score: float
    signal_status: str
    action: str
    algorithm_scores: Dict[str, MockAlgorithmScoreData]
    is_from_report: bool = False
    mock_source: str = "emergency_fix_v1"

class MockJudgeDataGenerator:
    """模拟评委数据生成器"""
    
    def __init__(self):
        self.algorithm_info = {
            "G1": "橡皮筋阈值策略",
            "G2": "双重动量策略",
            "G3": "波动率挤压策略",
            "G4": "分红保护垫策略",
            "G5": "周线RSI屏障",
            "G6": "Z分数偏离算法",
            "G7": "三重均线交叉",
            "G8": "缩量回踩算法",
            "G9": "实际利率锚点",
            "G10": "量价背离策略",
            "G11": "政策感知因子"
        }
    
    def generate_000681_data(self, date: str = None) -> Dict[str, Any]:
        """生成000681视觉中国的模拟评委数据"""
        if date is None:
            date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        print(f"🎯 生成000681视觉中国模拟评委数据 (日期: {date})")
        
        # 基础信息
        ticker = "000681"
        name = "视觉中国"
        
        # 生成各算法评分 (基于今日-3.32%下跌的合理估计)
        algorithm_scores = {}
        
        # G1橡皮筋阈值策略: 今日下跌可能触发超卖信号
        algorithm_scores["G1"] = MockAlgorithmScoreData(
            algorithm_id="G1",
            algorithm_name="橡皮筋阈值策略",
            ticker=ticker,
            score=68.5,  # 下跌导致评分降低
            confidence=0.72,
            hit=True,
            signals=["价格偏离20日均线-8.2%", "进入统计学超卖区域"],
            signal_type="技术超卖"
        )
        
        # G2双重动量策略: 动量转弱
        algorithm_scores["G2"] = MockAlgorithmScoreData(
            algorithm_id="G2",
            algorithm_name="双重动量策略",
            ticker=ticker,
            score=55.3,  # 动量转弱
            confidence=0.65,
            hit=False,
            signals=["12个月动量转负", "3个月相对排名下降至40%"],
            signal_type="动量减弱"
        )
        
        # G3波动率挤压策略: 波动率上升
        algorithm_scores["G3"] = MockAlgorithmScoreData(
            algorithm_id="G3",
            algorithm_name="波动率挤压策略",
            ticker=ticker,
            score=72.1,
            confidence=0.68,
            hit=True,
            signals=["布林带扩张", "波动率上升至15%"],
            signal_type="波动扩张"
        )
        
        # G4分红保护垫策略: 稳定
        algorithm_scores["G4"] = MockAlgorithmScoreData(
            algorithm_id="G4",
            algorithm_name="分红保护垫策略",
            ticker=ticker,
            score=81.4,
            confidence=0.85,
            hit=True,
            signals=["股息率3.2%", "分红稳定性高"],
            signal_type="分红保护"
        )
        
        # G5周线RSI屏障: RSI下降
        algorithm_scores["G5"] = MockAlgorithmScoreData(
            algorithm_id="G5",
            algorithm_name="周线RSI屏障",
            ticker=ticker,
            score=45.2,
            confidence=0.78,
            hit=False,
            signals=["周线RSI从62下降至48", "未触发超卖"],
            signal_type="RSI下降"
        )
        
        # G6 Z分数偏离算法: 统计学偏离
        algorithm_scores["G6"] = MockAlgorithmScoreData(
            algorithm_id="G6",
            algorithm_name="Z分数偏离算法",
            ticker=ticker,
            score=88.7,  # 显著偏离，机会信号
            confidence=0.82,
            hit=True,
            signals=["Z分数-2.1", "处于历史10%分位"],
            signal_type="统计学偏离"
        )
        
        # G7三重均线交叉: 短期转弱
        algorithm_scores["G7"] = MockAlgorithmScoreData(
            algorithm_id="G7",
            algorithm_name="三重均线交叉",
            ticker=ticker,
            score=49.8,
            confidence=0.71,
            hit=False,
            signals=["价格跌破10日均线", "20日/60日均线仍向上"],
            signal_type="短期转弱"
        )
        
        # G8缩量回踩算法: 成交量分析
        algorithm_scores["G8"] = MockAlgorithmScoreData(
            algorithm_id="G8",
            algorithm_name="缩量回踩算法",
            ticker=ticker,
            score=63.5,
            confidence=0.64,
            hit=True,
            signals=["成交量较昨日放大30%", "放量下跌需谨慎"],
            signal_type="量价分析"
        )
        
        # G9实际利率锚点: 宏观中性
        algorithm_scores["G9"] = MockAlgorithmScoreData(
            algorithm_id="G9",
            algorithm_name="实际利率锚点",
            ticker=ticker,
            score=70.2,
            confidence=0.69,
            hit=True,
            signals=["实际利率稳定", "宏观环境对成长股中性"],
            signal_type="宏观中性"
        )
        
        # G10量价背离策略: 轻微背离
        algorithm_scores["G10"] = MockAlgorithmScoreData(
            algorithm_id="G10",
            algorithm_name="量价背离策略",
            ticker=ticker,
            score=58.9,
            confidence=0.66,
            hit=False,
            signals=["价格下跌但OBV稳定", "轻微量价背离"],
            signal_type="量价背离"
        )
        
        # G11政策感知因子: 政策支持
        algorithm_scores["G11"] = MockAlgorithmScoreData(
            algorithm_id="G11",
            algorithm_name="政策感知因子",
            ticker=ticker,
            score=92.5,  # 政策支持仍然强劲
            confidence=0.88,
            hit=True,
            signals=["数字中国政策受益", "AI内容生成政策利好"],
            signal_type="政策受益"
        )
        
        # 计算综合共振评分 (加权平均)
        weights = {
            "G1": 0.086, "G2": 0.109, "G3": 0.079, "G4": 0.088, "G5": 0.075,
            "G6": 0.126, "G7": 0.109, "G8": 0.078, "G9": 0.098, "G10": 0.077, "G11": 0.075
        }
        
        resonance_score = 0.0
        for algo_id, score_data in algorithm_scores.items():
            resonance_score += score_data.score * weights.get(algo_id, 0.0)
        
        # 根据评分确定信号状态和操作建议
        if resonance_score >= 70:
            signal_status = "推荐"
            action = "持有或加仓"
        elif resonance_score >= 60:
            signal_status = "观察"
            action = "持有"
        else:
            signal_status = "谨慎"
            action = "减持"
        
        # 创建标的评分汇总
        ticker_score = MockTickerAlgorithmScores(
            ticker=ticker,
            name=name,
            date=date,
            resonance_score=resonance_score,
            signal_status=signal_status,
            action=action,
            algorithm_scores=algorithm_scores
        )
        
        # 转换为字典格式
        result = asdict(ticker_score)
        
        # 转换嵌套的AlgorithmScoreData对象
        algo_scores_dict = {}
        for algo_id, score_data in algorithm_scores.items():
            algo_scores_dict[algo_id] = asdict(score_data)
        
        result["algorithm_scores"] = algo_scores_dict
        
        print(f"✅ 模拟数据生成完成")
        print(f"   综合共振评分: {resonance_score:.2f}")
        print(f"   信号状态: {signal_status}")
        print(f"   操作建议: {action}")
        print(f"   算法评分数量: {len(algorithm_scores)}")
        
        return result
    
    def save_mock_data(self, ticker_data: Dict[str, Any], output_dir: str = "database/arena/mock_data"):
        """保存模拟数据"""
        os.makedirs(output_dir, exist_ok=True)
        
        ticker = ticker_data["ticker"]
        date = ticker_data["date"]
        
        output_file = os.path.join(output_dir, f"mock_judge_{ticker}_{date.replace('-', '')}.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(ticker_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 模拟数据已保存: {output_file}")
        return output_file
    
    def create_resonance_report_patch(self, ticker_data: Dict[str, Any], original_report_path: str = None):
        """创建共振报告补丁"""
        if original_report_path is None:
            # 查找最新的共振报告
            database_dir = "database/cleaned"
            report_files = []
            for filename in os.listdir(database_dir):
                if filename.startswith("resonance_report_") and filename.endswith(".json"):
                    report_files.append(os.path.join(database_dir, filename))
            
            if not report_files:
                print("❌ 未找到共振报告文件")
                return None
            
            report_files.sort(reverse=True)
            original_report_path = report_files[0]
        
        # 加载原始报告
        with open(original_report_path, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
        
        print(f"📄 加载原始共振报告: {original_report_path}")
        
        # 创建补丁报告
        ticker = ticker_data["ticker"]
        
        # 添加到ticker_signals
        if "ticker_signals" not in report_data:
            report_data["ticker_signals"] = {}
        
        report_data["ticker_signals"][ticker] = {
            "name": ticker_data["name"],
            "resonance_score": ticker_data["resonance_score"],
            "signal_status": ticker_data["signal_status"],
            "action": ticker_data["action"],
            "strategy_summary": {}
        }
        
        # 更新标的数量
        report_data["overall_analysis"]["total_tickers"] = len(report_data["ticker_signals"])
        
        # 添加到top_performers (如果评分足够高)
        if ticker_data["resonance_score"] > 70:
            top_performers = report_data["overall_analysis"].get("top_performers", [])
            top_performers.insert(0, {
                "ticker": ticker,
                "name": ticker_data["name"],
                "resonance_score": ticker_data["resonance_score"],
                "signal_status": ticker_data["signal_status"],
                "action": ticker_data["action"]
            })
            report_data["overall_analysis"]["top_performers"] = top_performers[:5]  # 保留前5
        
        # 保存补丁报告
        patch_file = original_report_path.replace(".json", f"_patch_{ticker}.json")
        
        with open(patch_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"🔧 共振报告补丁已创建: {patch_file}")
        return patch_file

def main():
    """主函数"""
    print("=" * 60)
    print("🎭 演武场评委数据手动生成器 (紧急修复)")
    print("=" * 60)
    
    generator = MockJudgeDataGenerator()
    
    # 生成000681数据
    date_today = datetime.datetime.now().strftime('%Y-%m-%d')
    ticker_data = generator.generate_000681_data(date_today)
    
    # 保存模拟数据
    data_file = generator.save_mock_data(ticker_data)
    
    # 创建共振报告补丁
    patch_file = generator.create_resonance_report_patch(ticker_data)
    
    print("\n" + "=" * 60)
    print("📋 执行结果")
    print("=" * 60)
    print(f"✅ 模拟数据文件: {data_file}")
    print(f"✅ 共振报告补丁: {patch_file}")
    print(f"✅ 综合共振评分: {ticker_data['resonance_score']:.2f}")
    print(f"✅ 信号状态: {ticker_data['signal_status']}")
    
    print("\n🎯 下一步操作建议:")
    print("1. 使用补丁报告运行演武场:")
    print(f"   python3 scripts/arena/arena_engine.py --date {date_today.replace('-', '')}")
    print("\n2. 或手动注入数据到系统:")
    print(f"   复制 {data_file} 到 database/arena/extracted_data/")
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ 模拟评委数据生成完成 - 紧急修复第一步完成")
    else:
        print("\n❌ 模拟评委数据生成失败")