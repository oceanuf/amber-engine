#!/usr/bin/env python3
"""
琥珀引擎演武场订单执行器 - V1.5.0 "分阶获利" 逻辑
实现 profit_taking_v1 钩子，分级锁定收益策略
符合 [最高执行指令] 专项一要求
"""

import os
import sys
import json
import time
import datetime
import hashlib
import uuid
from typing import Dict, List, Optional, Tuple, Any
import statistics
import math

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 分阶获利参数
PROFIT_TAKING_TIER_1 = 0.05  # 5% 收益，卖出30%仓位（市价单）
PROFIT_TAKING_TIER_2 = 0.08  # 8% 收益，再卖出30%仓位（限价单）
POSITION_REDUCTION_TIER_1 = 0.30  # 第一次减仓比例
POSITION_REDUCTION_TIER_2 = 0.30  # 第二次减仓比例
MAX_TIER_REDUCTION = 0.60  # 最大减仓比例（两阶段合计）

# 订单类型
ORDER_TYPE_MARKET = "market"
ORDER_TYPE_LIMIT = "limit"
ORDER_TYPE_STRATEGY = "strategy_profit_taking"

class ProfitTakingExecutor:
    """分阶获利执行器"""
    
    def __init__(self, arena_engine=None, fund_db_path: str = "database/arena/virtual_fund.json"):
        self.arena_engine = arena_engine
        self.fund_db_path = fund_db_path
        self.fund_data = None
        self.profit_taking_logs = []
        
        # 确保日志目录存在
        os.makedirs("logs/arena/profit_taking", exist_ok=True)
        
        self.load_fund_data()
    
    def load_fund_data(self) -> bool:
        """加载虚拟基金数据"""
        try:
            if os.path.exists(self.fund_db_path):
                with open(self.fund_db_path, 'r', encoding='utf-8') as f:
                    self.fund_data = json.load(f)
                print(f"✅ 加载虚拟基金数据: {self.fund_data['fund_name']}")
                return True
            else:
                print(f"❌ 基金数据文件不存在: {self.fund_db_path}")
                return False
        except Exception as e:
            print(f"❌ 加载基金数据失败: {e}")
            return False
    
    def save_fund_data(self):
        """保存基金数据"""
        try:
            # 更新最后修改时间
            self.fund_data["last_updated"] = datetime.datetime.now(
                datetime.timezone(datetime.timedelta(hours=8))
            ).isoformat()
            
            with open(self.fund_db_path, 'w', encoding='utf-8') as f:
                json.dump(self.fund_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"❌ 保存基金数据失败: {e}")
            return False
    
    def calculate_position_profit(self, position: Dict) -> Dict:
        """计算持仓盈利情况"""
        ticker = position["ticker"]
        avg_cost = position["avg_cost"]
        current_price = position["current_price"]
        quantity = position["quantity"]
        unrealized_pnl = position["unrealized_pnl"]
        unrealized_pnl_pct = position["unrealized_pnl_pct"]
        
        # 计算分级触发状态
        tier_1_triggered = unrealized_pnl_pct >= PROFIT_TAKING_TIER_1
        tier_2_triggered = unrealized_pnl_pct >= PROFIT_TAKING_TIER_2
        
        # 计算已执行的分阶减仓
        executed_tier_1 = False
        executed_tier_2 = False
        
        # 检查历史交易记录
        transaction_history = self.fund_data.get("transaction_history", [])
        for transaction in transaction_history:
            if (transaction.get("ticker") == ticker and 
                transaction.get("transaction_type") == "partial_profit_taking"):
                metadata = transaction.get("metadata", {})
                if metadata.get("profit_taking_tier") == 1:
                    executed_tier_1 = True
                elif metadata.get("profit_taking_tier") == 2:
                    executed_tier_2 = True
        
        profit_status = {
            "ticker": ticker,
            "avg_cost": avg_cost,
            "current_price": current_price,
            "quantity": quantity,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pnl_pct": unrealized_pnl_pct,
            "profit_pct_formatted": f"{unrealized_pnl_pct * 100:.2f}%",
            "tier_1_threshold": PROFIT_TAKING_TIER_1,
            "tier_2_threshold": PROFIT_TAKING_TIER_2,
            "tier_1_triggered": tier_1_triggered,
            "tier_2_triggered": tier_2_triggered,
            "executed_tier_1": executed_tier_1,
            "executed_tier_2": executed_tier_2,
            "can_execute_tier_1": tier_1_triggered and not executed_tier_1,
            "can_execute_tier_2": tier_2_triggered and not executed_tier_2,
            "reduction_pct_tier_1": POSITION_REDUCTION_TIER_1,
            "reduction_pct_tier_2": POSITION_REDUCTION_TIER_2,
            "remaining_position_after_tiers": 1.0 - (POSITION_REDUCTION_TIER_1 + POSITION_REDUCTION_TIER_2)
        }
        
        return profit_status
    
    def execute_profit_taking_v1(self, ticker: str, current_price: float, tier: int) -> Tuple[bool, str, Dict]:
        """
        执行分阶获利 v1 钩子
        
        参数:
            ticker: 股票代码
            current_price: 当前价格
            tier: 分阶等级 (1 或 2)
            
        返回:
            (是否成功, 消息, 交易记录)
        """
        print(f"🎯 执行分阶获利 v1 钩子: {ticker} (Tier {tier})")
        print(f"   当前价格: ¥{current_price:.2f}")
        
        # 查找持仓
        position_index = -1
        position_data = None
        
        for i, position in enumerate(self.fund_data.get("positions", [])):
            if position["ticker"] == ticker:
                position_index = i
                position_data = position
                break
        
        if position_index == -1:
            msg = f"未持有 {ticker}"
            print(f"❌ {msg}")
            return False, msg, None
        
        # 计算盈利状态
        profit_status = self.calculate_position_profit(position_data)
        
        # 检查是否可以执行该分阶
        if tier == 1:
            if not profit_status["can_execute_tier_1"]:
                if profit_status["executed_tier_1"]:
                    msg = f"Tier 1 已执行过，无法重复执行"
                else:
                    msg = f"Tier 1 未触发 (当前盈利: {profit_status['profit_pct_formatted']}, 需要: {PROFIT_TAKING_TIER_1*100:.1f}%)"
                print(f"❌ {msg}")
                return False, msg, None
            
            reduction_pct = POSITION_REDUCTION_TIER_1
            order_type = ORDER_TYPE_MARKET
            profit_threshold = PROFIT_TAKING_TIER_1
            
        elif tier == 2:
            if not profit_status["can_execute_tier_2"]:
                if profit_status["executed_tier_2"]:
                    msg = f"Tier 2 已执行过，无法重复执行"
                else:
                    msg = f"Tier 2 未触发 (当前盈利: {profit_status['profit_pct_formatted']}, 需要: {PROFIT_TAKING_TIER_2*100:.1f}%)"
                print(f"❌ {msg}")
                return False, msg, None
            
            reduction_pct = POSITION_REDUCTION_TIER_2
            order_type = ORDER_TYPE_LIMIT
            profit_threshold = PROFIT_TAKING_TIER_2
            
        else:
            msg = f"无效的分阶等级: {tier} (仅支持 1 或 2)"
            print(f"❌ {msg}")
            return False, msg, None
        
        # 计算卖出数量
        total_quantity = position_data["quantity"]
        sell_quantity = int(total_quantity * reduction_pct)
        
        if sell_quantity <= 0:
            msg = f"计算出的卖出数量为0"
            print(f"❌ {msg}")
            return False, msg, None
        
        # 生成交易记录
        transaction_id = f"PROFIT_TAKE_{ticker}_TIER{tier}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        current_time = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
        
        # 计算交易参数
        if order_type == ORDER_TYPE_MARKET:
            # 市价单：使用当前价格
            execution_price = current_price
            slippage = 0.02  # 市价单有较高滑点
            effective_price = execution_price * (1 - slippage)
        else:
            # 限价单：使用当前价格的102%作为限价
            execution_price = current_price * 1.02
            slippage = 0.0
            effective_price = execution_price
        
        total_proceeds = effective_price * sell_quantity
        commission = total_proceeds * 0.0005  # 0.05%佣金
        stamp_duty = total_proceeds * 0.001   # 0.1%印花税
        total_amount = total_proceeds - commission - stamp_duty
        
        # 计算这部分仓位的成本
        cost_basis = position_data["avg_cost"] * sell_quantity
        realized_pnl = total_amount - cost_basis
        realized_pnl_pct = realized_pnl / cost_basis if cost_basis > 0 else 0
        
        transaction = {
            "transaction_id": transaction_id,
            "transaction_type": "partial_profit_taking",
            "ticker": ticker,
            "name": position_data["name"],
            "action": "sell",
            "quantity": sell_quantity,
            "price": execution_price,
            "effective_price": effective_price,
            "slippage": slippage,
            "total_amount": total_amount,
            "timestamp": current_time.isoformat(),
            "locked_until": None,
            "lock_period_days": 0,
            "contract_id": f"PROFIT_TAKE_{ticker}_TIER{tier}",
            "status": "executed",
            "order_type": order_type,
            "rules_applied": {
                "profit_taking_tier": tier,
                "profit_threshold": profit_threshold,
                "reduction_percentage": reduction_pct,
                "original_lock_period_violation": False,
                "strategy_override": True
            },
            "execution_details": {
                "order_type": order_type,
                "filled_price": effective_price,
                "commission": commission,
                "stamp_duty": stamp_duty,
                "total_proceeds": total_proceeds,
                "exchange": "SZSE" if ticker.startswith("0") or ticker.startswith("3") else "SSE",
                "settlement_date": (current_time + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
                "realized_pnl": realized_pnl,
                "realized_pnl_pct": realized_pnl_pct * 100,
                "remaining_quantity": total_quantity - sell_quantity
            },
            "strategy_signal": {
                "signal_type": "profit_taking_v1",
                "tier": tier,
                "profit_threshold_met": profit_threshold,
                "current_profit_pct": profit_status["unrealized_pnl_pct"] * 100,
                "reduction_percentage": reduction_pct * 100
            },
            "risk_parameters": {
                "position_before": total_quantity,
                "position_after": total_quantity - sell_quantity,
                "reduction_percentage": reduction_pct * 100,
                "avg_cost_before": position_data["avg_cost"],
                "realized_profit_pct": realized_pnl_pct * 100
            },
            "metadata": {
                "executed_by": "琥珀引擎演武场 - ProfitTakingExecutor",
                "authorization": "[最高执行指令] 专项一",
                "engine_version": "V1.5.0",
                "simulation": True,
                "strategy_tag": "[STRATEGY_LOCKED_PROFIT]",
                "profit_taking_tier": tier,
                "notes": f"分阶获利 Tier {tier}: 盈利≥{profit_threshold*100:.1f}%时卖出{reduction_pct*100:.0f}%仓位"
            }
        }
        
        # 更新基金数据
        self.fund_data["current_capital"] += total_amount
        
        # 更新持仓数量
        if sell_quantity == total_quantity:
            # 如果卖出全部，移除持仓
            self.fund_data["positions"].pop(position_index)
        else:
            # 更新持仓数量
            position_data["quantity"] = total_quantity - sell_quantity
            position_data["market_value"] = current_price * position_data["quantity"]
            position_data["cost_basis"] = position_data["avg_cost"] * position_data["quantity"]
            
            # 重新计算浮动盈亏
            position_data["unrealized_pnl"] = (current_price - position_data["avg_cost"]) * position_data["quantity"]
            position_data["unrealized_pnl_pct"] = (current_price - position_data["avg_cost"]) / position_data["avg_cost"] if position_data["avg_cost"] > 0 else 0
        
        # 添加交易记录
        self.fund_data["transaction_history"].append(transaction)
        
        # 更新性能指标
        self.fund_data["performance_metrics"]["total_trades"] += 1
        if realized_pnl > 0:
            self.fund_data["performance_metrics"]["profitable_trades"] += 1
        
        # 更新胜率
        total_trades = self.fund_data["performance_metrics"]["total_trades"]
        profitable_trades = self.fund_data["performance_metrics"]["profitable_trades"]
        win_rate = profitable_trades / total_trades if total_trades > 0 else 0
        self.fund_data["performance_metrics"]["win_rate"] = win_rate
        
        # 记录分阶获利日志
        profit_log = {
            "timestamp": current_time.isoformat(),
            "ticker": ticker,
            "tier": tier,
            "profit_pct": profit_status["unrealized_pnl_pct"] * 100,
            "sell_quantity": sell_quantity,
            "remaining_quantity": total_quantity - sell_quantity,
            "realized_pnl": realized_pnl,
            "realized_pnl_pct": realized_pnl_pct * 100,
            "transaction_id": transaction_id,
            "strategy_tag": "[STRATEGY_LOCKED_PROFIT]"
        }
        
        self.profit_taking_logs.append(profit_log)
        
        # 保存数据
        self.save_fund_data()
        
        # 保存详细交易日志
        log_file = f"logs/arena/profit_taking/{transaction_id}.json"
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(transaction, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 分阶获利 Tier {tier} 执行成功: {ticker}")
        print(f"   卖出数量: {sell_quantity}股 ({reduction_pct*100:.0f}%)")
        print(f"   剩余数量: {total_quantity - sell_quantity}股")
        print(f"   执行价格: ¥{effective_price:.2f}/股 ({order_type}单)")
        print(f"   实现盈亏: ¥{realized_pnl:,.2f} ({realized_pnl_pct*100:.1f}%)")
        print(f"   策略标签: [STRATEGY_LOCKED_PROFIT]")
        print(f"   交易ID: {transaction_id}")
        print(f"   日志文件: {log_file}")
        
        return True, f"Tier {tier} 分阶获利成功", transaction
    
    def scan_all_positions_for_profit_taking(self, price_data: Dict[str, float]) -> Dict:
        """
        扫描所有持仓，检查是否需要执行分阶获利
        
        参数:
            price_data: {股票代码: 当前价格}
            
        返回:
            扫描结果和执行的交易
        """
        print("🔍 扫描所有持仓分阶获利机会...")
        
        scan_results = {
            "scan_time": datetime.datetime.now().isoformat(),
            "total_positions": 0,
            "eligible_positions": [],
            "executed_trades": [],
            "summary": {}
        }
        
        positions = self.fund_data.get("positions", [])
        scan_results["total_positions"] = len(positions)
        
        tier_1_eligible = []
        tier_2_eligible = []
        executed_trades = []
        
        for position in positions:
            ticker = position["ticker"]
            
            # 获取当前价格
            if ticker not in price_data:
                print(f"⚠️  跳过 {ticker}: 无价格数据")
                continue
            
            current_price = price_data[ticker]
            
            # 更新持仓价格
            position["current_price"] = current_price
            position["market_value"] = current_price * position["quantity"]
            position["unrealized_pnl"] = (current_price - position["avg_cost"]) * position["quantity"]
            position["unrealized_pnl_pct"] = (current_price - position["avg_cost"]) / position["avg_cost"] if position["avg_cost"] > 0 else 0
            
            # 计算盈利状态
            profit_status = self.calculate_position_profit(position)
            
            position_info = {
                "ticker": ticker,
                "name": position["name"],
                "quantity": position["quantity"],
                "avg_cost": position["avg_cost"],
                "current_price": current_price,
                "profit_pct": profit_status["unrealized_pnl_pct"] * 100,
                "tier_1_eligible": profit_status["can_execute_tier_1"],
                "tier_2_eligible": profit_status["can_execute_tier_2"],
                "executed_tier_1": profit_status["executed_tier_1"],
                "executed_tier_2": profit_status["executed_tier_2"]
            }
            
            scan_results["eligible_positions"].append(position_info)
            
            # 检查并执行分阶获利
            if profit_status["can_execute_tier_1"]:
                tier_1_eligible.append(ticker)
                print(f"🎯 {ticker}: 符合 Tier 1 条件 (盈利: {profit_status['profit_pct_formatted']})")
                
                # 执行 Tier 1
                success, message, transaction = self.execute_profit_taking_v1(ticker, current_price, 1)
                if success:
                    executed_trades.append({
                        "ticker": ticker,
                        "tier": 1,
                        "transaction_id": transaction.get("transaction_id"),
                        "profit_pct": profit_status["unrealized_pnl_pct"] * 100
                    })
            
            elif profit_status["can_execute_tier_2"]:
                tier_2_eligible.append(ticker)
                print(f"🎯 {ticker}: 符合 Tier 2 条件 (盈利: {profit_status['profit_pct_formatted']})")
                
                # 执行 Tier 2
                success, message, transaction = self.execute_profit_taking_v1(ticker, current_price, 2)
                if success:
                    executed_trades.append({
                        "ticker": ticker,
                        "tier": 2,
                        "transaction_id": transaction.get("transaction_id"),
                        "profit_pct": profit_status["unrealized_pnl_pct"] * 100
                    })
        
        # 保存更新后的持仓数据
        self.save_fund_data()
        
        scan_results["executed_trades"] = executed_trades
        scan_results["summary"] = {
            "tier_1_eligible_count": len(tier_1_eligible),
            "tier_2_eligible_count": len(tier_2_eligible),
            "trades_executed": len(executed_trades),
            "tier_1_eligible": tier_1_eligible,
            "tier_2_eligible": tier_2_eligible
        }
        
        # 保存扫描报告
        report_file = f"logs/arena/profit_taking/scan_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(scan_results, f, ensure_ascii=False, indent=2)
        
        print(f"📊 扫描完成:")
        print(f"   总持仓: {len(positions)}")
        print(f"   Tier 1 可执行: {len(tier_1_eligible)}")
        print(f"   Tier 2 可执行: {len(tier_2_eligible)}")
        print(f"   已执行交易: {len(executed_trades)}")
        print(f"   报告文件: {report_file}")
        
        return scan_results
    
    def generate_profit_taking_report(self) -> Dict:
        """生成分阶获利报告"""
        if not self.fund_data:
            return {"error": "基金数据未加载"}
        
        # 分析分阶获利交易
        transactions = self.fund_data.get("transaction_history", [])
        profit_taking_transactions = [t for t in transactions if t.get("transaction_type") == "partial_profit_taking"]
        
        # 按分阶统计
        tier_1_transactions = [t for t in profit_taking_transactions if t.get("metadata", {}).get("profit_taking_tier") == 1]
        tier_2_transactions = [t for t in profit_taking_transactions if t.get("metadata", {}).get("profit_taking_tier") == 2]
        
        # 计算总收益
        total_profit_tier_1 = sum(t.get("execution_details", {}).get("realized_pnl", 0) for t in tier_1_transactions)
        total_profit_tier_2 = sum(t.get("execution_details", {}).get("realized_pnl", 0) for t in tier_2_transactions)
        total_profit = total_profit_tier_1 + total_profit_tier_2
        
        # 分析当前持仓的潜在获利机会
        positions = self.fund_data.get("positions", [])
        potential_tier_1 = []
        potential_tier_2 = []
        
        for position in positions:
            profit_status = self.calculate_position_profit(position)
            
            if profit_status["can_execute_tier_1"]:
                potential_tier_1.append({
                    "ticker": position["ticker"],
                    "profit_pct": profit_status["unrealized_pnl_pct"] * 100,
                    "potential_profit": profit_status["unrealized_pnl"] * POSITION_REDUCTION_TIER_1
                })
            
            if profit_status["can_execute_tier_2"]:
                potential_tier_2.append({
                    "ticker": position["ticker"],
                    "profit_pct": profit_status["unrealized_pnl_pct"] * 100,
                    "potential_profit": profit_status["unrealized_pnl"] * POSITION_REDUCTION_TIER_2
                })
        
        report = {
            "report_time": datetime.datetime.now().isoformat(),
            "strategy_name": "分阶获利 v1",
            "parameters": {
                "tier_1_threshold": PROFIT_TAKING_TIER_1 * 100,
                "tier_2_threshold": PROFIT_TAKING_TIER_2 * 100,
                "tier_1_reduction": POSITION_REDUCTION_TIER_1 * 100,
                "tier_2_reduction": POSITION_REDUCTION_TIER_2 * 100,
                "max_total_reduction": MAX_TIER_REDUCTION * 100
            },
            "performance_summary": {
                "total_profit_taking_trades": len(profit_taking_transactions),
                "tier_1_trades": len(tier_1_transactions),
                "tier_2_trades": len(tier_2_transactions),
                "total_realized_profit": total_profit,
                "tier_1_profit": total_profit_tier_1,
                "tier_2_profit": total_profit_tier_2,
                "avg_profit_per_trade": total_profit / len(profit_taking_transactions) if profit_taking_transactions else 0
            },
            "current_opportunities": {
                "potential_tier_1_count": len(potential_tier_1),
                "potential_tier_2_count": len(potential_tier_2),
                "potential_tier_1": potential_tier_1,
                "potential_tier_2": potential_tier_2,
                "total_potential_profit": sum([p["potential_profit"] for p in potential_tier_1 + potential_tier_2])
            },
            "strategy_logs": self.profit_taking_logs[-10:] if self.profit_taking_logs else [],  # 最近10条日志
            "metadata": {
                "engine_version": "V1.5.0",
                "created_by": "ProfitTakingExecutor",
                "authorization": "[最高执行指令] 专项一"
            }
        }
        
        return report
    
    def print_strategy_summary(self):
        """打印策略摘要"""
        print("=" * 60)
        print("💰 分阶获利策略 v1 摘要")
        print("=" * 60)
        
        print("📊 策略参数:")
        print(f"   Tier 1: 盈利 ≥ {PROFIT_TAKING_TIER_1*100:.1f}% → 卖出{POSITION_REDUCTION_TIER_1*100:.0f}% (市价单)")
        print(f"   Tier 2: 盈利 ≥ {PROFIT_TAKING_TIER_2*100:.1f}% → 再卖出{POSITION_REDUCTION_TIER_2*100:.0f}% (限价单)")
        print(f"   最大减仓: {MAX_TIER_REDUCTION*100:.0f}% (两阶段合计)")
        
        report = self.generate_profit_taking_report()
        
        print(f"\\n📈 策略绩效:")
        print(f"   总获利交易: {report['performance_summary']['total_profit_taking_trades']}")
        print(f"   Tier 1 交易: {report['performance_summary']['tier_1_trades']}")
        print(f"   Tier 2 交易: {report['performance_summary']['tier_2_trades']}")
        print(f"   总实现盈利: ¥{report['performance_summary']['total_realized_profit']:,.2f}")
        print(f"   单笔平均盈利: ¥{report['performance_summary']['avg_profit_per_trade']:,.2f}")
        
        print(f"\\n🎯 当前机会:")
        print(f"   潜在 Tier 1: {report['current_opportunities']['potential_tier_1_count']}")
        print(f"   潜在 Tier 2: {report['current_opportunities']['potential_tier_2_count']}")
        print(f"   潜在总盈利: ¥{report['current_opportunities']['total_potential_profit']:,.2f}")
        
        print("\\n🏷️ 策略标签:")
        print("   [STRATEGY_LOCKED_PROFIT] - 所有分阶获利交易")
        
        print("=" * 60)

def main():
    """主函数 - 演示分阶获利策略"""
    print("=" * 60)
    print("💰 琥珀引擎演武场 - 分阶获利策略 v1")
    print("=" * 60)
    
    # 初始化执行器
    executor = ProfitTakingExecutor()
    
    # 打印策略摘要
    executor.print_strategy_summary()
    
    # 模拟价格数据
    print("\\n📈 模拟分阶获利扫描...")
    price_data = {
        "000681": 21.50,  # 当前价格21.50，假设成本20.07，盈利约7.1%
        "518880": 4.85    # 当前价格4.85，假设成本4.60，盈利约5.4%
    }
    
    # 扫描并执行分阶获利
    scan_results = executor.scan_all_positions_for_profit_taking(price_data)
    
    # 生成详细报告
    report = executor.generate_profit_taking_report()
    report_file = "logs/arena/profit_taking/strategy_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\\n📋 详细策略报告已保存: {report_file}")
    print("=" * 60)
    print("🎉 分阶获利策略演示完成")
    print("=" * 60)

if __name__ == "__main__":
    main()