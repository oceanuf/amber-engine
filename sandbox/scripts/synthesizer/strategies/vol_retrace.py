#!/usr/bin/env python3
"""
Volume Retracement Strategy (G8) - 缩量回踩策略
核心中的核心：识别"缩量回踩"形态
只有量缩到平均值的50%以下且回踩均线不破，才算成功
"""

import statistics
from typing import Dict, Any, List, Optional, Tuple
from .base_strategy import BaseStrategy


class VolumeRetracementStrategy(BaseStrategy):
    """缩量回踩策略"""
    
    def __init__(self):
        super().__init__(
            name="Volume-Retracement",
            description="识别缩量回踩形态：波动率萎缩至50%以下且价格回踩均线不破"
        )
    
    def get_required_history_days(self) -> int:
        """需要60天历史数据用于分析波动率萎缩"""
        return 60
    
    def calculate_atr(self, prices: List[float], period: int = 14) -> Optional[List[float]]:
        """
        计算平均真实波幅（ATR）作为波动率代理
        
        由于缺乏成交量数据，使用价格波动率作为替代
        ATR计算公式：
        1. 真实波幅 TR = max(当日高点-当日低点, |当日高点-前日收盘|, |当日低点-前日收盘|)
        2. 由于我们只有收盘价，简化版：TR = |当日收盘-前日收盘|
        3. ATR = SMA(TR, period)
        
        Args:
            prices: 价格列表（最新的在前）
            period: ATR周期
            
        Returns:
            ATR值列表，如果数据不足返回None
        """
        if len(prices) < period + 1:
            return None
        
        # 计算真实波幅（简化版）
        tr_values = []
        for i in range(period):
            tr = abs(prices[i] - prices[i + 1])  # 简化：当日与前一日的价格差
            tr_values.append(tr)
        
        # 计算ATR（简单移动平均）
        atr_values = []
        for i in range(len(tr_values) - period + 1):
            window = tr_values[i:i+period]
            atr = sum(window) / period
            atr_values.append(atr)
        
        return atr_values
    
    def calculate_volatility_ratio(self, prices: List[float], short_period: int = 5, long_period: int = 20) -> Optional[float]:
        """
        计算波动率比率（短期波动率 / 长期波动率）
        
        用于识别波动率萎缩：
        比率 < 0.5 表示短期波动率萎缩至长期平均的50%以下
        
        Args:
            prices: 价格列表
            short_period: 短期波动率计算周期
            long_period: 长期波动率计算周期
            
        Returns:
            波动率比率，如果数据不足返回None
        """
        if len(prices) < max(short_period, long_period) + 1:
            return None
        
        # 计算价格变化（日收益率）
        returns = []
        for i in range(min(len(prices) - 1, long_period)):
            if prices[i+1] != 0:
                daily_return = (prices[i] - prices[i+1]) / prices[i+1]
                returns.append(abs(daily_return))  # 使用绝对值
        
        if len(returns) < long_period:
            return None
        
        # 计算短期波动率（最近short_period天的平均绝对收益率）
        short_vol = statistics.mean(returns[:short_period]) if returns[:short_period] else 0
        
        # 计算长期波动率（long_period天的平均绝对收益率）
        long_vol = statistics.mean(returns[:long_period]) if returns[:long_period] else 0
        
        if long_vol == 0:
            return None
        
        return short_vol / long_vol
    
    def check_ma_support(self, prices: List[float], ma_period: int = 20, tolerance_pct: float = 2.0) -> Tuple[bool, Optional[float]]:
        """
        检查均线支撑
        
        判断价格是否"回踩均线不破"：
        1. 价格在均线附近（±tolerance_pct%）
        2. 近期价格从上方接近均线（回踩）
        
        Args:
            prices: 价格列表
            ma_period: 均线周期
            tolerance_pct: 容忍百分比
            
        Returns:
            (是否支撑有效, 价格与均线的偏离百分比)
        """
        if len(prices) < ma_period:
            return False, None
        
        current_price = prices[0]
        ma_value = self.calculate_moving_average(prices, ma_period)
        
        if ma_value is None or ma_value == 0:
            return False, None
        
        # 计算价格与均线的偏离百分比
        deviation_pct = ((current_price - ma_value) / ma_value) * 100
        
        # 判断是否在容忍范围内
        within_tolerance = abs(deviation_pct) <= tolerance_pct
        
        # 判断是否从上方回踩（当前价格接近或略低于均线）
        is_retracement_from_above = deviation_pct <= tolerance_pct
        
        # 判断近期趋势：价格是否从高位回落
        if len(prices) >= ma_period * 2:
            # 计算10天前的价格位置
            prices_10d_ago = prices[10:10+ma_period] if len(prices) >= 10+ma_period else prices[ma_period:2*ma_period]
            if prices_10d_ago:
                price_10d_ago = prices_10d_ago[0]
                ma_10d_ago = self.calculate_moving_average(prices_10d_ago, ma_period)
                
                if ma_10d_ago is not None and ma_10d_ago != 0:
                    deviation_10d_ago = ((price_10d_ago - ma_10d_ago) / ma_10d_ago) * 100
                    # 如果10天前价格显著高于均线，现在接近均线，则是回踩
                    is_falling_from_above = deviation_10d_ago > tolerance_pct and deviation_pct <= tolerance_pct
                    
                    is_support = within_tolerance and is_retracement_from_above and is_falling_from_above
                    return is_support, deviation_pct
        
        is_support = within_tolerance and is_retracement_from_above
        return is_support, deviation_pct
    
    def analyze(self, 
                ticker: str,
                history_data: Dict[str, Any],
                analysis_data: Optional[Dict[str, Any]] = None,
                global_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        分析缩量回踩形态
        
        逻辑:
        1. 计算波动率比率（短期/长期）
        2. 检查是否缩量（波动率比率 < 0.5）
        3. 检查价格是否回踩关键均线（MA20）且不破
        4. 确认近期价格从高位回落（回踩动作）
        5. 生成缩量回踩信号
        """
        # 获取历史价格数据
        prices = self.get_historical_prices(history_data, days=60)
        
        if len(prices) < 30:  # 至少需要30天进行有意义分析
            return self.create_result(
                hit=False,
                score=0.0,
                confidence=0.0,
                signals=["数据不足，无法分析缩量回踩"],
                metadata={
                    "error": "数据不足",
                    "available_days": len(prices),
                    "required_days": 30
                }
            )
        
        try:
            current_price = prices[0]
            
            # 1. 计算波动率萎缩
            vol_ratio = self.calculate_volatility_ratio(prices, short_period=5, long_period=20)
            
            # 2. 检查均线支撑
            ma_support_20, deviation_20 = self.check_ma_support(prices, ma_period=20, tolerance_pct=2.0)
            ma_support_10, deviation_10 = self.check_ma_support(prices, ma_period=10, tolerance_pct=2.5)
            
            # 3. 计算ATR（替代成交量）
            atr_values = self.calculate_atr(prices, period=14)
            current_atr = atr_values[0] if atr_values and len(atr_values) > 0 else None
            avg_atr = statistics.mean(atr_values) if atr_values and len(atr_values) > 5 else None
            
            # 4. 计算价格回撤幅度
            price_retracement = None
            if len(prices) >= 20:
                # 寻找近期高点（过去20天内）
                recent_high = max(prices[:20])
                current_price = prices[0]
                if recent_high != 0:
                    price_retracement = ((recent_high - current_price) / recent_high) * 100
            
            # 生成信号和元数据
            signals = []
            metadata = {
                "current_price": current_price,
                "volatility_ratio": round(vol_ratio, 3) if vol_ratio is not None else None,
                "ma20_support": ma_support_20,
                "ma20_deviation_pct": round(deviation_20, 2) if deviation_20 is not None else None,
                "ma10_support": ma_support_10,
                "ma10_deviation_pct": round(deviation_10, 2) if deviation_10 is not None else None,
                "current_atr": round(current_atr, 4) if current_atr is not None else None,
                "avg_atr": round(avg_atr, 4) if avg_atr is not None else None,
                "price_retracement_pct": round(price_retracement, 2) if price_retracement is not None else None,
                "data_days": len(prices)
            }
            
            hit = False
            score = 0.0
            confidence = 0.5
            
            # 规则1: 完美缩量回踩（核心信号）
            perfect_retracement = False
            if (vol_ratio is not None and vol_ratio < 0.5 and  # 波动率萎缩至50%以下
                ma_support_20 and  # 回踩MA20不破
                price_retracement is not None and 0 < price_retracement < 15):  # 适度回撤（0-15%）
                
                perfect_retracement = True
                hit = True
                
                # 根据条件强度计算得分
                base_score = 80.0
                
                # 波动率萎缩程度（越低越好）
                if vol_ratio < 0.3:
                    base_score += 10.0
                    vol_strength = "extreme"
                elif vol_ratio < 0.4:
                    base_score += 5.0
                    vol_strength = "strong"
                else:
                    vol_strength = "moderate"
                
                # 均线支撑精确度（偏离越小越好）
                if deviation_20 is not None and abs(deviation_20) < 1.0:
                    base_score += 5.0
                    support_precision = "excellent"
                elif deviation_20 is not None and abs(deviation_20) < 2.0:
                    base_score += 2.0
                    support_precision = "good"
                else:
                    support_precision = "acceptable"
                
                # 回撤幅度（适中最好）
                if price_retracement is not None and 5 < price_retracement < 10:
                    base_score += 5.0
                    retracement_quality = "optimal"
                elif price_retracement is not None and 0 < price_retracement < 5:
                    retracement_quality = "shallow"
                elif price_retracement is not None and 10 < price_retracement < 15:
                    retracement_quality = "deep"
                else:
                    retracement_quality = "unknown"
                
                score = min(100.0, base_score)
                confidence = 0.8
                
                signals.append(f"完美缩量回踩：波动率萎缩{vol_ratio:.2f}，回踩MA20偏离{deviation_20:.1f}%")
                metadata["signal_strength"] = "perfect"
                metadata["volatility_strength"] = vol_strength
                metadata["support_precision"] = support_precision
                metadata["retracement_quality"] = retracement_quality
            
            # 规则2: 良好缩量回踩（缺少一个条件）
            good_retracement = False
            if not perfect_retracement:
                condition_count = 0
                condition_details = []
                
                if vol_ratio is not None and vol_ratio < 0.6:
                    condition_count += 1
                    condition_details.append(f"波动率萎缩{vol_ratio:.2f}")
                
                if ma_support_20 or ma_support_10:
                    condition_count += 1
                    which_ma = "MA20" if ma_support_20 else "MA10"
                    deviation = deviation_20 if ma_support_20 else deviation_10
                    condition_details.append(f"回踩{which_ma}偏离{deviation:.1f}%")
                
                if price_retracement is not None and 0 < price_retracement < 20:
                    condition_count += 1
                    condition_details.append(f"价格回撤{price_retracement:.1f}%")
                
                if condition_count >= 2:  # 满足至少两个条件
                    good_retracement = True
                    hit = True
                    
                    # 根据满足的条件数量和质量计算得分
                    base_score = 40.0 + (condition_count - 2) * 20.0  # 40-80分
                    
                    # 额外加分项
                    if vol_ratio is not None and vol_ratio < 0.5:
                        base_score += 10.0
                    
                    if ma_support_20 and deviation_20 is not None and abs(deviation_20) < 1.5:
                        base_score += 5.0
                    
                    score = min(100.0, base_score)
                    confidence = 0.6
                    
                    condition_str = "，".join(condition_details)
                    signals.append(f"良好缩量回踩：{condition_str}")
                    metadata["signal_strength"] = "good"
                    metadata["met_conditions"] = condition_count
            
            # 规则3: 波动率极度萎缩（单条件强信号）
            if not perfect_retracement and not good_retracement:
                if vol_ratio is not None and vol_ratio < 0.4:
                    hit = True
                    score = 60.0 - vol_ratio * 20.0  # 52-60分（萎缩越严重得分越高）
                    confidence = 0.7
                    
                    signals.append(f"波动率极度萎缩：{vol_ratio:.2f}（长期平均的{vol_ratio*100:.0f}%）")
                    metadata["signal_strength"] = "volatility_extreme"
                    metadata["primary_signal"] = "volatility_collapse"
            
            # 规则4: 精准均线支撑（单条件强信号）
            if not perfect_retracement and not good_retracement:
                if ma_support_20 and deviation_20 is not None and abs(deviation_20) < 1.0:
                    hit = True
                    score = 50.0 + (1.0 - abs(deviation_20)) * 10.0  # 50-60分
                    confidence = 0.6
                    
                    signals.append(f"精准均线支撑：偏离MA20仅{deviation_20:.2f}%")
                    metadata["signal_strength"] = "precision_support"
                    metadata["primary_signal"] = "ma_support"
            
            # 规则5: ATR萎缩确认
            if current_atr is not None and avg_atr is not None and avg_atr > 0:
                atr_ratio = current_atr / avg_atr
                metadata["atr_ratio"] = round(atr_ratio, 3)
                
                if atr_ratio < 0.6:
                    # 加强现有信号或提供补充信号
                    if hit:
                        score = min(100.0, score + 5.0)
                        signals.append(f"ATR萎缩确认：{atr_ratio:.2f}")
                    else:
                        hit = True
                        score = 40.0 + (0.6 - atr_ratio) * 50.0  # 40-55分
                        confidence = 0.5
                        signals.append(f"ATR萎缩：{atr_ratio:.2f}")
                        metadata["signal_strength"] = "atr_based"
            
            if not signals:
                # 生成状态报告
                status_parts = []
                if vol_ratio is not None:
                    status_parts.append(f"波动率比率{vol_ratio:.2f}")
                if deviation_20 is not None:
                    status_parts.append(f"MA20偏离{deviation_20:.1f}%")
                
                if status_parts:
                    signals.append("状态：" + "，".join(status_parts))
                else:
                    signals.append("无显著缩量回踩信号")
                
                metadata["signal_strength"] = "neutral"
            
            # 添加趋势上下文
            if len(prices) >= 50:
                # 计算短期趋势（最近10天）
                if len(prices) >= 10:
                    recent_trend = ((prices[0] - prices[9]) / prices[9]) * 100 if prices[9] != 0 else 0
                    metadata["recent_10d_trend_pct"] = round(recent_trend, 2)
                    
                    if recent_trend < -2:
                        signals.append("短期下跌趋势")
                    elif recent_trend > 2:
                        signals.append("短期上涨趋势")
                
                # 计算中期趋势（最近30天）
                if len(prices) >= 30:
                    mid_trend = ((prices[0] - prices[29]) / prices[29]) * 100 if prices[29] != 0 else 0
                    metadata["mid_30d_trend_pct"] = round(mid_trend, 2)
            
            return self.create_result(
                hit=hit,
                score=score,
                confidence=confidence,
                signals=signals,
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Volume-Retracement分析失败: {e}")
            return self.create_result(
                hit=False,
                score=0.0,
                confidence=0.0,
                signals=[f"分析失败: {str(e)}"],
                metadata={"error": str(e)}
            )