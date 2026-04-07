#!/usr/bin/env python3
"""
Dividend Alpha Strategy (G4) - 分红保护垫策略
动态计算股息率，考虑税收损耗后的真实净收益
"""

import statistics
from typing import Dict, Any, List, Optional
from .base_strategy import BaseStrategy


class DividendAlphaStrategy(BaseStrategy):
    """分红保护垫策略"""
    
    def __init__(self):
        super().__init__(
            name="Dividend-Alpha",
            description="动态计算股息率，考虑税收损耗后的真实净收益，评估分红保护垫"
        )
        
        # 模拟股息数据（实际应用中应从API获取）
        # 这里使用常见ETF的历史平均股息率
        self.dividend_rates = {
            "518880": 0.018,  # 黄金ETF历史平均股息率约1.8%
            "510300": 0.025,  # 沪深300ETF约2.5%
            "510500": 0.018,  # 中证500ETF约1.8%
            "588000": 0.022,  # 科创50ETF约2.2%
        }
        
        # 税收率假设（股息红利税）
        self.tax_rate = 0.20  # 20%税率
    
    def get_required_history_days(self) -> int:
        """需要60天历史数据计算价格稳定性"""
        return 60
    
    def estimate_dividend_yield(self, ticker: str, current_price: float) -> float:
        """估算股息收益率"""
        # 从预设数据获取基准股息率
        base_rate = self.dividend_rates.get(ticker, 0.02)  # 默认2%
        
        # 可以根据历史波动率调整股息率（波动越大，要求的股息补偿越高）
        # 这里简化处理，返回基准值
        return base_rate
    
    def calculate_net_dividend_yield(self, gross_yield: float, tax_rate: float = None) -> float:
        """计算税后净股息收益率"""
        if tax_rate is None:
            tax_rate = self.tax_rate
        
        net_yield = gross_yield * (1 - tax_rate)
        return net_yield
    
    def calculate_price_stability(self, prices: List[float], window: int = 60) -> float:
        """计算价格稳定性（波动率倒数）"""
        if len(prices) < window:
            return 0.0
        
        window_prices = prices[:window]
        
        # 计算波动率（标准差）
        if len(window_prices) > 1:
            mean_price = statistics.mean(window_prices)
            variance = sum((p - mean_price) ** 2 for p in window_prices) / (len(window_prices) - 1)
            std_dev = variance ** 0.5
            
            # 波动率（标准差/均值）
            if mean_price > 0:
                volatility = std_dev / mean_price
                # 稳定性 = 1 / (1 + 波动率) ，归一化到0-1
                stability = 1.0 / (1.0 + volatility * 10)  # 放大系数使结果更敏感
                return max(0.0, min(1.0, stability))
        
        return 0.5  # 默认中等稳定性
    
    def calculate_dividend_protection_score(self, 
                                          net_dividend_yield: float,
                                          price_stability: float,
                                          current_price: float,
                                          ma60: Optional[float],
                                          prices: List[float]) -> Dict[str, Any]:
        """计算分红保护垫评分"""
        
        score = 0.0
        confidence = 0.5
        signals = []
        metadata = {}
        
        # 规则1: 高股息率保护
        if net_dividend_yield > 0.03:  # 净股息率 > 3%
            score += 40.0
            confidence += 0.2
            signals.append("高股息保护: 净股息率超过3%")
            metadata["high_yield"] = True
        elif net_dividend_yield > 0.02:  # 净股息率 > 2%
            score += 25.0
            confidence += 0.1
            signals.append("中等股息保护: 净股息率超过2%")
            metadata["medium_yield"] = True
        elif net_dividend_yield > 0.01:  # 净股息率 > 1%
            score += 10.0
            signals.append("基础股息保护: 净股息率超过1%")
            metadata["low_yield"] = True
        
        # 规则2: 价格稳定性贡献
        stability_score = price_stability * 30.0
        score += stability_score
        confidence += price_stability * 0.1
        
        if price_stability > 0.8:
            signals.append("高价格稳定性: 低波动环境")
            metadata["high_stability"] = True
        elif price_stability > 0.6:
            signals.append("中等价格稳定性")
            metadata["medium_stability"] = True
        
        # 规则3: 价格位置判断（如果低于均线，股息保护更有价值）
        if ma60 is not None and ma60 > 0:
            price_ratio = current_price / ma60
            
            if price_ratio < 0.9:  # 价格低于60日均线10%
                score += 20.0
                confidence += 0.1
                signals.append("价格低位: 当前价格低于60日均线")
                metadata["price_below_ma"] = True
                metadata["price_ratio"] = round(price_ratio, 4)
            elif price_ratio < 1.0:  # 价格低于均线但不足10%
                score += 10.0
                signals.append("价格适中: 接近60日均线")
                metadata["price_near_ma"] = True
                metadata["price_ratio"] = round(price_ratio, 4)
        
        # 规则4: 股息覆盖下跌风险
        # 简单估算：年化股息率能否覆盖潜在下跌风险
        # 假设潜在下跌风险 = 年化波动率
        if len(prices) > 20:
            annualized_volatility = self.calculate_annualized_volatility(prices[:20])
            coverage_ratio = net_dividend_yield / annualized_volatility if annualized_volatility > 0 else 0
            
            if coverage_ratio > 0.5:
                score += 15.0
                confidence += 0.1
                signals.append("股息覆盖风险: 股息收益能覆盖部分波动风险")
                metadata["coverage_ratio"] = round(coverage_ratio, 4)
                metadata["good_coverage"] = True
        
        score = min(100.0, score)
        confidence = min(0.9, confidence)
        
        return {
            "score": score,
            "confidence": confidence,
            "signals": signals,
            "metadata": metadata
        }
    
    def calculate_annualized_volatility(self, prices: List[float]) -> float:
        """计算年化波动率（简化版）"""
        if len(prices) < 2:
            return 0.0
        
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                daily_return = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(daily_return)
        
        if len(returns) < 2:
            return 0.0
        
        mean_return = statistics.mean(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        daily_volatility = variance ** 0.5
        
        # 年化波动率（假设252个交易日）
        annualized_vol = daily_volatility * (252 ** 0.5)
        return annualized_vol
    
    def analyze(self, 
                ticker: str,
                history_data: Dict[str, Any],
                analysis_data: Optional[Dict[str, Any]] = None,
                global_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        分析分红保护垫
        
        逻辑:
        1. 估算股息收益率
        2. 计算税后净股息率
        3. 评估价格稳定性
        4. 计算分红保护垫综合评分
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
            if len(prices) < 60:
                return self.create_result(
                    hit=False,
                    score=0.0,
                    confidence=0.0,
                    signals=[f"数据不足，需要60天，实际{len(prices)}天"],
                    metadata={"error": "数据不足"}
                )
            
            current_price = prices[0]
            
            # 估算股息收益率
            gross_dividend_yield = self.estimate_dividend_yield(ticker, current_price)
            
            # 计算税后净股息率
            net_dividend_yield = self.calculate_net_dividend_yield(gross_dividend_yield)
            
            # 计算价格稳定性
            price_stability = self.calculate_price_stability(prices, window=60)
            
            # 计算60日均线（用于价格位置判断）
            ma60 = self.calculate_moving_average(prices, 60)
            
            # 计算分红保护垫评分
            protection_result = self.calculate_dividend_protection_score(
                net_dividend_yield=net_dividend_yield,
                price_stability=price_stability,
                current_price=current_price,
                ma60=ma60,
                prices=prices
            )
            
            # 合并信号和元数据
            signals = protection_result["signals"]
            metadata = protection_result["metadata"]
            
            # 添加基础数据
            metadata.update({
                "current_price": current_price,
                "gross_dividend_yield": round(gross_dividend_yield, 4),
                "net_dividend_yield": round(net_dividend_yield, 4),
                "tax_rate": self.tax_rate,
                "price_stability": round(price_stability, 4),
                "ma60": round(ma60, 4) if ma60 else None,
                "annualized_volatility": round(self.calculate_annualized_volatility(prices[:20]), 4)
            })
            
            # 判断是否命中（只要有一定股息保护就算命中）
            hit = protection_result["score"] > 10.0
            
            if not signals:
                signals.append("股息保护分析完成")
                metadata["signal_type"] = "analysis_complete"
            
            # 根据评分确定信号类型
            if protection_result["score"] > 50:
                signals.append("强分红保护垫: 高股息率且价格稳定")
                metadata["signal_type"] = "strong_dividend_protection"
            elif protection_result["score"] > 30:
                signals.append("中等分红保护垫: 提供基础保护")
                metadata["signal_type"] = "medium_dividend_protection"
            elif protection_result["score"] > 10:
                signals.append("弱分红保护垫: 有限保护作用")
                metadata["signal_type"] = "weak_dividend_protection"
            else:
                signals.append("无有效分红保护: 股息率过低或价格不稳定")
                metadata["signal_type"] = "no_dividend_protection"
            
            return self.create_result(
                hit=hit,
                score=protection_result["score"],
                confidence=protection_result["confidence"],
                signals=signals,
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Dividend-Alpha分析失败: {e}")
            return self.create_result(
                hit=False,
                score=0.0,
                confidence=0.0,
                signals=[f"分析失败: {str(e)}"],
                metadata={"error": str(e)}
            )