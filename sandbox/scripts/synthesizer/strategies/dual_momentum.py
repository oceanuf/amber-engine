#!/usr/bin/env python3
"""
Dual Momentum Strategy (G2) - 双重动量策略
12个月绝对动能 > 0 且 3个月相对动能排名在前30%
"""

import statistics
from typing import Dict, Any, List, Optional
from .base_strategy import BaseStrategy


class DualMomentumStrategy(BaseStrategy):
    """双重动量策略"""
    
    def __init__(self):
        super().__init__(
            name="Dual-Momentum",
            description="12个月绝对动能 > 0 且 3个月相对动能排名在前30%"
        )
    
    def get_required_history_days(self) -> int:
        """需要250个交易日（约12个月）历史数据"""
        return 250
    
    def calculate_momentum(self, prices: List[float], period_days: int) -> Optional[float]:
        """计算指定周期的动量（收益率）"""
        if len(prices) < period_days + 1:
            return None
        
        # 最新价格
        current_price = prices[0]
        # period_days天前的价格
        past_price = prices[period_days]
        
        if past_price == 0:
            return None
        
        # 计算收益率
        momentum = ((current_price - past_price) / past_price) * 100
        return momentum
    
    def analyze(self, 
                ticker: str,
                history_data: Dict[str, Any],
                analysis_data: Optional[Dict[str, Any]] = None,
                global_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        分析双重动量
        
        逻辑:
        1. 计算12个月（250交易日）绝对动量
        2. 计算3个月（63交易日）动量
        3. 计算3个月动量在历史分布中的百分位
        4. 判断是否满足双重条件
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
            # 获取历史价格数据
            prices = self.get_historical_prices(history_data, days=250)
            if len(prices) < 250:
                return self.create_result(
                    hit=False,
                    score=0.0,
                    confidence=0.0,
                    signals=[f"数据不足，需要250天，实际{len(prices)}天"],
                    metadata={"error": "数据不足"}
                )
            
            # 计算动量周期（交易日）
            # 12个月 ≈ 250个交易日
            # 3个月 ≈ 63个交易日
            momentum_12m = self.calculate_momentum(prices, 250)  # 12个月
            momentum_3m = self.calculate_momentum(prices, 63)    # 3个月
            
            if momentum_12m is None or momentum_3m is None:
                return self.create_result(
                    hit=False,
                    score=0.0,
                    confidence=0.0,
                    signals=["无法计算动量"],
                    metadata={"error": "动量计算失败"}
                )
            
            # 计算历史3个月动量序列（滚动计算）
            historical_3m_momentums = []
            for i in range(63, min(len(prices), 250)):
                if i + 63 <= len(prices):
                    window_current = prices[i-63]
                    window_past = prices[i]
                    if window_past != 0:
                        momentum = ((window_current - window_past) / window_past) * 100
                        historical_3m_momentums.append(momentum)
            
            if not historical_3m_momentums:
                return self.create_result(
                    hit=False,
                    score=0.0,
                    confidence=0.0,
                    signals=["无法计算历史动量分布"],
                    metadata={"error": "历史动量数据不足"}
                )
            
            # 计算当前3个月动量的历史百分位
            sorted_momentums = sorted(historical_3m_momentums)
            count_below = sum(1 for m in sorted_momentums if m < momentum_3m)
            percentile = count_below / len(sorted_momentums)
            
            # 生成信号
            signals = []
            metadata = {
                "momentum_12m_percent": round(momentum_12m, 4),
                "momentum_3m_percent": round(momentum_3m, 4),
                "momentum_3m_percentile": round(percentile, 4),
                "historical_momentums_count": len(historical_3m_momentums),
                "historical_momentum_mean": round(statistics.mean(historical_3m_momentums), 4),
                "historical_momentum_std": round(statistics.stdev(historical_3m_momentums), 4) if len(historical_3m_momentums) > 1 else 0.0
            }
            
            # 判断是否命中
            hit = False
            score = 0.0
            confidence = 0.5
            
            # 规则1: 12个月绝对动量 > 0 且 3个月动量百分位 > 70%（前30%）
            if momentum_12m > 0 and percentile > 0.7:
                hit = True
                
                # 计算得分：基于12个月动量大小和3个月动量排名
                momentum_score = min(50.0, momentum_12m * 2.0)  # 每1%动量得2分，最多50分
                percentile_score = (percentile - 0.7) * 100.0  # 百分位超过70%的部分折算为分数
                
                score = 30.0 + momentum_score + percentile_score
                score = min(100.0, score)
                
                confidence = 0.6 + (percentile - 0.7) * 0.3
                confidence = min(0.9, confidence)
                
                signals.append("双重动量共振: 长期向上且短期强势")
                metadata["signal_type"] = "dual_momentum_resonance"
                metadata["momentum_score"] = round(momentum_score, 2)
                metadata["percentile_score"] = round(percentile_score, 2)
            
            # 规则2: 仅12个月动量 > 0
            elif momentum_12m > 0:
                hit = True
                score = 20.0 + min(30.0, momentum_12m * 1.5)
                confidence = 0.5
                
                signals.append("绝对动量向上: 长期趋势积极")
                metadata["signal_type"] = "absolute_momentum"
            
            # 规则3: 仅3个月动量百分位 > 70%
            elif percentile > 0.7:
                hit = True
                score = 15.0 + (percentile - 0.7) * 50.0
                confidence = 0.4
                
                signals.append("相对动量强势: 短期表现优异")
                metadata["signal_type"] = "relative_momentum"
            
            # 规则4: 12个月动量 < 0 且 3个月动量百分位 < 30%
            elif momentum_12m < 0 and percentile < 0.3:
                hit = True
                score = 10.0  # 警示信号
                confidence = 0.6
                
                signals.append("双重动量疲弱: 长期向下且短期弱势")
                metadata["signal_type"] = "dual_momentum_weak"
            
            if not signals:
                signals.append("动量信号中性")
                metadata["signal_type"] = "neutral"
            
            return self.create_result(
                hit=hit,
                score=score,
                confidence=confidence,
                signals=signals,
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Dual-Momentum分析失败: {e}")
            return self.create_result(
                hit=False,
                score=0.0,
                confidence=0.0,
                signals=[f"分析失败: {str(e)}"],
                metadata={"error": str(e)}
            )