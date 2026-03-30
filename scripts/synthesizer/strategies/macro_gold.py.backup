#!/usr/bin/env python3
"""
Macro Gold Strategy (G9) - 宏观对冲锚定策略
剥离名义金价中的利率杂质，寻找黄金真正的"隐性引力点"
公式：黄金价格 - f(10年期美债实际利率)
"""

import statistics
from typing import Dict, Any, List, Optional
from .base_strategy import BaseStrategy


class MacroGoldStrategy(BaseStrategy):
    """宏观对冲锚定策略"""
    
    def __init__(self):
        super().__init__(
            name="Macro-Gold",
            description="剥离名义金价中的利率杂质，分析实际利率对黄金的宏观影响"
        )
    
    def get_required_history_days(self) -> int:
        """需要250天历史数据用于分析利率趋势"""
        return 250
    
    def get_treasury_yield_data(self, global_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        获取美债收益率数据（模拟/待接入真实数据）
        
        目前使用模拟数据，后续需要从宏观数据API获取真实的10年期美债实际利率
        实际利率 = 名义利率 - 预期通胀率
        
        Args:
            global_params: 全局参数配置，可能包含利率数据
            
        Returns:
            美债收益率数据字典
        """
        # 模拟数据 - 10年期美债实际利率（单位：%）
        # 实际数据应从宏观数据API获取
        simulated_yields = {
            "2026-03-29": 2.15,  # 2.15%
            "2026-03-28": 2.18,
            "2026-03-27": 2.12,
            "2026-03-26": 2.20,
            "2026-03-25": 2.22,
            "2026-03-24": 2.19,
            "2026-03-23": 2.16,
            "2026-03-22": 2.14,
            "2026-03-21": 2.10,
            "2026-03-20": 2.08,
            # 历史数据（简化模拟）
            "long_term_average": 2.0,
            "current_yield": 2.15,
            "yield_trend": "stable",  # rising, falling, stable
            "inflation_expectation": 2.3,  # 预期通胀率
            "real_yield": -0.15,  # 实际利率 = 名义利率 - 通胀预期
        }
        
        # 如果global_params中包含利率数据，优先使用
        if global_params and "treasury_yields" in global_params:
            return global_params["treasury_yields"]
        
        return simulated_yields
    
    def calculate_gold_attractiveness(self, 
                                    gold_price: float,
                                    real_yield: float,
                                    historical_prices: List[float],
                                    historical_yields: List[float]) -> Dict[str, Any]:
        """
        计算黄金吸引力分数
        
        核心逻辑：实际利率与黄金价格通常呈负相关
        实际利率下降 → 黄金吸引力上升
        实际利率上升 → 黄金吸引力下降
        
        Args:
            gold_price: 当前黄金价格
            real_yield: 当前实际利率（%）
            historical_prices: 历史黄金价格列表
            historical_yields: 历史实际利率列表
            
        Returns:
            吸引力分析结果
        """
        if not historical_prices or not historical_yields:
            return {
                "attractiveness_score": 50.0,
                "gold_yield_correlation": 0.0,
                "relative_attractiveness": 0.5,
                "signal_strength": "neutral"
            }
        
        try:
            # 计算历史黄金价格与实际利率的相关性（简化版）
            # 实际中应使用更复杂的相关性和回归分析
            price_changes = []
            yield_changes = []
            
            # 计算每日变化
            for i in range(1, min(len(historical_prices), len(historical_yields))):
                price_change = ((historical_prices[i-1] - historical_prices[i]) / historical_prices[i]) * 100
                yield_change = historical_yields[i-1] - historical_yields[i]
                price_changes.append(price_change)
                yield_changes.append(yield_change)
            
            # 计算相关系数（简化版，使用协方差和标准差）
            if len(price_changes) > 1 and len(yield_changes) > 1:
                price_mean = statistics.mean(price_changes)
                yield_mean = statistics.mean(yield_changes)
                
                covariance = sum((p - price_mean) * (y - yield_mean) 
                               for p, y in zip(price_changes, yield_changes)) / len(price_changes)
                price_std = statistics.stdev(price_changes) if len(price_changes) > 1 else 1.0
                yield_std = statistics.stdev(yield_changes) if len(yield_changes) > 1 else 1.0
                
                if price_std > 0 and yield_std > 0:
                    correlation = covariance / (price_std * yield_std)
                else:
                    correlation = 0.0
            else:
                correlation = 0.0
            
            # 计算黄金吸引力分数
            # 规则：实际利率越低，黄金吸引力越高
            # 假设黄金的理想实际利率环境是负实际利率
            
            # 计算当前实际利率在历史中的位置
            if historical_yields:
                sorted_yields = sorted(historical_yields)
                count_below = sum(1 for y in sorted_yields if y < real_yield)
                yield_percentile = count_below / len(sorted_yields)
            else:
                yield_percentile = 0.5
            
            # 吸引力评分逻辑
            # 实际利率越低（特别是负利率），黄金吸引力越高
            attractiveness_score = 50.0  # 基准分
            
            if real_yield < 0:
                # 负实际利率环境，黄金具有天然吸引力
                attractiveness_score = 70.0 + abs(real_yield) * 10.0
                signal_strength = "strong_bullish"
            elif real_yield < 1.0:
                # 低实际利率环境
                attractiveness_score = 60.0 + (1.0 - real_yield) * 10.0
                signal_strength = "bullish"
            elif real_yield > 3.0:
                # 高实际利率环境，压制黄金
                attractiveness_score = 30.0 - (real_yield - 3.0) * 5.0
                signal_strength = "bearish"
            else:
                # 中等实际利率
                attractiveness_score = 50.0
                signal_strength = "neutral"
            
            # 考虑相关性强度调整
            if abs(correlation) > 0.5:
                # 强相关性，增加置信度
                if correlation < -0.5:
                    # 强负相关（利率下降→金价上涨），吸引力更高
                    attractiveness_score = min(100.0, attractiveness_score * 1.2)
                    signal_strength = "very_strong_bullish" if signal_strength == "strong_bullish" else signal_strength
            
            # 考虑利率趋势
            # 如果实际利率处于下降趋势，即使当前水平不低，未来预期利好黄金
            if len(historical_yields) >= 5:
                recent_yields = historical_yields[:5]
                yield_trend = statistics.mean(recent_yields[:3]) - statistics.mean(recent_yields[3:])
                if yield_trend < -0.1:  # 下降趋势
                    attractiveness_score = min(100.0, attractiveness_score + 15.0)
                    signal_strength = "trend_bullish"
                elif yield_trend > 0.1:  # 上升趋势
                    attractiveness_score = max(0.0, attractiveness_score - 15.0)
                    signal_strength = "trend_bearish"
            
            attractiveness_score = max(0.0, min(100.0, attractiveness_score))
            
            return {
                "attractiveness_score": round(attractiveness_score, 2),
                "gold_yield_correlation": round(correlation, 4),
                "real_yield": round(real_yield, 4),
                "yield_percentile": round(yield_percentile, 4),
                "signal_strength": signal_strength,
                "price_yield_ratio": round(gold_price / max(0.1, abs(real_yield)), 4) if real_yield != 0 else 0.0
            }
            
        except Exception as e:
            self.logger.error(f"计算黄金吸引力失败: {e}")
            return {
                "attractiveness_score": 50.0,
                "gold_yield_correlation": 0.0,
                "real_yield": real_yield,
                "yield_percentile": 0.5,
                "signal_strength": "error",
                "error": str(e)
            }
    
    def analyze(self, 
                ticker: str,
                history_data: Dict[str, Any],
                analysis_data: Optional[Dict[str, Any]] = None,
                global_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        分析宏观利率环境对黄金的影响
        
        逻辑:
        1. 获取当前黄金价格和历史价格
        2. 获取10年期美债实际利率数据（模拟/真实）
        3. 计算黄金吸引力分数
        4. 基于实际利率水平和趋势生成信号
        """
        # 验证数据充足性
        valid, message = self.validate_data_sufficiency(history_data)
        if not valid:
            return self.create_result(
                hit=False,
                score=0.0,
                confidence=0.0,
                signals=[f"数据不足: {message}"],
                metadata={"error": message}
            )
        
        try:
            # 检查是否为黄金ETF（518880）
            if ticker != "518880":
                return self.create_result(
                    hit=False,
                    score=50.0,  # 非黄金资产，返回中性评分
                    confidence=0.3,
                    signals=["本策略仅适用于黄金资产"],
                    metadata={"applicable": False, "reason": "非黄金资产"}
                )
            
            # 获取历史价格数据
            prices = self.get_historical_prices(history_data, days=250)
            if len(prices) < 60:
                return self.create_result(
                    hit=False,
                    score=50.0,
                    confidence=0.3,
                    signals=["历史数据不足，无法进行宏观分析"],
                    metadata={"error": "历史数据不足"}
                )
            
            current_price = prices[0]
            
            # 获取美债收益率数据
            treasury_data = self.get_treasury_yield_data(global_params)
            
            # 提取实际利率（模拟数据）
            real_yield = treasury_data.get("real_yield", 2.15)  # 默认值
            
            # 创建历史实际利率序列（模拟）
            # 实际中应从历史数据库中获取
            historical_yields = [
                2.15, 2.18, 2.12, 2.20, 2.22, 2.19, 2.16, 2.14, 2.10, 2.08,
                2.05, 2.03, 2.00, 1.98, 1.95, 1.93, 1.90, 1.88, 1.85, 1.83,
                1.80, 1.78, 1.75, 1.73, 1.70
            ]
            
            # 确保历史数据长度与价格匹配
            historical_yields = historical_yields[:min(len(prices), len(historical_yields))]
            
            # 计算黄金吸引力
            attractiveness = self.calculate_gold_attractiveness(
                current_price, real_yield, prices, historical_yields
            )
            
            # 生成信号
            signals = []
            metadata = {
                "current_price": current_price,
                "real_yield_percent": real_yield,
                "attractiveness_score": attractiveness["attractiveness_score"],
                "gold_yield_correlation": attractiveness["gold_yield_correlation"],
                "yield_percentile": attractiveness["yield_percentile"],
                "signal_strength": attractiveness["signal_strength"],
                "price_yield_ratio": attractiveness.get("price_yield_ratio", 0.0),
                "data_source": "simulated"  # 标记为模拟数据
            }
            
            # 判断是否命中
            hit = False
            score = attractiveness["attractiveness_score"]
            confidence = 0.5
            
            signal_strength = attractiveness.get("signal_strength", "neutral")
            
            # 根据信号强度设置命中条件和置信度
            if signal_strength in ["very_strong_bullish", "strong_bullish"]:
                hit = True
                confidence = 0.8
                signals.append(f"宏观利好: 实际利率{real_yield}%，黄金吸引力强")
                metadata["signal_type"] = "macro_bullish"
                
            elif signal_strength in ["bullish", "trend_bullish"]:
                hit = True
                confidence = 0.6
                signals.append(f"宏观偏多: 实际利率{real_yield}%，黄金有吸引力")
                metadata["signal_type"] = "macro_mild_bullish"
                
            elif signal_strength in ["bearish", "trend_bearish"]:
                hit = True
                confidence = 0.6
                signals.append(f"宏观压制: 实际利率{real_yield}%偏高，压制黄金")
                metadata["signal_type"] = "macro_bearish"
                
            else:  # neutral
                hit = False
                confidence = 0.4
                signals.append(f"宏观中性: 实际利率{real_yield}%，黄金无显著吸引力")
                metadata["signal_type"] = "macro_neutral"
            
            # 添加数据质量说明
            if metadata["data_source"] == "simulated":
                signals.append("注意: 使用模拟利率数据，需接入真实宏观数据")
                metadata["data_quality"] = "simulated"
                confidence = confidence * 0.7  # 模拟数据降低置信度
            
            return self.create_result(
                hit=hit,
                score=score,
                confidence=confidence,
                signals=signals,
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Macro-Gold分析失败: {e}")
            return self.create_result(
                hit=False,
                score=50.0,
                confidence=0.0,
                signals=[f"宏观分析失败: {str(e)}"],
                metadata={"error": str(e)}
            )