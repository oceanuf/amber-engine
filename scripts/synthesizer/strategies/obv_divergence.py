#!/usr/bin/env python3
"""
OBV Divergence Strategy (G10) - 能量潮背离策略
监测OBV指标，当价格横盘震荡而OBV指标向上突破时，捕捉主力潜伏吸筹的信号
"""

import statistics
from typing import Dict, Any, List, Optional, Tuple
from .base_strategy import BaseStrategy


class OBVDivergenceStrategy(BaseStrategy):
    """能量潮背离策略"""
    
    def __init__(self):
        super().__init__(
            name="OBV-Divergence",
            description="监测OBV指标背离，捕捉主力资金潜伏吸筹信号"
        )
    
    def get_required_history_days(self) -> int:
        """需要60天历史数据用于OBV计算和背离检测"""
        return 60
    
    def simulate_volume_data(self, prices: List[float]) -> List[float]:
        """
        模拟成交量数据（由于当前数据源无成交量）
        
        真实环境中应从历史数据中获取实际成交量
        模拟逻辑：价格波动大的日子通常伴随较高成交量
        
        Args:
            prices: 价格序列
            
        Returns:
            模拟成交量序列
        """
        volumes = []
        
        for i in range(len(prices)):
            if i == 0:
                # 首日使用基准成交量
                base_volume = 1000000  # 基准成交量
                volatility = 0.02  # 基准波动率
            else:
                # 计算价格变化率
                price_change = abs((prices[i-1] - prices[i]) / prices[i])
                # 波动率越大，成交量越高
                volatility = min(0.1, max(0.01, price_change * 5))
            
            # 生成模拟成交量：基准 × 波动率系数 × 随机因子
            import random
            random_factor = random.uniform(0.8, 1.2)  # 80%-120%随机波动
            volume = 1000000 * volatility * random_factor
            volumes.append(volume)
        
        return volumes
    
    def calculate_obv(self, prices: List[float], volumes: List[float]) -> List[float]:
        """
        计算OBV（能量潮）指标
        
        OBV公式:
        - 如果今日收盘价 > 昨日收盘价: OBV = 前一日OBV + 今日成交量
        - 如果今日收盘价 < 昨日收盘价: OBV = 前一日OBV - 今日成交量
        - 如果今日收盘价 = 昨日收盘价: OBV = 前一日OBV
        
        Args:
            prices: 价格序列（最新在前）
            volumes: 成交量序列（与价格对应）
            
        Returns:
            OBV序列（与价格对应顺序）
        """
        if len(prices) != len(volumes) or len(prices) == 0:
            return []
        
        # 反转序列为时间顺序（最旧在前）
        prices_chrono = list(reversed(prices))
        volumes_chrono = list(reversed(volumes))
        
        obv_values = [volumes_chrono[0]]  # 初始OBV为第一日成交量
        
        for i in range(1, len(prices_chrono)):
            if prices_chrono[i] > prices_chrono[i-1]:
                # 价格上涨，OBV增加
                obv = obv_values[-1] + volumes_chrono[i]
            elif prices_chrono[i] < prices_chrono[i-1]:
                # 价格下跌，OBV减少
                obv = obv_values[-1] - volumes_chrono[i]
            else:
                # 价格不变，OBV不变
                obv = obv_values[-1]
            
            obv_values.append(obv)
        
        # 反转回最新在前顺序
        return list(reversed(obv_values))
    
    def detect_divergence(self, 
                         prices: List[float], 
                         obv_values: List[float],
                         window: int = 20) -> Dict[str, Any]:
        """
        检测价格与OBV的背离
        
        背离类型:
        1. 看涨背离: 价格下跌或横盘，但OBV上升
        2. 看跌背离: 价格上涨，但OBV下降
        
        Args:
            prices: 价格序列（最新在前）
            obv_values: OBV序列（最新在前）
            window: 分析窗口
            
        Returns:
            背离检测结果
        """
        if len(prices) < window or len(obv_values) < window:
            return {
                "divergence_detected": False,
                "divergence_type": "none",
                "strength": 0.0,
                "price_trend": "unknown",
                "obv_trend": "unknown",
                "confidence": 0.0
            }
        
        # 分析价格趋势（使用最近window天的数据）
        recent_prices = prices[:window]
        recent_obv = obv_values[:window]
        
        # 计算价格趋势（线性回归斜率）
        price_slope = self.calculate_trend_slope(recent_prices)
        obv_slope = self.calculate_trend_slope(recent_obv)
        
        # 计算价格和OBV的波动性
        price_volatility = statistics.stdev(recent_prices) / statistics.mean(recent_prices) if len(recent_prices) > 1 else 0
        obv_volatility = statistics.stdev(recent_obv) / statistics.mean(recent_obv) if len(recent_obv) > 1 and statistics.mean(recent_obv) != 0 else 0
        
        # 判断趋势方向
        price_trend = "up" if price_slope > 0.001 else ("down" if price_slope < -0.001 else "flat")
        obv_trend = "up" if obv_slope > 0 else ("down" if obv_slope < 0 else "flat")
        
        # 检测背离
        divergence_detected = False
        divergence_type = "none"
        strength = 0.0
        confidence = 0.0
        
        # 看涨背离条件：价格横盘或下跌，但OBV明显上升
        if price_trend in ["flat", "down"] and obv_trend == "up":
            # 计算背离强度
            price_change = (recent_prices[0] - recent_prices[-1]) / recent_prices[-1]
            obv_change = (recent_obv[0] - recent_obv[-1]) / abs(recent_obv[-1]) if recent_obv[-1] != 0 else 0
            
            # OBV上升幅度越大，背离信号越强
            if obv_change > 0.1:  # OBV上升超过10%
                divergence_detected = True
                divergence_type = "bullish"
                strength = min(1.0, obv_change * 2)  # 强度与OBV变化成正比
                confidence = 0.6 + min(0.3, strength * 0.3)
                
                # 如果价格明显下跌而OBV上升，信号更强
                if price_trend == "down" and price_change < -0.05:
                    strength = min(1.0, strength * 1.5)
                    confidence = min(0.9, confidence + 0.1)
        
        # 看跌背离条件：价格上涨，但OBV下降
        elif price_trend == "up" and obv_trend == "down":
            price_change = (recent_prices[0] - recent_prices[-1]) / recent_prices[-1]
            obv_change = (recent_obv[0] - recent_obv[-1]) / abs(recent_obv[-1]) if recent_obv[-1] != 0 else 0
            
            if obv_change < -0.1:  # OBV下降超过10%
                divergence_detected = True
                divergence_type = "bearish"
                strength = min(1.0, abs(obv_change) * 2)
                confidence = 0.6 + min(0.3, strength * 0.3)
                
                # 如果价格明显上涨而OBV下降，信号更强
                if price_change > 0.05:
                    strength = min(1.0, strength * 1.5)
                    confidence = min(0.9, confidence + 0.1)
        
        # 横盘突破检测：价格窄幅震荡，OBV突破前高
        if price_volatility < 0.02 and obv_volatility > 0.05:  # 低价格波动，高OBV波动
            # 检查OBV是否突破近期高点
            obv_high = max(recent_obv)
            obv_current = recent_obv[0]
            
            if obv_current > obv_high * 1.05:  # OBV突破前高5%
                divergence_detected = True
                divergence_type = "breakout"
                strength = min(1.0, (obv_current / obv_high - 1) * 10)
                confidence = 0.7
                price_trend = "flat_breakout"
        
        return {
            "divergence_detected": divergence_detected,
            "divergence_type": divergence_type,
            "strength": round(strength, 4),
            "price_trend": price_trend,
            "obv_trend": obv_trend,
            "price_slope": round(price_slope, 6),
            "obv_slope": round(obv_slope, 6),
            "price_volatility": round(price_volatility, 4),
            "obv_volatility": round(obv_volatility, 4),
            "confidence": round(confidence, 4)
        }
    
    def calculate_trend_slope(self, values: List[float]) -> float:
        """计算线性趋势斜率（简单线性回归）"""
        if len(values) < 2:
            return 0.0
        
        n = len(values)
        x = list(range(n))
        
        # 计算斜率（简化公式）
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x[i] * values[i] for i in range(n))
        sum_x2 = sum(x[i] * x[i] for i in range(n))
        
        numerator = n * sum_xy - sum_x * sum_y
        denominator = n * sum_x2 - sum_x * sum_x
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def analyze(self, 
                ticker: str,
                history_data: Dict[str, Any],
                analysis_data: Optional[Dict[str, Any]] = None,
                global_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        分析OBV背离信号
        
        逻辑:
        1. 获取历史价格数据
        2. 生成模拟成交量数据（实际环境中使用真实成交量）
        3. 计算OBV指标
        4. 检测价格与OBV的背离
        5. 生成交易信号
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
            prices = self.get_historical_prices(history_data, days=60)
            if len(prices) < 20:
                return self.create_result(
                    hit=False,
                    score=50.0,
                    confidence=0.3,
                    signals=["历史数据不足，无法进行OBV分析"],
                    metadata={"error": "历史数据不足"}
                )
            
            # 模拟成交量数据（实际环境应使用真实成交量）
            volumes = self.simulate_volume_data(prices)
            
            # 计算OBV指标
            obv_values = self.calculate_obv(prices, volumes)
            
            if not obv_values:
                return self.create_result(
                    hit=False,
                    score=50.0,
                    confidence=0.3,
                    signals=["无法计算OBV指标"],
                    metadata={"error": "OBV计算失败"}
                )
            
            # 检测背离
            divergence = self.detect_divergence(prices, obv_values, window=20)
            
            # 生成信号
            signals = []
            metadata = {
                "divergence_detected": divergence["divergence_detected"],
                "divergence_type": divergence["divergence_type"],
                "divergence_strength": divergence["strength"],
                "price_trend": divergence["price_trend"],
                "obv_trend": divergence["obv_trend"],
                "price_slope": divergence["price_slope"],
                "obv_slope": divergence["obv_slope"],
                "price_volatility": divergence["price_volatility"],
                "obv_volatility": divergence["obv_volatility"],
                "current_price": prices[0],
                "current_obv": obv_values[0],
                "obv_values_count": len(obv_values),
                "data_source": "simulated_volume"  # 标记为模拟成交量
            }
            
            # 判断是否命中
            hit = divergence["divergence_detected"]
            confidence = divergence["confidence"]
            
            # 根据背离类型计算得分
            score = 50.0  # 基准分
            
            if divergence["divergence_type"] == "bullish":
                # 看涨背离：得分与强度成正比
                score = 60.0 + divergence["strength"] * 40.0
                signals.append(f"看涨背离: 价格{divergence['price_trend']}，OBV{divergence['obv_trend']}，强度{divergence['strength']:.2f}")
                metadata["signal_type"] = "bullish_divergence"
                
            elif divergence["divergence_type"] == "bearish":
                # 看跌背离：得分与强度成反比
                score = 40.0 - divergence["strength"] * 40.0
                signals.append(f"看跌背离: 价格{divergence['price_trend']}，OBV{divergence['obv_trend']}，强度{divergence['strength']:.2f}")
                metadata["signal_type"] = "bearish_divergence"
                
            elif divergence["divergence_type"] == "breakout":
                # 横盘突破
                score = 70.0 + divergence["strength"] * 30.0
                signals.append(f"OBV突破: 价格横盘，OBV突破前高，强度{divergence['strength']:.2f}")
                metadata["signal_type"] = "obv_breakout"
                
            else:
                # 无背离
                score = 50.0
                signals.append(f"无显著背离: 价格{divergence['price_trend']}，OBV{divergence['obv_trend']}")
                metadata["signal_type"] = "no_divergence"
            
            score = max(0.0, min(100.0, score))
            
            # 添加数据质量说明
            if metadata["data_source"] == "simulated_volume":
                signals.append("注意: 使用模拟成交量数据，需接入真实成交量")
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
            self.logger.error(f"OBV-Divergence分析失败: {e}")
            return self.create_result(
                hit=False,
                score=50.0,
                confidence=0.0,
                signals=[f"OBV分析失败: {str(e)}"],
                metadata={"error": str(e)}
            )