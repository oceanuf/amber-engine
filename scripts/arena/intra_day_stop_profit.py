#!/usr/bin/env python3
"""
盘中止盈钩子 - V1.7.0 "智库并网"专项行动
专项二：盘中监控点火 - 止盈钩子部署

功能：
1. 实现动态止盈逻辑，根据市场状况调整止盈点
2. 集成到Arena引擎，实现盘中自动止盈
3. 支持多种止盈策略：移动止盈、分批止盈、技术指标止盈

作者: 工程师 Cheese 🧀
日期: 2026-04-05
"""

import os
import sys
import json
import datetime
import math
from typing import Dict, List, Any, Optional, Tuple
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置路径
CONFIG_FILE = "config/stop_profit_strategies.json"
LOG_DIR = "logs/stop_profit"
EXECUTION_LOG = "logs/stop_profit/executions.json"

# 配置日志
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, f"stop_profit_{datetime.date.today().isoformat()}.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class StopProfitHook:
    """盘中止盈钩子"""
    
    def __init__(self, strategy: str = "trailing_stop"):
        self.strategy = strategy
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """加载止盈策略配置"""
        default_config = {
            "version": "1.0.0",
            "strategies": {
                "trailing_stop": {
                    "description": "移动止盈策略",
                    "activation_threshold": 0.08,  # 盈利8%后激活
                    "trailing_distance": 0.05,  # 跟踪距离5%
                    "min_profit": 0.03,  # 最小盈利3%
                    "max_drawdown": 0.02  # 最大回撤2%
                },
                "partial_profit": {
                    "description": "分批止盈策略",
                    "profit_targets": [0.05, 0.10, 0.15],  # 盈利目标
                    "sell_percentages": [0.3, 0.3, 0.4],  # 卖出比例
                    "stop_loss": -0.05  # 止损点-5%
                },
                "technical_stop": {
                    "description": "技术指标止盈",
                    "rsi_overbought": 70,  # RSI超买线
                    "rsi_oversold": 30,  # RSI超卖线
                    "bbands_deviation": 2.0,  # 布林带标准差
                    "ma_cross_signal": True  # 均线交叉信号
                },
                "volatility_adjusted": {
                    "description": "波动率调整止盈",
                    "base_profit_target": 0.10,  # 基础盈利目标10%
                    "volatility_multiplier": 1.5,  # 波动率乘数
                    "atr_period": 14,  # ATR周期
                    "max_position_size": 0.2  # 最大仓位20%
                }
            },
            "default_strategy": "trailing_stop",
            "execution_rules": {
                "require_confirmation": False,  # 是否需要确认
                "max_daily_trades": 3,  # 每日最大交易次数
                "min_trade_size": 100,  # 最小交易数量
                "slippage_limit": 0.001  # 滑点限制0.1%
            }
        }
        
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                # 深度合并配置
                import copy
                merged_config = copy.deepcopy(default_config)
                self._deep_update(merged_config, user_config)
                logger.info(f"已加载用户止盈配置: {CONFIG_FILE}")
                return merged_config
            except Exception as e:
                logger.error(f"加载用户止盈配置失败，使用默认配置: {e}")
                
        return default_config
    
    def _deep_update(self, target: Dict, source: Dict):
        """深度更新字典"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
    
    def calculate_stop_profit(self, 
                             position: Dict[str, Any], 
                             market_data: Dict[str, Any],
                             strategy: Optional[str] = None) -> Dict[str, Any]:
        """计算止盈点
        
        参数:
            position: 持仓信息
            market_data: 市场数据（包含价格、指标等）
            strategy: 止盈策略名称，默认为初始化时设置的策略
            
        返回:
            止盈计算结果
        """
        if strategy is None:
            strategy = self.strategy
            
        strategy_config = self.config['strategies'].get(strategy)
        if not strategy_config:
            logger.warning(f"策略 {strategy} 不存在，使用默认策略")
            strategy = self.config['default_strategy']
            strategy_config = self.config['strategies'][strategy]
        
        # 提取持仓信息
        ticker = position.get('ticker', 'unknown')
        cost_price = position.get('average_cost', 0)
        current_price = market_data.get('close', 0)
        quantity = position.get('quantity', 0)
        
        if cost_price <= 0 or current_price <= 0:
            logger.warning(f"{ticker} 价格数据无效: cost={cost_price}, current={current_price}")
            return {
                "ticker": ticker,
                "error": "价格数据无效",
                "action": "hold"
            }
        
        # 计算当前盈亏
        pnl_abs = current_price - cost_price
        pnl_pct = pnl_abs / cost_price
        total_value = current_price * quantity
        
        logger.info(f"{ticker} 持仓分析: 成本={cost_price:.2f}, 现价={current_price:.2f}, 盈亏={pnl_pct:.2%}")
        
        # 根据策略计算止盈点
        if strategy == "trailing_stop":
            result = self._trailing_stop_strategy(position, market_data, strategy_config, pnl_pct)
        elif strategy == "partial_profit":
            result = self._partial_profit_strategy(position, market_data, strategy_config, pnl_pct)
        elif strategy == "technical_stop":
            result = self._technical_stop_strategy(position, market_data, strategy_config, pnl_pct)
        elif strategy == "volatility_adjusted":
            result = self._volatility_adjusted_strategy(position, market_data, strategy_config, pnl_pct)
        else:
            logger.error(f"未知策略: {strategy}")
            result = {
                "ticker": ticker,
                "strategy": strategy,
                "error": "未知策略",
                "action": "hold"
            }
        
        # 添加公共信息
        result.update({
            "ticker": ticker,
            "strategy": strategy,
            "cost_price": cost_price,
            "current_price": current_price,
            "pnl_abs": pnl_abs,
            "pnl_pct": pnl_pct,
            "quantity": quantity,
            "position_value": total_value,
            "calculated_at": datetime.datetime.now().isoformat()
        })
        
        return result
    
    def _trailing_stop_strategy(self, 
                               position: Dict[str, Any], 
                               market_data: Dict[str, Any],
                               config: Dict[str, Any],
                               pnl_pct: float) -> Dict[str, Any]:
        """移动止盈策略"""
        ticker = position.get('ticker', 'unknown')
        
        # 检查是否达到激活阈值
        activation_threshold = config.get('activation_threshold', 0.08)
        
        if pnl_pct < activation_threshold:
            return {
                "action": "hold",
                "reason": f"盈利未达到激活阈值 {activation_threshold:.1%}",
                "current_profit": pnl_pct,
                "activation_threshold": activation_threshold,
                "distance_to_activate": activation_threshold - pnl_pct
            }
        
        # 获取持仓历史最高价
        position_history = position.get('price_history', [])
        if position_history:
            highest_price = max(position_history)
        else:
            highest_price = market_data.get('close', 0)
        
        current_price = market_data.get('close', 0)
        trailing_distance = config.get('trailing_distance', 0.05)
        
        # 计算移动止盈点
        trailing_stop_price = highest_price * (1 - trailing_distance)
        
        # 检查是否触发止盈
        if current_price <= trailing_stop_price:
            return {
                "action": "sell",
                "reason": f"价格跌破移动止盈点 {trailing_stop_price:.2f}",
                "current_price": current_price,
                "trailing_stop_price": trailing_stop_price,
                "highest_price": highest_price,
                "trailing_distance": trailing_distance,
                "profit_at_exit": pnl_pct
            }
        
        # 检查是否达到最小盈利
        min_profit = config.get('min_profit', 0.03)
        if pnl_pct >= min_profit:
            # 检查回撤是否超过最大允许值
            drawdown_from_high = (highest_price - current_price) / highest_price
            max_drawdown = config.get('max_drawdown', 0.02)
            
            if drawdown_from_high > max_drawdown:
                return {
                    "action": "sell",
                    "reason": f"回撤 {drawdown_from_high:.2%} 超过最大允许值 {max_drawdown:.1%}",
                    "current_price": current_price,
                    "highest_price": highest_price,
                    "drawdown": drawdown_from_high,
                    "max_drawdown": max_drawdown
                }
        
        # 保持持仓，更新止盈点
        return {
            "action": "hold",
            "reason": "价格在移动止盈点之上",
            "current_price": current_price,
            "trailing_stop_price": trailing_stop_price,
            "highest_price": highest_price,
            "current_profit": pnl_pct,
            "drawdown_from_high": (highest_price - current_price) / highest_price
        }
    
    def _partial_profit_strategy(self,
                                position: Dict[str, Any],
                                market_data: Dict[str, Any],
                                config: Dict[str, Any],
                                pnl_pct: float) -> Dict[str, Any]:
        """分批止盈策略"""
        ticker = position.get('ticker', 'unknown')
        quantity = position.get('quantity', 0)
        
        # 获取已止盈记录
        profit_taken = position.get('profit_taken', [])
        total_sold = sum(p.get('quantity', 0) for p in profit_taken)
        remaining_qty = quantity - total_sold
        
        if remaining_qty <= 0:
            return {
                "action": "hold",
                "reason": "已全部止盈",
                "remaining_quantity": 0
            }
        
        # 检查盈利目标
        profit_targets = config.get('profit_targets', [0.05, 0.10, 0.15])
        sell_percentages = config.get('sell_percentages', [0.3, 0.3, 0.4])
        
        # 找到当前达到的最高目标
        target_index = -1
        for i, target in enumerate(profit_targets):
            if pnl_pct >= target:
                target_index = i
        
        if target_index < 0:
            # 未达到任何盈利目标
            stop_loss = config.get('stop_loss', -0.05)
            if pnl_pct <= stop_loss:
                return {
                    "action": "sell",
                    "reason": f"触碰到损点 {stop_loss:.1%}",
                    "current_profit": pnl_pct,
                    "stop_loss": stop_loss,
                    "sell_quantity": remaining_qty,
                    "sell_percentage": 1.0
                }
            
            return {
                "action": "hold",
                "reason": f"未达到盈利目标 (当前: {pnl_pct:.2%}, 最低目标: {profit_targets[0]:.1%})",
                "current_profit": pnl_pct,
                "next_target": profit_targets[0],
                "distance_to_target": profit_targets[0] - pnl_pct
            }
        
        # 检查是否已经执行过该目标的止盈
        target_executed = False
        for taken in profit_taken:
            if taken.get('target_index') == target_index:
                target_executed = True
                break
        
        if target_executed:
            # 已执行过该目标的止盈，检查下一个目标
            if target_index + 1 < len(profit_targets):
                next_target = profit_targets[target_index + 1]
                return {
                    "action": "hold",
                    "reason": f"已执行目标{target_index}止盈，等待下一个目标 {next_target:.1%}",
                    "current_profit": pnl_pct,
                    "next_target": next_target
                }
            else:
                return {
                    "action": "hold",
                    "reason": "已执行所有目标止盈",
                    "current_profit": pnl_pct
                }
        
        # 执行该目标的止盈
        sell_percentage = sell_percentages[target_index] if target_index < len(sell_percentages) else 0.3
        sell_quantity = math.floor(remaining_qty * sell_percentage)
        
        if sell_quantity <= 0:
            sell_quantity = remaining_qty  # 至少卖1股
        
        return {
            "action": "partial_sell",
            "reason": f"达到盈利目标 {profit_targets[target_index]:.1%}",
            "current_profit": pnl_pct,
            "target_index": target_index,
            "target_profit": profit_targets[target_index],
            "sell_percentage": sell_percentage,
            "sell_quantity": sell_quantity,
            "remaining_after_sell": remaining_qty - sell_quantity
        }
    
    def _technical_stop_strategy(self,
                               position: Dict[str, Any],
                               market_data: Dict[str, Any],
                               config: Dict[str, Any],
                               pnl_pct: float) -> Dict[str, Any]:
        """技术指标止盈策略"""
        ticker = position.get('ticker', 'unknown')
        
        # 检查技术指标
        indicators = market_data.get('indicators', {})
        
        sell_signals = []
        
        # 1. RSI超买检查
        rsi = indicators.get('rsi')
        rsi_overbought = config.get('rsi_overbought', 70)
        if rsi and rsi >= rsi_overbought:
            sell_signals.append({
                "type": "rsi_overbought",
                "value": rsi,
                "threshold": rsi_overbought,
                "strength": (rsi - rsi_overbought) / rsi_overbought
            })
        
        # 2. 布林带上轨突破
        bbands_upper = indicators.get('bbands_upper')
        current_price = market_data.get('close', 0)
        if bbands_upper and current_price > bbands_upper:
            deviation = config.get('bbands_deviation', 2.0)
            sell_signals.append({
                "type": "bbands_breakout",
                "current_price": current_price,
                "bbands_upper": bbands_upper,
                "deviation": deviation
            })
        
        # 3. 均线死叉信号（如果有均线数据）
        ma_cross = indicators.get('ma_cross')
        if config.get('ma_cross_signal', True) and ma_cross == 'death_cross':
            sell_signals.append({
                "type": "ma_death_cross",
                "signal": ma_cross
            })
        
        # 评估卖出信号
        if sell_signals:
            # 根据信号强度和当前盈利决定是否卖出
            signal_strength = len(sell_signals)
            
            # 如果有强烈卖出信号且盈利为正，考虑卖出
            if pnl_pct > 0 or signal_strength >= 2:
                return {
                    "action": "sell",
                    "reason": f"技术指标发出卖出信号 ({signal_strength}个)",
                    "signals": sell_signals,
                    "current_profit": pnl_pct,
                    "signal_strength": signal_strength
                }
            else:
                return {
                    "action": "hold",
                    "reason": f"技术指标卖出信号但当前亏损，继续持有",
                    "signals": sell_signals,
                    "current_profit": pnl_pct,
                    "signal_strength": signal_strength
                }
        
        # 检查RSI超卖（可能是不错的加仓点，但这里只处理止盈）
        rsi_oversold = config.get('rsi_oversold', 30)
        if rsi and rsi <= rsi_oversold and pnl_pct > 0:
            # 虽然超卖，但有盈利，可以考虑部分止盈
            return {
                "action": "partial_sell",
                "reason": f"RSI超卖但当前有盈利，建议部分止盈",
                "rsi": rsi,
                "rsi_oversold": rsi_oversold,
                "current_profit": pnl_pct,
                "sell_percentage": 0.3  # 卖出30%
            }
        
        # 没有明确的卖出信号
        return {
            "action": "hold",
            "reason": "技术指标未发出明确卖出信号",
            "current_profit": pnl_pct
        }
    
    def _volatility_adjusted_strategy(self,
                                     position: Dict[str, Any],
                                     market_data: Dict[str, Any],
                                     config: Dict[str, Any],
                                     pnl_pct: float) -> Dict[str, Any]:
        """波动率调整止盈策略"""
        ticker = position.get('ticker', 'unknown')
        
        # 获取波动率数据
        volatility = market_data.get('volatility', {})
        atr = volatility.get('atr', 0)  # 平均真实波幅
        current_price = market_data.get('close', 0)
        
        if atr <= 0 or current_price <= 0:
            logger.warning(f"{ticker} 波动率数据无效，使用基础止盈")
            return self._trailing_stop_strategy(position, market_data, 
                                               self.config['strategies']['trailing_stop'], 
                                               pnl_pct)
        
        # 计算波动率调整的盈利目标
        base_profit_target = config.get('base_profit_target', 0.10)
        volatility_multiplier = config.get('volatility_multiplier', 1.5)
        
        # 计算ATR百分比
        atr_pct = atr / current_price
        
        # 调整盈利目标：波动率越高，盈利目标越高
        adjusted_target = base_profit_target + (atr_pct * volatility_multiplier)
        
        # 计算波动率调整的止盈点
        cost_price = position.get('average_cost', 0)
        profit_target_price = cost_price * (1 + adjusted_target)
        
        if current_price >= profit_target_price:
            return {
                "action": "sell",
                "reason": f"达到波动率调整止盈点 {profit_target_price:.2f}",
                "current_price": current_price,
                "profit_target_price": profit_target_price,
                "adjusted_target": adjusted_target,
                "base_target": base_profit_target,
                "atr_pct": atr_pct,
                "current_profit": pnl_pct
            }
        
        # 计算动态止损点（基于波动率）
        # 止损点 = 成本价 - (ATR * 2)
        stop_loss_price = cost_price - (atr * 2)
        
        if current_price <= stop_loss_price:
            return {
                "action": "sell",
                "reason": f"触波动率调整止损点 {stop_loss_price:.2f}",
                "current_price": current_price,
                "stop_loss_price": stop_loss_price,
                "atr": atr,
                "current_profit": pnl_pct
            }
        
        # 计算当前盈利与目标的距离
        distance_to_target = (profit_target_price - current_price) / current_price
        
        return {
            "action": "hold",
            "reason": f"价格未达到波动率调整止盈点",
            "current_price": current_price,
            "profit_target_price": profit_target_price,
            "stop_loss_price": stop_loss_price,
            "adjusted_target": adjusted_target,
            "atr_pct": atr_pct,
            "current_profit": pnl_pct,
            "distance_to_target": distance_to_target
        }
    
    def execute_stop_profit(self, 
                           decision: Dict[str, Any],
                           position: Dict[str, Any]) -> Dict[str, Any]:
        """执行止盈决策
        
        参数:
            decision: 止盈决策结果
            position: 原始持仓信息
            
        返回:
            执行结果
        """
        ticker = decision.get('ticker', 'unknown')
        action = decision.get('action', 'hold')
        
        execution_result = {
            "ticker": ticker,
            "action": action,
            "decision": decision,
            "executed_at": datetime.datetime.now().isoformat(),
            "execution_id": f"stop_profit_{int(datetime.datetime.now().timestamp())}"
        }
        
        if action == 'hold':
            execution_result['status'] = 'no_action'
            execution_result['message'] = '保持持仓，不执行交易'
            logger.info(f"{ticker}: 保持持仓 - {decision.get('reason', '无理由')}")
            
        elif action in ['sell', 'partial_sell']:
            # 这里应该调用实际的交易执行模块
            # 目前先记录执行决策
            
            execution_rules = self.config['execution_rules']
            
            if execution_rules.get('require_confirmation', False):
                execution_result['status'] = 'pending_confirmation'
                execution_result['message'] = '等待确认执行'
                execution_result['requires_confirmation'] = True
            else:
                execution_result['status'] = 'execution_required'
                execution_result['message'] = '需要执行交易'
                
                # 模拟执行结果
                execution_result['simulated_execution'] = {
                    "quantity": decision.get('sell_quantity', position.get('quantity', 0)),
                    "price": decision.get('current_price', 0),
                    "estimated_value": decision.get('current_price', 0) * decision.get('sell_quantity', 0),
                    "estimated_slippage": execution_rules.get('slippage_limit', 0.001),
                    "execution_time": datetime.datetime.now().isoformat()
                }
                
                logger.info(f"{ticker}: 执行{action} - {decision.get('reason', '无理由')}")
        
        # 记录执行日志
        self._log_execution(execution_result)
        
        return execution_result
    
    def _log_execution(self, execution_result: Dict[str, Any]):
        """记录执行日志"""
        try:
            # 加载现有日志
            executions = []
            if os.path.exists(EXECUTION_LOG):
                with open(EXECUTION_LOG, 'r', encoding='utf-8') as f:
                    try:
                        executions = json.load(f)
                        if not isinstance(executions, list):
                            executions = []
                    except:
                        executions = []
            
            # 添加新执行记录
            executions.append(execution_result)
            
            # 保存日志（保留最近1000条记录）
            with open(EXECUTION_LOG, 'w', encoding='utf-8') as f:
                json.dump(executions[-1000:], f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"记录执行日志失败: {e}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='琥珀引擎盘中止盈钩子')
    parser.add_argument('--position-file', type=str, required=False,
                       help='持仓文件路径（JSON格式）')
    parser.add_argument('--market-data', type=str, required=False,
                       help='市场数据文件路径（JSON格式）')
    parser.add_argument('--strategy', type=str, default='trailing_stop',
                       choices=['trailing_stop', 'partial_profit', 'technical_stop', 'volatility_adjusted'],
                       help='止盈策略选择')
    parser.add_argument('--execute', action='store_true',
                       help='实际执行交易（否则只计算不执行）')
    
    args = parser.parse_args()
    
    # 创建止盈钩子
    hook = StopProfitHook(strategy=args.strategy)
    
    # 加载测试数据
    if args.position_file and os.path.exists(args.position_file):
        with open(args.position_file, 'r', encoding='utf-8') as f:
            position = json.load(f)
    else:
        # 使用模拟持仓
        position = {
            "ticker": "000681",
            "average_cost": 10.0,
            "quantity": 1000,
            "price_history": [10.0, 10.5, 11.0, 10.8, 11.2],
            "profit_taken": []
        }
    
    if args.market_data and os.path.exists(args.market_data):
        with open(args.market_data, 'r', encoding='utf-8') as f:
            market_data = json.load(f)
    else:
        # 使用模拟市场数据
        market_data = {
            "close": 11.5,
            "high": 11.8,
            "low": 11.2,
            "volume": 100000,
            "indicators": {
                "rsi": 65,
                "bbands_upper": 12.0,
                "bbands_lower": 10.5
            },
            "volatility": {
                "atr": 0.15
            }
        }
    
    print(f"\n🎯 止盈策略分析: {args.strategy}")
    print(f"   标的: {position['ticker']}")
    print(f"   持仓成本: {position['average_cost']:.2f}")
    print(f"   当前价格: {market_data['close']:.2f}")
    
    # 计算止盈决策
    decision = hook.calculate_stop_profit(position, market_data, args.strategy)
    
    print(f"\n📊 决策结果: {decision['action']}")
    print(f"   理由: {decision['reason']}")
    print(f"   当前盈利: {decision.get('pnl_pct', 0):.2%}")
    
    if 'trailing_stop_price' in decision:
        print(f"   移动止盈点: {decision['trailing_stop_price']:.2f}")
    
    if 'profit_target_price' in decision:
        print(f"   目标止盈点: {decision['profit_target_price']:.2f}")
    
    if 'stop_loss_price' in decision:
        print(f"   止损点: {decision['stop_loss_price']:.2f}")
    
    # 如果需要执行
    if args.execute:
        print(f"\n⚡ 执行止盈决策...")
        execution = hook.execute_stop_profit(decision, position)
        print(f"   执行状态: {execution['status']}")
        print(f"   执行ID: {execution['execution_id']}")
        
        if execution.get('simulated_execution'):
            sim = execution['simulated_execution']
            print(f"   模拟执行: {sim['quantity']}股 @ {sim['price']:.2f}")


if __name__ == "__main__":
    main()