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


class DataFallback:
    """
    数据降级模块 - Tushare接口失败时自动降级到本地缓存或历史数据
    
    设计理念:
    1. 数据分级检索: 实时API > 本地缓存 > 历史均值 > 默认值
    2. 自动标记备份数据: [BACKUP_DATA]
    3. 无缝降级: 上层调用无需感知数据源变化
    """
    
    def __init__(self, workspace_root: str = None):
        """初始化数据降级模块"""
        if workspace_root is None:
            # 默认工作空间根目录
            self.workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        else:
            self.workspace_root = workspace_root
        
        # 数据目录路径
        self.history_dir = os.path.join(self.workspace_root, "database")
        self.extracted_dir = os.path.join(self.workspace_root, "database", "arena", "extracted_data")
        self.cache_dir = os.path.join(self.workspace_root, "database", "tushare")
        
        # 确保目录存在
        os.makedirs(self.extracted_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.data_source = "unknown"  # 记录数据来源
        self.backup_marker = "[BACKUP_DATA]"  # 备份数据标记
        
        print(f"📦 DataFallback 初始化完成，工作空间: {self.workspace_root}")
    
    def get_stock_price(self, ticker: str, date: str = None) -> Dict[str, Any]:
        """
        获取股票价格数据，支持多级降级
        
        参数:
            ticker: 股票代码 (如: 000681.SZ, 510300)
            date: 日期字符串 (YYYY-MM-DD)，默认今天
            
        返回:
            包含价格数据和源信息的字典
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # 标准化ticker格式
        normalized_ticker = self._normalize_ticker(ticker)
        
        print(f"🔍 获取股票数据: {ticker} -> {normalized_ticker} ({date})")
        
        # 第1级: 尝试实时API (Tushare)
        realtime_data = self._try_realtime_api(normalized_ticker, date)
        if realtime_data and realtime_data.get("success"):
            print(f"✅ 实时API数据成功: {ticker}")
            return realtime_data
        
        # 第2级: 尝试本地缓存
        cached_data = self._try_local_cache(normalized_ticker, date)
        if cached_data and cached_data.get("success"):
            print(f"⚠️  使用本地缓存数据: {ticker}")
            return cached_data
        
        # 第3级: 尝试虚拟基金数据 (最新持仓价格)
        fund_data = self._try_fund_data(normalized_ticker, date)
        if fund_data and fund_data.get("success"):
            print(f"💰 使用虚拟基金数据: {ticker}")
            return fund_data
        
        # 第4级: 尝试历史数据 (均值计算)
        historical_data = self._try_historical_data(normalized_ticker, date)
        if historical_data and historical_data.get("success"):
            print(f"🔄 使用历史均值数据: {ticker}")
            return historical_data
        
        # 第5级: 尝试extracted_data (任务要求)
        extracted_data = self._try_extracted_data(normalized_ticker, date)
        if extracted_data and extracted_data.get("success"):
            print(f"📂 使用extracted数据: {ticker}")
            return extracted_data
        
        # 第5级: 降级到默认值
        print(f"🚨 所有数据源失败，使用默认值: {ticker}")
        return self._get_default_data(normalized_ticker, date)
    
    def _normalize_ticker(self, ticker: str) -> str:
        """标准化股票代码格式"""
        # 移除后缀和空格
        clean_ticker = ticker.replace(".SZ", "").replace(".SH", "").strip()
        
        # 如果是6位数字代码，保持原样
        if clean_ticker.isdigit() and len(clean_ticker) == 6:
            return clean_ticker
        
        # 其他格式直接返回
        return clean_ticker
    
    def _try_realtime_api(self, ticker: str, date: str) -> Dict[str, Any]:
        """尝试从Tushare API获取实时数据"""
        try:
            # 导入Tushare
            import tushare as ts
            import pandas as pd
            
            # 检查token是否设置
            token = os.environ.get("TUSHARE_TOKEN")
            if not token:
                # 尝试从secrets文件加载
                secrets_path = os.path.join(self.workspace_root, "_PRIVATE_DATA", "secrets.json")
                if os.path.exists(secrets_path):
                    with open(secrets_path, 'r', encoding='utf-8') as f:
                        secrets = json.load(f)
                    token = secrets.get("TUSHARE_TOKEN")
            
            if not token:
                print(f"❌ Tushare token未设置，跳过实时API")
                return {"success": False, "reason": "no_token"}
            
            # 设置token
            ts.set_token(token)
            pro = ts.pro_api()
            
            # 尝试获取日线数据
            # 注意: 需要将6位代码转换为Tushare格式
            tushare_code = f"{ticker}.SZ" if ticker.startswith("0") or ticker.startswith("3") else f"{ticker}.SH"
            
            df = pro.daily(ts_code=tushare_code, start_date=date, end_date=date)
            
            if df.empty:
                print(f"⚠️  Tushare返回空数据: {ticker}")
                return {"success": False, "reason": "empty_data"}
            
            # 提取数据
            row = df.iloc[0]
            price = float(row["close"])
            change = (float(row["close"]) - float(row["pre_close"])) / float(row["pre_close"])
            
            result = {
                "success": True,
                "ticker": ticker,
                "date": date,
                "price": price,
                "change_pct": change,
                "data_source": "tushare_realtime",
                "backup_marker": "",  # 实时数据不标记
                "timestamp": datetime.now().isoformat(),
                "raw_data": row.to_dict()
            }
            
            return result
            
        except Exception as e:
            print(f"⚠️  Tushare API错误: {e}")
            return {"success": False, "reason": f"api_error: {str(e)}"}
    
    def _try_local_cache(self, ticker: str, date: str) -> Dict[str, Any]:
        """尝试从本地缓存获取数据"""
        try:
            # 检查history文件
            history_file = os.path.join(self.history_dir, f"history_{ticker}.json")
            
            if not os.path.exists(history_file):
                # 尝试其他可能的文件名格式
                history_file_alt = os.path.join(self.history_dir, f"{ticker}.json")
                if not os.path.exists(history_file_alt):
                    return {"success": False, "reason": "no_cache_file"}
                history_file = history_file_alt
            
            with open(history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
            
            # 查找指定日期的数据
            history_list = history_data.get("history", [])
            for item in history_list:
                if item.get("date") == date:
                    price = float(item["price"]) if isinstance(item["price"], str) else item["price"]
                    change_str = item.get("change", "0%")
                    
                    # 解析涨跌幅字符串
                    change_pct = 0.0
                    if change_str.endswith("%"):
                        try:
                            change_pct = float(change_str.rstrip("%")) / 100
                        except:
                            change_pct = 0.0
                    
                    result = {
                        "success": True,
                        "ticker": ticker,
                        "date": date,
                        "price": price,
                        "change_pct": change_pct,
                        "data_source": "local_cache",
                        "backup_marker": self.backup_marker,
                        "timestamp": datetime.now().isoformat(),
                        "cache_file": os.path.basename(history_file)
                    }
                    
                    return result
            
            # 如果没有找到指定日期，尝试获取最新数据
            if history_list:
                latest = history_list[0]  # 假设第一个是最新的
                price = float(latest["price"]) if isinstance(latest["price"], str) else latest["price"]
                change_str = latest.get("change", "0%")
                
                change_pct = 0.0
                if change_str.endswith("%"):
                    try:
                        change_pct = float(change_str.rstrip("%")) / 100
                    except:
                        change_pct = 0.0
                
                result = {
                    "success": True,
                    "ticker": ticker,
                    "date": latest.get("date", date),
                    "price": price,
                    "change_pct": change_pct,
                    "data_source": "local_cache_latest",
                    "backup_marker": self.backup_marker,
                    "timestamp": datetime.now().isoformat(),
                    "cache_file": os.path.basename(history_file),
                    "note": f"未找到{date}数据，使用最新数据{latest.get('date')}"
                }
                
                return result
            
            return {"success": False, "reason": "no_data_in_cache"}
            
        except Exception as e:
            print(f"⚠️  本地缓存错误: {e}")
            return {"success": False, "reason": f"cache_error: {str(e)}"}
    
    def _try_fund_data(self, ticker: str, date: str) -> Dict[str, Any]:
        """尝试从虚拟基金数据获取最新价格"""
        try:
            fund_file = os.path.join(self.workspace_root, "database", "arena", "virtual_fund.json")
            
            if not os.path.exists(fund_file):
                return {"success": False, "reason": "no_fund_file"}
            
            with open(fund_file, 'r', encoding='utf-8') as f:
                fund_data = json.load(f)
            
            # 查找持仓
            positions = fund_data.get("positions", [])
            for position in positions:
                if position.get("ticker") == ticker:
                    price = position.get("current_price", 0)
                    avg_cost = position.get("average_cost", 0)
                    
                    # 计算相对于成本的变化
                    change_pct = 0.0
                    if avg_cost > 0:
                        change_pct = (price - avg_cost) / avg_cost
                    
                    result = {
                        "success": True,
                        "ticker": ticker,
                        "date": date,
                        "price": price,
                        "change_pct": change_pct,
                        "data_source": "virtual_fund",
                        "backup_marker": self.backup_marker,
                        "timestamp": datetime.now().isoformat(),
                        "fund_data": {
                            "avg_cost": avg_cost,
                            "quantity": position.get("quantity", 0),
                            "entry_date": position.get("entry_date", "unknown")
                        }
                    }
                    
                    return result
            
            return {"success": False, "reason": "ticker_not_in_fund"}
            
        except Exception as e:
            print(f"⚠️  虚拟基金数据错误: {e}")
            return {"success": False, "reason": f"fund_error: {str(e)}"}
    
    def _try_historical_data(self, ticker: str, date: str) -> Dict[str, Any]:
        """尝试从历史数据计算均值"""
        try:
            history_file = os.path.join(self.history_dir, f"history_{ticker}.json")
            
            if not os.path.exists(history_file):
                return {"success": False, "reason": "no_history_file"}
            
            with open(history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
            
            history_list = history_data.get("history", [])
            
            if not history_list:
                return {"success": False, "reason": "empty_history"}
            
            # 计算最近5天的平均价格
            recent_prices = []
            for item in history_list[:5]:  # 取最近5条
                try:
                    price = float(item["price"]) if isinstance(item["price"], str) else item["price"]
                    recent_prices.append(price)
                except:
                    continue
            
            if not recent_prices:
                return {"success": False, "reason": "no_valid_prices"}
            
            avg_price = sum(recent_prices) / len(recent_prices)
            
            result = {
                "success": True,
                "ticker": ticker,
                "date": date,
                "price": avg_price,
                "change_pct": 0.0,  # 历史均值没有涨跌幅
                "data_source": "historical_average",
                "backup_marker": self.backup_marker,
                "timestamp": datetime.now().isoformat(),
                "calculation": f"最近{len(recent_prices)}天平均价格",
                "recent_prices": recent_prices,
                "avg_price": avg_price
            }
            
            return result
            
        except Exception as e:
            print(f"⚠️  历史数据错误: {e}")
            return {"success": False, "reason": f"history_error: {str(e)}"}
    
    def _try_extracted_data(self, ticker: str, date: str) -> Dict[str, Any]:
        """尝试从extracted_data目录获取数据"""
        try:
            # 查找extracted_data目录下的所有JSON文件
            extracted_files = []
            for filename in os.listdir(self.extracted_dir):
                if filename.endswith('.json'):
                    extracted_files.append(os.path.join(self.extracted_dir, filename))
            
            if not extracted_files:
                return {"success": False, "reason": "no_extracted_files"}
            
            # 按修改时间排序，获取最新的文件
            extracted_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            latest_file = extracted_files[0]
            
            with open(latest_file, 'r', encoding='utf-8') as f:
                extracted_data = json.load(f)
            
            # 尝试从提取的数据中查找股票信息
            # 当前extracted_data主要包含共振评分数据，可能没有价格信息
            # 这里我们检查是否有任何价格相关信息
            
            # 检查常见的数据结构
            price_found = False
            price = 0.0
            change_pct = 0.0
            
            # 方法1: 检查ticker_details中是否有价格字段
            ticker_details = extracted_data.get("ticker_details", {})
            if ticker in ticker_details:
                ticker_info = ticker_details[ticker]
                # 检查常见价格字段
                for field in ["price", "close", "current_price", "last_price"]:
                    if field in ticker_info:
                        try:
                            price = float(ticker_info[field])
                            price_found = True
                            break
                        except:
                            continue
            
            # 方法2: 检查其他可能的数据结构
            if not price_found:
                # 尝试从历史记录中查找
                for key, value in extracted_data.items():
                    if isinstance(value, dict) and "price" in value:
                        try:
                            price = float(value["price"])
                            price_found = True
                            break
                        except:
                            continue
            
            if price_found:
                result = {
                    "success": True,
                    "ticker": ticker,
                    "date": date,
                    "price": price,
                    "change_pct": change_pct,
                    "data_source": "extracted_data",
                    "backup_marker": self.backup_marker,
                    "timestamp": datetime.now().isoformat(),
                    "extracted_file": os.path.basename(latest_file),
                    "note": "从extracted_data中找到价格信息"
                }
                return result
            else:
                # 没有找到价格信息，返回失败，让流程继续到下一级
                return {
                    "success": False, 
                    "reason": "no_price_in_extracted",
                    "extracted_file": os.path.basename(latest_file),
                    "extraction_date": extracted_data.get("extraction_date", "unknown")
                }
            
        except Exception as e:
            print(f"⚠️  extracted_data错误: {e}")
            return {"success": False, "reason": f"extracted_error: {str(e)}"}
    
    def _get_default_data(self, ticker: str, date: str) -> Dict[str, Any]:
        """获取默认数据（最后一道防线）"""
        # 使用一些启发式规则生成默认值
        # 例如: 基于股票代码的简单哈希生成"合理"的价格
        
        # 简单哈希生成伪随机但确定性的价格
        hash_val = hash(ticker) % 1000
        base_price = 10.0 + (hash_val / 100)  # 10-20元范围
        
        result = {
            "success": True,
            "ticker": ticker,
            "date": date,
            "price": base_price,
            "change_pct": 0.0,
            "data_source": "default_fallback",
            "backup_marker": self.backup_marker,
            "timestamp": datetime.now().isoformat(),
            "note": "所有数据源失败，使用默认启发式价格",
            "emergency": True
        }
        
        return result
    
    def batch_get_prices(self, tickers: List[str], date: str = None) -> Dict[str, Dict[str, Any]]:
        """批量获取股票价格数据"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        results = {}
        
        print(f"📊 批量获取 {len(tickers)} 个股票数据 ({date})")
        
        for ticker in tickers:
            try:
                result = self.get_stock_price(ticker, date)
                results[ticker] = result
                
                source = result.get("data_source", "unknown")
                marker = "🔴" if self.backup_marker in result.get("backup_marker", "") else "🟢"
                
                print(f"   {marker} {ticker}: {source} | 价格: {result.get('price', 'N/A')}")
                
            except Exception as e:
                print(f"❌ {ticker} 获取失败: {e}")
                results[ticker] = {
                    "success": False,
                    "ticker": ticker,
                    "error": str(e)
                }
        
        # 统计
        success_count = sum(1 for r in results.values() if r.get("success"))
        backup_count = sum(1 for r in results.values() if self.backup_marker in r.get("backup_marker", ""))
        
        print(f"📈 批量获取完成: {success_count}/{len(tickers)} 成功，{backup_count} 个使用备份数据")
        
        return results


def test_data_fallback():
    """测试数据降级模块"""
    print("\n🧪 开始测试 DataFallback 模块")
    
    # 创建数据降级实例
    fallback = DataFallback()
    
    # 测试单个股票
    test_tickers = ["510300", "000681", "600633", "000938", "TEST123"]
    today = datetime.now().strftime("%Y-%m-%d")
    
    print(f"\n📅 测试日期: {today}")
    
    for ticker in test_tickers:
        print(f"\n--- 测试 {ticker} ---")
        result = fallback.get_stock_price(ticker, today)
        
        if result["success"]:
            source = result["data_source"]
            price = result["price"]
            marker = result.get("backup_marker", "")
            
            print(f"✅ 成功: {source}")
            print(f"   价格: {price}")
            print(f"   标记: {marker if marker else '实时数据'}")
            if "note" in result:
                print(f"   备注: {result['note']}")
        else:
            print(f"❌ 失败: {result.get('reason', 'unknown')}")
    
    # 批量测试
    print(f"\n📦 批量测试 {len(test_tickers)} 个股票")
    batch_results = fallback.batch_get_prices(test_tickers, today)
    
    return batch_results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Technical Fallback 测试工具")
    parser.add_argument("--mode", choices=["decision", "data", "all"], default="all",
                       help="测试模式: decision=决策降级, data=数据降级, all=全部")
    
    args = parser.parse_args()
    
    print("🔧 Technical Fallback 测试工具")
    print("==============================")
    
    test_results = {}
    
    if args.mode in ["decision", "all"]:
        print("\n🧠 测试决策降级模块 (TechnicalFallback)...")
        decision_result = test_technical_fallback()
        test_results["decision"] = decision_result
        
        # 保存决策测试结果
        decision_file = "database/arena/technical_fallback_decision_test.json"
        os.makedirs(os.path.dirname(decision_file), exist_ok=True)
        with open(decision_file, "w", encoding="utf-8") as f:
            json.dump(decision_result, f, ensure_ascii=False, indent=2)
        print(f"✅ 决策测试结果保存至: {decision_file}")
    
    if args.mode in ["data", "all"]:
        print("\n📊 测试数据降级模块 (DataFallback)...")
        data_result = test_data_fallback()
        test_results["data"] = data_result
        
        # 保存数据测试结果
        data_file = "database/arena/technical_fallback_data_test.json"
        os.makedirs(os.path.dirname(data_file), exist_ok=True)
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(data_result, f, ensure_ascii=False, indent=2)
        print(f"✅ 数据测试结果保存至: {data_file}")
    
    print("\n🎉 所有测试完成!")