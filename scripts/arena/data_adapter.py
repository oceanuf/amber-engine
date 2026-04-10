#!/usr/bin/env python3
"""
演武场数据适配器
从resonance_report提取算法评分数据，转换为算法权重计算模块所需的格式
"""

import os
import sys
import json
import datetime
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict, field

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@dataclass
class AlgorithmScoreData:
    """算法评分数据类"""
    algorithm_id: str  # G1, G2, ..., G11
    algorithm_name: str  # 算法名称
    ticker: str  # 标的代码
    score: float  # 算法评分 (0-100)
    confidence: float  # 置信度 (0-1)
    hit: bool  # 是否命中
    signals: List[str]  # 信号描述
    signal_type: str  # 信号类型
    
@dataclass
class TickerAlgorithmScores:
    """标的算法评分汇总"""
    ticker: str
    name: str
    date: str
    resonance_score: float  # 综合共振评分
    signal_status: str  # 信号状态
    action: str  # 建议操作
    algorithm_scores: Dict[str, AlgorithmScoreData]  # {算法ID: 评分数据}
    
@dataclass  
class DailyAlgorithmPerformance:
    """每日算法绩效数据"""
    date: str
    benchmark_return: float  # 基准收益率 (510300)
    ticker_performances: Dict[str, Dict[str, float]]  # {标的: {算法ID: 收益率}}
    ticker_benchmark_returns: Dict[str, float]  # {标的: 基准收益率}
    algorithm_scores: Dict[str, TickerAlgorithmScores]  # {标的: 算法评分汇总}

class ResonanceReportAdapter:
    """共振报告数据适配器"""
    
    # 算法名称映射 (共振报告中的算法名称 -> 算法ID)
    ALGORITHM_NAME_MAPPING = {
        "Gravity-Dip": "G1",
        "Dual-Momentum": "G2", 
        "Vol-Squeeze": "G3",
        "Dividend-Alpha": "G4",
        "Weekly-RSI": "G5",
        "Z-Score-Bias": "G6",
        "Triple-Cross": "G7",
        "Volume-Retracement": "G8",
        "Macro-Gold": "G9",
        "OBV-Divergence": "G10",
        "Policy-Resonance": "G11"  # 假设G11是政策共振
    }
    
    # 反向映射
    ALGORITHM_ID_MAPPING = {v: k for k, v in ALGORITHM_NAME_MAPPING.items()}
    
    def __init__(self, report_path: Optional[str] = None):
        """
        初始化适配器
        
        参数:
            report_path: 共振报告文件路径，如果为None则自动查找最新报告
        """
        self.report_path = report_path
        self.report_data = None
        
    def find_latest_report(self) -> str:
        """查找最新的共振报告文件"""
        database_dir = "database"
        
        if not os.path.exists(database_dir):
            raise FileNotFoundError(f"数据库目录不存在: {database_dir}")
        
        # 查找所有resonance_report文件
        report_files = []
        for filename in os.listdir(database_dir):
            if filename.startswith("resonance_report_") and filename.endswith(".json"):
                report_files.append(os.path.join(database_dir, filename))
        
        if not report_files:
            raise FileNotFoundError("未找到共振报告文件")
        
        # 按日期排序，获取最新的
        report_files.sort(reverse=True)
        return report_files[0]
    
    def load_report(self, report_path: Optional[str] = None) -> bool:
        """加载共振报告"""
        if report_path is None:
            if self.report_path is None:
                self.report_path = self.find_latest_report()
            report_path = self.report_path
        
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                self.report_data = json.load(f)
            
            print(f"✅ 加载共振报告: {report_path}")
            print(f"   报告日期: {self.report_data['metadata']['generated_at']}")
            print(f"   标的数量: {self.report_data['overall_analysis']['total_tickers']}")
            print(f"   策略数量: {self.report_data['metadata']['strategies_count']}")
            
            return True
            
        except Exception as e:
            print(f"❌ 加载共振报告失败: {e}")
            return False
    
    def extract_algorithm_scores(self) -> Dict[str, TickerAlgorithmScores]:
        """
        从共振报告提取算法评分数据
        
        返回:
            {标的代码: TickerAlgorithmScores}
        """
        if self.report_data is None:
            if not self.load_report():
                return {}
        
        ticker_scores = {}
        
        # 获取报告日期
        report_date = self.report_data['metadata']['generated_at'][:10]  # 取日期部分
        
        # 处理ticker_signals中的标的
        ticker_signals = self.report_data.get("ticker_signals", {})
        
        for ticker, ticker_data in ticker_signals.items():
            algorithm_scores = {}
            
            # 提取策略摘要
            strategy_summary = ticker_data.get("strategy_summary", {})
            
            for algo_name, algo_data in strategy_summary.items():
                # 映射算法名称到算法ID
                if algo_name in self.ALGORITHM_NAME_MAPPING:
                    algo_id = self.ALGORITHM_NAME_MAPPING[algo_name]
                    
                    # 创建算法评分数据
                    score_data = AlgorithmScoreData(
                        algorithm_id=algo_id,
                        algorithm_name=algo_name,
                        ticker=ticker,
                        score=algo_data.get("score", 0.0),
                        confidence=algo_data.get("confidence", 0.5),
                        hit=algo_data.get("hit", False),
                        signals=algo_data.get("signals", []),
                        signal_type=algo_data.get("signal_type", "unknown")
                    )
                    
                    algorithm_scores[algo_id] = score_data
                else:
                    print(f"⚠️  未知算法名称: {algo_name}")
            
            # 创建标的评分汇总
            ticker_score = TickerAlgorithmScores(
                ticker=ticker,
                name=ticker_data.get("name", ""),
                date=report_date,
                resonance_score=ticker_data.get("resonance_score", 0.0),
                signal_status=ticker_data.get("signal_status", "未知"),
                action=ticker_data.get("action", "未知"),
                algorithm_scores=algorithm_scores
            )
            
            ticker_scores[ticker] = ticker_score
        
        print(f"✅ 提取算法评分数据完成")
        print(f"   处理标的: {len(ticker_scores)}个")
        print(f"   总算法评分: {sum(len(ts.algorithm_scores) for ts in ticker_scores.values())}条")
        
        return ticker_scores
    
    def calculate_initial_scores(self, 
                                ticker_scores: Dict[str, TickerAlgorithmScores],
                                algorithm_weights: Dict[str, float]) -> Dict[str, float]:
        """
        计算标的初始综合评分 S_initial = Σ(G_i_score * G_i_weight)
        
        参数:
            ticker_scores: 标的算法评分数据
            algorithm_weights: 算法权重 {算法ID: 权重}
            
        返回:
            {标的代码: 初始综合评分}
        """
        initial_scores = {}
        
        for ticker, ticker_data in ticker_scores.items():
            total_score = 0.0
            
            for algo_id, algo_score_data in ticker_data.algorithm_scores.items():
                algo_weight = algorithm_weights.get(algo_id, 0.0)
                
                # 计算加权评分
                weighted_score = algo_score_data.score * algo_weight
                total_score += weighted_score
            
            initial_scores[ticker] = total_score
        
        return initial_scores
    
    def assign_queues(self, 
                     initial_scores: Dict[str, float],
                     team1_threshold: float = 70.0,
                     team2_threshold: float = 60.0) -> Tuple[Dict[str, List[str]], Dict[str, float]]:
        """
        根据初始评分分配队列
        
        参数:
            initial_scores: {标的代码: 初始评分}
            team1_threshold: 1队阈值
            team2_threshold: 2队阈值
            
        返回:
            (queue_assignments, sorted_scores)
            queue_assignments: {"team1": [], "team2": [], "observation": []}
            sorted_scores: {标的代码: 评分} (按评分降序)
        """
        # 按评分降序排序
        sorted_tickers = sorted(
            initial_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        sorted_scores = dict(sorted_tickers)
        
        # 分配队列
        queue_assignments = {
            "team1": [],  # 演武场1队
            "team2": [],  # 演武场2队  
            "observation": []  # 观察池
        }
        
        for ticker, score in sorted_tickers:
            if score >= team1_threshold:
                queue_assignments["team1"].append(ticker)
            elif score >= team2_threshold:
                queue_assignments["team2"].append(ticker)
            else:
                queue_assignments["observation"].append(ticker)
        
        print(f"✅ 队列分配完成")
        print(f"   1队 ({team1_threshold}+): {len(queue_assignments['team1'])}个")
        print(f"   2队 ({team2_threshold}+): {len(queue_assignments['team2'])}个")  
        print(f"   观察池: {len(queue_assignments['observation'])}个")
        
        return queue_assignments, sorted_scores
    
    def generate_daily_performance_data(self,
                                      ticker_scores: Dict[str, TickerAlgorithmScores],
                                      benchmark_return: float = 0.0) -> DailyAlgorithmPerformance:
        """
        生成每日算法绩效数据 (模拟版本)
        
        注意: 实际实现中需要从历史数据获取真实的收益率数据
        这里使用算法评分作为收益率的代理
        
        参数:
            ticker_scores: 标的算法评分数据
            benchmark_return: 基准收益率
            
        返回:
            DailyAlgorithmPerformance对象
        """
        date = list(ticker_scores.values())[0].date if ticker_scores else datetime.datetime.now().strftime("%Y-%m-%d")
        
        # 模拟数据: 使用算法评分作为收益率代理
        ticker_performances = {}
        ticker_benchmark_returns = {}
        
        for ticker, ticker_data in ticker_scores.items():
            ticker_benchmark_returns[ticker] = benchmark_return
            
            algo_returns = {}
            for algo_id, algo_score_data in ticker_data.algorithm_scores.items():
                # 简单映射: 评分越高，预期收益率越高
                # 实际实现中需要从历史数据计算
                expected_return = algo_score_data.score / 100.0  # 将0-100分映射为0-1的收益率
                algo_returns[algo_id] = expected_return
            
            ticker_performances[ticker] = algo_returns
        
        performance_data = DailyAlgorithmPerformance(
            date=date,
            benchmark_return=benchmark_return,
            ticker_performances=ticker_performances,
            ticker_benchmark_returns=ticker_benchmark_returns,
            algorithm_scores=ticker_scores
        )
        
        return performance_data

def test_adapter():
    """测试数据适配器"""
    print("🧪 开始测试共振报告数据适配器...")
    
    # 初始化适配器
    adapter = ResonanceReportAdapter()
    
    # 加载最新报告
    if not adapter.load_report():
        print("❌ 报告加载失败，退出测试")
        return
    
    # 提取算法评分数据
    ticker_scores = adapter.extract_algorithm_scores()
    
    if not ticker_scores:
        print("❌ 未提取到算法评分数据，退出测试")
        return
    
    # 模拟算法权重 (等权重)
    algorithm_weights = {}
    for algo_id in adapter.ALGORITHM_ID_MAPPING.keys():
        algorithm_weights[algo_id] = 1.0 / len(adapter.ALGORITHM_ID_MAPPING)
    
    print(f"\\n⚖️  算法权重 (等权重):")
    for algo_id, weight in algorithm_weights.items():
        print(f"   {algo_id}: {weight:.4f}")
    
    # 计算初始综合评分
    initial_scores = adapter.calculate_initial_scores(ticker_scores, algorithm_weights)
    
    print(f"\\n📊 标的初始综合评分:")
    for ticker, score in sorted(initial_scores.items(), key=lambda x: x[1], reverse=True):
        ticker_name = ticker_scores[ticker].name if ticker in ticker_scores else ticker
        print(f"   {ticker} ({ticker_name}): {score:.2f}")
    
    # 分配队列
    queue_assignments, sorted_scores = adapter.assign_queues(initial_scores)
    
    print(f"\\n🏟️  队列分配结果:")
    print(f"   1队 (≥70分): {queue_assignments['team1']}")
    print(f"   2队 (≥60分): {queue_assignments['team2']}")
    print(f"   观察池: {queue_assignments['observation']}")
    
    # 生成每日绩效数据 (模拟)
    print(f"\\n📈 生成每日绩效数据 (模拟)...")
    performance_data = adapter.generate_daily_performance_data(ticker_scores, benchmark_return=0.005)
    
    print(f"   基准收益率: {performance_data.benchmark_return:.4f}")
    print(f"   标的数量: {len(performance_data.ticker_performances)}")
    print(f"   日期: {performance_data.date}")
    
    # 保存提取的数据
    output_dir = "database/arena/extracted_data"
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f"extracted_scores_{performance_data.date}.json")
    
    output_data = {
        "extraction_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "report_date": performance_data.date,
        "ticker_count": len(ticker_scores),
        "initial_scores": initial_scores,
        "queue_assignments": queue_assignments,
        "algorithm_weights": algorithm_weights,
        "ticker_details": {
            ticker: {
                "name": data.name,
                "resonance_score": data.resonance_score,
                "signal_status": data.signal_status,
                "action": data.action,
                "algorithm_scores": {
                    algo_id: {
                        "score": algo_data.score,
                        "confidence": algo_data.confidence,
                        "hit": algo_data.hit
                    }
                    for algo_id, algo_data in data.algorithm_scores.items()
                }
            }
            for ticker, data in ticker_scores.items()
        }
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\\n✅ 测试完成!")
    print(f"   提取的数据已保存: {output_file}")
    
    return output_data

if __name__ == "__main__":
    test_adapter()