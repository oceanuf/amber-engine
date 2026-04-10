#!/usr/bin/env python3
"""
TechnicalFallback - 降级决策模块
首席架构师Gemini "零点修复指令" 核心组件

功能: 在评委数据缺失时，基于技术指标执行降级决策
原则: 仅允许"持有"或"防御性补仓"，严禁无情报状态下开新仓
"""

import os
import sys
import json
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import statistics
import math

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TechnicalFallback:
    """
    降级决策模块 - 评委数据缺失时激活的"影子运行"机制
    
    设计理念:
    1. 当系统"失明"(情报缺失)时，基于肌肉记忆(技术指标)进行防守
    2. 决策范围受限: 仅允许持有或防御性补仓
    3. 严禁在情报缺失状态下开新仓，避免盲目进攻
    """
    
    def __init__(self, fund_data: Dict[str, Any]):
        """
        初始化降级决策模块
        
        参数:
            fund_data: 虚拟基金数据
        """
        self.fund_data = fund_data
        self.decision_log = []
        
        # 技术指标权重配置
        self.technical_weights = {
            "price_momentum": 0.35,      # 价格动量 (短期价格变化)
            "volume_trend": 0.25,        # 成交量趋势
            "market_context": 0.20,      # 市场环境判断
            "position_analysis": 0.20,    # 持仓分析
        }
        
        # 决策阈值
        self.BUY_THRESHOLD = -0.03       # 下跌超过3%触发防御性补仓
        self.SELL_THRESHOLD = 0.05       # 上涨超过5%触发部分止盈
        self.HOLD_RANGE = (-0.02, 0.02)  # ±2%内持仓观望
        
        print("🛡️  TechnicalFallback 激活: 进入降级决策模式")
        print("   规则: 仅允许'持有'或'防御性补仓'，严禁无情报开新仓")
    
    def analyze_position(self, position: Dict[str, Any], 
                        market_trend: str = "STABLE") -> Dict[str, Any]:
        """
        分析单个持仓，生成降级决策建议
        
        参数:
            position: 持仓数据
            market_trend: 市场趋势 (STABLE/BULL/BEAR)
            
        返回:
            决策建议字典
        """
        ticker = position.get("ticker", "")
        name = position.get("name", "")
        current_price = position.get("current_price", 0)
        avg_cost = position.get("average_cost", 0)
        quantity = position.get("quantity", 0)
        pnl_pct = position.get("unrealized_pnl_pct", 0)
        entry_date = position.get("entry_date", "")
        
        # 基础分析
        days_held = self._calculate_days_held(entry_date)
        position_value = current_price * quantity
        
        # 技术指标分析
        technical_score = self._calculate_technical_score(
            position, market_trend, days_held
        )
        
        # 生成决策
        decision = self._generate_decision(
            pnl_pct, technical_score, market_trend, days_held
        )
        
        # 构建建议
        recommendation = {
            "ticker": ticker,
            "name": name,
            "decision": decision["action"],
            "reason": decision["reason"],
            "confidence": technical_score["total_score"],
            "technical_analysis": technical_score,
            "position_data": {
                "current_price": current_price,
                "avg_cost": avg_cost,
                "pnl_pct": pnl_pct,
                "days_held": days_held,
                "position_value": position_value,
            },
            "recommended_action": decision.get("recommended_action", {}),
            "timestamp": datetime.now().isoformat(),
        }
        
        # 记录决策
        self.decision_log.append(recommendation)
        
        return recommendation
    
    def _calculate_technical_score(self, position: Dict[str, Any], 
                                 market_trend: str, days_held: int) -> Dict[str, Any]:
        """
        计算技术指标综合评分
        
        返回包含各项指标得分的字典
        """
        ticker = position.get("ticker", "")
        pnl_pct = position.get("unrealized_pnl_pct", 0)
        current_price = position.get("current_price", 0)
        avg_cost = position.get("average_cost", 0)
        
        # 1. 价格动量得分 (基于盈亏百分比)
        if pnl_pct < -0.05:  # 下跌超过5%
            price_momentum_score = 0.2
        elif pnl_pct < -0.02:  # 下跌2-5%
            price_momentum_score = 0.4
        elif pnl_pct < 0.02:   # ±2%内
            price_momentum_score = 0.7
        elif pnl_pct < 0.05:   # 上涨2-5%
            price_momentum_score = 0.6
        else:                  # 上涨超过5%
            price_momentum_score = 0.5
        
        # 2. 成交量趋势得分 (简化版，实际应接入成交量数据)
        # 假设: 持仓天数越多，成交量信息越可靠
        volume_reliability = min(days_held / 30, 1.0)  # 30天后认为可靠
        volume_trend_score = 0.6 * volume_reliability + 0.4 * (1 - volume_reliability)
        
        # 3. 市场环境得分
        if market_trend == "BULL":
            market_score = 0.8
        elif market_trend == "STABLE":
            market_score = 0.6
        else:  # BEAR
            market_score = 0.3
        
        # 4. 持仓分析得分
        # 检查是否过度集中
        total_portfolio_value = sum(
            p.get("current_price", 0) * p.get("quantity", 0) 
            for p in self.fund_data.get("positions", [])
        )
        
        position_value = current_price * position.get("quantity", 0)
        if total_portfolio_value > 0:
            concentration = position_value / total_portfolio_value
            # 单股仓位≤20%得高分
            if concentration <= 0.2:
                position_score = 0.8
            elif concentration <= 0.3:
                position_score = 0.6
            else:
                position_score = 0.4
        else:
            position_score = 0.5
        
        # 加权总分
        total_score = (
            price_momentum_score * self.technical_weights["price_momentum"] +
            volume_trend_score * self.technical_weights["volume_trend"] +
            market_score * self.technical_weights["market_context"] +
            position_score * self.technical_weights["position_analysis"]
        )
        
        return {
            "price_momentum": round(price_momentum_score, 3),
            "volume_trend": round(volume_trend_score, 3),
            "market_context": round(market_score, 3),
            "position_analysis": round(position_score, 3),
            "total_score": round(total_score, 3),
            "weights": self.technical_weights,
        }
    
    def _generate_decision(self, pnl_pct: float, technical_score: Dict[str, Any],
                          market_trend: str, days_held: int) -> Dict[str, Any]:
        """
        基于技术指标生成决策
        
        决策原则:
        - 仅允许: 持有(HOLD)或防御性补仓(DEFENSIVE_BUY)
        - 严禁: 无情报状态下开新仓(NEW_BUY)
        - 可考虑: 部分止盈(PARTIAL_PROFIT_TAKING)
        """
        total_score = technical_score["total_score"]
        
        # 默认决策
        decision = {
            "action": "HOLD",
            "reason": "技术指标中性，持仓观望",
            "emergency_mode": True,
        }
        
        # 防御性补仓条件
        if (pnl_pct < self.BUY_THRESHOLD and 
            market_trend in ["STABLE", "BULL"] and
            total_score > 0.4):
            
            # 计算建议补仓数量 (不超过现有持仓的20%)
            recommended_quantity = "现有持仓的10-20%"
            
            decision = {
                "action": "DEFENSIVE_BUY",
                "reason": f"下跌{pnl_pct:.1%} > {self.BUY_THRESHOLD:.1%}阈值，市场{market_trend}，适合防御性左侧布局",
                "recommended_action": {
                    "type": "defensive_buy",
                    "quantity": recommended_quantity,
                    "rationale": "价格回踩超过阈值，基于均值回归假设执行防御性补仓",
                    "risk_note": "仅限现有持仓补仓，严禁开新仓",
                },
                "emergency_mode": True,
            }
        
        # 部分止盈条件 (仅在上涨较多时考虑)
        elif (pnl_pct > self.SELL_THRESHOLD and 
              days_held > 30 and  # 必须超过锁定期
              total_score > 0.5):
            
            decision = {
                "action": "PARTIAL_PROFIT_TAKING",
                "reason": f"上涨{pnl_pct:.1%} > {self.SELL_THRESHOLD:.1%}阈值，锁定部分利润",
                "recommended_action": {
                    "type": "partial_sell",
                    "quantity": "持仓的10-30%",
                    "rationale": "价格反弹超过止盈阈值，执行利润保护",
                    "risk_note": "需检查锁定期限制",
                },
                "emergency_mode": True,
            }
        
        # 持仓观望条件
        elif (self.HOLD_RANGE[0] <= pnl_pct <= self.HOLD_RANGE[1] or
              total_score < 0.4):
            
            decision = {
                "action": "HOLD",
                "reason": f"价格波动{pnl_pct:.1%}在容忍范围内({self.HOLD_RANGE[0]:.1%}~{self.HOLD_RANGE[1]:.1%})，技术指标谨慎",
                "emergency_mode": True,
            }
        
        return decision
    
    def _calculate_days_held(self, entry_date: str) -> int:
        """计算持仓天数"""
        try:
            if not entry_date:
                return 0
            
            # 处理不同的日期格式
            if "T" in entry_date:
                entry_dt = datetime.fromisoformat(entry_date.replace("Z", "+00:00"))
            else:
                entry_dt = datetime.strptime(entry_date, "%Y-%m-%d")
            
            days_held = (datetime.now() - entry_dt).days
            return max(days_held, 0)
        except Exception:
            return 0
    
    def analyze_all_positions(self, market_trend: str = "STABLE") -> List[Dict[str, Any]]:
        """
        分析所有持仓，生成整体降级决策报告
        
        返回:
            所有持仓的决策建议列表
        """
        positions = self.fund_data.get("positions", [])
        recommendations = []
        
        print(f"📊 开始分析 {len(positions)} 个持仓 (降级模式)")
        
        for position in positions:
            recommendation = self.analyze_position(position, market_trend)
            recommendations.append(recommendation)
            
            # 打印简要结果
            ticker = position.get("ticker", "")
            decision = recommendation["decision"]
            reason = recommendation["reason"][:50] + "..." if len(recommendation["reason"]) > 50 else recommendation["reason"]
            
            print(f"   {ticker}: {decision} - {reason}")
        
        # 生成整体风险评估
        overall_risk = self._assess_overall_risk(recommendations)
        
        print(f"✅ 降级决策分析完成")
        print(f"   风险评估: {overall_risk['level']} ({overall_risk['score']}/10)")
        print(f"   建议持仓: {len([r for r in recommendations if r['decision'] == 'HOLD'])}个")
        print(f"   建议补仓: {len([r for r in recommendations if r['decision'] == 'DEFENSIVE_BUY'])}个")
        
        return {
            "recommendations": recommendations,
            "overall_risk": overall_risk,
            "market_trend": market_trend,
            "analysis_time": datetime.now().isoformat(),
            "emergency_mode": True,
            "module": "TechnicalFallback",
        }
    
    def _assess_overall_risk(self, recommendations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """评估整体风险水平"""
        total_positions = len(recommendations)
        if total_positions == 0:
            return {"level": "LOW", "score": 2, "reason": "无持仓"}
        
        # 统计决策类型
        hold_count = len([r for r in recommendations if r["decision"] == "HOLD"])
        buy_count = len([r for r in recommendations if r["decision"] == "DEFENSIVE_BUY"])
        sell_count = len([r for r in recommendations if r["decision"] == "PARTIAL_PROFIT_TAKING"])
        
        # 计算平均信心度
        avg_confidence = sum(r.get("confidence", 0.5) for r in recommendations) / total_positions
        
        # 风险评估逻辑
        risk_score = 5  # 基准分
        
        # 调整因素
        if buy_count > 0:
            risk_score += 2  # 有补仓建议，风险略增
        if avg_confidence < 0.4:
            risk_score += 3  # 信心度低，风险增加
        if sell_count > 0:
            risk_score -= 1  # 有止盈建议，风险降低
        
        # 限制范围
        risk_score = max(1, min(10, risk_score))
        
        # 风险等级映射
        if risk_score <= 3:
            level = "LOW"
        elif risk_score <= 6:
            level = "MEDIUM"
        else:
            level = "HIGH"
        
        return {
            "level": level,
            "score": risk_score,
            "hold_count": hold_count,
            "buy_count": buy_count,
            "sell_count": sell_count,
            "avg_confidence": round(avg_confidence, 3),
            "total_positions": total_positions,
        }
    
    def get_decision_summary(self) -> Dict[str, Any]:
        """获取决策摘要"""
        return {
            "total_decisions": len(self.decision_log),
            "decisions_by_type": self._count_decisions_by_type(),
            "technical_weights": self.technical_weights,
            "thresholds": {
                "BUY_THRESHOLD": self.BUY_THRESHOLD,
                "SELL_THRESHOLD": self.SELL_THRESHOLD,
                "HOLD_RANGE": self.HOLD_RANGE,
            },
            "last_analysis": datetime.now().isoformat(),
        }
    
    def _count_decisions_by_type(self) -> Dict[str, int]:
        """按类型统计决策数量"""
        counts = {"HOLD": 0, "DEFENSIVE_BUY": 0, "PARTIAL_PROFIT_TAKING": 0}
        for decision in self.decision_log:
            action = decision.get("decision", "HOLD")
            if action in counts:
                counts[action] += 1
        return counts


def test_technical_fallback():
    """测试降级决策模块"""
    print("🧪 开始测试 TechnicalFallback 模块")
    
    # 创建测试基金数据
    test_fund_data = {
        "fund_id": "TEST_FUND",
        "current_capital": 1000000,
        "positions": [
            {
                "ticker": "000681",
                "name": "视觉中国",
                "quantity": 4747,
                "current_price": 20.37,
                "average_cost": 21.07,
                "unrealized_pnl_pct": -0.0331,
                "entry_date": "2026-04-08",
            },
            {
                "ticker": "600633",
                "name": "浙数文化",
                "quantity": 7764,
                "current_price": 12.52,
                "average_cost": 12.88,
                "unrealized_pnl_pct": -0.0283,
                "entry_date": "2026-04-08",
            },
            {
                "ticker": "000938",
                "name": "紫光股份",
                "quantity": 3779,
                "current_price": 27.02,
                "average_cost": 26.46,
                "unrealized_pnl_pct": 0.0211,
                "entry_date": "2026-04-08",
            }
        ]
    }
    
    # 创建降级决策实例
    fallback = TechnicalFallback(test_fund_data)
    
    # 分析所有持仓
    result = fallback.analyze_all_positions(market_trend="STABLE")
    
    print(f"\n📋 测试结果摘要:")
    print(f"   分析持仓: {len(result['recommendations'])}个")
    print(f"   市场趋势: {result['market_trend']}")
    print(f"   紧急模式: {result['emergency_mode']}")
    print(f"   风险评估: {result['overall_risk']['level']}")
    
    # 打印详细决策
    print(f"\n📊 详细决策建议:")
    for rec in result["recommendations"]:
        ticker = rec["ticker"]
        decision = rec["decision"]
        reason = rec["reason"]
        confidence = rec["confidence"]
        
        print(f"   {ticker}:")
        print(f"     决策: {decision}")
        print(f"     理由: {reason}")
        print(f"     信心度: {confidence:.3f}")
        
        if "recommended_action" in rec and rec["recommended_action"]:
            action = rec["recommended_action"]
            print(f"     建议: {action['type']} - {action.get('quantity', 'N/A')}")
    
    return result


if __name__ == "__main__":
    # 运行测试
    test_result = test_technical_fallback()
    
    # 保存测试结果
    output_file = "database/arena/technical_fallback_test.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(test_result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 测试完成，结果保存至: {output_file}")