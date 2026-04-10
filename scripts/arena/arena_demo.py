#!/usr/bin/env python3
"""
演武场总控管理器演示
展示演武场完整工作流程，集成算法权重计算与队列分配
"""

import os
import sys
import json
import datetime
import numpy as np
from typing import Dict, List, Tuple, Optional, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入我们的模块
from scripts.arena.algorithm_weighter import AlgorithmWeighter, AlgorithmPerformance
from scripts.arena.data_adapter import ResonanceReportAdapter

class ArenaManagerDemo:
    """演武场管理器演示"""
    
    def __init__(self):
        """初始化管理器"""
        print("=" * 70)
        print("🏟️  琥珀引擎演武场总控管理器演示")
        print("=" * 70)
        
        # 初始化组件
        self.weighter = AlgorithmWeighter()
        self.adapter = ResonanceReportAdapter()
        
        # 模拟数据
        self.simulation_date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # 队列配置
        self.team1_threshold = 70.0  # 1队阈值
        self.team2_threshold = 60.0  # 2队阈值
        self.max_team1_size = 30     # 1队最大容量
        self.max_team2_size = 20     # 2队最大容量
        
        print(f"📅 演示日期: {self.simulation_date}")
        print(f"⚖️  队列阈值: 1队≥{self.team1_threshold}分, 2队≥{self.team2_threshold}分")
        print(f"📊 队列容量: 1队{self.max_team1_size}支, 2队{self.max_team2_size}支")
        print()
    
    def run_full_demo(self):
        """运行完整演示流程"""
        print("🚀 开始演武场完整演示流程")
        print("-" * 70)
        
        # 步骤1: 加载共振报告
        print("1️⃣  步骤1: 加载共振报告数据")
        if not self.adapter.load_report():
            print("   ⚠️  报告加载失败，使用模拟数据")
            ticker_scores = self.create_simulation_data()
        else:
            ticker_scores = self.adapter.extract_algorithm_scores()
            if not ticker_scores:
                print("   ⚠️  数据提取失败，使用模拟数据")
                ticker_scores = self.create_simulation_data()
        
        # 步骤2: 计算初始综合评分
        print("\\n2️⃣  步骤2: 计算标的初始综合评分")
        algorithm_weights = self.weighter.current_weights
        initial_scores = self.calculate_initial_scores(ticker_scores, algorithm_weights)
        
        # 打印评分结果
        print("   📊 标的评分结果:")
        for ticker, score in sorted(initial_scores.items(), key=lambda x: x[1], reverse=True):
            ticker_name = ticker_scores.get(ticker, {}).get("name", ticker) if isinstance(ticker_scores, dict) else ticker
            print(f"     {ticker} ({ticker_name}): {score:.2f}分")
        
        # 步骤3: 分配队列
        print("\\n3️⃣  步骤3: 分配演武场队列")
        queue_assignments = self.assign_queues(initial_scores)
        
        # 步骤4: 模拟每日绩效数据
        print("\\n4️⃣  步骤4: 生成算法绩效数据")
        daily_performances = self.create_daily_performance_data(ticker_scores, initial_scores)
        
        # 步骤5: 更新算法权重
        print("\\n5️⃣  步骤5: 动态更新算法权重")
        new_weights = self.weighter.update_weights(daily_performances, benchmark_return=0.005)
        
        # 步骤6: 显示最终结果
        print("\\n6️⃣  步骤6: 显示最终结果")
        self.display_final_results(queue_assignments, initial_scores, new_weights)
        
        print("\\n" + "=" * 70)
        print("🎉 演武场演示流程完成!")
        print("=" * 70)
    
    def create_simulation_data(self) -> Dict:
        """创建模拟数据"""
        print("   🎭 创建模拟数据 (10个标的, 11个算法)")
        
        tickers = [
            {"code": "000001", "name": "平安银行", "category": "金融"},
            {"code": "000002", "name": "万科A", "category": "房地产"},
            {"code": "000063", "name": "中兴通讯", "category": "通信"},
            {"code": "000858", "name": "五粮液", "category": "消费"},
            {"code": "002415", "name": "海康威视", "category": "科技"},
            {"code": "300750", "name": "宁德时代", "category": "新能源"},
            {"code": "600036", "name": "招商银行", "category": "金融"},
            {"code": "600519", "name": "贵州茅台", "category": "消费"},
            {"code": "601318", "name": "中国平安", "category": "保险"},
            {"code": "603259", "name": "药明康德", "category": "医药"}
        ]
        
        # 算法列表
        algorithms = [f"G{i+1}" for i in range(11)]
        
        ticker_scores = {}
        for ticker in tickers:
            code = ticker["code"]
            name = ticker["name"]
            
            # 为每个算法生成随机评分
            algo_scores = {}
            for algo_id in algorithms:
                # 生成基于正态分布的评分 (均值为60，标准差为15)
                base_score = np.random.normal(60, 15)
                score = max(0, min(100, base_score))  # 限制在0-100范围内
                
                algo_scores[algo_id] = {
                    "score": score,
                    "confidence": np.random.uniform(0.6, 0.9),
                    "hit": score > 70  # 评分>70视为命中
                }
            
            ticker_scores[code] = {
                "name": name,
                "category": ticker["category"],
                "algorithm_scores": algo_scores,
                "resonance_score": sum(s["score"] for s in algo_scores.values()) / len(algorithms)
            }
        
        print(f"     创建{len(ticker_scores)}个标的的模拟数据")
        return ticker_scores
    
    def calculate_initial_scores(self, ticker_scores: Dict, algorithm_weights: Dict[str, float]) -> Dict[str, float]:
        """计算初始综合评分 S_initial = Σ(G_i_score * G_i_weight)"""
        initial_scores = {}
        
        for ticker, ticker_data in ticker_scores.items():
            total_score = 0.0
            
            if "algorithm_scores" in ticker_data:
                for algo_id, algo_data in ticker_data["algorithm_scores"].items():
                    algo_weight = algorithm_weights.get(algo_id, 0.0)
                    algo_score = algo_data.get("score", 0.0)
                    
                    weighted_score = algo_score * algo_weight
                    total_score += weighted_score
            else:
                # 如果没有算法评分数据，使用随机值
                total_score = np.random.uniform(40, 80)
            
            initial_scores[ticker] = total_score
        
        return initial_scores
    
    def assign_queues(self, initial_scores: Dict[str, float]) -> Dict[str, List[str]]:
        """分配队列"""
        # 按评分降序排序
        sorted_tickers = sorted(
            initial_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        queue_assignments = {
            "team1": [],  # 演武场1队
            "team2": [],  # 演武场2队
            "observation": []  # 观察池
        }
        
        for ticker, score in sorted_tickers:
            if score >= self.team1_threshold and len(queue_assignments["team1"]) < self.max_team1_size:
                queue_assignments["team1"].append(ticker)
            elif score >= self.team2_threshold and len(queue_assignments["team2"]) < self.max_team2_size:
                queue_assignments["team2"].append(ticker)
            else:
                queue_assignments["observation"].append(ticker)
        
        return queue_assignments
    
    def create_daily_performance_data(self, ticker_scores: Dict, initial_scores: Dict[str, float]) -> Dict[str, AlgorithmPerformance]:
        """创建每日算法绩效数据"""
        daily_performances = {}
        
        # 算法列表
        algorithms = [f"G{i+1}" for i in range(11)]
        
        for algo_id in algorithms:
            # 收集该算法对所有标的的评分
            algo_scores = []
            
            for ticker, ticker_data in ticker_scores.items():
                if "algorithm_scores" in ticker_data and algo_id in ticker_data["algorithm_scores"]:
                    score = ticker_data["algorithm_scores"][algo_id].get("score", 0.0)
                    algo_scores.append(score)
            
            # 如果没有评分数据，使用随机值
            if not algo_scores:
                algo_scores = [np.random.uniform(40, 80) for _ in range(5)]
            
            # 计算平均评分并转换为预期收益率
            avg_score = sum(algo_scores) / len(algo_scores)
            
            # 模拟超额收益: 评分越高，预期超额收益越高
            # 这里使用简化映射: 评分100分对应5%日超额收益
            avg_excess_return = (avg_score / 100.0) * 0.05
            
            # 创建绩效对象
            perf = AlgorithmPerformance(
                algorithm_id=algo_id,
                algorithm_name=f"算法{algo_id}",
                date=self.simulation_date,
                daily_score=avg_score,
                recommended_tickers=list(ticker_scores.keys())[:3],  # 前3个标的
                ticker_returns={ticker: np.random.normal(0.001, 0.01) for ticker in list(ticker_scores.keys())[:3]},
                ticker_benchmark_returns={ticker: 0.005 for ticker in list(ticker_scores.keys())[:3]},
                avg_excess_return=avg_excess_return,
                performance_metric=((1 + avg_excess_return) ** 30) - 1,
                confidence=np.random.uniform(0.6, 0.9),
                is_enabled=True
            )
            
            daily_performances[algo_id] = perf
        
        return daily_performances
    
    def display_final_results(self, queue_assignments: Dict[str, List[str]], 
                            initial_scores: Dict[str, float], 
                            new_weights: Dict[str, float]):
        """显示最终结果"""
        print("\\n" + "=" * 70)
        print("📋 演武场最终结果摘要")
        print("=" * 70)
        
        # 显示队列分配
        print("\\n🏆 演武场队列分配:")
        print(f"   1队 ({self.team1_threshold}+分): {len(queue_assignments['team1'])}支")
        for i, ticker in enumerate(queue_assignments['team1'][:10], 1):
            score = initial_scores.get(ticker, 0)
            print(f"     {i:2d}. {ticker}: {score:.2f}分")
        
        if len(queue_assignments['team1']) > 10:
            print(f"     ... 还有{len(queue_assignments['team1']) - 10}支")
        
        print(f"\\n   2队 ({self.team2_threshold}+分): {len(queue_assignments['team2'])}支")
        for i, ticker in enumerate(queue_assignments['team2'][:10], 1):
            score = initial_scores.get(ticker, 0)
            print(f"     {i:2d}. {ticker}: {score:.2f}分")
        
        if len(queue_assignments['team2']) > 10:
            print(f"     ... 还有{len(queue_assignments['team2']) - 10}支")
        
        print(f"\\n   👁️  观察池: {len(queue_assignments['observation'])}支")
        
        # 显示算法权重变化
        print("\\n⚖️  算法权重动态调整结果:")
        print("   (权重变化反映算法近期表现)")
        
        # 获取算法名称映射
        algo_names = {
            "G1": "橡皮筋阈值",
            "G2": "双重动量", 
            "G3": "波动率挤压",
            "G4": "分红保护垫",
            "G5": "周线RSI",
            "G6": "Z分数偏离",
            "G7": "三重均线",
            "G8": "缩量回踩",
            "G9": "宏观黄金",
            "G10": "OBV背离",
            "G11": "基差计算"
        }
        
        # 按权重降序排序
        sorted_weights = sorted(
            new_weights.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        for algo_id, weight in sorted_weights:
            algo_name = algo_names.get(algo_id, algo_id)
            weight_pct = weight * 100
            
            # 添加性能指示器
            if weight_pct >= 15:
                indicator = "🚀"
            elif weight_pct >= 10:
                indicator = "📈"
            elif weight_pct >= 5:
                indicator = "📊"
            else:
                indicator = "📉"
            
            print(f"     {indicator} {algo_id} ({algo_name}): {weight_pct:.2f}%")
        
        # 显示资金分配
        print("\\n💰 资金分配计划:")
        team1_capital = len(queue_assignments['team1']) * 100000
        team2_capital = len(queue_assignments['team2']) * 50000
        total_capital = team1_capital + team2_capital
        
        print(f"   1队资金: {team1_capital:,}元 ({len(queue_assignments['team1'])}支 × 10万)")
        print(f"   2队资金: {team2_capital:,}元 ({len(queue_assignments['team2'])}支 × 5万)")
        print(f"   总占用资金: {total_capital:,}元")
        print(f"   现金储备: {max(0, 5000000 - total_capital):,}元 (总资金池500万)")
        
        # 保存结果
        self.save_results(queue_assignments, initial_scores, new_weights)
    
    def save_results(self, queue_assignments: Dict[str, List[str]], 
                    initial_scores: Dict[str, float], 
                    new_weights: Dict[str, float]):
        """保存演示结果"""
        results_dir = "database/arena/demo_results"
        os.makedirs(results_dir, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(results_dir, f"arena_demo_results_{timestamp}.json")
        
        results = {
            "simulation_date": self.simulation_date,
            "demo_timestamp": timestamp,
            "queue_thresholds": {
                "team1": self.team1_threshold,
                "team2": self.team2_threshold
            },
            "queue_assignments": queue_assignments,
            "initial_scores": initial_scores,
            "algorithm_weights": new_weights,
            "capital_allocation": {
                "team1_capital": len(queue_assignments['team1']) * 100000,
                "team2_capital": len(queue_assignments['team2']) * 50000,
                "total_allocated": len(queue_assignments['team1']) * 100000 + len(queue_assignments['team2']) * 50000,
                "total_pool": 5000000,
                "cash_reserve": 5000000 - (len(queue_assignments['team1']) * 100000 + len(queue_assignments['team2']) * 50000)
            },
            "metadata": {
                "generated_by": "ArenaManagerDemo",
                "version": "1.0.0",
                "note": "演示数据，包含模拟成分"
            }
        }
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\\n💾 演示结果已保存: {results_file}")

def main():
    """主函数"""
    demo = ArenaManagerDemo()
    demo.run_full_demo()

if __name__ == "__main__":
    main()