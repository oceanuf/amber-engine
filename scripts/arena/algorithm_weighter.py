#!/usr/bin/env python3
"""
演武场算法权重计算模块
实现G1-G11算法权重动态调整机制
符合演武场实施细则V1.1要求

核心特性：
1. EWMA指数加权移动平均 (α=0.1，半衰期约6.5天)
2. 算法表现度量：基于超额收益的绩效评估
3. 权重边界保护：1%-30%范围限制
4. Softmax归一化：防止分母为零溢出
5. 状态回滚能力：支持一键回滚到历史状态

@author: 工程师 Cheese 🧀
@version: V1.0.0
@date: 2026-04-07
@依据: 演武场实施细则V1.1 + 架构师Gemini审计反馈
"""

import os
import sys
import json
import math
import datetime
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict, field
import copy

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@dataclass
class AlgorithmPerformance:
    """算法绩效数据类"""
    algorithm_id: str  # G1, G2, ..., G11
    algorithm_name: str  # 算法名称
    date: str  # 绩效日期
    
    # 当日表现数据
    daily_score: float = 0.0  # 当日算法评分 (0-100)
    recommended_tickers: List[str] = field(default_factory=list)  # 推荐标的列表
    ticker_returns: Dict[str, float] = field(default_factory=dict)  # 标的收益率 {ticker: return}
    ticker_benchmark_returns: Dict[str, float] = field(default_factory=dict)  # 基准收益率
    
    # 计算得出的绩效指标
    avg_excess_return: float = 0.0  # 平均超额收益
    performance_metric: float = 0.0  # 绩效度量值 (1+avg_excess_return)^30 - 1
    weighted_performance: float = 0.0  # EWMA加权后的绩效
    
    # 权重相关
    raw_weight: float = 0.0  # 原始计算权重
    smoothed_weight: float = 0.0  # 平滑后权重
    final_weight: float = 0.0  # 最终归一化权重
    
    # 元数据
    confidence: float = 0.5  # 置信度 (0-1)
    is_enabled: bool = True  # 算法是否启用
    metadata: Dict = field(default_factory=dict)  # 额外元数据

@dataclass
class WeightHistory:
    """权重历史记录"""
    date: str
    algorithm_weights: Dict[str, float]  # {algorithm_id: weight}
    algorithm_performances: Dict[str, AlgorithmPerformance]  # {algorithm_id: performance}
    total_performance: float = 0.0  # 当日总绩效
    benchmark_return: float = 0.0  # 基准收益 (510300)
    notes: str = ""  # 备注

class AlgorithmWeighter:
    """算法权重计算引擎"""
    
    def __init__(self, 
                 config_path: str = "config/arena_algorithm_config.json",
                 history_path: str = "database/arena/algorithm_weights_history.json",
                 initial_weights_path: str = "config/strategy_weights.json"):
        """
        初始化权重计算引擎
        
        参数:
            config_path: 算法配置文件路径
            history_path: 权重历史记录路径
            initial_weights_path: 初始权重配置文件路径
        """
        self.config_path = config_path
        self.history_path = history_path
        self.initial_weights_path = initial_weights_path
        
        # 常量配置 (可覆盖)
        self.ALPHA = 0.1  # EWMA衰减因子，对应半衰期约6.5天
        self.MIN_WEIGHT = 0.01  # 最小权重 1%
        self.MAX_WEIGHT = 0.30  # 最大权重 30%
        self.WINDOW_SIZE = 30  # 绩效计算窗口 (天)
        self.SMOOTHING_FACTOR = 0.2  # 权重平滑因子 (0.2表示20%的新权重，80%的旧权重)
        
        # 算法定义 (G1-G11)
        self.algorithms = {
            "G1": {
                "name": "Gravity-Dip",
                "description": "橡皮筋阈值策略，捕捉价格回归机会",
                "enabled": True
            },
            "G2": {
                "name": "Dual-Momentum",
                "description": "双重动量策略，长期向上且短期强势",
                "enabled": True
            },
            "G3": {
                "name": "Vol-Squeeze", 
                "description": "波动率挤压策略，识别低波动潜伏期",
                "enabled": True
            },
            "G4": {
                "name": "Dividend-Alpha",
                "description": "分红保护垫策略，评估股息收益保护",
                "enabled": True
            },
            "G5": {
                "name": "Weekly-RSI",
                "description": "周线RSI超买超卖屏障，30/70规则，提供一票否决权",
                "enabled": True
            },
            "G6": {
                "name": "Z-Score-Bias",
                "description": "Z分数偏离策略，利用60日标准差寻找统计学极端错价回归",
                "enabled": True
            },
            "G7": {
                "name": "Triple-Cross",
                "description": "三重均线交叉策略，监测5/20/60/120四重均线的多头排列",
                "enabled": True
            },
            "G8": {
                "name": "Volume-Retracement",
                "description": "缩量回踩策略，识别波动率萎缩至50%以下且回踩均线不破",
                "enabled": True
            },
            "G9": {
                "name": "Macro-Gold",
                "description": "宏观对冲锚定策略，剥离名义金价中的利率杂质，分析实际利率对黄金的宏观影响",
                "enabled": True
            },
            "G10": {
                "name": "OBV-Divergence",
                "description": "能量潮背离策略，监测OBV指标背离，捕捉主力资金潜伏吸筹信号",
                "enabled": True
            },
            "G11": {
                "name": "Basis-Calculator",  # 假设G11是基差计算器
                "description": "基差计算策略，分析期货现货价差机会",
                "enabled": True
            }
        }
        
        # 状态数据
        self.current_weights = {}  # 当前权重 {algorithm_id: weight}
        self.weight_history = []  # 权重历史记录
        self.algorithm_performances = {}  # 算法绩效历史 {date: {algorithm_id: performance}}
        
        # 确保目录存在
        os.makedirs(os.path.dirname(self.history_path), exist_ok=True)
        
        # 加载配置和历史数据
        self.load_config()
        self.load_history()
        
        # 如果历史为空，初始化权重
        if not self.current_weights:
            self.initialize_weights()
    
    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 更新常量配置
                if "ewma_alpha" in config:
                    self.ALPHA = config["ewma_alpha"]
                if "min_weight" in config:
                    self.MIN_WEIGHT = config["min_weight"]
                if "max_weight" in config:
                    self.MAX_WEIGHT = config["max_weight"]
                if "window_size" in config:
                    self.WINDOW_SIZE = config["window_size"]
                if "smoothing_factor" in config:
                    self.SMOOTHING_FACTOR = config["smoothing_factor"]
                
                # 更新算法配置
                if "algorithms" in config:
                    for algo_id, algo_config in config["algorithms"].items():
                        if algo_id in self.algorithms:
                            self.algorithms[algo_id].update(algo_config)
                
                print(f"✅ 加载配置文件: {self.config_path}")
                return True
                
        except Exception as e:
            print(f"⚠️  配置文件加载失败，使用默认配置: {e}")
        
        return False
    
    def load_history(self):
        """加载权重历史数据"""
        try:
            if os.path.exists(self.history_path):
                with open(self.history_path, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)
                
                # 解析历史数据
                if "current_weights" in history_data:
                    self.current_weights = history_data["current_weights"]
                
                if "weight_history" in history_data:
                    # 这里简化处理，实际需要更复杂的反序列化
                    self.weight_history = history_data["weight_history"][-100:]  # 保留最近100条
                
                if "algorithm_performances" in history_data:
                    self.algorithm_performances = history_data["algorithm_performances"]
                
                print(f"✅ 加载权重历史: {self.history_path} ({len(self.weight_history)}条记录)")
                return True
                
        except Exception as e:
            print(f"⚠️  权重历史加载失败，重新初始化: {e}")
        
        return False
    
    def save_history(self):
        """保存权重历史数据"""
        try:
            history_data = {
                "metadata": {
                    "saved_at": datetime.datetime.now(
                        datetime.timezone(datetime.timedelta(hours=8))
                    ).isoformat(),
                    "version": "1.0.0",
                    "algorithm_count": len(self.algorithms),
                    "ewma_alpha": self.ALPHA,
                    "min_weight": self.MIN_WEIGHT,
                    "max_weight": self.MAX_WEIGHT
                },
                "current_weights": self.current_weights,
                "weight_history": self.weight_history[-100:],  # 保留最近100条
                "algorithm_performances": self.algorithm_performances
            }
            
            with open(self.history_path, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
            
            # 创建备份
            backup_dir = os.path.join(os.path.dirname(self.history_path), "backups")
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, f"algorithm_weights_backup_{timestamp}.json")
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 保存权重历史: {self.history_path} (备份: {backup_path})")
            return True
            
        except Exception as e:
            print(f"❌ 保存权重历史失败: {e}")
            return False
    
    def initialize_weights(self):
        """初始化算法权重 (等权重分配)"""
        print("🎯 初始化算法权重 (等权重分配)")
        
        enabled_algorithms = [algo_id for algo_id, algo in self.algorithms.items() if algo["enabled"]]
        initial_weight = 1.0 / len(enabled_algorithms) if enabled_algorithms else 0.0
        
        for algo_id in self.algorithms:
            if self.algorithms[algo_id]["enabled"]:
                self.current_weights[algo_id] = initial_weight
            else:
                self.current_weights[algo_id] = 0.0
        
        print(f"   已启用算法: {len(enabled_algorithms)}个")
        print(f"   初始权重: {initial_weight:.4f} 每个算法")
        
        # 保存初始化状态
        self.save_history()
    
    def calculate_excess_returns(self, 
                                ticker_returns: Dict[str, float],
                                benchmark_returns: Dict[str, float]) -> List[float]:
        """
        计算超额收益列表
        
        参数:
            ticker_returns: {标的代码: 收益率}
            benchmark_returns: {标的代码: 基准收益率}
            
        返回:
            超额收益列表
        """
        excess_returns = []
        
        for ticker, return_val in ticker_returns.items():
            if ticker in benchmark_returns:
                benchmark_return = benchmark_returns[ticker]
                excess_return = return_val - benchmark_return
                excess_returns.append(excess_return)
            else:
                # 如果没有基准数据，使用默认值
                excess_returns.append(return_val - 0.0)  # 假设基准收益为0
        
        return excess_returns
    
    def calculate_performance_metric(self, excess_returns: List[float]) -> float:
        """
        计算算法绩效度量值
        
        公式: performance = (1 + avg_excess_return)^30 - 1
        
        参数:
            excess_returns: 超额收益列表
            
        返回:
            绩效度量值
        """
        if not excess_returns:
            return 0.0
        
        # 计算平均超额收益
        avg_excess_return = sum(excess_returns) / len(excess_returns)
        
        # 计算绩效度量值
        # 使用30次方是因为窗口大小是30天
        performance = math.pow(1 + avg_excess_return, self.WINDOW_SIZE) - 1
        
        return performance
    
    def apply_ewma_smoothing(self, 
                           current_performance: float, 
                           previous_weighted_performance: float) -> float:
        """
        应用EWMA指数加权移动平均平滑
        
        公式: weighted_performance = α * current_performance + (1-α) * previous_weighted_performance
        
        参数:
            current_performance: 当前绩效
            previous_weighted_performance: 之前加权绩效
            
        返回:
            加权后的绩效
        """
        weighted_performance = (
            self.ALPHA * current_performance + 
            (1 - self.ALPHA) * previous_weighted_performance
        )
        
        return weighted_performance
    
    def calculate_raw_weights(self, weighted_performances: Dict[str, float]) -> Dict[str, float]:
        """
        计算原始权重
        
        参数:
            weighted_performances: {算法ID: 加权绩效}
            
        返回:
            {算法ID: 原始权重}
        """
        # 检查是否所有绩效都为负或零
        all_non_positive = all(perf <= 0 for perf in weighted_performances.values())
        
        if all_non_positive:
            print("⚠️  所有算法绩效都为非正数，使用Softmax处理")
            return self.softmax_weights(weighted_performances)
        
        # 正常情况：使用绩效比例作为权重
        total_performance = sum(weighted_performances.values())
        
        if total_performance <= 0:
            print("⚠️  总绩效为零或负数，使用等权重分配")
            return self.equal_weights(list(weighted_performances.keys()))
        
        # 计算原始权重
        raw_weights = {}
        for algo_id, performance in weighted_performances.items():
            raw_weights[algo_id] = performance / total_performance
        
        return raw_weights
    
    def softmax_weights(self, performances: Dict[str, float]) -> Dict[str, float]:
        """
        使用Softmax函数计算权重 (防止分母为零)
        
        参数:
            performances: {算法ID: 绩效值}
            
        返回:
            {算法ID: Softmax权重}
        """
        # 将绩效值转换为logits (确保数值稳定)
        logits = list(performances.values())
        
        # 如果所有值都是负数，先平移使其最大值为0
        if max(logits) < 0:
            logits = [x - max(logits) for x in logits]
        
        # 计算Softmax
        exp_logits = [math.exp(x) for x in logits]
        sum_exp = sum(exp_logits)
        
        if sum_exp == 0:
            # 极端情况：所有exp都下溢为0，使用等权重
            return self.equal_weights(list(performances.keys()))
        
        softmax_probs = [exp / sum_exp for exp in exp_logits]
        
        # 转换为字典
        raw_weights = {}
        for i, algo_id in enumerate(performances.keys()):
            raw_weights[algo_id] = softmax_probs[i]
        
        return raw_weights
    
    def equal_weights(self, algorithm_ids: List[str]) -> Dict[str, float]:
        """等权重分配"""
        weight = 1.0 / len(algorithm_ids) if algorithm_ids else 0.0
        return {algo_id: weight for algo_id in algorithm_ids}
    
    def apply_weight_bounds(self, raw_weights: Dict[str, float]) -> Dict[str, float]:
        """
        应用权重边界限制 (1%-30%)
        
        参数:
            raw_weights: 原始权重
            
        返回:
            边界限制后的权重
        """
        bounded_weights = {}
        
        for algo_id, weight in raw_weights.items():
            # 应用上下界
            bounded_weight = max(self.MIN_WEIGHT, min(self.MAX_WEIGHT, weight))
            bounded_weights[algo_id] = bounded_weight
        
        # 重新归一化
        total_bounded = sum(bounded_weights.values())
        if total_bounded > 0:
            normalized_weights = {
                algo_id: weight / total_bounded 
                for algo_id, weight in bounded_weights.items()
            }
        else:
            # 极端情况：使用等权重
            normalized_weights = self.equal_weights(list(raw_weights.keys()))
        
        return normalized_weights
    
    def smooth_weights(self, 
                      new_raw_weights: Dict[str, float], 
                      previous_weights: Dict[str, float]) -> Dict[str, float]:
        """
        平滑权重更新 (防止剧烈波动)
        
        公式: weight(t) = 0.8 * weight(t-1) + 0.2 * raw_weight(t)
        
        参数:
            new_raw_weights: 新计算的原始权重
            previous_weights: 之前的权重
            
        返回:
            平滑后的权重
        """
        smoothed_weights = {}
        
        for algo_id in new_raw_weights:
            new_weight = new_raw_weights[algo_id]
            prev_weight = previous_weights.get(algo_id, new_weight)
            
            smoothed_weight = (
                (1 - self.SMOOTHING_FACTOR) * prev_weight + 
                self.SMOOTHING_FACTOR * new_weight
            )
            smoothed_weights[algo_id] = smoothed_weight
        
        return smoothed_weights
    
    def normalize_weights(self, weights: Dict[str, float]) -> Dict[str, float]:
        """权重归一化 (确保和为1)"""
        total = sum(weights.values())
        
        if total == 0:
            return self.equal_weights(list(weights.keys()))
        
        normalized = {algo_id: weight / total for algo_id, weight in weights.items()}
        return normalized
    
    def update_weights(self, 
                      daily_performances: Dict[str, AlgorithmPerformance],
                      benchmark_return: float = 0.0) -> Dict[str, float]:
        """
        更新算法权重 (主函数)
        
        参数:
            daily_performances: 当日算法绩效数据
            benchmark_return: 当日基准收益率
            
        返回:
            更新后的权重 {算法ID: 权重}
        """
        print("=" * 60)
        print("🏆 开始更新算法权重")
        print("=" * 60)
        
        current_date = datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=8))
        ).strftime("%Y-%m-%d")
        
        print(f"📅 更新日期: {current_date}")
        print(f"📊 基准收益: {benchmark_return:.4f}")
        print(f"🔢 处理算法: {len(daily_performances)}个")
        
        # 步骤1: 计算每个算法的加权绩效 (EWMA)
        weighted_performances = {}
        
        for algo_id, performance in daily_performances.items():
            if not self.algorithms[algo_id]["enabled"]:
                print(f"   ⏭️  算法 {algo_id} 已禁用，跳过")
                continue
            
            # 获取历史加权绩效 (如果存在)
            previous_weighted_perf = 0.0
            if current_date in self.algorithm_performances:
                prev_perf = self.algorithm_performances[current_date].get(algo_id)
                if prev_perf:
                    previous_weighted_perf = prev_perf.get("weighted_performance", 0.0)
            
            # 计算当前绩效
            current_perf = performance.performance_metric
            
            # 应用EWMA平滑
            weighted_perf = self.apply_ewma_smoothing(current_perf, previous_weighted_perf)
            weighted_performances[algo_id] = weighted_perf
            
            # 更新绩效数据
            performance.weighted_performance = weighted_perf
            
            print(f"   📈 算法 {algo_id}: 当前绩效={current_perf:.6f}, 加权绩效={weighted_perf:.6f}")
        
        # 步骤2: 计算原始权重
        print("\\n📊 计算原始权重...")
        raw_weights = self.calculate_raw_weights(weighted_performances)
        
        for algo_id, weight in raw_weights.items():
            if algo_id in daily_performances:
                daily_performances[algo_id].raw_weight = weight
            print(f"   ⚖️  算法 {algo_id}: 原始权重={weight:.6f}")
        
        # 步骤3: 应用权重边界
        print("\\n🛡️  应用权重边界 (1%-30%)...")
        bounded_weights = self.apply_weight_bounds(raw_weights)
        
        for algo_id, weight in bounded_weights.items():
            if algo_id in daily_performances:
                daily_performances[algo_id].smoothed_weight = weight
            print(f"   🔒 算法 {algo_id}: 边界后权重={weight:.6f}")
        
        # 步骤4: 平滑权重 (防止剧烈波动)
        print("\\n🌀 平滑权重更新...")
        smoothed_weights = self.smooth_weights(bounded_weights, self.current_weights)
        
        for algo_id, weight in smoothed_weights.items():
            print(f"   📉 算法 {algo_id}: 平滑后权重={weight:.6f}")
        
        # 步骤5: 归一化权重
        print("\\n🔢 归一化权重...")
        final_weights = self.normalize_weights(smoothed_weights)
        
        for algo_id, weight in final_weights.items():
            if algo_id in daily_performances:
                daily_performances[algo_id].final_weight = weight
            print(f"   ✅ 算法 {algo_id}: 最终权重={weight:.6f}")
        
        # 步骤6: 更新当前权重
        self.current_weights = final_weights
        
        # 步骤7: 保存历史记录
        history_entry = {
            "date": current_date,
            "algorithm_weights": final_weights,
            "algorithm_performances": {
                algo_id: asdict(perf) 
                for algo_id, perf in daily_performances.items()
            },
            "total_performance": sum(weighted_performances.values()),
            "benchmark_return": benchmark_return,
            "notes": f"权重更新完成，处理{len(daily_performances)}个算法"
        }
        
        self.weight_history.append(history_entry)
        
        # 保存算法绩效数据
        if current_date not in self.algorithm_performances:
            self.algorithm_performances[current_date] = {}
        
        for algo_id, perf in daily_performances.items():
            self.algorithm_performances[current_date][algo_id] = asdict(perf)
        
        # 保存到文件
        self.save_history()
        
        print("\\n" + "=" * 60)
        print(f"🎉 权重更新完成! 日期: {current_date}")
        print(f"   处理算法: {len(daily_performances)}个")
        print(f"   总加权绩效: {sum(weighted_performances.values()):.6f}")
        print(f"   权重保存到: {self.history_path}")
        print("=" * 60)
        
        return final_weights
    
    def rollback_to_date(self, target_date: str) -> bool:
        """
        回滚到指定日期的权重状态
        
        参数:
            target_date: 目标日期 (YYYY-MM-DD)
            
        返回:
            是否成功
        """
        print(f"🔄 尝试回滚到日期: {target_date}")
        
        # 查找目标日期的历史记录
        target_entry = None
        for entry in reversed(self.weight_history):
            if entry["date"] == target_date:
                target_entry = entry
                break
        
        if not target_entry:
            print(f"❌ 未找到目标日期的权重记录: {target_date}")
            return False
        
        # 回滚权重
        self.current_weights = target_entry["algorithm_weights"]
        
        # 过滤历史记录，保留到目标日期为止
        self.weight_history = [entry for entry in self.weight_history if entry["date"] <= target_date]
        
        # 过滤算法绩效数据
        dates_to_keep = [entry["date"] for entry in self.weight_history]
        self.algorithm_performances = {
            date: perfs 
            for date, perfs in self.algorithm_performances.items() 
            if date in dates_to_keep
        }
        
        # 保存回滚后的状态
        self.save_history()
        
        print(f"✅ 成功回滚到日期: {target_date}")
        print(f"   回滚后权重: {self.current_weights}")
        
        return True
    
    def get_weight_summary(self) -> Dict:
        """获取权重摘要"""
        enabled_algorithms = [
            algo_id for algo_id, algo in self.algorithms.items() 
            if algo["enabled"]
        ]
        
        summary = {
            "total_algorithms": len(self.algorithms),
            "enabled_algorithms": len(enabled_algorithms),
            "disabled_algorithms": len(self.algorithms) - len(enabled_algorithms),
            "current_weights": self.current_weights,
            "weight_range": {
                "min": self.MIN_WEIGHT,
                "max": self.MAX_WEIGHT
            },
            "ewma_alpha": self.ALPHA,
            "history_count": len(self.weight_history),
            "last_updated": self.weight_history[-1]["date"] if self.weight_history else "N/A"
        }
        
        return summary
    
    def print_weight_summary(self):
        """打印权重摘要"""
        summary = self.get_weight_summary()
        
        print("=" * 60)
        print("📊 算法权重摘要")
        print("=" * 60)
        
        print(f"算法总数: {summary['total_algorithms']}")
        print(f"已启用: {summary['enabled_algorithms']}")
        print(f"已禁用: {summary['disabled_algorithms']}")
        print(f"权重范围: {summary['weight_range']['min']*100:.1f}% - {summary['weight_range']['max']*100:.1f}%")
        print(f"EWMA Alpha: {summary['ewma_alpha']} (半衰期约{math.log(0.5)/math.log(1-summary['ewma_alpha']):.1f}天)")
        print(f"历史记录: {summary['history_count']}条")
        print(f"最后更新: {summary['last_updated']}")
        
        print("\\n📈 当前权重分布:")
        print("-" * 40)
        
        sorted_weights = sorted(
            summary['current_weights'].items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        for algo_id, weight in sorted_weights:
            algo_name = self.algorithms[algo_id]["name"]
            print(f"  {algo_id} ({algo_name}): {weight*100:.2f}%")
        
        print("=" * 60)

# 测试函数
def test_algorithm_weighter():
    """测试算法权重计算引擎"""
    print("🧪 开始测试算法权重计算引擎...")
    
    # 初始化引擎
    weighter = AlgorithmWeighter()
    
    # 打印初始权重
    weighter.print_weight_summary()
    
    # 创建模拟的每日绩效数据
    print("\\n📊 创建模拟绩效数据...")
    
    daily_performances = {}
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # 为每个算法创建模拟数据
    for algo_id in weighter.algorithms:
        if weighter.algorithms[algo_id]["enabled"]:
            # 模拟超额收益 (正态分布，均值为0.001，标准差为0.005)
            excess_returns = np.random.normal(0.001, 0.005, 10).tolist()
            
            # 计算绩效度量
            avg_excess_return = sum(excess_returns) / len(excess_returns)
            performance_metric = math.pow(1 + avg_excess_return, 30) - 1
            
            # 创建绩效对象
            perf = AlgorithmPerformance(
                algorithm_id=algo_id,
                algorithm_name=weighter.algorithms[algo_id]["name"],
                date=current_date,
                daily_score=np.random.randint(50, 95),
                recommended_tickers=["000001", "000002", "000003"],
                ticker_returns={"000001": 0.01, "000002": 0.02, "000003": -0.01},
                ticker_benchmark_returns={"000001": 0.005, "000002": 0.008, "000003": -0.005},
                avg_excess_return=avg_excess_return,
                performance_metric=performance_metric,
                confidence=np.random.uniform(0.6, 0.9)
            )
            
            daily_performances[algo_id] = perf
            
            print(f"   {algo_id}: 平均超额收益={avg_excess_return:.6f}, 绩效度量={performance_metric:.6f}")
    
    # 更新权重
    print("\\n⚖️  更新算法权重...")
    new_weights = weighter.update_weights(daily_performances, benchmark_return=0.005)
    
    # 打印更新后的权重摘要
    print("\\n📊 更新后的权重摘要:")
    weighter.print_weight_summary()
    
    # 测试回滚功能
    print("\\n🔄 测试回滚功能...")
    weighter.rollback_to_date(current_date)
    
    print("\\n✅ 测试完成!")

if __name__ == "__main__":
    test_algorithm_weighter()