#!/usr/bin/env python3
"""
Triple Cross Strategy (G7) - 三重均线交叉策略
实现5/20/60/120四重均线的"多头排列"监测
识别强势趋势结构
"""

import statistics
from typing import Dict, Any, List, Optional, Tuple
from .base_strategy import BaseStrategy


class TripleCrossStrategy(BaseStrategy):
    """三重均线交叉策略"""
    
    def __init__(self):
        super().__init__(
            name="Triple-Cross",
            description="监测5/20/60/120四重均线的多头排列，识别强势趋势结构"
        )
    
    def get_required_history_days(self) -> int:
        """需要120天历史数据用于计算120日均线"""
        return 120
    
    def calculate_multiple_mas(self, prices: List[float]) -> Dict[str, Optional[float]]:
        """
        计算多重移动平均线
        
        Returns:
            包含各周期均线的字典
        """
        ma_periods = [5, 20, 60, 120]
        mas = {}
        
        for period in ma_periods:
            if len(prices) >= period:
                mas[f"ma{period}"] = self.calculate_moving_average(prices, period)
            else:
                mas[f"ma{period}"] = None
        
        return mas
    
    def check_bullish_alignment(self, mas: Dict[str, Optional[float]]) -> Tuple[bool, List[str]]:
        """
        检查多头排列
        
        多头排列条件:
        1. MA5 > MA20 > MA60 > MA120 (严格排序)
        2. 所有均线方向向上（可选，需要历史数据）
        
        Returns:
            (是否多头排列, 违反的条件列表)
        """
        violations = []
        
        # 检查均线是否存在
        required_mas = ["ma5", "ma20", "ma60", "ma120"]
        for ma_key in required_mas:
            if mas.get(ma_key) is None:
                violations.append(f"{ma_key}无法计算")
                return False, violations
        
        # 检查多头排列顺序
        if not (mas["ma5"] > mas["ma20"]):
            violations.append("MA5 ≤ MA20")
        
        if not (mas["ma20"] > mas["ma60"]):
            violations.append("MA20 ≤ MA60")
        
        if not (mas["ma60"] > mas["ma120"]):
            violations.append("MA60 ≤ MA120")
        
        is_bullish = len(violations) == 0
        return is_bullish, violations
    
    def check_bearish_alignment(self, mas: Dict[str, Optional[float]]) -> Tuple[bool, List[str]]:
        """
        检查空头排列
        
        空头排列条件:
        1. MA5 < MA20 < MA60 < MA120 (严格排序)
        
        Returns:
            (是否空头排列, 违反的条件列表)
        """
        violations = []
        
        # 检查均线是否存在
        required_mas = ["ma5", "ma20", "ma60", "ma120"]
        for ma_key in required_mas:
            if mas.get(ma_key) is None:
                violations.append(f"{ma_key}无法计算")
                return False, violations
        
        # 检查空头排列顺序
        if not (mas["ma5"] < mas["ma20"]):
            violations.append("MA5 ≥ MA20")
        
        if not (mas["ma20"] < mas["ma60"]):
            violations.append("MA20 ≥ MA60")
        
        if not (mas["ma60"] < mas["ma120"]):
            violations.append("MA60 ≥ MA120")
        
        is_bearish = len(violations) == 0
        return is_bearish, violations
    
    def calculate_ma_trend(self, prices: List[float], period: int, lookback_days: int = 5) -> Optional[float]:
        """
        计算均线趋势（斜率）
        
        Args:
            prices: 价格序列
            period: 均线周期
            lookback_days: 回顾天数（用于计算趋势）
            
        Returns:
            趋势斜率（正数表示向上），如果无法计算返回None
        """
        if len(prices) < period + lookback_days:
            return None
        
        # 计算当前均线值
        current_ma = self.calculate_moving_average(prices[:period], period)
        
        # 计算lookback_days前的均线值
        lookback_prices = prices[lookback_days:lookback_days+period]
        if len(lookback_prices) < period:
            return None
        
        previous_ma = self.calculate_moving_average(lookback_prices, period)
        
        if current_ma is None or previous_ma is None or previous_ma == 0:
            return None
        
        # 计算百分比变化
        trend_pct = ((current_ma - previous_ma) / previous_ma) * 100
        return trend_pct
    
    def analyze(self, 
                ticker: str,
                history_data: Dict[str, Any],
                analysis_data: Optional[Dict[str, Any]] = None,
                global_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        分析均线排列
        
        逻辑:
        1. 计算5/20/60/120日均线
        2. 检查多头/空头排列
        3. 分析均线趋势方向
        4. 评估趋势强度和稳定性
        5. 生成趋势信号
        """
        # 验证数据充足性（但允许部分均线无法计算）
        prices = self.get_historical_prices(history_data, days=120)
        
        if len(prices) < 20:  # 至少需要20天计算MA5和MA20
            return self.create_result(
                hit=False,
                score=0.0,
                confidence=0.0,
                signals=["数据不足，无法计算均线系统"],
                metadata={
                    "error": "数据不足",
                    "available_days": len(prices),
                    "required_days": 20
                }
            )
        
        try:
            # 计算多重移动平均线
            mas = self.calculate_multiple_mas(prices)
            
            # 获取当前价格
            current_price = prices[0] if prices else None
            
            # 检查多头排列
            is_bullish, bullish_violations = self.check_bullish_alignment(mas)
            
            # 检查空头排列
            is_bearish, bearish_violations = self.check_bearish_alignment(mas)
            
            # 生成信号和元数据
            signals = []
            metadata = {
                "current_price": current_price,
                "ma5": mas.get("ma5"),
                "ma20": mas.get("ma20"),
                "ma60": mas.get("ma60"),
                "ma120": mas.get("ma120"),
                "is_bullish_alignment": is_bullish,
                "is_bearish_alignment": is_bearish,
                "bullish_violations": bullish_violations,
                "bearish_violations": bearish_violations,
                "available_periods": []
            }
            
            # 记录可用的均线周期
            for period in [5, 20, 60, 120]:
                if mas.get(f"ma{period}") is not None:
                    metadata["available_periods"].append(period)
            
            hit = False
            score = 0.0
            confidence = 0.5
            
            # 规则1: 完美多头排列
            if is_bullish:
                hit = True
                score = 80.0  # 基础高分
                confidence = 0.7
                
                # 检查价格位置
                if current_price is not None and mas["ma5"] is not None:
                    if current_price > mas["ma5"]:
                        signals.append("完美多头排列：价格在MA5之上")
                        score += 10.0
                        metadata["price_position"] = "above_ma5"
                    else:
                        signals.append("完美多头排列：价格在MA5之下")
                        metadata["price_position"] = "below_ma5"
                
                # 检查均线趋势
                trend_strength = 0
                for period in [5, 20, 60, 120]:
                    trend = self.calculate_ma_trend(prices, period, lookback_days=5)
                    if trend is not None:
                        metadata[f"ma{period}_trend_5d"] = round(trend, 4)
                        if trend > 0:
                            trend_strength += 1
                
                if trend_strength >= 3:  # 至少3条均线向上
                    signals.append("均线系统整体向上")
                    score += 5.0
                    confidence = min(0.9, confidence + 0.1)
                
                metadata["trend_strength"] = trend_strength
                metadata["signal_type"] = "perfect_bullish_alignment"
            
            # 规则2: 完美空头排列
            elif is_bearish:
                hit = True
                score = 20.0  # 空头排列得分较低（反向信号）
                confidence = 0.6
                
                signals.append("完美空头排列：趋势向下")
                metadata["signal_type"] = "perfect_bearish_alignment"
                
                # 空头排列时，如果价格在MA5之下，趋势更强
                if current_price is not None and mas["ma5"] is not None:
                    if current_price < mas["ma5"]:
                        signals.append("价格在MA5之下，下跌趋势强劲")
                        metadata["price_position"] = "below_ma5"
                    else:
                        metadata["price_position"] = "above_ma5"
            
            # 规则3: 部分多头排列（MA5 > MA20 > MA60）
            elif (mas.get("ma5") is not None and mas.get("ma20") is not None and 
                  mas.get("ma60") is not None and mas["ma5"] > mas["ma20"] > mas["ma60"]):
                hit = True
                
                # 检查MA60和MA120的关系
                if mas.get("ma120") is not None:
                    if mas["ma60"] > mas["ma120"]:
                        signals.append("强势多头排列：MA5>MA20>MA60>MA120")
                        score = 70.0
                        metadata["signal_type"] = "strong_bullish_alignment"
                    else:
                        signals.append("中期多头排列：MA5>MA20>MA60")
                        score = 50.0
                        metadata["signal_type"] = "medium_term_bullish"
                else:
                    signals.append("短期多头排列：MA5>MA20>MA60")
                    score = 40.0
                    metadata["signal_type"] = "short_term_bullish"
                
                confidence = 0.6
            
            # 规则4: 部分空头排列（MA5 < MA20 < MA60）
            elif (mas.get("ma5") is not None and mas.get("ma20") is not None and 
                  mas.get("ma60") is not None and mas["ma5"] < mas["ma20"] < mas["ma60"]):
                hit = True
                
                if mas.get("ma120") is not None:
                    if mas["ma60"] < mas["ma120"]:
                        signals.append("强势空头排列：MA5<MA20<MA60<MA120")
                        score = 30.0
                        metadata["signal_type"] = "strong_bearish_alignment"
                    else:
                        signals.append("中期空头排列：MA5<MA20<MA60")
                        score = 40.0
                        metadata["signal_type"] = "medium_term_bearish"
                else:
                    signals.append("短期空头排列：MA5<MA20<MA60")
                    score = 40.0
                    metadata["signal_type"] = "short_term_bearish"
                
                confidence = 0.6
            
            # 规则5: 黄金交叉（MA5上穿MA20）
            elif (mas.get("ma5") is not None and mas.get("ma20") is not None and 
                  len(prices) >= 25):  # 需要足够数据判断交叉
                # 计算5天前的MA5和MA20
                if len(prices) >= 30:
                    prices_5d_ago = prices[5:25]  # 5天前的价格（用于计算5天前的MA5和MA20）
                    mas_5d_ago = self.calculate_multiple_mas(prices_5d_ago)
                    
                    if (mas_5d_ago.get("ma5") is not None and mas_5d_ago.get("ma20") is not None and
                        mas_5d_ago["ma5"] <= mas_5d_ago["ma20"] and mas["ma5"] > mas["ma20"]):
                        hit = True
                        score = 60.0
                        confidence = 0.6
                        signals.append("黄金交叉：MA5上穿MA20")
                        metadata["signal_type"] = "golden_cross"
            
            # 规则6: 死亡交叉（MA5下穿MA20）
            elif (mas.get("ma5") is not None and mas.get("ma20") is not None and 
                  len(prices) >= 25):
                if len(prices) >= 30:
                    prices_5d_ago = prices[5:25]
                    mas_5d_ago = self.calculate_multiple_mas(prices_5d_ago)
                    
                    if (mas_5d_ago.get("ma5") is not None and mas_5d_ago.get("ma20") is not None and
                        mas_5d_ago["ma5"] >= mas_5d_ago["ma20"] and mas["ma5"] < mas["ma20"]):
                        hit = True
                        score = 30.0
                        confidence = 0.6
                        signals.append("死亡交叉：MA5下穿MA20")
                        metadata["signal_type"] = "death_cross"
            
            # 规则7: 均线粘合（多条均线接近）
            if (mas.get("ma5") is not None and mas.get("ma20") is not None and 
                mas.get("ma60") is not None):
                # 计算均线之间的最大差距
                ma_values = [mas["ma5"], mas["ma20"], mas["ma60"]]
                max_ma = max(ma_values)
                min_ma = min(ma_values)
                range_pct = ((max_ma - min_ma) / min_ma) * 100 if min_ma != 0 else 0
                
                if range_pct < 2.0:  # 均线粘合（差距小于2%）
                    if not hit:  # 如果没有其他信号
                        hit = True
                        score = 20.0
                        confidence = 0.4
                    
                    signals.append(f"均线粘合：MA5/20/60差距{range_pct:.1f}%")
                    metadata["ma_convergence"] = True
                    metadata["ma_range_pct"] = round(range_pct, 2)
                else:
                    metadata["ma_convergence"] = False
                    metadata["ma_range_pct"] = round(range_pct, 2)
            
            if not signals:
                # 生成基础状态信号
                if mas.get("ma5") is not None and mas.get("ma20") is not None:
                    if mas["ma5"] > mas["ma20"]:
                        signals.append("MA5 > MA20 (短期偏多)")
                    else:
                        signals.append("MA5 ≤ MA20 (短期偏空)")
                
                metadata["signal_type"] = "neutral"
            
            # 添加价格与均线关系
            if current_price is not None:
                for period in [5, 20, 60, 120]:
                    ma_key = f"ma{period}"
                    if mas.get(ma_key) is not None:
                        ma_value = mas[ma_key]
                        price_vs_ma = ((current_price - ma_value) / ma_value) * 100 if ma_value != 0 else 0
                        metadata[f"price_vs_ma{period}_pct"] = round(price_vs_ma, 2)
                        
                        if period == 20:  # MA20是重要参考
                            if price_vs_ma > 5:
                                signals.append(f"价格显著高于MA20 (+{price_vs_ma:.1f}%)")
                            elif price_vs_ma < -5:
                                signals.append(f"价格显著低于MA20 ({price_vs_ma:.1f}%)")
            
            return self.create_result(
                hit=hit,
                score=score,
                confidence=confidence,
                signals=signals,
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Triple-Cross分析失败: {e}")
            return self.create_result(
                hit=False,
                score=0.0,
                confidence=0.0,
                signals=[f"分析失败: {str(e)}"],
                metadata={"error": str(e)}
            )