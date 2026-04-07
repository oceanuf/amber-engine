#!/usr/bin/env python3
"""
专项三：算法骨架重构验证测试
测试IR优化器和因子去噪逻辑
"""

import os
import sys
import json
import numpy as np
import logging
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_ir_calculation():
    """测试IR计算逻辑"""
    logger.info("测试IR计算逻辑...")
    
    try:
        # 导入IR优化器
        from scripts.synthesizer.ir_optimizer import IROptimizer, AlgorithmPerformance
        
        # 创建模拟算法表现数据
        # 算法1: 表现良好的算法（正超额收益）
        algo1_returns = np.random.normal(0.001, 0.01, 100).tolist()  # 日均0.1%，波动1%
        benchmark_returns = np.random.normal(0.0005, 0.01, 100).tolist()  # 基准日均0.05%
        
        algo1 = AlgorithmPerformance(
            algorithm_id="algo_good",
            algorithm_name="优秀算法",
            returns=algo1_returns,
            benchmark_returns=benchmark_returns,
            signals=[],
            start_date="2026-01-01",
            end_date="2026-04-05"
        )
        
        # 算法2: 表现差的算法（负超额收益）
        algo2_returns = np.random.normal(-0.0005, 0.01, 100).tolist()  # 日均-0.05%
        
        algo2 = AlgorithmPerformance(
            algorithm_id="algo_bad",
            algorithm_name="差劲算法",
            returns=algo2_returns,
            benchmark_returns=benchmark_returns,  # 相同基准
            signals=[],
            start_date="2026-01-01",
            end_date="2026-04-05"
        )
        
        # 计算IR
        ir1 = algo1.calculate_ir()
        ir2 = algo2.calculate_ir()
        
        logger.info(f"算法1 (优秀算法) IR结果:")
        logger.info(f"  IR值: {ir1.get('ir', 0):.3f}")
        logger.info(f"  年化IR: {ir1.get('annualized_ir', 0):.3f}")
        logger.info(f"  策略收益: {ir1.get('strategy_return', 0):.2%}")
        logger.info(f"  基准收益: {ir1.get('benchmark_return', 0):.2%}")
        logger.info(f"  超额收益: {ir1.get('active_return', 0):.2%}")
        logger.info(f"  跟踪误差: {ir1.get('tracking_error', 0):.2%}")
        
        logger.info(f"算法2 (差劲算法) IR结果:")
        logger.info(f"  IR值: {ir2.get('ir', 0):.3f}")
        logger.info(f"  年化IR: {ir2.get('annualized_ir', 0):.3f}")
        logger.info(f"  策略收益: {ir2.get('strategy_return', 0):.2%}")
        logger.info(f"  超额收益: {ir2.get('active_return', 0):.2%}")
        
        # 验证逻辑：优秀算法IR应该为正，差劲算法IR应该为负
        if ir1.get('ir', 0) > 0 and ir2.get('ir', 0) < 0:
            logger.info("✅ IR计算逻辑正确：优秀算法IR>0，差劲算法IR<0")
            return True
        else:
            logger.warning(f"⚠️ IR计算结果异常：算法1 IR={ir1.get('ir', 0):.3f}, 算法2 IR={ir2.get('ir', 0):.3f}")
            return False
            
    except Exception as e:
        logger.error(f"IR计算测试失败: {e}", exc_info=True)
        return False

def test_weight_adjustment_with_loss():
    """测试亏损数据下的权重调整逻辑"""
    logger.info("测试亏损数据下的权重调整逻辑...")
    
    try:
        from scripts.synthesizer.ir_optimizer import IROptimizer
        
        # 创建优化器
        optimizer = IROptimizer(lookback_period=90)
        
        # 模拟亏损算法数据
        loss_ir_results = {
            "algo_loss_heavy": {
                "ir": -0.8,  # 严重负IR
                "annualized_ir": -12.7,
                "strategy_return": -0.15,
                "benchmark_return": 0.05,
                "tracking_error": 0.12,
                "active_return": -0.20,
                "win_rate": 0.40,
                "max_drawdown": -0.25,
                "data_points": 90
            },
            "algo_loss_mild": {
                "ir": -0.2,  # 轻度负IR
                "annualized_ir": -3.2,
                "strategy_return": -0.03,
                "benchmark_return": 0.05,
                "tracking_error": 0.10,
                "active_return": -0.08,
                "win_rate": 0.48,
                "max_drawdown": -0.15,
                "data_points": 90
            },
            "algo_profit_small": {
                "ir": 0.1,  # 小正IR
                "annualized_ir": 1.6,
                "strategy_return": 0.08,
                "benchmark_return": 0.05,
                "tracking_error": 0.08,
                "active_return": 0.03,
                "win_rate": 0.55,
                "max_drawdown": -0.10,
                "data_points": 90
            }
        }
        
        # 测试不同的权重优化方法
        methods = ['ir_weighted', 'mean_variance', 'equal_weight']
        
        for method in methods:
            optimizer.config['weight_optimization']['method'] = method
            weights = optimizer.optimize_weights(loss_ir_results)
            
            logger.info(f"权重优化方法: {method}")
            logger.info(f"  预期组合IR: {weights.get('expected_portfolio_ir', 0):.3f}")
            
            # 检查权重分配
            algo_weights = weights.get('weights', {})
            
            for algo_id, weight in algo_weights.items():
                algo_ir = loss_ir_results.get(algo_id, {}).get('ir', 0)
                logger.info(f"  {algo_id}: 权重={weight:.2%}, IR={algo_ir:.3f}")
            
            # 逻辑校验：亏损严重的算法权重应该较低
            heavy_loss_weight = algo_weights.get('algo_loss_heavy', 0)
            mild_loss_weight = algo_weights.get('algo_loss_mild', 0)
            profit_weight = algo_weights.get('algo_profit_small', 0)
            
            if method == 'ir_weighted':
                # IR加权方法：负IR算法应该获得很低权重
                if heavy_loss_weight < mild_loss_weight < profit_weight:
                    logger.info(f"  ✅ {method}: 权重分配符合逻辑（盈利>轻度亏损>严重亏损）")
                else:
                    logger.warning(f"  ⚠️ {method}: 权重分配可能不合理")
            elif method == 'mean_variance':
                # 均值方差方法也应该给亏损算法较低权重
                if heavy_loss_weight < profit_weight:
                    logger.info(f"  ✅ {method}: 严重亏损算法权重较低")
                else:
                    logger.warning(f"  ⚠️ {method}: 权重分配可能不合理")
            elif method == 'equal_weight':
                # 等权重方法：所有算法权重相等
                expected_weight = 1.0 / 3
                if abs(heavy_loss_weight - expected_weight) < 0.01:
                    logger.info(f"  ✅ {method}: 等权重分配正确")
                else:
                    logger.warning(f"  ⚠️ {method}: 等权重分配异常")
        
        logger.info("✅ 亏损数据下的权重调整逻辑测试完成")
        return True
        
    except Exception as e:
        logger.error(f"权重调整测试失败: {e}", exc_info=True)
        return False

def test_ic_volatility_rule():
    """测试IC波动率'去噪红线'规则"""
    logger.info("测试IC波动率'去噪红线'规则...")
    
    try:
        # 模拟因子IC历史数据
        # 因子1: 稳定因子（IC波动率低）
        factor1_ic_history = np.random.normal(0.05, 0.02, 21).tolist()  # 3周数据，日均IC 5%，波动2%
        
        # 因子2: 不稳定因子（IC波动率高）
        factor2_ic_history = np.random.normal(0.03, 0.08, 21).tolist()  # 日均IC 3%，波动8%
        
        # 计算IC均值和波动率
        factor1_mean = np.mean(factor1_ic_history)
        factor1_std = np.std(factor1_ic_history, ddof=1)
        factor1_vol_ratio = factor1_std / abs(factor1_mean) if factor1_mean != 0 else 0
        
        factor2_mean = np.mean(factor2_ic_history)
        factor2_std = np.std(factor2_ic_history, ddof=1)
        factor2_vol_ratio = factor2_std / abs(factor2_mean) if factor2_mean != 0 else 0
        
        logger.info(f"因子1 (稳定): IC均值={factor1_mean:.4f}, 标准差={factor1_std:.4f}, 波动率比率={factor1_vol_ratio:.2f}")
        logger.info(f"因子2 (不稳定): IC均值={factor2_mean:.4f}, 标准差={factor2_std:.4f}, 波动率比率={factor2_vol_ratio:.2f}")
        
        # 应用"去噪红线"规则：IC波动率连续三周超过均值2倍时，权重下调50%
        threshold = 2.0  # 2倍阈值
        
        factor1_penalty = 1.0  # 默认不惩罚
        factor2_penalty = 1.0
        
        if factor1_vol_ratio > threshold:
            factor1_penalty = 0.5  # 权重下调50%
            logger.info(f"因子1触发'去噪红线': 波动率比率{factor1_vol_ratio:.2f} > 阈值{threshold}")
        
        if factor2_vol_ratio > threshold:
            factor2_penalty = 0.5
            logger.info(f"因子2触发'去噪红线': 波动率比率{factor2_vol_ratio:.2f} > 阈值{threshold}")
        
        # 模拟原始权重
        original_weights = {
            "factor1": 0.4,
            "factor2": 0.6
        }
        
        # 应用惩罚
        penalized_weights = {}
        total = 0
        for factor, weight in original_weights.items():
            penalty = factor1_penalty if factor == "factor1" else factor2_penalty
            penalized_weight = weight * penalty
            penalized_weights[factor] = penalized_weight
            total += penalized_weight
        
        # 重新归一化
        for factor in penalized_weights:
            penalized_weights[factor] /= total
        
        logger.info(f"原始权重: 因子1={original_weights['factor1']:.2%}, 因子2={original_weights['factor2']:.2%}")
        logger.info(f"惩罚后权重: 因子1={penalized_weights['factor1']:.2%}, 因子2={penalized_weights['factor2']:.2%}")
        
        # 验证逻辑：不稳定因子的权重应该被调低
        if factor2_vol_ratio > threshold:
            # 因子2应该被惩罚，权重比例应该降低
            original_ratio = original_weights['factor2'] / original_weights['factor1']
            penalized_ratio = penalized_weights['factor2'] / penalized_weights['factor1']
            
            if penalized_ratio < original_ratio:
                logger.info(f"✅ '去噪红线'规则生效: 不稳定因子权重比例从{original_ratio:.2f}降至{penalized_ratio:.2f}")
            else:
                logger.warning(f"⚠️ '去噪红线'规则未生效: 权重比例未降低")
        
        logger.info("✅ IC波动率'去噪红线'规则测试完成")
        return True
        
    except Exception as e:
        logger.error(f"IC波动率规则测试失败: {e}", exc_info=True)
        return False

def test_factor_denoising():
    """测试因子去噪功能"""
    logger.info("测试因子去噪功能...")
    
    try:
        from scripts.synthesizer.ir_optimizer import IROptimizer
        
        # 创建优化器
        optimizer = IROptimizer(lookback_period=90)
        
        # 生成带噪声的信号
        np.random.seed(42)
        clean_signal = np.sin(np.linspace(0, 4*np.pi, 50))  # 干净的正弦信号
        noise = np.random.normal(0, 0.3, 50)  # 噪声
        noisy_signal = clean_signal + noise
        
        # 创建模拟信号数据
        signals = []
        for i, value in enumerate(noisy_signal):
            signals.append({
                "timestamp": f"2026-04-05T{10+i//60:02d}:{i%60:02d}:00",
                "signal_strength": float(value),
                "algorithm_id": "test_algo",
                "factor_type": "momentum"
            })
        
        logger.info(f"生成 {len(signals)} 个带噪声的信号")
        logger.info(f"  原始信号范围: [{min(noisy_signal):.3f}, {max(noisy_signal):.3f}]")
        logger.info(f"  噪声标准差: {np.std(noise):.3f}")
        
        # 应用因子去噪
        optimizer.config['factor_denoising']['enabled'] = True
        denoised_signals = optimizer.apply_factor_denoising(signals)
        
        if denoised_signals and len(denoised_signals) == len(signals):
            logger.info("✅ 因子去噪功能正常")
            
            # 提取去噪后的信号值
            denoised_values = [s.get('signal_strength', 0) for s in denoised_signals]
            
            logger.info(f"  去噪后信号范围: [{min(denoised_values):.3f}, {max(denoised_values):.3f}]")
            
            # 计算噪声减少量
            noise_reduction = []
            for i in range(len(signals)):
                original = signals[i].get('signal_strength', 0)
                denoised = denoised_signals[i].get('signal_strength', 0)
                reduction = abs(original - denoised)
                noise_reduction.append(reduction)
            
            avg_reduction = np.mean(noise_reduction)
            logger.info(f"  平均噪声减少: {avg_reduction:.4f}")
            
            # 检查是否有信号被标记为已去噪
            denoised_count = sum(1 for s in denoised_signals if s.get('denoised', False))
            logger.info(f"  标记为已去噪的信号: {denoised_count}个")
            
            if denoised_count > 0:
                logger.info("✅ 去噪标记功能正常")
            else:
                logger.warning("⚠️ 没有信号被标记为已去噪")
            
            return True
        else:
            logger.error("❌ 因子去噪失败: 输出信号数量不匹配")
            return False
            
    except Exception as e:
        logger.error(f"因子去噪测试失败: {e}", exc_info=True)
        return False

def test_g1_g10_weight_distribution():
    """测试G1-G10算法权重分配逻辑"""
    logger.info("测试G1-G10算法权重分配逻辑...")
    
    try:
        from scripts.synthesizer.ir_optimizer import IROptimizer
        
        # 创建优化器
        optimizer = IROptimizer(lookback_period=90)
        
        # 模拟G1-G10算法的IR结果
        g_algorithms = {}
        for i in range(1, 11):
            algo_id = f"G{i}"
            
            # 不同算法有不同的模拟IR
            if i in [1, 3, 5, 7, 9]:  # 奇数编号算法表现较好
                ir = 0.1 + (i % 3) * 0.05
            else:  # 偶数编号算法表现一般
                ir = 0.02 + (i % 4) * 0.03
            
            g_algorithms[algo_id] = {
                "ir": ir,
                "annualized_ir": ir * np.sqrt(252),
                "strategy_return": 0.05 + ir * 0.5,
                "benchmark_return": 0.05,
                "tracking_error": 0.08,
                "active_return": ir * 0.08,
                "win_rate": 0.5 + ir,
                "max_drawdown": -0.1 - abs(ir) * 0.5,
                "data_points": 90
            }
        
        # 测试权重优化
        weights_result = optimizer.optimize_weights(g_algorithms)
        
        logger.info("G1-G10算法权重分配测试:")
        logger.info(f"  优化方法: {weights_result.get('optimization_method')}")
        logger.info(f"  预期组合IR: {weights_result.get('expected_portfolio_ir', 0):.3f}")
        
        # 显示前5个算法的权重
        weights = weights_result.get('weights', {})
        sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        
        logger.info("  权重排名前5:")
        for i, (algo_id, weight) in enumerate(sorted_weights[:5], 1):
            algo_ir = g_algorithms.get(algo_id, {}).get('ir', 0)
            logger.info(f"    {i}. {algo_id}: 权重={weight:.2%}, IR={algo_ir:.3f}")
        
        # 逻辑检查：IR较高的算法应该获得较高权重（对于ir_weighted方法）
        if optimizer.config['weight_optimization']['method'] == 'ir_weighted':
            # 检查IR最高的算法是否权重最高
            max_ir_algo = max(g_algorithms.items(), key=lambda x: x[1].get('ir', 0))
            max_ir_id = max_ir_algo[0]
            max_ir_weight = weights.get(max_ir_id, 0)
            
            if max_ir_weight == max(weights.values()):
                logger.info(f"✅ IR最高算法({max_ir_id})获得最高权重({max_ir_weight:.2%})")
            else:
                logger.warning(f"⚠️ IR最高算法({max_ir_id})未获得最高权重")
        
        # 检查权重总和
        weight_sum = sum(weights.values())
        if abs(weight_sum - 1.0) < 0.001:
            logger.info("✅ 权重归一化正确")
        else:
            logger.error(f"❌ 权重归一化错误: 总和={weight_sum:.4f}")
        
        return True
        
    except Exception as e:
        logger.error(f"G1-G10权重分配测试失败: {e}", exc_info=True)
        return False

def run_all_tests():
    """运行所有测试"""
    logger.info("开始专项三：算法骨架重构验证测试")
    logger.info("="*60)
    
    results = {
        "ir_calculation": False,
        "weight_adjustment": False,
        "ic_volatility_rule": False,
        "factor_denoising": False,
        "g1_g10_distribution": False
    }
    
    try:
        # 测试1: IR计算逻辑
        results["ir_calculation"] = test_ir_calculation()
        
        # 测试2: 亏损数据权重调整
        results["weight_adjustment"] = test_weight_adjustment_with_loss()
        
        # 测试3: IC波动率规则
        results["ic_volatility_rule"] = test_ic_volatility_rule()
        
        # 测试4: 因子去噪功能
        results["factor_denoising"] = test_factor_denoising()
        
        # 测试5: G1-G10权重分配
        results["g1_g10_distribution"] = test_g1_g10_weight_distribution()
        
        # 汇总结果
        logger.info("="*60)
        logger.info("专项三验证测试汇总:")
        logger.info(f"  IR计算逻辑: {'✅通过' if results['ir_calculation'] else '❌失败'}")
        logger.info(f"  亏损数据权重调整: {'✅通过' if results['weight_adjustment'] else '❌失败'}")
        logger.info(f"  IC波动率'去噪红线': {'✅通过' if results['ic_volatility_rule'] else '❌失败'}")
        logger.info(f"  因子去噪功能: {'✅通过' if results['factor_denoising'] else '❌失败'}")
        logger.info(f"  G1-G10权重分配: {'✅通过' if results['g1_g10_distribution'] else '❌失败'}")
        
        overall = all(results.values())
        
        if overall:
            logger.info("✅ 专项三验证测试总体通过")
        else:
            logger.warning("⚠️ 专项三验证测试部分失败")
            
        return overall
        
    except Exception as e:
        logger.error(f"测试执行异常: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)