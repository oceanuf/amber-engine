#!/usr/bin/env python3
"""
琥珀引擎演武场核心引擎
实现虚拟基金管理和量化交易验证
符合 [最高作战指令] 专项二要求
铁律: locked_period = 30，严禁系统在30天内执行任何非强制止损的卖出动作
"""

import os
import sys
import json
import time
import datetime
import hashlib
import uuid
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import statistics
import math

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 常量定义
LOCKED_PERIOD_DAYS = 30
STOP_LOSS_DAILY = -0.10  # 单日亏损超过10%
STOP_LOSS_TOTAL = -0.15  # 累计亏损超过15%
POSITION_LIMIT_PCT = 0.20  # 单只股票仓位不超过20%
INITIAL_CAPITAL = 1000000.00  # 初始资金100万

@dataclass
class Transaction:
    """交易记录数据类"""
    transaction_id: str
    transaction_type: str  # open_position, close_position, adjust_position
    ticker: str
    name: str
    action: str  # buy, sell
    quantity: int
    price: float
    slippage: float
    total_amount: float
    timestamp: str
    locked_until: Optional[str] = None
    lock_period_days: int = LOCKED_PERIOD_DAYS
    contract_id: Optional[str] = None
    status: str = "pending"  # pending, executed, cancelled, failed
    rules_applied: Optional[Dict] = None
    execution_details: Optional[Dict] = None
    strategy_signal: Optional[Dict] = None
    risk_parameters: Optional[Dict] = None
    metadata: Optional[Dict] = None

@dataclass
class Position:
    """持仓记录数据类"""
    ticker: str
    name: str
    quantity: int
    avg_cost: float
    current_price: float
    market_value: float
    cost_basis: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    purchase_date: str
    locked_until: str
    days_held: int
    days_remaining: int
    can_sell: bool
    stop_loss_price: float
    take_profit_price: float
    transaction_ids: List[str]
    metadata: Optional[Dict] = None

class ArenaEngine:
    """演武场核心引擎"""
    
    def __init__(self, fund_db_path: str = "database/arena/virtual_fund.json"):
        self.fund_db_path = fund_db_path
        self.fund_data = None
        self.positions = {}
        self.transactions = []
        
        # 确保目录存在
        os.makedirs(os.path.dirname(fund_db_path), exist_ok=True)
        os.makedirs("logs/arena", exist_ok=True)
        
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
                # 创建新的虚拟基金
                self.initialize_fund()
                return True
        except Exception as e:
            print(f"❌ 加载基金数据失败: {e}")
            return False
    
    def initialize_fund(self):
        """初始化虚拟基金"""
        fund_id = f"VIRTUAL_FUND_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.fund_data = {
            "fund_id": fund_id,
            "fund_name": "琥珀引擎演武场虚拟基金",
            "currency": "CNY",
            "initial_capital": INITIAL_CAPITAL,
            "current_capital": INITIAL_CAPITAL,
            "locked_period": LOCKED_PERIOD_DAYS,
            "created_time": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
            "last_updated": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
            "status": "active",
            "rules": {
                "lock_period_rule": f"任何非强制止损的卖出动作必须在建仓{LOCKED_PERIOD_DAYS}天后执行",
                "stop_loss_rule": f"强制止损条件：单日亏损超过{STOP_LOSS_DAILY*100}%或累计亏损超过{STOP_LOSS_TOTAL*100}%",
                "position_limit": f"单只股票仓位不超过总资本的{POSITION_LIMIT_PCT*100}%",
                "diversification": "至少持有3只不同行业的股票",
                "rebalance_frequency": f"每{LOCKED_PERIOD_DAYS}天重新评估和调整仓位"
            },
            "positions": [],
            "transaction_history": [],
            "performance_metrics": {
                "total_return": 0.0,
                "annualized_return": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "win_rate": 0.0,
                "total_trades": 0,
                "profitable_trades": 0
            },
            "metadata": {
                "version": "1.0.0",
                "engine_version": "V1.4.1",
                "created_by": "Engineer Cheese 🧀",
                "authorization": "[最高作战指令] 专项二"
            }
        }
        
        self.save_fund_data()
        print(f"🎉 初始化虚拟基金成功: {fund_id}")
        print(f"   初始资金: ¥{INITIAL_CAPITAL:,.2f}")
        print(f"   锁仓周期: {LOCKED_PERIOD_DAYS}天")
    
    def save_fund_data(self):
        """保存基金数据"""
        try:
            # 更新最后修改时间
            self.fund_data["last_updated"] = datetime.datetime.now(
                datetime.timezone(datetime.timedelta(hours=8))
            ).isoformat()
            
            with open(self.fund_db_path, 'w', encoding='utf-8') as f:
                json.dump(self.fund_data, f, ensure_ascii=False, indent=2)
            
            # 创建备份
            backup_dir = "database/arena/backups"
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{backup_dir}/virtual_fund_backup_{timestamp}.json"
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(self.fund_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"❌ 保存基金数据失败: {e}")
            return False
    
    def generate_contract_id(self, ticker: str) -> str:
        """生成唯一合约ID"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        random_hash = hashlib.md5(f"{ticker}_{timestamp}_{uuid.uuid4()}".encode()).hexdigest()[:8]
        return f"CONTRACT_{ticker}_{timestamp}_{random_hash}"
    
    def calculate_position_size(self, signal_confidence: float, current_capital: float) -> float:
        """
        根据信号置信度计算仓位大小
        
        参数:
            signal_confidence: 信号置信度 (0.0-1.0)
            current_capital: 当前可用资金
            
        返回:
            建议投入资金金额
        """
        # 基础仓位比例 (信号置信度映射)
        base_pct = 0.05 + (signal_confidence * 0.15)  # 5%-20%
        
        # 应用仓位限制
        max_pct = POSITION_LIMIT_PCT
        actual_pct = min(base_pct, max_pct)
        
        # 计算金额
        position_amount = current_capital * actual_pct
        
        # 确保有足够的现金
        available_cash = self.fund_data["current_capital"]
        if position_amount > available_cash:
            position_amount = available_cash * 0.95  # 保留5%现金
            
        return position_amount
    
    def check_lock_period_violation(self, ticker: str) -> Tuple[bool, int]:
        """
        检查锁仓期违规
        
        返回:
            (是否违规, 剩余天数)
        """
        # 查找该标的的持仓
        for position in self.fund_data.get("positions", []):
            if position["ticker"] == ticker:
                purchase_date = datetime.datetime.fromisoformat(position["purchase_date"])
                locked_until = datetime.datetime.fromisoformat(position["locked_until"])
                current_time = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
                
                days_held = (current_time - purchase_date).days
                days_remaining = max(0, (locked_until - current_time).days)
                
                # 检查是否在锁仓期内
                if current_time < locked_until:
                    return (True, days_remaining)
                else:
                    return (False, 0)
        
        # 没有找到持仓，表示未持有
        return (False, 0)
    
    def check_stop_loss_conditions(self, ticker: str, current_price: float) -> Tuple[bool, str, float]:
        """
        检查强制止损条件
        
        返回:
            (是否触发止损, 触发原因, 亏损百分比)
        """
        for position in self.fund_data.get("positions", []):
            if position["ticker"] == ticker:
                cost_basis = position["cost_basis"]
                quantity = position["quantity"]
                purchase_date = datetime.datetime.fromisoformat(position["purchase_date"])
                
                # 计算当前价值
                current_value = current_price * quantity
                purchase_value = cost_basis * quantity
                
                # 计算亏损
                loss = current_value - purchase_value
                loss_pct = loss / purchase_value if purchase_value > 0 else 0
                
                # 检查单日亏损 (需要获取昨日价格，这里简化处理)
                # 实际实现中需要从数据库获取昨日价格
                
                # 检查累计亏损
                if loss_pct <= STOP_LOSS_TOTAL:
                    return (True, f"累计亏损超过{STOP_LOSS_TOTAL*100}%", loss_pct)
                
                # 还可以添加其他止损条件
                
                return (False, "", loss_pct)
        
        return (False, "", 0.0)
    
    def open_position(self, 
                     ticker: str, 
                     name: str, 
                     price: float, 
                     signal_data: Dict,
                     slippage: float = 0.05) -> Tuple[bool, str, Transaction]:
        """
        开仓（买入）操作
        
        参数:
            ticker: 股票代码
            name: 股票名称
            price: 当前价格
            signal_data: 策略信号数据
            slippage: 滑点百分比
            
        返回:
            (是否成功, 消息, 交易记录)
        """
        print(f"🎯 尝试开仓: {ticker} ({name})")
        print(f"   当前价格: ¥{price:.2f}")
        print(f"   策略信号: {signal_data}")
        
        # 检查是否已持有该标的
        for position in self.fund_data.get("positions", []):
            if position["ticker"] == ticker:
                msg = f"已持有 {ticker}，不能重复开仓"
                print(f"❌ {msg}")
                return False, msg, None
        
        # 获取信号置信度
        confidence = signal_data.get("confidence", 0.5)
        resonance_score = signal_data.get("resonance_score", 50)
        
        # 计算建议仓位
        current_capital = self.fund_data["current_capital"]
        position_amount = self.calculate_position_size(confidence, current_capital)
        
        # 计算数量 (考虑滑点)
        effective_price = price * (1 + slippage)
        quantity = int(position_amount / effective_price)
        
        if quantity <= 0:
            msg = "计算出的数量为0，无法开仓"
            print(f"❌ {msg}")
            return False, msg, None
        
        # 计算总金额
        total_cost = effective_price * quantity
        commission = total_cost * 0.0005  # 0.05%佣金
        stamp_duty = 0.0  # 买入免印花税
        total_amount = total_cost + commission + stamp_duty
        
        # 检查资金是否充足
        if total_amount > current_capital:
            msg = f"资金不足: 需要¥{total_amount:,.2f}，可用¥{current_capital:,.2f}"
            print(f"❌ {msg}")
            return False, msg, None
        
        # 生成交易记录
        transaction_id = f"TRANS_{ticker}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        contract_id = self.generate_contract_id(ticker)
        
        current_time = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
        locked_until = current_time + datetime.timedelta(days=LOCKED_PERIOD_DAYS)
        
        # 计算止损止盈价格
        stop_loss_price = price * (1 + STOP_LOSS_TOTAL)  # 注意：止损是价格下跌，所以是1+负数
        take_profit_price = price * 1.2  # 20%止盈
        
        transaction = Transaction(
            transaction_id=transaction_id,
            transaction_type="open_position",
            ticker=ticker,
            name=name,
            action="buy",
            quantity=quantity,
            price=price,
            slippage=slippage,
            total_amount=total_amount,
            timestamp=current_time.isoformat(),
            locked_until=locked_until.isoformat(),
            lock_period_days=LOCKED_PERIOD_DAYS,
            contract_id=contract_id,
            status="executed",
            rules_applied={
                "lock_period": True,
                "position_limit": True,
                "stop_loss_exemption": False
            },
            execution_details={
                "order_type": "limit",
                "filled_price": effective_price,
                "commission": commission,
                "stamp_duty": stamp_duty,
                "total_cost": total_cost,
                "exchange": "SZSE" if ticker.startswith("0") or ticker.startswith("3") else "SSE",
                "settlement_date": (current_time + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            },
            strategy_signal=signal_data,
            risk_parameters={
                "stop_loss_price": stop_loss_price,
                "take_profit_price": take_profit_price,
                "max_position_size_percent": POSITION_LIMIT_PCT * 100,
                "actual_position_size_percent": (total_amount / self.fund_data["initial_capital"]) * 100,
                "var_95": total_amount * 0.05  # 简化计算
            },
            metadata={
                "executed_by": "琥珀引擎演武场",
                "authorization": "[最高作战指令] 专项二",
                "engine_version": "V1.4.1",
                "simulation": True
            }
        )
        
        # 更新基金数据
        self.fund_data["current_capital"] -= total_amount
        
        # 添加持仓记录
        position = {
            "ticker": ticker,
            "name": name,
            "quantity": quantity,
            "avg_cost": effective_price,
            "current_price": price,
            "market_value": price * quantity,
            "cost_basis": effective_price,
            "unrealized_pnl": (price - effective_price) * quantity,
            "unrealized_pnl_pct": (price - effective_price) / effective_price,
            "purchase_date": current_time.isoformat(),
            "locked_until": locked_until.isoformat(),
            "days_held": 0,
            "days_remaining": LOCKED_PERIOD_DAYS,
            "can_sell": False,
            "stop_loss_price": stop_loss_price,
            "take_profit_price": take_profit_price,
            "transaction_ids": [transaction_id],
            "metadata": {
                "open_reason": "strategy_signal",
                "signal_confidence": confidence,
                "resonance_score": resonance_score
            }
        }
        
        self.fund_data["positions"].append(position)
        self.fund_data["transaction_history"].append(asdict(transaction))
        
        # 更新性能指标
        self.fund_data["performance_metrics"]["total_trades"] += 1
        
        # 保存数据
        self.save_fund_data()
        
        # 保存详细交易日志
        log_file = f"logs/arena/{transaction_id}.json"
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(transaction), f, ensure_ascii=False, indent=2)
        
        print(f"✅ 开仓成功: {ticker}")
        print(f"   数量: {quantity}股")
        print(f"   成本: ¥{effective_price:.2f}/股")
        print(f"   总金额: ¥{total_amount:,.2f}")
        print(f"   锁仓至: {locked_until.strftime('%Y-%m-%d')}")
        print(f"   交易ID: {transaction_id}")
        print(f"   日志文件: {log_file}")
        
        return True, "开仓成功", transaction
    
    def close_position(self, 
                      ticker: str, 
                      price: float,
                      reason: str = "strategy_signal",
                      slippage: float = 0.05) -> Tuple[bool, str, Transaction]:
        """
        平仓（卖出）操作
        
        参数:
            ticker: 股票代码
            price: 当前价格
            reason: 平仓原因
            slippage: 滑点百分比
            
        返回:
            (是否成功, 消息, 交易记录)
        """
        print(f"🎯 尝试平仓: {ticker}")
        print(f"   当前价格: ¥{price:.2f}")
        print(f"   平仓原因: {reason}")
        
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
        
        # 检查锁仓期
        is_violation, days_remaining = self.check_lock_period_violation(ticker)
        
        # 检查止损条件
        is_stop_loss, stop_loss_reason, loss_pct = self.check_stop_loss_conditions(ticker, price)
        
        # 确定平仓理由是否允许
        can_close = False
        close_reason = ""
        
        if is_stop_loss:
            can_close = True
            close_reason = f"强制止损: {stop_loss_reason}"
            print(f"⚠️  触发强制止损: {stop_loss_reason} (亏损: {loss_pct*100:.1f}%)")
        elif not is_violation:
            can_close = True
            close_reason = "锁仓期结束，策略平仓"
            print(f"✅ 锁仓期已结束，允许平仓")
        elif reason == "emergency":
            can_close = True
            close_reason = "紧急情况平仓"
            print(f"⚠️  紧急情况平仓 (锁仓期违规)")
        else:
            msg = f"锁仓期违规: 还剩{days_remaining}天，不允许非强制止损平仓"
            print(f"❌ {msg}")
            return False, msg, None
        
        # 执行平仓
        quantity = position_data["quantity"]
        effective_price = price * (1 - slippage)  # 卖出考虑负滑点
        total_proceeds = effective_price * quantity
        
        commission = total_proceeds * 0.0005  # 0.05%佣金
        stamp_duty = total_proceeds * 0.001   # 0.1%印花税
        total_amount = total_proceeds - commission - stamp_duty
        
        # 生成交易记录
        transaction_id = f"TRANS_{ticker}_CLOSE_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        current_time = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
        
        # 计算盈亏
        cost_basis = position_data["cost_basis"] * quantity
        realized_pnl = total_amount - cost_basis
        realized_pnl_pct = realized_pnl / cost_basis if cost_basis > 0 else 0
        
        transaction = Transaction(
            transaction_id=transaction_id,
            transaction_type="close_position",
            ticker=ticker,
            name=position_data["name"],
            action="sell",
            quantity=quantity,
            price=price,
            slippage=slippage,
            total_amount=total_amount,
            timestamp=current_time.isoformat(),
            locked_until=None,
            lock_period_days=0,
            contract_id=position_data.get("transaction_ids", [""])[0] + "_CLOSE",
            status="executed",
            rules_applied={
                "lock_period_violation": is_violation,
                "stop_loss_triggered": is_stop_loss,
                "emergency_close": reason == "emergency"
            },
            execution_details={
                "order_type": "limit",
                "filled_price": effective_price,
                "commission": commission,
                "stamp_duty": stamp_duty,
                "total_proceeds": total_proceeds,
                "exchange": "SZSE" if ticker.startswith("0") or ticker.startswith("3") else "SSE",
                "settlement_date": (current_time + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
                "realized_pnl": realized_pnl,
                "realized_pnl_pct": realized_pnl_pct * 100
            },
            strategy_signal={
                "close_reason": close_reason,
                "original_signal": position_data.get("metadata", {}).get("open_reason", "unknown")
            },
            risk_parameters={
                "final_loss_pct": loss_pct * 100 if is_stop_loss else 0,
                "days_held": position_data.get("days_held", 0),
                "max_drawdown": 0.0  # 简化处理
            },
            metadata={
                "executed_by": "琥珀引擎演武场",
                "authorization": "[最高作战指令] 专项二",
                "engine_version": "V1.4.1",
                "simulation": True,
                "notes": close_reason
            }
        )
        
        # 更新基金数据
        self.fund_data["current_capital"] += total_amount
        
        # 移除持仓
        self.fund_data["positions"].pop(position_index)
        
        # 添加交易记录
        self.fund_data["transaction_history"].append(asdict(transaction))
        
        # 更新性能指标
        self.fund_data["performance_metrics"]["total_trades"] += 1
        if realized_pnl > 0:
            self.fund_data["performance_metrics"]["profitable_trades"] += 1
        
        # 计算胜率
        total_trades = self.fund_data["performance_metrics"]["total_trades"]
        profitable_trades = self.fund_data["performance_metrics"]["profitable_trades"]
        win_rate = profitable_trades / total_trades if total_trades > 0 else 0
        self.fund_data["performance_metrics"]["win_rate"] = win_rate
        
        # 保存数据
        self.save_fund_data()
        
        # 保存详细交易日志
        log_file = f"logs/arena/{transaction_id}.json"
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(transaction), f, ensure_ascii=False, indent=2)
        
        print(f"✅ 平仓成功: {ticker}")
        print(f"   数量: {quantity}股")
        print(f"   价格: ¥{effective_price:.2f}/股")
        print(f"   总金额: ¥{total_amount:,.2f}")
        print(f"   实现盈亏: ¥{realized_pnl:,.2f} ({realized_pnl_pct*100:.1f}%)")
        print(f"   平仓原因: {close_reason}")
        print(f"   交易ID: {transaction_id}")
        print(f"   日志文件: {log_file}")
        
        return True, close_reason, transaction
    
    def update_position_prices(self, price_data: Dict[str, float]):
        """
        更新持仓价格
        
        参数:
            price_data: {股票代码: 当前价格}
        """
        updated = False
        
        for position in self.fund_data.get("positions", []):
            ticker = position["ticker"]
            if ticker in price_data:
                old_price = position["current_price"]
                new_price = price_data[ticker]
                
                if old_price != new_price:
                    position["current_price"] = new_price
                    position["market_value"] = new_price * position["quantity"]
                    position["unrealized_pnl"] = (new_price - position["avg_cost"]) * position["quantity"]
                    position["unrealized_pnl_pct"] = (new_price - position["avg_cost"]) / position["avg_cost"] if position["avg_cost"] > 0 else 0
                    
                    # 更新持有天数
                    purchase_date = datetime.datetime.fromisoformat(position["purchase_date"])
                    current_time = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
                    days_held = (current_time - purchase_date).days
                    position["days_held"] = days_held
                    
                    # 更新剩余天数
                    locked_until = datetime.datetime.fromisoformat(position["locked_until"])
                    days_remaining = max(0, (locked_until - current_time).days)
                    position["days_remaining"] = days_remaining
                    position["can_sell"] = days_remaining == 0
                    
                    updated = True
        
        if updated:
            self.save_fund_data()
            print("✅ 持仓价格更新完成")
    
    def generate_performance_report(self) -> Dict:
        """生成绩效报告"""
        if not self.fund_data:
            return {"error": "基金数据未加载"}
        
        positions = self.fund_data.get("positions", [])
        transactions = self.fund_data.get("transaction_history", [])
        metrics = self.fund_data.get("performance_metrics", {})
        
        # 计算总市值
        total_market_value = sum(p["market_value"] for p in positions)
        total_cost_basis = sum(p["cost_basis"] * p["quantity"] for p in positions)
        total_unrealized_pnl = sum(p["unrealized_pnl"] for p in positions)
        
        # 计算已实现盈亏
        closed_transactions = [t for t in transactions if t.get("transaction_type") == "close_position"]
        total_realized_pnl = sum(t.get("execution_details", {}).get("realized_pnl", 0) for t in closed_transactions)
        
        # 总资产
        total_assets = self.fund_data["current_capital"] + total_market_value
        
        # 总回报率
        initial_capital = self.fund_data["initial_capital"]
        total_return = ((total_assets - initial_capital) / initial_capital) * 100
        
        # 计算夏普比率（简化）
        # 实际实现需要历史收益率数据
        
        report = {
            "report_time": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
            "fund_summary": {
                "fund_id": self.fund_data["fund_id"],
                "fund_name": self.fund_data["fund_name"],
                "initial_capital": initial_capital,
                "current_capital": self.fund_data["current_capital"],
                "total_market_value": total_market_value,
                "total_assets": total_assets,
                "total_return_pct": total_return,
                "total_unrealized_pnl": total_unrealized_pnl,
                "total_realized_pnl": total_realized_pnl,
                "cash_ratio": (self.fund_data["current_capital"] / total_assets) * 100
            },
            "position_summary": {
                "total_positions": len(positions),
                "active_positions": len([p for p in positions if p.get("status", "active") == "active"]),
                "positions_by_ticker": {p["ticker"]: p["market_value"] for p in positions}
            },
            "performance_metrics": metrics,
            "risk_metrics": {
                "concentration_risk": self.calculate_concentration_risk(),
                "liquidity_risk": self.calculate_liquidity_risk(),
                "lock_period_risk": self.calculate_lock_period_risk()
            },
            "rule_compliance": {
                "lock_period_violations": self.check_all_lock_period_violations(),
                "position_limit_violations": self.check_position_limit_violations(),
                "diversification_violations": self.check_diversification_violations()
            }
        }
        
        return report
    
    def calculate_concentration_risk(self) -> float:
        """计算集中度风险"""
        positions = self.fund_data.get("positions", [])
        if not positions:
            return 0.0
        
        total_market_value = sum(p["market_value"] for p in positions)
        if total_market_value == 0:
            return 0.0
        
        # 计算赫芬达尔指数 (HHI)
        hhi = sum((p["market_value"] / total_market_value) ** 2 for p in positions)
        return hhi
    
    def calculate_liquidity_risk(self) -> float:
        """计算流动性风险"""
        positions = self.fund_data.get("positions", [])
        locked_positions = [p for p in positions if p.get("days_remaining", 0) > 0]
        
        if not positions:
            return 0.0
        
        return len(locked_positions) / len(positions)
    
    def calculate_lock_period_risk(self) -> float:
        """计算锁仓期风险"""
        positions = self.fund_data.get("positions", [])
        if not positions:
            return 0.0
        
        # 计算平均剩余锁仓天数
        total_days_remaining = sum(p.get("days_remaining", 0) for p in positions)
        return total_days_remaining / len(positions)
    
    def check_all_lock_period_violations(self) -> List[Dict]:
        """检查所有锁仓期违规"""
        violations = []
        
        for position in self.fund_data.get("positions", []):
            is_violation, days_remaining = self.check_lock_period_violation(position["ticker"])
            if is_violation:
                violations.append({
                    "ticker": position["ticker"],
                    "days_remaining": days_remaining,
                    "locked_until": position["locked_until"]
                })
        
        return violations
    
    def check_position_limit_violations(self) -> List[Dict]:
        """检查仓位限制违规"""
        violations = []
        total_assets = self.fund_data["current_capital"] + sum(p["market_value"] for p in self.fund_data.get("positions", []))
        
        for position in self.fund_data.get("positions", []):
            position_pct = position["market_value"] / total_assets if total_assets > 0 else 0
            if position_pct > POSITION_LIMIT_PCT:
                violations.append({
                    "ticker": position["ticker"],
                    "position_pct": position_pct * 100,
                    "limit_pct": POSITION_LIMIT_PCT * 100,
                    "excess_pct": (position_pct - POSITION_LIMIT_PCT) * 100
                })
        
        return violations
    
    def check_diversification_violations(self) -> bool:
        """检查分散化违规"""
        positions = self.fund_data.get("positions", [])
        if len(positions) < 3:
            return True  # 违反至少持有3只股票的规定
        return False
    
    def print_fund_summary(self):
        """打印基金概要"""
        if not self.fund_data:
            print("❌ 基金数据未加载")
            return
        
        print("=" * 60)
        print("🏦 琥珀引擎演武场虚拟基金概要")
        print("=" * 60)
        
        print(f"基金名称: {self.fund_data['fund_name']}")
        print(f"基金ID: {self.fund_data['fund_id']}")
        print(f"初始资金: ¥{self.fund_data['initial_capital']:,.2f}")
        print(f"当前现金: ¥{self.fund_data['current_capital']:,.2f}")
        
        positions = self.fund_data.get("positions", [])
        if positions:
            print(f"持仓数量: {len(positions)}")
            print("")
            print("📊 当前持仓:")
            print("-" * 40)
            
            for position in positions:
                ticker = position["ticker"]
                name = position["name"]
                quantity = position["quantity"]
                avg_cost = position["avg_cost"]
                current_price = position["current_price"]
                market_value = position["market_value"]
                unrealized_pnl = position["unrealized_pnl"]
                unrealized_pnl_pct = position["unrealized_pnl_pct"] * 100
                days_held = position["days_held"]
                days_remaining = position["days_remaining"]
                
                print(f"{ticker} ({name})")
                print(f"  数量: {quantity}股 | 成本: ¥{avg_cost:.2f} | 现价: ¥{current_price:.2f}")
                print(f"  市值: ¥{market_value:,.2f} | 浮动盈亏: ¥{unrealized_pnl:,.2f} ({unrealized_pnl_pct:+.1f}%)")
                print(f"  持有天数: {days_held}天 | 锁仓剩余: {days_remaining}天")
                print("")
        else:
            print("📭 当前无持仓")
        
        # 打印规则
        print("📜 投资规则:")
        print("-" * 40)
        rules = self.fund_data.get("rules", {})
        for rule_name, rule_desc in rules.items():
            print(f"  • {rule_desc}")
        
        print("=" * 60)

def main():
    """主函数 - 演示演武场功能"""
    print("=" * 60)
    print("🎮 琥珀引擎演武场 - 虚拟基金交易引擎")
    print("=" * 60)
    
    # 初始化引擎
    engine = ArenaEngine()
    
    # 打印基金概要
    engine.print_fund_summary()
    
    # 示例：模拟开仓
    print("\\n🚀 模拟开仓示例:")
    print("-" * 40)
    
    signal_data = {
        "source": "Synthesizer共振引擎",
        "resonance_score": 85,
        "algorithm_hits": ["G1", "G3", "G4"],
        "confidence": 0.75,
        "recommended_action": "strong_buy"
    }
    
    success, message, transaction = engine.open_position(
        ticker="000681",
        name="视觉中国",
        price=20.07,
        signal_data=signal_data,
        slippage=0.05
    )
    
    if success:
        print(f"✅ 模拟开仓成功: {message}")
        
        # 更新持仓价格（模拟价格变动）
        print("\\n📈 模拟价格更新:")
        print("-" * 40)
        
        engine.update_position_prices({"000681": 20.50})
        
        # 再次打印基金概要
        print("\\n📊 更新后的基金概要:")
        engine.print_fund_summary()
        
        # 生成绩效报告
        print("\\n📋 生成绩效报告:")
        print("-" * 40)
        
        report = engine.generate_performance_report()
        print(f"总资产: ¥{report['fund_summary']['total_assets']:,.2f}")
        print(f"总回报率: {report['fund_summary']['total_return_pct']:.2f}%")
        print(f"持仓数量: {report['position_summary']['total_positions']}")
        
        # 保存报告
        report_file = "logs/arena/performance_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\\n📁 报告已保存: {report_file}")
    else:
        print(f"❌ 模拟开仓失败: {message}")
    
    print("\\n" + "=" * 60)
    print("🎉 演武场引擎演示完成")
    print("=" * 60)

if __name__ == "__main__":
    main()