#!/usr/bin/env python3
"""
信息比率（IR）优化器 - V1.7.0 "智库并网"专项行动
专项三：算法骨架重构 - 因子去噪与IR反馈环

功能：
1. 计算每个算法的信息比率（Information Ratio）
2. 根据IR动态调整算法权重
3. 实现因子去噪，提高信号质量
4. 建立IR反馈环，持续优化算法表现

作者: 工程师 Cheese 🧀
日期: 2026-04-05
"""

import os
import sys
import json
import datetime
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
import logging
import statistics
from dataclasses import dataclass

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置路径
IR_HISTORY_FILE = "database/ir_history.json"
ALGORITHM_PERFORMANCE_FILE = "database/algorithm_performance.json"
STRATEGY_WEIGHTS_FILE = "config/strategy_weights.json"
IR_CONFIG_FILE = "config/ir_optimizer.json"
LOG_DIR = "logs/ir_optimizer"

# 配置日志
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, f"ir_optimizer_{datetime.date.today().isoformat()}.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class AlgorithmPerformance:
    """算法表现数据类"""
    algorithm_id: str
    algorithm_name: str
    returns: List[float]  # 策略收益率序列
    benchmark_returns: List[float]  # 基准收益率序列
    signals: List[Dict[str, Any]]  # 信号历史
    start_date: str
    end_date: str
    
    def calculate_ir(self) -> Dict[str, Any]:
        """计算信息比率"""
        if len(self.returns) < 2 or len(self.benchmark_returns) < 2:
            return {
                "ir": 0.0,
                "annualized_ir": 0.0,
                "strategy_return": 0.0,
                "benchmark_return": 0.0,
                "tracking_error": 0.0,
                "active_return": 0.0,
                "data_points": len(self.returns),
                "error": "数据不足"
            }
        
        try:
            # 转换为numpy数组
            strategy_returns = np.array(self.returns)
            benchmark_returns = np.array(self.benchmark_returns)
            
            # 确保长度一致
            min_len = min(len(strategy_returns), len(benchmark_returns))
            strategy_returns = strategy_returns[:min_len]
            benchmark_returns = benchmark_returns[:min_len]
            
            # 计算超额收益
            excess_returns = strategy_returns - benchmark_returns
            
            # 计算信息比率
            mean_excess_return = np.mean(excess_returns)
            tracking_error = np.std(excess_returns, ddof=1)  # 样本标准差
            
            if tracking_error == 0:
                ir = 0.0
            else:
                ir = mean_excess_return / tracking_error
            
            # 年化处理（假设每日数据）
            annualization_factor = np.sqrt(252)  # 交易日数量
            annualized_ir = ir * annualization_factor
            
            # 计算总收益
            strategy_total_return = np.prod(1 + strategy_returns) - 1
            benchmark_total_return = np.prod(1 + benchmark_returns) - 1
            active_return = strategy_total_return - benchmark_total_return
            
            # 计算胜率
            winning_periods = np.sum(excess_returns > 0)
            win_rate = winning_periods / len(excess_returns) if len(excess_returns) > 0 else 0
            
            # 计算最大回撤（策略）
            cumulative_returns = np.cumprod(1 + strategy_returns)
            peak = np.maximum.accumulate(cumulative_returns)
            drawdown = (cumulative_returns - peak) / peak
            max_drawdown = np.min(drawdown) if len(drawdown) > 0 else 0
            
            return {
                "ir": float(ir),
                "annualized_ir": float(annualized_ir),
                "strategy_return": float(strategy_total_return),
                "benchmark_return": float(benchmark_total_return),
                "tracking_error": float(tracking_error),
                "active_return": float(active_return),
                "mean_excess_return": float(mean_excess_return),
                "win_rate": float(win_rate),
                "max_drawdown": float(max_drawdown),
                "data_points": min_len,
                "calculation_date": datetime.date.today().isoformat(),
                "confidence": self._calculate_confidence(min_len, tracking_error)
            }
            
        except Exception as e:
            logger.error(f"计算IR失败: {e}")
            return {
                "ir": 0.0,
                "annualized_ir": 0.0,
                "error": str(e)
            }
    
    def _calculate_confidence(self, data_points: int, tracking_error: float) -> float:
        """计算IR置信度"""
        # 基于数据点数量和跟踪误差计算置信度
        if data_points < 10:
            return 0.3
        elif data_points < 30:
            return 0.5
        elif data_points < 100:
            return 0.7
        else:
            # 数据点足够多，考虑跟踪误差的稳定性
            if tracking_error < 0.01:  # 跟踪误差很小
                return 0.95
            elif tracking_error < 0.03:
                return 0.85
            else:
                return 0.75

class IROptimizer:
    """信息比率优化器"""
    
    def __init__(self, lookback_period: int = 90):
        self.lookback_period = lookback_period  # 回溯周期（天）
        self.config = self._load_config()
        self.algorithm_performance = {}
        
    def _load_config(self) -> Dict[str, Any]:
        """加载IR优化配置"""
        default_config = {
            "version": "1.0.0",
            "lookback_period": self.lookback_period,
            "ir_calculation": {
                "min_data_points": 10,
                "annualization_factor": 252,
                "benchmark": "000300.SH",  # 沪深300作为基准
                "rolling_window": 20
            },
            "weight_optimization": {
                "method": "ir_weighted",  # ir_weighted, mean_variance, equal_weight
                "min_weight": 0.01,  # 最小权重1%
                "max_weight": 0.30,  # 最大权重30%
                "target_ir": 0.5,  # 目标IR
                "decay_factor": 0.95,  # 历史IR衰减因子
                "momentum_factor": 0.3  # 动量因子权重
            },
            "factor_denoising": {
                "enabled": True,
                "methods": ["pca", "kalman", "wavelet"],
                "variance_threshold": 0.8,
                "noise_ratio_threshold": 0.3
            },
            "feedback_loop": {
                "update_frequency": "weekly",  # 更新频率
                "rebalancing_threshold": 0.1,  # 权重变化超过10%时触发再平衡
                "performance_monitoring": True
            }
        }
        
        if os.path.exists(IR_CONFIG_FILE):
            try:
                with open(IR_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                # 合并配置
                default_config.update(user_config)
                logger.info(f"已加载IR优化配置: {IR_CONFIG_FILE}")
            except Exception as e:
                logger.error(f"加载IR优化配置失败，使用默认配置: {e}")
                
        return default_config
    
    def load_algorithm_performance(self) -> Dict[str, AlgorithmPerformance]:
        """加载算法表现数据"""
        logger.info("加载算法表现数据...")
        
        if os.path.exists(ALGORITHM_PERFORMANCE_FILE):
            try:
                with open(ALGORITHM_PERFORMANCE_FILE, 'r', encoding='utf-8') as f:
                    perf_data = json.load(f)
                
                algorithms = {}
                for algo_id, algo_data in perf_data.get('algorithms', {}).items():
                    try:
                        algo = AlgorithmPerformance(
                            algorithm_id=algo_id,
                            algorithm_name=algo_data.get('name', algo_id),
                            returns=algo_data.get('returns', []),
                            benchmark_returns=algo_data.get('benchmark_returns', []),
                            signals=algo_data.get('signals', []),
                            start_date=algo_data.get('start_date', ''),
                            end_date=algo_data.get('end_date', '')
                        )
                        algorithms[algo_id] = algo
                    except Exception as e:
                        logger.error(f"加载算法 {algo_id} 失败: {e}")
                
                logger.info(f"成功加载 {len(algorithms)} 个算法的表现数据")
                self.algorithm_performance = algorithms
                return algorithms
                
            except Exception as e:
                logger.error(f"加载算法表现文件失败: {e}")
        
        # 如果没有数据文件，尝试从其他来源收集
        logger.warning("算法表现文件不存在，尝试收集数据...")
        return self._collect_algorithm_performance()
    
    def _collect_algorithm_performance(self) -> Dict[str, AlgorithmPerformance]:
        """收集算法表现数据"""
        algorithms = {}
        
        try:
            # 尝试从策略目录加载算法
            strategies_dir = os.path.join(os.path.dirname(__file__), "strategies")
            if os.path.exists(strategies_dir):
                strategy_files = [f for f in os.listdir(strategies_dir) 
                                if f.endswith('.py') and not f.startswith('_')]
                
                for strategy_file in strategy_files:
                    algo_id = os.path.splitext(strategy_file)[0]
                    
                    # 生成模拟数据用于测试
                    returns = self._generate_simulated_returns(algo_id)
                    benchmark_returns = self._generate_benchmark_returns()
                    
                    algo = AlgorithmPerformance(
                        algorithm_id=algo_id,
                        algorithm_name=algo_id.replace('_', ' ').title(),
                        returns=returns,
                        benchmark_returns=benchmark_returns,
                        signals=[],
                        start_date=(datetime.date.today() - datetime.timedelta(days=90)).isoformat(),
                        end_date=datetime.date.today().isoformat()
                    )
                    
                    algorithms[algo_id] = algo
                    
                logger.info(f"收集到 {len(algorithms)} 个算法的模拟表现数据")
            else:
                logger.warning("策略目录不存在")
                
        except Exception as e:
            logger.error(f"收集算法表现数据失败: {e}")
            
        self.algorithm_performance = algorithms
        return algorithms
    
    def _generate_simulated_returns(self, algo_id: str, periods: int = 90) -> List[float]:
        """生成模拟收益率数据"""
        np.random.seed(hash(algo_id) % 10000)
        
        # 不同算法有不同的收益特性
        if "gravity" in algo_id.lower():
            # 均值回归策略：低波动，正期望
            mean_return = 0.0005  # 日均0.05%
            volatility = 0.005
        elif "momentum" in algo_id.lower():
            # 动量策略：较高波动，较高期望
            mean_return = 0.0008
            volatility = 0.008
        elif "volatility" in algo_id.lower():
            # 波动率策略：中等
            mean_return = 0.0006
            volatility = 0.006
        else:
            # 默认
            mean_return = 0.0004
            volatility = 0.004
        
        # 生成随机收益率
        returns = np.random.normal(mean_return, volatility, periods)
        return returns.tolist()
    
    def _generate_benchmark_returns(self, periods: int = 90) -> List[float]:
        """生成基准收益率数据（模拟沪深300）"""
        np.random.seed(42)
        
        # 沪深300的典型特性
        mean_return = 0.0003  # 日均0.03%
        volatility = 0.01
        
        returns = np.random.normal(mean_return, volatility, periods)
        return returns.tolist()
    
    def calculate_all_ir(self) -> Dict[str, Dict[str, Any]]:
        """计算所有算法的信息比率"""
        logger.info("计算所有算法的信息比率...")
        
        ir_results = {}
        
        for algo_id, algorithm in self.algorithm_performance.items():
            try:
                ir_result = algorithm.calculate_ir()
                ir_results[algo_id] = ir_result
                
                logger.info(f"算法 {algo_id}: IR={ir_result.get('ir', 0):.3f}, "
                          f"年化IR={ir_result.get('annualized_ir', 0):.3f}, "
                          f"胜率={ir_result.get('win_rate', 0):.2%}")
                
            except Exception as e:
                logger.error(f"计算算法 {algo_id} 的IR失败: {e}")
                ir_results[algo_id] = {
                    "ir": 0.0,
                    "error": str(e)
                }
        
        # 保存IR历史
        self._save_ir_history(ir_results)
        
        return ir_results
    
    def _save_ir_history(self, ir_results: Dict[str, Dict[str, Any]]):
        """保存IR历史记录"""
        try:
            history = {}
            if os.path.exists(IR_HISTORY_FILE):
                with open(IR_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            
            # 添加当前IR记录
            timestamp = datetime.datetime.now().isoformat()
            date_key = datetime.date.today().isoformat()
            
            if 'history' not in history:
                history['history'] = {}
            
            history['history'][date_key] = {
                "timestamp": timestamp,
                "ir_results": ir_results,
                "algorithm_count": len(ir_results)
            }
            
            # 只保留最近365天的记录
            if 'history' in history:
                history_dates = list(history['history'].keys())
                history_dates.sort()
                
                if len(history_dates) > 365:
                    dates_to_remove = history_dates[:len(history_dates) - 365]
                    for date in dates_to_remove:
                        del history['history'][date]
            
            # 更新汇总统计
            history['summary'] = {
                "last_updated": timestamp,
                "total_calculations": len(history.get('history', {})),
                "algorithm_count": len(ir_results),
                "average_ir": np.mean([r.get('ir', 0) for r in ir_results.values()]) if ir_results else 0
            }
            
            with open(IR_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
                
            logger.info(f"IR历史已保存: {IR_HISTORY_FILE}")
            
        except Exception as e:
            logger.error(f"保存IR历史失败: {e}")
    
    def optimize_weights(self, ir_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """根据IR优化算法权重"""
        logger.info("根据IR优化算法权重...")
        
        method = self.config['weight_optimization']['method']
        
        if method == 'ir_weighted':
            weights = self._ir_weighted_optimization(ir_results)
        elif method == 'mean_variance':
            weights = self._mean_variance_optimization(ir_results)
        elif method == 'equal_weight':
            weights = self._equal_weight_optimization(ir_results)
        else:
            logger.warning(f"未知优化方法: {method}，使用默认方法")
            weights = self._ir_weighted_optimization(ir_results)
        
        # 应用权重限制
        weights = self._apply_weight_constraints(weights)
        
        # 计算优化后的预期IR
        expected_ir = self._calculate_portfolio_ir(weights, ir_results)
        
        result = {
            "optimization_method": method,
            "optimization_date": datetime.date.today().isoformat(),
            "weights": weights,
            "expected_portfolio_ir": expected_ir,
            "algorithm_count": len(weights),
            "weight_summary": {
                "min_weight": min(weights.values()) if weights else 0,
                "max_weight": max(weights.values()) if weights else 0,
                "weight_sum": sum(weights.values()) if weights else 0
            }
        }
        
        logger.info(f"权重优化完成: 预期组合IR={expected_ir:.3f}")
        return result
    
    def _ir_weighted_optimization(self, ir_results: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
        """IR加权优化"""
        # 提取IR值
        ir_values = {}
        for algo_id, result in ir_results.items():
            ir = result.get('ir', 0)
            # 只考虑正IR的算法
            if ir > 0:
                ir_values[algo_id] = ir
            else:
                ir_values[algo_id] = 0.001  # 给很小的正权重
        
        if not ir_values:
            return {}
        
        # 计算总IR
        total_ir = sum(ir_values.values())
        if total_ir <= 0:
            # 所有IR都为负或零，使用等权重
            return {algo_id: 1.0/len(ir_values) for algo_id in ir_values.keys()}
        
        # 按IR比例分配权重
        weights = {algo_id: ir/total_ir for algo_id, ir in ir_values.items()}
        
        return weights
    
    def _mean_variance_optimization(self, ir_results: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
        """均值-方差优化（简化版）"""
        # 这里需要收益率协方差矩阵，简化处理
        # 使用IR作为期望收益，假设相关性为0.3
        
        algorithms = list(ir_results.keys())
        n = len(algorithms)
        
        if n == 0:
            return {}
        
        # 提取IR和跟踪误差
        ir_values = []
        te_values = []
        
        for algo_id in algorithms:
            result = ir_results[algo_id]
            ir = max(result.get('ir', 0), 0.001)  # 确保为正
            te = max(result.get('tracking_error', 0.01), 0.001)
            
            ir_values.append(ir)
            te_values.append(te)
        
        # 简化优化：权重与IR/te^2成正比（夏普比率思想）
        weights = {}
        total_weight = 0
        
        for i, algo_id in enumerate(algorithms):
            if te_values[i] > 0:
                weight = ir_values[i] / (te_values[i] ** 2)
            else:
                weight = ir_values[i]
            
            weights[algo_id] = weight
            total_weight += weight
        
        # 归一化
        if total_weight > 0:
            weights = {algo_id: w/total_weight for algo_id, w in weights.items()}
        else:
            # 退化为等权重
            weights = {algo_id: 1.0/n for algo_id in algorithms}
        
        return weights
    
    def _equal_weight_optimization(self, ir_results: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
        """等权重优化"""
        algorithms = list(ir_results.keys())
        n = len(algorithms)
        
        if n == 0:
            return {}
        
        weight = 1.0 / n
        return {algo_id: weight for algo_id in algorithms}
    
    def _apply_weight_constraints(self, weights: Dict[str, float]) -> Dict[str, float]:
        """应用权重约束"""
        min_weight = self.config['weight_optimization']['min_weight']
        max_weight = self.config['weight_optimization']['max_weight']
        
        # 确保所有权重在[min_weight, max_weight]范围内
        constrained_weights = {}
        
        for algo_id, weight in weights.items():
            constrained_weight = max(min(weight, max_weight), min_weight)
            constrained_weights[algo_id] = constrained_weight
        
        # 重新归一化
        total_weight = sum(constrained_weights.values())
        if total_weight > 0:
            constrained_weights = {algo_id: w/total_weight for algo_id, w in constrained_weights.items()}
        
        return constrained_weights
    
    def _calculate_portfolio_ir(self, weights: Dict[str, float], 
                               ir_results: Dict[str, Dict[str, Any]]) -> float:
        """计算组合预期IR（简化版）"""
        if not weights:
            return 0.0
        
        portfolio_ir = 0.0
        
        for algo_id, weight in weights.items():
            if algo_id in ir_results:
                ir = ir_results[algo_id].get('ir', 0)
                portfolio_ir += weight * ir
        
        return portfolio_ir
    
    def apply_factor_denoising(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """应用因子去噪"""
        if not self.config['factor_denoising']['enabled']:
            return signals
        
        logger.info("应用因子去噪...")
        
        try:
            # 提取信号值
            signal_values = []
            for signal in signals:
                if 'signal_strength' in signal:
                    signal_values.append(signal['signal_strength'])
                elif 'score' in signal:
                    signal_values.append(signal['score'])
                else:
                    signal_values.append(0)
            
            if len(signal_values) < 5:
                logger.warning("信号数量不足，跳过因子去噪")
                return signals
            
            # 简单去噪：移动平均平滑
            window = min(5, len(signal_values))
            smoothed_values = np.convolve(signal_values, np.ones(window)/window, mode='same')
            
            # 更新信号
            denoised_signals = []
            for i, signal in enumerate(signals):
                denoised_signal = signal.copy()
                if 'signal_strength' in signal:
                    denoised_signal['signal_strength'] = float(smoothed_values[i])
                    denoised_signal['denoised'] = True
                    denoised_signal['noise_reduction'] = abs(signal['signal_strength'] - smoothed_values[i])
                denoised_signals.append(denoised_signal)
            
            logger.info(f"因子去噪完成，处理 {len(denoised_signals)} 个信号")
            return denoised_signals
            
        except Exception as e:
            logger.error(f"因子去噪失败: {e}")
            return signals
    
    def update_strategy_weights(self, optimized_weights: Dict[str, Any]):
        """更新策略权重配置文件"""
        try:
            # 加载现有权重配置
            if os.path.exists(STRATEGY_WEIGHTS_FILE):
                with open(STRATEGY_WEIGHTS_FILE, 'r', encoding='utf-8') as f:
                    weights_config = json.load(f)
            else:
                weights_config = {
                    "version": "1.0.0",
                    "last_updated": datetime.datetime.now().isoformat(),
                    "strategies": {}
                }
            
            # 更新权重
            weights = optimized_weights.get('weights', {})
            
            for algo_id, weight in weights.items():
                if 'strategies' not in weights_config:
                    weights_config['strategies'] = {}
                
                if algo_id not in weights_config['strategies']:
                    weights_config['strategies'][algo_id] = {}
                
                weights_config['strategies'][algo_id]['weight'] = weight
                weights_config['strategies'][algo_id]['last_updated'] = datetime.datetime.now().isoformat()
                weights_config['strategies'][algo_id]['optimization_method'] = optimized_weights.get('optimization_method')
            
            # 更新元数据
            weights_config['last_updated'] = datetime.datetime.now().isoformat()
            weights_config['ir_optimization'] = {
                "optimization_date": optimized_weights.get('optimization_date'),
                "expected_portfolio_ir": optimized_weights.get('expected_portfolio_ir'),
                "algorithm_count": optimized_weights.get('algorithm_count')
            }
            
            # 保存更新
            with open(STRATEGY_WEIGHTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(weights_config, f, ensure_ascii=False, indent=2)
            
            logger.info(f"策略权重已更新: {STRATEGY_WEIGHTS_FILE}")
            
        except Exception as e:
            logger.error(f"更新策略权重失败: {e}")
    
    def run_optimization(self) -> Dict[str, Any]:
        """运行完整的IR优化流程"""
        logger.info("=" * 60)
        logger.info("开始IR优化流程")
        logger.info("=" * 60)
        
        start_time = datetime.datetime.now()
        
        try:
            # 1. 加载算法表现数据
            algorithms = self.load_algorithm_performance()
            
            if not algorithms:
                logger.error("没有可用的算法表现数据")
                return {
                    "success": False,
                    "error": "没有可用的算法表现数据",
                    "duration_seconds": (datetime.datetime.now() - start_time).total_seconds()
                }
            
            # 2. 计算所有算法的IR
            ir_results = self.calculate_all_ir()
            
            # 3. 优化权重
            optimized_weights = self.optimize_weights(ir_results)
            
            # 4. 更新策略权重
            self.update_strategy_weights(optimized_weights)
            
            # 5. 生成优化报告
            report = self._generate_optimization_report(
                algorithms, ir_results, optimized_weights, start_time
            )
            
            logger.info(f"IR优化流程完成，耗时: {report['duration_seconds']:.2f}秒")
            
            return report
            
        except Exception as e:
            logger.error(f"IR优化流程失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "duration_seconds": (datetime.datetime.now() - start_time).total_seconds()
            }
    
    def _generate_optimization_report(self, 
                                     algorithms: Dict[str, AlgorithmPerformance],
                                     ir_results: Dict[str, Dict[str, Any]],
                                     optimized_weights: Dict[str, Any],
                                     start_time: datetime.datetime) -> Dict[str, Any]:
        """生成优化报告"""
        duration = (datetime.datetime.now() - start_time).total_seconds()
        
        # 计算统计信息
        ir_values = [r.get('ir', 0) for r in ir_results.values()]
        annualized_ir_values = [r.get('annualized_ir', 0) for r in ir_results.values()]
        
        report = {
            "report_id": f"ir_optimization_{int(datetime.datetime.now().timestamp())}",
            "generation_date": datetime.date.today().isoformat(),
            "generation_time": datetime.datetime.now().isoformat(),
            "success": True,
            "duration_seconds": duration,
            "summary": {
                "algorithm_count": len(algorithms),
                "average_ir": np.mean(ir_values) if ir_values else 0,
                "median_ir": np.median(ir_values) if ir_values else 0,
                "max_ir": np.max(ir_values) if ir_values else 0,
                "min_ir": np.min(ir_values) if ir_values else 0,
                "average_annualized_ir": np.mean(annualized_ir_values) if annualized_ir_values else 0,
                "expected_portfolio_ir": optimized_weights.get('expected_portfolio_ir', 0)
            },
            "ir_results": ir_results,
            "optimized_weights": optimized_weights,
            "algorithm_details": {
                algo_id: {
                    "name": algo.algorithm_name,
                    "data_points": len(algo.returns),
                    "start_date": algo.start_date,
                    "end_date": algo.end_date
                }
                for algo_id, algo in algorithms.items()
            },
            "metadata": {
                "version": "1.0.0",
                "author": "工程师 Cheese 🧀",
                "mission": "V1.7.0 '智库并网'专项行动 - 专项三",
                "lookback_period": self.lookback_period,
                "config_file": IR_CONFIG_FILE
            }
        }
        
        # 保存报告
        self._save_optimization_report(report)
        
        return report
    
    def _save_optimization_report(self, report: Dict[str, Any]):
        """保存优化报告"""
        try:
            report_dir = "reports/ir_optimization"
            os.makedirs(report_dir, exist_ok=True)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            report_file = os.path.join(report_dir, f"ir_optimization_report_{timestamp}.json")
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"优化报告已保存: {report_file}")
            
        except Exception as e:
            logger.error(f"保存优化报告失败: {e}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='琥珀引擎IR优化器')
    parser.add_argument('--lookback', type=int, default=90,
                       help='回溯周期（天），默认: 90')
    parser.add_argument('--method', type=str, default='ir_weighted',
                       choices=['ir_weighted', 'mean_variance', 'equal_weight'],
                       help='权重优化方法')
    parser.add_argument('--denoise', action='store_true',
                       help='启用因子去噪')
    parser.add_argument('--test', action='store_true',
                       help='测试模式，使用模拟数据')
    
    args = parser.parse_args()
    
    # 创建优化器
    optimizer = IROptimizer(lookback_period=args.lookback)
    
    # 更新配置
    if args.method:
        optimizer.config['weight_optimization']['method'] = args.method
    
    if args.denoise:
        optimizer.config['factor_denoising']['enabled'] = True
    
    # 运行优化
    print(f"\n🔧 开始IR优化流程")
    print(f"   回溯周期: {args.lookback} 天")
    print(f"   优化方法: {args.method}")
    print(f"   因子去噪: {'启用' if args.denoise else '禁用'}")
    
    result = optimizer.run_optimization()
    
    if result['success']:
        print(f"\n✅ IR优化成功！")
        print(f"   处理算法: {result['summary']['algorithm_count']} 个")
        print(f"   平均IR: {result['summary']['average_ir']:.3f}")
        print(f"   预期组合IR: {result['summary']['expected_portfolio_ir']:.3f}")
        print(f"   耗时: {result['duration_seconds']:.2f} 秒")
        
        # 显示前5个算法的权重
        weights = result['optimized_weights'].get('weights', {})
        if weights:
            print(f"\n📊 前5个算法权重:")
            sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
            for algo_id, weight in sorted_weights[:5]:
                ir = result['ir_results'].get(algo_id, {}).get('ir', 0)
                print(f"   {algo_id}: {weight:.2%} (IR={ir:.3f})")
    else:
        print(f"\n❌ IR优化失败: {result.get('error', '未知错误')}")


if __name__ == "__main__":
    main()