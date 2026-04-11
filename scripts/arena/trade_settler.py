#!/usr/bin/env python3
"""
琥珀引擎 - 交易清算模块 (Trade Settler)
版本: V1.0.0
功能: 自动检测已完成的交易，计算盈亏，生成交易日志
法典依据: 任务指令[2616-0411-P0E] - 虚拟基金清算自动化与实战复盘闭环
作者: Engineer Cheese 🧀
创建日期: 2026-04-11
"""

import os
import sys
import json
import datetime
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import hashlib

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class TradeRecord:
    """交易记录数据类"""
    trade_id: str
    ticker: str
    name: str
    action: str  # 'buy' 或 'sell'
    quantity: int
    price: float
    timestamp: str
    transaction_id: str
    contract_id: str
    status: str
    
    def to_dict(self):
        return asdict(self)

@dataclass
class SettledTrade:
    """已清算交易数据类"""
    settlement_id: str
    ticker: str
    name: str
    buy_transaction_id: str
    sell_transaction_id: Optional[str]
    buy_price: float
    sell_price: float
    buy_quantity: int
    sell_quantity: int
    buy_timestamp: str
    sell_timestamp: Optional[str]
    holding_days: int
    total_investment: float
    total_proceeds: float
    absolute_pnl: float
    pnl_percentage: float
    commission: float
    stamp_duty: float
    net_pnl: float
    roi: float  # 年化收益率
    status: str  # 'open', 'closed', 'partial'
    strategy_signal: Dict[str, Any]
    execution_details: Dict[str, Any]
    
    def to_dict(self):
        return asdict(self)

class TradeSettler:
    """
    交易清算器 - 负责检测已完成交易并计算盈亏
    """
    
    def __init__(self, workspace_root: Optional[str] = None):
        """
        初始化交易清算器
        
        Args:
            workspace_root: 工作空间根目录，如果为None则从环境变量或默认路径获取
        """
        self.workspace_root = workspace_root or self._get_workspace_root()
        self.virtual_fund_path = os.path.join(self.workspace_root, "database", "arena", "virtual_fund.json")
        self.trade_log_path = os.path.join(self.workspace_root, "reports", "arena", "trade_log.json")
        
        # 确保目录存在
        os.makedirs(os.path.dirname(self.trade_log_path), exist_ok=True)
        
        logger.info(f"交易清算器初始化完成，工作空间: {self.workspace_root}")
        logger.info(f"交易日志文件: {self.trade_log_path}")
    
    def _get_workspace_root(self) -> str:
        """获取工作空间根目录"""
        # 优先从环境变量获取
        workspace = os.environ.get("GITHUB_WORKSPACE")
        if workspace and os.path.exists(workspace):
            return workspace
        
        # 默认路径（amber-engine目录）
        default_path = "/home/luckyelite/.openclaw/workspace/amber-engine"
        if os.path.exists(default_path):
            return default_path
        
        # 当前脚本的祖父目录
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return script_dir
    
    def _load_virtual_fund(self) -> Dict:
        """加载虚拟基金数据"""
        try:
            with open(self.virtual_fund_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载virtual_fund.json失败: {e}")
            raise
    
    def _extract_transactions(self, fund_data: Dict) -> List[TradeRecord]:
        """
        从virtual_fund数据中提取所有交易记录
        
        Args:
            fund_data: 虚拟基金数据
            
        Returns:
            交易记录列表
        """
        transactions = []
        
        for tx in fund_data.get('transaction_history', []):
            try:
                record = TradeRecord(
                    trade_id=tx.get('transaction_id', ''),
                    ticker=tx.get('ticker', ''),
                    name=tx.get('name', ''),
                    action=tx.get('action', ''),
                    quantity=tx.get('quantity', 0),
                    price=tx.get('price', 0.0),
                    timestamp=tx.get('timestamp', ''),
                    transaction_id=tx.get('transaction_id', ''),
                    contract_id=tx.get('contract_id', ''),
                    status=tx.get('status', '')
                )
                transactions.append(record)
            except Exception as e:
                logger.warning(f"解析交易记录失败: {tx}, 错误: {e}")
        
        logger.info(f"提取到 {len(transactions)} 条交易记录")
        return transactions
    
    def _match_buy_sell_pairs(self, transactions: List[TradeRecord]) -> List[Tuple[TradeRecord, Optional[TradeRecord]]]:
        """
        匹配买入和卖出交易对
        
        Args:
            transactions: 交易记录列表
            
        Returns:
            (买入记录, 卖出记录) 元组列表，卖出记录可能为None（表示仍持有）
        """
        # 按标的和合约分组
        ticker_groups = {}
        for tx in transactions:
            key = (tx.ticker, tx.contract_id)
            if key not in ticker_groups:
                ticker_groups[key] = []
            ticker_groups[key].append(tx)
        
        pairs = []
        
        for (ticker, contract_id), tx_list in ticker_groups.items():
            # 按时间排序
            tx_list.sort(key=lambda x: x.timestamp)
            
            # 简单匹配：买入后第一个卖出（目前系统只有买入，暂未实现卖出）
            buy_tx = None
            sell_tx = None
            
            for tx in tx_list:
                if tx.action == 'buy' and buy_tx is None:
                    buy_tx = tx
                elif tx.action == 'sell' and buy_tx is not None:
                    sell_tx = tx
                    break
            
            if buy_tx:
                pairs.append((buy_tx, sell_tx))
        
        logger.info(f"匹配到 {len(pairs)} 个交易对（{sum(1 for _, sell in pairs if sell is not None)} 个已清算）")
        return pairs
    
    def _calculate_settlement(self, buy_tx: TradeRecord, sell_tx: Optional[TradeRecord]) -> SettledTrade:
        """
        计算交易清算结果
        
        Args:
            buy_tx: 买入交易
            sell_tx: 卖出交易（None表示仍持有）
            
        Returns:
            清算结果
        """
        # 获取原始交易数据以提取额外信息
        fund_data = self._load_virtual_fund()
        buy_details = None
        sell_details = None
        
        for tx in fund_data.get('transaction_history', []):
            if tx.get('transaction_id') == buy_tx.transaction_id:
                buy_details = tx
            if sell_tx and tx.get('transaction_id') == sell_tx.transaction_id:
                sell_details = tx
        
        # 计算基础指标
        buy_price = buy_tx.price
        buy_quantity = buy_tx.quantity
        total_investment = buy_price * buy_quantity
        
        if sell_tx:
            sell_price = sell_tx.price
            sell_quantity = sell_tx.quantity
            total_proceeds = sell_price * sell_quantity
            absolute_pnl = total_proceeds - total_investment
            pnl_percentage = (absolute_pnl / total_investment * 100) if total_investment > 0 else 0
            
            # 计算持有天数
            try:
                buy_date = datetime.datetime.strptime(buy_tx.timestamp, "%Y-%m-%dT%H:%M:%S%z")
                sell_date = datetime.datetime.strptime(sell_tx.timestamp, "%Y-%m-%dT%H:%M:%S%z")
                holding_days = (sell_date - buy_date).days
            except ValueError:
                holding_days = 0
            
            # 计算年化收益率
            roi = (absolute_pnl / total_investment * 365 / holding_days * 100) if holding_days > 0 else 0
            
            # 获取手续费和印花税（从执行详情中）
            commission = 0.0
            stamp_duty = 0.0
            if buy_details and 'execution_details' in buy_details:
                commission += buy_details['execution_details'].get('commission', 0.0)
            if sell_details and 'execution_details' in sell_details:
                commission += sell_details['execution_details'].get('commission', 0.0)
                stamp_duty += sell_details['execution_details'].get('stamp_duty', 0.0)
            
            net_pnl = absolute_pnl - commission - stamp_duty
            
            status = 'closed'
        else:
            # 未卖出，使用当前价格计算浮动盈亏
            # 注意：这里需要获取当前价格，简化起见使用买入价
            sell_price = buy_price
            sell_quantity = 0
            total_proceeds = 0
            absolute_pnl = 0
            pnl_percentage = 0
            holding_days = 0
            roi = 0
            commission = 0.0
            stamp_duty = 0.0
            net_pnl = 0.0
            status = 'open'
        
        # 生成清算ID
        settlement_id = hashlib.md5(f"{buy_tx.transaction_id}_{sell_tx.transaction_id if sell_tx else 'open'}".encode()).hexdigest()[:12]
        
        # 获取策略信号
        strategy_signal = buy_details.get('strategy_signal', {}) if buy_details else {}
        
        # 获取执行详情
        execution_details = buy_details.get('execution_details', {}) if buy_details else {}
        
        settlement = SettledTrade(
            settlement_id=settlement_id,
            ticker=buy_tx.ticker,
            name=buy_tx.name,
            buy_transaction_id=buy_tx.transaction_id,
            sell_transaction_id=sell_tx.transaction_id if sell_tx else None,
            buy_price=buy_price,
            sell_price=sell_price,
            buy_quantity=buy_quantity,
            sell_quantity=sell_quantity,
            buy_timestamp=buy_tx.timestamp,
            sell_timestamp=sell_tx.timestamp if sell_tx else None,
            holding_days=holding_days,
            total_investment=total_investment,
            total_proceeds=total_proceeds,
            absolute_pnl=absolute_pnl,
            pnl_percentage=pnl_percentage,
            commission=commission,
            stamp_duty=stamp_duty,
            net_pnl=net_pnl,
            roi=roi,
            status=status,
            strategy_signal=strategy_signal,
            execution_details=execution_details
        )
        
        return settlement
    
    def _load_existing_trade_log(self) -> List[Dict]:
        """加载现有的交易日志"""
        if not os.path.exists(self.trade_log_path):
            return []
        
        try:
            with open(self.trade_log_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"加载交易日志失败: {e}，将创建新日志")
            return []
    
    def _save_trade_log(self, settlements: List[SettledTrade]) -> bool:
        """
        保存交易日志
        
        Args:
            settlements: 清算结果列表
            
        Returns:
            是否成功
        """
        try:
            # 转换为字典列表
            settlements_dict = [s.to_dict() for s in settlements]
            
            # 添加元数据
            trade_log = {
                "metadata": {
                    "version": "1.0.0",
                    "generated_at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "generated_by": "TradeSettler",
                    "total_settlements": len(settlements),
                    "closed_settlements": sum(1 for s in settlements if s.status == 'closed'),
                    "open_settlements": sum(1 for s in settlements if s.status == 'open')
                },
                "settlements": settlements_dict
            }
            
            # 保存文件
            with open(self.trade_log_path, 'w', encoding='utf-8') as f:
                json.dump(trade_log, f, ensure_ascii=False, indent=2)
            
            logger.info(f"交易日志已保存: {self.trade_log_path}")
            logger.info(f"总计 {len(settlements)} 个清算记录 ({sum(1 for s in settlements if s.status == 'closed')} 个已关闭)")
            return True
            
        except Exception as e:
            logger.error(f"保存交易日志失败: {e}")
            return False
    
    def run(self) -> bool:
        """
        执行交易清算流程
        
        Returns:
            是否成功
        """
        try:
            logger.info("开始执行交易清算流程...")
            
            # 加载数据
            fund_data = self._load_virtual_fund()
            
            # 提取交易记录
            transactions = self._extract_transactions(fund_data)
            
            if not transactions:
                logger.warning("未找到交易记录")
                return False
            
            # 匹配买卖对
            pairs = self._match_buy_sell_pairs(transactions)
            
            # 计算清算结果
            settlements = []
            for buy_tx, sell_tx in pairs:
                settlement = self._calculate_settlement(buy_tx, sell_tx)
                settlements.append(settlement)
            
            # 保存日志
            success = self._save_trade_log(settlements)
            
            if success:
                logger.info("交易清算流程完成")
            else:
                logger.error("交易清算流程失败")
            
            return success
            
        except Exception as e:
            logger.error(f"交易清算流程异常: {e}")
            return False

def main():
    """主函数"""
    settler = TradeSettler()
    success = settler.run()
    
    if success:
        print("✅ 交易清算成功")
        sys.exit(0)
    else:
        print("❌ 交易清算失败")
        sys.exit(1)

if __name__ == "__main__":
    main()