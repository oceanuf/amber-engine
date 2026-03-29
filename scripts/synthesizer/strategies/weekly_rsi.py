#!/usr/bin/env python3
"""
Weekly RSI Strategy (G5) - 周线RSI超买超卖屏障
建立周线级的超买超卖屏障（30/70规则），并提供一票否决权能力
"""

import statistics
from typing import Dict, Any, List, Optional, Tuple
from .base_strategy import BaseStrategy


class WeeklyRSIStrategy(BaseStrategy):
    """周线RSI策略"""
    
    def __init__(self):
        super().__init__(
            name="Weekly-RSI",
            description="周线相对强弱指数策略，30/70超买超卖规则，提供一票否决权"
        )
    
    def get_required_history_days(self) -> int:
        """
        获取所需历史数据天数
        
        对于周线RSI，需要至少70天（14周×5交易日）
        如果数据不足，可以降级使用日线RSI（需要至少14天）
        """
        return 70  # 14周数据
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """
        计算RSI（相对强弱指数）
        
        Args:
            prices: 价格列表（最新的在前）
            period: RSI周期（默认14）
            
        Returns:
            RSI值（0-100），如果数据不足返回None
        """
        if len(prices) < period + 1:  # 需要period+1个价格点计算period个变化
            return None
        
        # 计算价格变化
        changes = []
        for i in range(period):
            change = prices[i] - prices[i + 1]  # 当前价格 - 前一天价格
            changes.append(change)
        
        # 分离上涨和下跌
        gains = [change for change in changes if change > 0]
        losses = [-change for change in changes if change < 0]  # 取绝对值
        
        # 计算平均上涨和平均下跌
        if not gains:
            avg_gain = 0
        else:
            avg_gain = sum(gains) / period
        
        if not losses:
            avg_loss = 0
        else:
            avg_loss = sum(losses) / period
        
        # 计算RS
        if avg_loss == 0:
            if avg_gain == 0:
                return 50.0  # 无变化
            else:
                return 100.0  # 只有上涨
        
        rs = avg_gain / avg_loss
        
        # 计算RSI
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_weekly_rsi(self, prices: List[float]) -> Optional[float]:
        """
        计算周线RSI
        
        逻辑：将日线数据转换为周线数据（每周5个交易日）
        然后计算14周RSI
        
        Args:
            prices: 日线价格列表（最新的在前）
            
        Returns:
            周线RSI值，如果数据不足返回None
        """
        if len(prices) < 70:  # 14周×5天
            # 数据不足，降级使用日线RSI
            return self.calculate_rsi(prices, period=14)
        
        # 转换为周线数据（每周最后一个交易日的价格）
        weekly_prices = []
        for i in range(0, len(prices), 5):
            if i < len(prices):
                weekly_prices.append(prices[i])
        
        # 取最近70天对应的14周
        weekly_prices = weekly_prices[:14]
        
        if len(weekly_prices) < 15:  # 需要14周+1周计算变化
            return self.calculate_rsi(prices, period=14)  # 降级使用日线RSI
        
        # 计算周线RSI
        return self.calculate_rsi(weekly_prices, period=14)
    
    def analyze(self, 
                ticker: str,
                history_data: Dict[str, Any],
                analysis_data: Optional[Dict[str, Any]] = None,
                global_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        分析RSI信号
        
        逻辑:
        1. 计算RSI值（优先周线，不足则用日线）
        2. 应用30/70规则：RSI<30超卖，RSI>70超买
        3. 特别关注RSI>80的极端超买状态（一票否决权触发点）
        4. 生成相应的信号和得分
        """
        # 验证数据充足性
        valid, message = self.validate_data_sufficiency(history_data)
        
        # 即使数据不足70天，也尝试计算日线RSI
        prices = self.get_historical_prices(history_data, days=70)
        
        if len(prices) < 15:  # 至少需要15天计算14日RSI
            return self.create_result(
                hit=False,
                score=0.0,
                confidence=0.0,
                signals=[f"数据不足，无法计算RSI: 需要15天，实际{len(prices)}天"],
                metadata={
                    "error": "数据不足",
                    "available_days": len(prices),
                    "required_days": 15,
                    "rsi_value": None,
                    "rsi_type": "无法计算"
                }
            )
        
        try:
            # 尝试计算周线RSI
            weekly_rsi = self.calculate_weekly_rsi(prices)
            
            # 确定RSI类型和值
            if weekly_rsi is not None and len(prices) >= 70:
                rsi_value = weekly_rsi
                rsi_type = "weekly"
                metadata_rsi_type = "周线RSI"
            else:
                # 降级使用日线RSI
                rsi_value = self.calculate_rsi(prices, period=14)
                if rsi_value is None:
                    return self.create_result(
                        hit=False,
                        score=0.0,
                        confidence=0.0,
                        signals=["RSI计算失败"],
                        metadata={"error": "RSI计算失败", "rsi_value": None}
                    )
                rsi_type = "daily"
                metadata_rsi_type = "日线RSI（周线数据不足）"
            
            # 生成信号
            signals = []
            metadata = {
                "rsi_value": round(rsi_value, 2),
                "rsi_type": metadata_rsi_type,
                "data_days": len(prices),
                "calculation_type": rsi_type
            }
            
            hit = False
            score = 0.0
            confidence = 0.5
            
            # 规则1: 极端超卖 (RSI < 30)
            if rsi_value < 30:
                hit = True
                # RSI越低，得分越高（超卖程度越深）
                oversold_level = (30 - rsi_value) / 30  # 0-1范围
                score = 20.0 + oversold_level * 80.0  # 20-100分
                confidence = 0.5 + oversold_level * 0.4  # 0.5-0.9置信度
                
                if rsi_value < 20:
                    signals.append(f"极度超卖: {metadata_rsi_type}={rsi_value:.1f} < 20")
                    metadata["signal_strength"] = "extreme_oversold"
                else:
                    signals.append(f"超卖: {metadata_rsi_type}={rsi_value:.1f} < 30")
                    metadata["signal_strength"] = "oversold"
            
            # 规则2: 极端超买 (RSI > 70)
            elif rsi_value > 70:
                hit = True
                # RSI越高，得分越高（但这是反向信号，表示风险）
                overbought_level = (rsi_value - 70) / 30  # 0-1范围
                score = 20.0 + overbought_level * 80.0  # 20-100分
                confidence = 0.5 + overbought_level * 0.4  # 0.5-0.9置信度
                
                if rsi_value > 80:
                    signals.append(f"极度超买: {metadata_rsi_type}={rsi_value:.1f} > 80")
                    metadata["signal_strength"] = "extreme_overbought"
                    metadata["veto_trigger"] = True  # 一票否决权触发点
                else:
                    signals.append(f"超买: {metadata_rsi_type}={rsi_value:.1f} > 70")
                    metadata["signal_strength"] = "overbought"
                    metadata["veto_trigger"] = False
            
            # 规则3: 中性区域 (RSI 30-70)
            else:
                # 靠近中性区域（50）得分较低，偏离中性区域得分增加
                distance_from_50 = abs(rsi_value - 50) / 20  # 0-1范围
                score = 10.0 + distance_from_50 * 20.0  # 10-30分
                confidence = 0.3
                
                if rsi_value > 50:
                    signals.append(f"偏强: {metadata_rsi_type}={rsi_value:.1f}")
                    metadata["signal_strength"] = "slightly_strong"
                else:
                    signals.append(f"偏弱: {metadata_rsi_type}={rsi_value:.1f}")
                    metadata["signal_strength"] = "slightly_weak"
                
                metadata["distance_from_neutral"] = round(distance_from_50, 3)
            
            # 添加RSI趋势分析（如果数据足够）
            if len(prices) >= 28:  # 至少28天计算两个RSI点
                recent_rsi = self.calculate_rsi(prices[:14], period=14)
                previous_rsi = self.calculate_rsi(prices[7:21], period=14)  # 一周前
                
                if recent_rsi is not None and previous_rsi is not None:
                    rsi_trend = recent_rsi - previous_rsi
                    metadata["rsi_trend"] = round(rsi_trend, 2)
                    
                    if abs(rsi_trend) > 10:
                        if rsi_trend > 0:
                            signals.append("RSI快速上升")
                        else:
                            signals.append("RSI快速下降")
            
            if not signals:
                signals.append(f"RSI中性: {metadata_rsi_type}={rsi_value:.1f}")
            
            return self.create_result(
                hit=hit,
                score=score,
                confidence=confidence,
                signals=signals,
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Weekly-RSI分析失败: {e}")
            return self.create_result(
                hit=False,
                score=0.0,
                confidence=0.0,
                signals=[f"分析失败: {str(e)}"],
                metadata={"error": str(e)}
            )