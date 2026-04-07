#!/usr/bin/env python3
"""
Gravity Dip Strategy (G1) - 橡皮筋阈值策略
计算价格与均线的偏离，并分析偏离在历史分布中的百分位
"""

import statistics
from typing import Dict, Any, List, Optional
from .base_strategy import BaseStrategy


class GravityDipStrategy(BaseStrategy):
    """橡皮筋阈值策略"""
    
    def __init__(self):
        super().__init__(
            name="Gravity-Dip",
            description="计算价格与均线的偏离，分析偏离在历史分布中的百分位，捕捉回归机会"
        )
    
    def get_required_history_days(self) -> int:
        """需要250天历史数据用于分位数分析"""
        return 250
    
    def analyze(self, 
                ticker: str,
                history_data: Dict[str, Any],
                analysis_data: Optional[Dict[str, Any]] = None,
                global_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        分析价格与均线的偏离
        
        逻辑:
        1. 计算当前价格与20日均线的偏离百分比
        2. 计算历史偏离值列表
        3. 分析当前偏离在历史分布中的百分位
        4. 如果偏离较大且处于极端百分位（<10%或>90%），则产生信号
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
            if len(prices) < 60:  # 至少需要60天计算20日均线
                return self.create_result(
                    hit=False,
                    score=0.0,
                    confidence=0.0,
                    signals=["数据不足，无法计算20日均线"],
                    metadata={"error": "数据不足"}
                )
            
            # 计算当前价格和20日均线
            current_price = prices[0]  # 最新价格
            ma20 = self.calculate_moving_average(prices, 20)
            
            if ma20 is None or ma20 == 0:
                return self.create_result(
                    hit=False,
                    score=0.0,
                    confidence=0.0,
                    signals=["无法计算20日均线"],
                    metadata={"error": "MA20计算失败"}
                )
            
            # 计算当前偏离
            current_deviation = ((current_price - ma20) / ma20) * 100
            
            # 计算历史偏离值（每天的价格与对应20日均线的偏离）
            historical_deviations = []
            for i in range(20, min(len(prices), 250)):
                price = prices[i]
                # 计算i点的20日均线（使用i-19到i的价格）
                if i >= 19:
                    window_prices = prices[i-19:i+1]
                    historical_ma20 = statistics.mean(window_prices)
                    if historical_ma20 != 0:
                        deviation = ((price - historical_ma20) / historical_ma20) * 100
                        historical_deviations.append(deviation)
            
            if not historical_deviations:
                return self.create_result(
                    hit=False,
                    score=0.0,
                    confidence=0.0,
                    signals=["无法计算历史偏离分布"],
                    metadata={"error": "历史偏离数据不足"}
                )
            
            # 计算当前偏离的历史百分位
            percentile = self.calculate_price_deviation_percentile(
                current_price, ma20, historical_deviations
            )
            
            # 计算Z分数
            z_score = self.calculate_z_score(current_deviation, historical_deviations)
            
            # 生成信号
            signals = []
            metadata = {
                "current_price": current_price,
                "ma20": ma20,
                "current_deviation_percent": round(current_deviation, 4),
                "deviation_percentile": round(percentile, 4),
                "z_score": round(z_score, 4),
                "historical_deviations_count": len(historical_deviations),
                "historical_deviation_mean": round(statistics.mean(historical_deviations), 4),
                "historical_deviation_std": round(statistics.stdev(historical_deviations), 4) if len(historical_deviations) > 1 else 0.0
            }
            
            # 判断是否命中
            hit = False
            score = 0.0
            confidence = 0.5
            
            # 规则1: 如果偏离超过2倍标准差（Z分数 > 2或 < -2）
            if abs(z_score) > 2.0:
                hit = True
                # 偏离越大，得分越高（但不超过100）
                score = min(100.0, 30.0 + abs(z_score) * 10.0)
                confidence = min(0.9, 0.5 + abs(z_score) * 0.1)
                
                if z_score < -2:
                    signals.append("极度超卖: 价格显著低于均线")
                    metadata["signal_type"] = "oversold"
                else:
                    signals.append("极度超买: 价格显著高于均线")
                    metadata["signal_type"] = "overbought"
            
            # 规则2: 如果处于历史极端百分位（<10%或>90%）
            elif percentile < 0.1 or percentile > 0.9:
                hit = True
                # 百分位越极端，得分越高
                extremeness = max(percentile, 1 - percentile)
                score = 20.0 + extremeness * 80.0
                confidence = 0.5 + extremeness * 0.3
                
                if percentile < 0.1:
                    signals.append("历史性低位: 偏离处于历史最低10%区间")
                    metadata["signal_type"] = "historical_low"
                else:
                    signals.append("历史性高位: 偏离处于历史最高10%区间")
                    metadata["signal_type"] = "historical_high"
            
            # 规则3: 适度偏离（1-2倍标准差）
            elif abs(z_score) > 1.0:
                hit = True
                score = 15.0 + (abs(z_score) - 1.0) * 15.0
                confidence = 0.4
                
                if z_score < 0:
                    signals.append("适度超卖: 价格低于均线")
                else:
                    signals.append("适度超买: 价格高于均线")
                metadata["signal_type"] = "moderate_deviation"
            
            if not signals:
                signals.append("无显著偏离信号")
                metadata["signal_type"] = "no_signal"
            
            return self.create_result(
                hit=hit,
                score=score,
                confidence=confidence,
                signals=signals,
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Gravity-Dip分析失败: {e}")
            return self.create_result(
                hit=False,
                score=0.0,
                confidence=0.0,
                signals=[f"分析失败: {str(e)}"],
                metadata={"error": str(e)}
            )