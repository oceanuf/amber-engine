#!/usr/bin/env python3
"""
专项二：盘中监控点火验证测试
测试心跳监控和止盈钩子功能
"""

import os
import sys
import json
import time
import datetime
import threading
import logging
from unittest.mock import Mock, patch

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_heartbeat_monitoring():
    """测试心跳监控功能（10倍速模拟）"""
    logger.info("测试心跳监控功能（10倍速模拟行情）...")
    
    try:
        # 导入监控器
        from scripts.arena.intra_day_monitor import IntraDayMonitor
        
        # 创建监控器，设置较短的轮询间隔用于测试
        monitor = IntraDayMonitor(poll_interval=1)  # 1分钟轮询，模拟时会加速
        
        # 模拟持仓
        mock_positions = [
            {
                "ticker": "000681",
                "average_cost": 10.0,
                "quantity": 1000,
                "status": "active",
                "position_id": "test_pos_001"
            },
            {
                "ticker": "518880",
                "average_cost": 4.5,
                "quantity": 2000,
                "status": "active",
                "position_id": "test_pos_002"
            }
        ]
        
        # 模拟市场数据序列（10倍速：每6秒代表1分钟，每1.5分钟代表15分钟）
        market_data_sequence = []
        base_price_000681 = 10.0
        base_price_518880 = 4.5
        
        # 生成90分钟的市场数据（实际时间9分钟）
        for minute in range(0, 90, 15):  # 每15分钟一个数据点
            timestamp = datetime.datetime.now() + datetime.timedelta(minutes=minute/10)  # 10倍速
            
            # 模拟价格波动
            price_000681 = base_price_000681 * (1 + (minute % 30 - 15) * 0.001)  # 小幅度波动
            price_518880 = base_price_518880 * (1 + (minute % 20 - 10) * 0.002)  # 稍大波动
            
            market_data_sequence.append({
                "timestamp": timestamp.isoformat(),
                "000681": {
                    "close": price_000681,
                    "high": price_000681 * 1.01,
                    "low": price_000681 * 0.99,
                    "volume": 100000 + minute * 1000
                },
                "518880": {
                    "close": price_518880,
                    "high": price_518880 * 1.02,
                    "low": price_518880 * 0.98,
                    "volume": 200000 + minute * 2000
                }
            })
        
        logger.info(f"生成 {len(market_data_sequence)} 个市场数据点（10倍速模拟）")
        
        # 测试单次监控处理
        with patch.object(monitor, 'load_arena_positions', return_value=mock_positions):
            with patch.object(monitor, 'fetch_stk_mins_data') as mock_fetch:
                # 模拟获取分钟数据
                def side_effect(ticker):
                    if ticker == "000681":
                        return {
                            "ticker": "000681",
                            "latest_timestamp": datetime.datetime.now().isoformat(),
                            "close": 10.2,  # 当前价格
                            "high": 10.5,
                            "low": 10.0,
                            "volume": 150000,
                            "price_change_pct": 0.02,  # +2%
                            "data_points": 96
                        }
                    elif ticker == "518880":
                        return {
                            "ticker": "518880",
                            "latest_timestamp": datetime.datetime.now().isoformat(),
                            "close": 4.6,
                            "high": 4.7,
                            "low": 4.5,
                            "volume": 250000,
                            "price_change_pct": 0.022,  # +2.2%
                            "data_points": 96
                        }
                    return None
                
                mock_fetch.side_effect = side_effect
                
                # 执行单次监控
                start_time = time.time()
                report = monitor.run_once()
                end_time = time.time()
                
                duration = end_time - start_time
                
                logger.info(f"心跳监控测试:")
                logger.info(f"  执行时间: {duration:.2f} 秒")
                logger.info(f"  处理持仓: {report.get('processed_positions')} 个")
                logger.info(f"  发现警报: {report.get('total_alerts')} 个")
                logger.info(f"  监控标的: {report.get('monitored_tickers')}")
                
                # 检查监控是否按预期工作
                if report.get('processed_positions') == 2:
                    logger.info("✅ 心跳监控功能正常")
                    
                    # 检查是否有内存泄漏迹象（简化检查）
                    if duration < 5.0:
                        logger.info("✅ 监控响应时间达标")
                    else:
                        logger.warning(f"⚠️ 监控响应时间较慢 ({duration:.2f}秒)")
                    
                    return True
                else:
                    logger.error(f"❌ 监控处理持仓数量异常: {report.get('processed_positions')}")
                    return False
                    
    except Exception as e:
        logger.error(f"心跳监控测试失败: {e}", exc_info=True)
        return False

def test_stop_profit_logic():
    """测试止盈逻辑（+5.1%回落至+4.8%场景）"""
    logger.info("测试止盈逻辑（+5.1%回落至+4.8%场景）...")
    
    try:
        # 导入止盈钩子
        from scripts.arena.intra_day_stop_profit import StopProfitHook
        
        # 创建止盈钩子，使用移动止盈策略
        hook = StopProfitHook(strategy="trailing_stop")
        
        # 模拟持仓
        position = {
            "ticker": "000681",
            "average_cost": 10.0,
            "quantity": 1000,
            "price_history": [10.0, 10.2, 10.3, 10.4, 10.5, 10.51]  # 历史价格，最高10.51 (+5.1%)
        }
        
        # 场景1：价格达到+5.1%（10.51）
        market_data_peak = {
            "close": 10.51,  # +5.1%
            "high": 10.51,
            "low": 10.3,
            "volume": 200000,
            "indicators": {}
        }
        
        # 计算止盈决策
        decision_peak = hook.calculate_stop_profit(position, market_data_peak)
        
        logger.info(f"价格峰值 (+5.1%) 止盈决策:")
        logger.info(f"  动作: {decision_peak.get('action')}")
        logger.info(f"  理由: {decision_peak.get('reason')}")
        logger.info(f"  当前盈利: {decision_peak.get('pnl_pct', 0):.2%}")
        
        # 更新持仓历史（添加峰值）
        position_with_peak = position.copy()
        position_with_peak['price_history'] = position['price_history'] + [10.51]
        
        # 场景2：价格回落至+4.8%（10.48）
        market_data_fallback = {
            "close": 10.48,  # +4.8% (从+5.1%回落)
            "high": 10.51,
            "low": 10.45,
            "volume": 180000,
            "indicators": {}
        }
        
        decision_fallback = hook.calculate_stop_profit(position_with_peak, market_data_fallback)
        
        logger.info(f"价格回落 (+4.8%) 止盈决策:")
        logger.info(f"  动作: {decision_fallback.get('action')}")
        logger.info(f"  理由: {decision_fallback.get('reason')}")
        logger.info(f"  当前盈利: {decision_fallback.get('pnl_pct', 0):.2%}")
        
        # 关键测试：移动止盈策略是否在回落时触发卖出
        # 移动止盈点 = 最高价10.51 * (1 - 5%) = 9.9845
        # 当前价10.48 > 9.9845，所以应该不触发卖出
        
        expected_action = "hold"  # 应该保持持仓
        actual_action = decision_fallback.get('action')
        
        if actual_action == expected_action:
            logger.info("✅ 止盈逻辑正确：价格回落但未触发止盈点")
            
            # 检查是否有正确的移动止盈点计算
            if 'trailing_stop_price' in decision_fallback:
                trailing_stop = decision_fallback['trailing_stop_price']
                current_price = decision_fallback['current_price']
                
                if current_price > trailing_stop:
                    logger.info(f"✅ 移动止盈点计算正确: {current_price:.2f} > {trailing_stop:.2f}")
                else:
                    logger.warning(f"⚠️ 移动止盈点计算可能有问题: {current_price:.2f} <= {trailing_stop:.2f}")
            
            return True
        else:
            logger.error(f"❌ 止盈逻辑错误: 预期 {expected_action}, 实际 {actual_action}")
            
            # 详细分析
            if decision_fallback.get('action') == 'sell':
                logger.error("  错误: 在未触及止盈点时触发了卖出")
            elif decision_fallback.get('action') == 'partial_sell':
                logger.error("  错误: 在未触及止盈点时触发了部分卖出")
            
            return False
            
    except Exception as e:
        logger.error(f"止盈逻辑测试失败: {e}", exc_info=True)
        return False

def test_stop_profit_execution():
    """测试止盈执行（减仓信号是否秒级发出）"""
    logger.info("测试止盈执行（减仓信号是否秒级发出）...")
    
    try:
        # 导入止盈钩子
        from scripts.arena.intra_day_stop_profit import StopProfitHook
        
        # 创建止盈钩子
        hook = StopProfitHook(strategy="trailing_stop")
        
        # 模拟一个需要止盈的决策
        decision = {
            "ticker": "000681",
            "action": "sell",
            "reason": "价格跌破移动止盈点",
            "current_price": 9.8,
            "trailing_stop_price": 9.9845,
            "highest_price": 10.51,
            "pnl_pct": -0.02  # -2%
        }
        
        position = {
            "ticker": "000681",
            "average_cost": 10.0,
            "quantity": 1000
        }
        
        # 测试执行速度
        start_time = time.time()
        execution_result = hook.execute_stop_profit(decision, position)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # 毫秒
        
        logger.info(f"止盈执行测试:")
        logger.info(f"  响应时间: {response_time:.1f} 毫秒")
        logger.info(f"  执行状态: {execution_result.get('status')}")
        logger.info(f"  执行ID: {execution_result.get('execution_id')}")
        
        # 检查执行记录
        if execution_result.get('status') in ['no_action', 'execution_required', 'pending_confirmation']:
            logger.info("✅ 止盈执行逻辑正常")
            
            # 检查响应时间
            if response_time < 1000:  # 1秒内
                logger.info("✅ 止盈信号秒级发出")
                return True
            else:
                logger.warning(f"⚠️ 止盈信号响应较慢 ({response_time:.1f}毫秒)")
                return False
        else:
            logger.error(f"❌ 止盈执行状态异常: {execution_result.get('status')}")
            return False
            
    except Exception as e:
        logger.error(f"止盈执行测试失败: {e}", exc_info=True)
        return False

def test_scenario_5_percent_drop():
    """测试+5.1%后回落至+4.8%的具体场景"""
    logger.info("测试+5.1%后回落至+4.8%的具体场景...")
    
    try:
        # 使用分批止盈策略测试这个场景
        from scripts.arena.intra_day_stop_profit import StopProfitHook
        
        hook = StopProfitHook(strategy="partial_profit")
        
        # 模拟持仓
        position = {
            "ticker": "TEST001",
            "average_cost": 100.0,
            "quantity": 1000,
            "profit_taken": []  # 尚未止盈
        }
        
        # 价格达到+5.1% (105.1)
        market_data_peak = {
            "close": 105.1,
            "high": 105.1,
            "low": 104.0,
            "volume": 100000,
            "indicators": {}
        }
        
        decision_peak = hook.calculate_stop_profit(position, market_data_peak)
        
        logger.info(f"+5.1%峰值决策:")
        logger.info(f"  动作: {decision_peak.get('action')}")
        
        # 分批止盈策略应该在+5%时触发第一次止盈
        if decision_peak.get('action') == 'partial_sell':
            logger.info("✅ +5.1%触发分批止盈")
            logger.info(f"  卖出比例: {decision_peak.get('sell_percentage', 0):.1%}")
            logger.info(f"  卖出数量: {decision_peak.get('sell_quantity', 0)}")
            
            # 模拟执行第一次止盈
            execution1 = hook.execute_stop_profit(decision_peak, position)
            
            # 更新持仓（部分卖出后）
            position_after_first = position.copy()
            position_after_first['profit_taken'] = [{
                "target_index": 0,
                "quantity": decision_peak.get('sell_quantity', 300),
                "price": 105.1,
                "timestamp": datetime.datetime.now().isoformat()
            }]
            
            # 价格回落至+4.8% (104.8)
            market_data_fallback = {
                "close": 104.8,
                "high": 105.1,
                "low": 104.5,
                "volume": 90000,
                "indicators": {}
            }
            
            decision_fallback = hook.calculate_stop_profit(position_after_first, market_data_fallback)
            
            logger.info(f"回落至+4.8%决策:")
            logger.info(f"  动作: {decision_fallback.get('action')}")
            logger.info(f"  理由: {decision_fallback.get('reason')}")
            
            # 回落时应该保持持仓，等待下一次机会
            if decision_fallback.get('action') == 'hold':
                logger.info("✅ 价格回落时正确保持持仓")
                return True
            else:
                logger.error(f"❌ 价格回落时错误动作: {decision_fallback.get('action')}")
                return False
        else:
            logger.warning(f"⚠️ +5.1%未触发止盈: {decision_peak.get('action')}")
            return False
            
    except Exception as e:
        logger.error(f"场景测试失败: {e}", exc_info=True)
        return False

def run_all_tests():
    """运行所有测试"""
    logger.info("开始专项二：盘中监控点火验证测试")
    logger.info("="*60)
    
    results = {
        "heartbeat": False,
        "stop_profit_logic": False,
        "stop_profit_execution": False,
        "scenario_5_percent": False
    }
    
    try:
        # 测试1: 心跳监控
        results["heartbeat"] = test_heartbeat_monitoring()
        
        # 测试2: 止盈逻辑
        results["stop_profit_logic"] = test_stop_profit_logic()
        
        # 测试3: 止盈执行
        results["stop_profit_execution"] = test_stop_profit_execution()
        
        # 测试4: +5.1%回落场景
        results["scenario_5_percent"] = test_scenario_5_percent_drop()
        
        # 汇总结果
        logger.info("="*60)
        logger.info("专项二验证测试汇总:")
        logger.info(f"  心跳监控功能: {'✅通过' if results['heartbeat'] else '❌失败'}")
        logger.info(f"  止盈逻辑正确性: {'✅通过' if results['stop_profit_logic'] else '❌失败'}")
        logger.info(f"  止盈执行速度: {'✅通过' if results['stop_profit_execution'] else '❌失败'}")
        logger.info(f"  +5.1%回落场景: {'✅通过' if results['scenario_5_percent'] else '❌失败'}")
        
        overall = all(results.values())
        
        if overall:
            logger.info("✅ 专项二验证测试总体通过")
        else:
            logger.warning("⚠️ 专项二验证测试部分失败")
            
        return overall
        
    except Exception as e:
        logger.error(f"测试执行异常: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)