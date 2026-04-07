#!/usr/bin/env python3
"""
Volatility Squeeze Strategy (G3) - 波动率挤压策略
结合布林带和Keltner通道识别低波动潜伏期
"""

import statistics
import math
from typing import Dict, Any, List, Optional
from .base_strategy import BaseStrategy


class VolSqueezeStrategy(BaseStrategy):
    """波动率挤压策略"""
    
    def __init__(self):
        super().__init__(
            name="Vol-Squeeze",
            description="结合布林带和Keltner通道识别低波动潜伏期"
        )
    
    def get_required_history_days(self) -> int:
        """需要60天历史数据计算通道"""
        return 60
    
    def calculate_bollinger_bands(self, prices: List[float], window: int = 20, std_dev: float = 2.0) -> Dict[str, Optional[float]]:
        """计算布林带"""
        if len(prices) < window:
            return {"middle": None, "upper": None, "lower": None, "width": None}
        
        window_prices = prices[:window]
        middle = statistics.mean(window_prices)
        
        if len(window_prices) > 1:
            std = statistics.stdev(window_prices)
            upper = middle + std_dev * std
            lower = middle - std_dev * std
            width = (upper - lower) / middle * 100  # 带宽百分比
        else:
            upper = middle
            lower = middle
            width = 0.0
        
        return {
            "middle": middle,
            "upper": upper,
            "lower": lower,
            "width": width
        }
    
    def calculate_keltner_channels(self, prices: List[float], 
                                  window: int = 20, 
                                  atr_multiplier: float = 1.5) -> Dict[str, Optional[float]]:
        """计算Keltner通道"""
        if len(prices) < window + 1:
            return {"middle": None, "upper": None, "lower": None, "width": None}
        
        # 计算EMA作为中线
        window_prices = prices[:window]
        # 简单EMA计算
        ema = statistics.mean(window_prices)
        
        # 计算ATR（平均真实波幅）
        true_ranges = []
        for i in range(1, min(len(prices), window + 1)):
            high = max(prices[i-1], prices[i])
            low = min(prices[i-1], prices[i])
            true_range = high - low
            true_ranges.append(true_range)
        
        if true_ranges:
            atr = statistics.mean(true_ranges)
        else:
            atr = 0.0
        
        upper = ema + atr_multiplier * atr
        lower = ema - atr_multiplier * atr
        width = (upper - lower) / ema * 100 if ema != 0 else 0.0
        
        return {
            "middle": ema,
            "upper": upper,
            "lower": lower,
            "width": width
        }
    
    def calculate_historical_bandwidth_percentile(self, 
                                                 prices: List[float],
                                                 window: int = 20,
                                                 lookback_days: int = 100) -> Dict[str, Any]:
        """计算历史带宽百分位"""
        if len(prices) < lookback_days + window:
            return {"current_width": None, "percentile": None, "historical_widths": []}
        
        # 计算当前带宽
        current_bb = self.calculate_bollinger_bands(prices, window)
        current_width = current_bb["width"]
        
        # 计算历史带宽序列
        historical_widths = []
        for i in range(window, min(len(prices), lookback_days + window)):
            window_prices = prices[i-window:i]
            if len(window_prices) >= window:
                bb = self.calculate_bollinger_bands(window_prices, window)
                if bb["width"] is not None:
                    historical_widths.append(bb["width"])
        
        # 计算百分位
        percentile = None
        if historical_widths and current_width is not None:
            sorted_widths = sorted(historical_widths)
            count_below = sum(1 for w in sorted_widths if w < current_width)
            percentile = count_below / len(sorted_widths)
        
        return {
            "current_width": current_width,
            "percentile": percentile,
            "historical_widths": historical_widths
        }
    
    def analyze(self, 
                ticker: str,
                history_data: Dict[str, Any],
                analysis_data: Optional[Dict[str, Any]] = None,
                global_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        分析波动率挤压
        
        逻辑:
        1. 计算布林带和Keltner通道
        2. 检测布林带是否在Keltner通道内部（波动率挤压）
        3. 分析当前波动率在历史中的百分位
        4. 识别低波动潜伏期
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
            prices = self.get_historical_prices(history_data, days=100)
            if len(prices) < 60:
                return self.create_result(
                    hit=False,
                    score=0.0,
                    confidence=0.0,
                    signals=[f"数据不足，需要60天，实际{len(prices)}天"],
                    metadata={"error": "数据不足"}
                )
            
            current_price = prices[0]
            
            # 计算布林带（20日，2倍标准差）
            bb = self.calculate_bollinger_bands(prices, window=20, std_dev=2.0)
            
            # 计算Keltner通道（20日，1.5倍ATR）
            kc = self.calculate_keltner_channels(prices, window=20, atr_multiplier=1.5)
            
            if bb["middle"] is None or kc["middle"] is None:
                return self.create_result(
                    hit=False,
                    score=0.0,
                    confidence=0.0,
                    signals=["无法计算技术通道"],
                    metadata={"error": "通道计算失败"}
                )
            
            # 计算历史带宽百分位
            bandwidth_analysis = self.calculate_historical_bandwidth_percentile(
                prices, window=20, lookback_days=100
            )
            
            # 检测波动率挤压条件
            squeeze_detected = False
            squeeze_strength = 0.0
            
            # 条件1: 布林带上轨 < Keltner上轨 且 布林带下轨 > Keltner下轨
            if (bb["upper"] is not None and kc["upper"] is not None and
                bb["lower"] is not None and kc["lower"] is not None):
                if bb["upper"] < kc["upper"] and bb["lower"] > kc["lower"]:
                    squeeze_detected = True
                    # 计算挤压强度（重叠比例）
                    bb_width = bb["upper"] - bb["lower"]
                    kc_width = kc["upper"] - kc["lower"]
                    if kc_width > 0:
                        squeeze_strength = 1.0 - (bb_width / kc_width)
                        squeeze_strength = max(0.0, min(1.0, squeeze_strength))
            
            # 生成信号
            signals = []
            metadata = {
                "current_price": current_price,
                "bb_middle": round(bb["middle"], 4) if bb["middle"] else None,
                "bb_upper": round(bb["upper"], 4) if bb["upper"] else None,
                "bb_lower": round(bb["lower"], 4) if bb["lower"] else None,
                "bb_width_percent": round(bb["width"], 4) if bb["width"] else None,
                "kc_middle": round(kc["middle"], 4) if kc["middle"] else None,
                "kc_upper": round(kc["upper"], 4) if kc["upper"] else None,
                "kc_lower": round(kc["lower"], 4) if kc["lower"] else None,
                "kc_width_percent": round(kc["width"], 4) if kc["width"] else None,
                "squeeze_detected": squeeze_detected,
                "squeeze_strength": round(squeeze_strength, 4),
                "bandwidth_percentile": round(bandwidth_analysis["percentile"], 4) if bandwidth_analysis["percentile"] else None,
                "historical_widths_count": len(bandwidth_analysis["historical_widths"]),
                "historical_width_mean": round(statistics.mean(bandwidth_analysis["historical_widths"]), 4) if bandwidth_analysis["historical_widths"] else None
            }
            
            # 判断是否命中
            hit = False
            score = 0.0
            confidence = 0.5
            
            # 规则1: 强烈挤压信号（挤压检测 + 历史低波动）
            if squeeze_detected and bandwidth_analysis["percentile"] is not None:
                if bandwidth_analysis["percentile"] < 0.2:  # 历史最低20%
                    hit = True
                    
                    # 计算得分：基于挤压强度和波动率百分位
                    squeeze_score = squeeze_strength * 40.0  # 挤压强度贡献最多40分
                    percentile_score = (0.2 - bandwidth_analysis["percentile"]) * 100.0  # 百分位贡献
                    
                    score = 30.0 + squeeze_score + percentile_score
                    score = min(100.0, score)
                    
                    confidence = 0.7 + squeeze_strength * 0.2
                    confidence = min(0.9, confidence)
                    
                    signals.append("强烈波动率挤压: 技术通道重叠且历史低波动")
                    metadata["signal_type"] = "strong_squeeze"
                    metadata["squeeze_score"] = round(squeeze_score, 2)
                    metadata["percentile_score"] = round(percentile_score, 2)
            
            # 规则2: 中等挤压信号
            elif squeeze_detected:
                hit = True
                score = 20.0 + squeeze_strength * 30.0
                confidence = 0.5 + squeeze_strength * 0.2
                
                signals.append("波动率挤压: 技术通道重叠")
                metadata["signal_type"] = "moderate_squeeze"
            
            # 规则3: 历史低波动（无挤压）
            elif bandwidth_analysis["percentile"] is not None and bandwidth_analysis["percentile"] < 0.3:
                hit = True
                score = 15.0 + (0.3 - bandwidth_analysis["percentile"]) * 50.0
                confidence = 0.4
                
                signals.append("低波动环境: 历史性波动率收缩")
                metadata["signal_type"] = "low_volatility"
            
            # 规则4: 价格接近通道边界
            if bb["upper"] is not None and bb["lower"] is not None:
                bb_middle = bb["middle"]
                if bb_middle is not None and bb_middle != 0:
                    price_position = (current_price - bb["lower"]) / (bb["upper"] - bb["lower"])
                    
                    if price_position < 0.2:  # 价格在下轨附近
                        hit = True
                        score = max(score, 10.0)  # 确保至少10分
                        signals.append("价格接近布林带下轨")
                        metadata["price_position"] = round(price_position, 4)
                        metadata["position_signal"] = "near_lower_band"
                    
                    elif price_position > 0.8:  # 价格在上轨附近
                        hit = True
                        score = max(score, 10.0)
                        signals.append("价格接近布林带上轨")
                        metadata["price_position"] = round(price_position, 4)
                        metadata["position_signal"] = "near_upper_band"
            
            if not signals:
                signals.append("波动率信号中性")
                metadata["signal_type"] = "neutral"
            
            return self.create_result(
                hit=hit,
                score=score,
                confidence=confidence,
                signals=signals,
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Vol-Squeeze分析失败: {e}")
            return self.create_result(
                hit=False,
                score=0.0,
                confidence=0.0,
                signals=[f"分析失败: {str(e)}"],
                metadata={"error": str(e)}
            )