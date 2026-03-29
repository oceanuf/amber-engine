#!/usr/bin/env python3
"""
Z-Score Bias Strategy (G6) - Z分数偏离策略
利用60日标准差，寻找统计学上的"极端错价"回归机会
"""

import statistics
from typing import Dict, Any, List, Optional
from .base_strategy import BaseStrategy


class ZScoreBiasStrategy(BaseStrategy):
    """Z分数偏离策略"""
    
    def __init__(self):
        super().__init__(
            name="Z-Score-Bias",
            description="利用60日标准差计算价格偏离的Z分数，捕捉统计学上的极端错价回归"
        )
    
    def get_required_history_days(self) -> int:
        """需要60天历史数据用于Z分数计算"""
        return 60
    
    def analyze(self, 
                ticker: str,
                history_data: Dict[str, Any],
                analysis_data: Optional[Dict[str, Any]] = None,
                global_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        分析价格偏离的Z分数
        
        逻辑:
        1. 计算最近60天的价格序列
        2. 计算60日移动平均线和标准差
        3. 计算当前价格相对于60日均线的Z分数
        4. 判断Z分数是否处于极端状态（如|Z| > 2）
        5. 生成回归信号
        """
        # 验证数据充足性
        valid, message = self.validate_data_sufficiency(history_data)
        if not valid:
            # 即使数据不足60天，也尝试用可用数据计算
            prices = self.get_historical_prices(history_data, days=60)
            if len(prices) < 30:  # 最少需要30天进行有意义计算
                return self.create_result(
                    hit=False,
                    score=0.0,
                    confidence=0.0,
                    signals=[f"数据不足: {message}"],
                    metadata={
                        "error": message,
                        "available_days": len(prices),
                        "required_days": 30
                    }
                )
        
        try:
            # 获取60天历史价格
            prices = self.get_historical_prices(history_data, days=60)
            
            if len(prices) < 30:
                return self.create_result(
                    hit=False,
                    score=0.0,
                    confidence=0.0,
                    signals=["数据不足，无法计算Z分数"],
                    metadata={
                        "error": "数据不足",
                        "available_days": len(prices),
                        "required_days": 30
                    }
                )
            
            current_price = prices[0]  # 最新价格
            
            # 计算60日移动平均线
            if len(prices) >= 60:
                ma_window = 60
            else:
                ma_window = len(prices)  # 使用所有可用数据
            
            ma60 = self.calculate_moving_average(prices, ma_window)
            
            if ma60 is None or ma60 == 0:
                return self.create_result(
                    hit=False,
                    score=0.0,
                    confidence=0.0,
                    signals=["无法计算移动平均线"],
                    metadata={"error": "MA计算失败"}
                )
            
            # 计算价格偏离（百分比）
            price_deviation_pct = ((current_price - ma60) / ma60) * 100
            
            # 计算历史偏离值序列（用于计算标准差）
            historical_deviations = []
            for i in range(len(prices)):
                # 对于每个点，计算其与之前ma_window日均线的偏离
                if i >= ma_window - 1:
                    window_prices = prices[i-ma_window+1:i+1]
                    historical_ma = statistics.mean(window_prices)
                    if historical_ma != 0:
                        deviation = ((prices[i] - historical_ma) / historical_ma) * 100
                        historical_deviations.append(deviation)
            
            # 如果历史偏离数据不足，使用价格本身计算Z分数
            if len(historical_deviations) < 10:
                # 使用价格序列直接计算Z分数
                if len(prices) >= 10:
                    z_score = self.calculate_z_score(current_price, prices)
                    metadata_deviation_type = "price_z_score"
                    deviation_std = statistics.stdev(prices) if len(prices) > 1 else 0
                else:
                    return self.create_result(
                        hit=False,
                        score=0.0,
                        confidence=0.0,
                        signals=["历史数据不足，无法计算Z分数"],
                        metadata={"error": "历史数据不足"}
                    )
            else:
                # 使用偏离序列计算Z分数
                z_score = self.calculate_z_score(price_deviation_pct, historical_deviations)
                metadata_deviation_type = "deviation_z_score"
                deviation_std = statistics.stdev(historical_deviations) if len(historical_deviations) > 1 else 0
            
            # 计算当前偏离的历史百分位（如果历史偏离数据足够）
            if historical_deviations and len(historical_deviations) >= 20:
                percentile = self.calculate_price_deviation_percentile(
                    current_price, ma60, historical_deviations
                )
                metadata_percentile = round(percentile, 4)
            else:
                percentile = 0.5
                metadata_percentile = None
            
            # 生成信号
            signals = []
            metadata = {
                "current_price": current_price,
                f"ma{ma_window}": ma60,
                "price_deviation_percent": round(price_deviation_pct, 4),
                "z_score": round(z_score, 4),
                "deviation_type": metadata_deviation_type,
                "deviation_std": round(deviation_std, 4) if deviation_std else 0.0,
                "deviation_percentile": metadata_percentile,
                "historical_deviations_count": len(historical_deviations),
                "calculation_window": ma_window
            }
            
            hit = False
            score = 0.0
            confidence = 0.5
            
            # 规则1: 极端Z分数（|Z| > 2.5）
            if abs(z_score) > 2.5:
                hit = True
                # Z分数绝对值越大，得分越高
                z_abs = abs(z_score)
                score = 30.0 + min(z_abs * 15.0, 70.0)  # 30-100分
                confidence = min(0.9, 0.5 + (z_abs - 2.5) * 0.1)
                
                if z_score < -2.5:
                    signals.append(f"极端低估: Z分数={z_score:.2f} < -2.5")
                    metadata["signal_type"] = "extreme_undervalued"
                    metadata["mean_reversion_direction"] = "up"
                else:
                    signals.append(f"极端高估: Z分数={z_score:.2f} > 2.5")
                    metadata["signal_type"] = "extreme_overvalued"
                    metadata["mean_reversion_direction"] = "down"
            
            # 规则2: 显著Z分数（|Z| > 2.0）
            elif abs(z_score) > 2.0:
                hit = True
                z_abs = abs(z_score)
                score = 20.0 + (z_abs - 2.0) * 20.0  # 20-40分
                confidence = 0.5 + (z_abs - 2.0) * 0.1
                
                if z_score < -2.0:
                    signals.append(f"显著低估: Z分数={z_score:.2f} < -2.0")
                    metadata["signal_type"] = "significantly_undervalued"
                else:
                    signals.append(f"显著高估: Z分数={z_score:.2f} > 2.0")
                    metadata["signal_type"] = "significantly_overvalued"
            
            # 规则3: 适度Z分数（|Z| > 1.5）
            elif abs(z_score) > 1.5:
                hit = True
                z_abs = abs(z_score)
                score = 10.0 + (z_abs - 1.5) * 20.0  # 10-30分
                confidence = 0.4
                
                if z_score < -1.5:
                    signals.append(f"适度低估: Z分数={z_score:.2f} < -1.5")
                    metadata["signal_type"] = "moderately_undervalued"
                else:
                    signals.append(f"适度高估: Z分数={z_score:.2f} > 1.5")
                    metadata["signal_type"] = "moderately_overvalued"
            
            # 规则4: 基于百分位的信号（如果历史数据足够）
            if metadata_percentile is not None:
                if percentile < 0.1:  # 历史最低10%
                    hit = True
                    # 补充得分
                    score = max(score, 25.0 + (0.1 - percentile) * 150.0)  # 25-40分
                    signals.append(f"历史性低位: 偏离处于历史最低{percentile*100:.1f}%")
                    metadata["historical_position"] = "extreme_low"
                
                elif percentile > 0.9:  # 历史最高10%
                    hit = True
                    score = max(score, 25.0 + (percentile - 0.9) * 150.0)  # 25-40分
                    signals.append(f"历史性高位: 偏离处于历史最高{(1-percentile)*100:.1f}%")
                    metadata["historical_position"] = "extreme_high"
            
            if not signals:
                signals.append(f"Z分数正常: {z_score:.2f}")
                metadata["signal_type"] = "normal"
            
            # 添加趋势分析
            if len(prices) >= ma_window * 2:
                # 计算当前Z分数和30天前的Z分数对比
                recent_prices = prices[:ma_window]
                older_prices = prices[30:30+ma_window] if len(prices) >= 30+ma_window else prices[ma_window:2*ma_window]
                
                if len(recent_prices) >= 10 and len(older_prices) >= 10:
                    recent_price = recent_prices[0]
                    older_price = older_prices[0] if older_prices else older_prices[-1]
                    
                    recent_ma = statistics.mean(recent_prices)
                    older_ma = statistics.mean(older_prices)
                    
                    if recent_ma != 0 and older_ma != 0:
                        recent_deviation = ((recent_price - recent_ma) / recent_ma) * 100
                        older_deviation = ((older_price - older_ma) / older_ma) * 100
                        
                        deviation_change = recent_deviation - older_deviation
                        metadata["deviation_30d_change"] = round(deviation_change, 4)
                        
                        if abs(deviation_change) > 5:
                            if deviation_change > 0:
                                signals.append("偏离程度在扩大")
                            else:
                                signals.append("偏离程度在缩小")
            
            return self.create_result(
                hit=hit,
                score=score,
                confidence=confidence,
                signals=signals,
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Z-Score-Bias分析失败: {e}")
            return self.create_result(
                hit=False,
                score=0.0,
                confidence=0.0,
                signals=[f"分析失败: {str(e)}"],
                metadata={"error": str(e)}
            )