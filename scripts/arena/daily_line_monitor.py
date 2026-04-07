#!/usr/bin/env python3
"""
日线监控模块 - V1.7.0 "智库并网"专项行动 (日线模式)
专项二调整：放弃实时模拟盘，专注日线策略

功能：
1. 每日收盘后执行，基于日线数据监控
2. 监控持仓标的的日线表现
3. 触发止盈止损规则（基于日线）
4. 生成日线监控报告

作者: 工程师 Cheese 🧀
日期: 2026-04-06
修改记录: 从盘中监控调整为日线监控，放弃实时分钟线
"""

import os
import sys
import json
import datetime
import time
import logging
from typing import Dict, List, Any, Optional
import threading
import queue

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置路径
ARENA_DB_FILE = "database/arena/virtual_fund.json"
POSITIONS_DIR = "logs/arena"
TUSHARE_DAILY_DIR = "database"  # 日线数据目录
REPORTS_DIR = "logs/daily_line"  # 修改报告目录
CONFIG_FILE = "config/daily_line_monitor.json"

# 执行配置 - 改为每日收盘后执行
EXECUTION_TIME = "18:00"  # 每日收盘后执行
EXECUTION_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]  # 交易日

# 配置日志
os.makedirs(REPORTS_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(REPORTS_DIR, f"monitor_{datetime.date.today().isoformat()}.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DailyLineMonitor:
    """日线监控器"""
    
    def __init__(self, execution_time: str = EXECUTION_TIME):
        self.execution_time = execution_time
        self.running = False
        self.monitor_thread = None
        self.alerts_queue = queue.Queue()
        
        # 加载配置
        self.config = self._load_config()
        
        # 确保目录存在
        os.makedirs(TUSHARE_DAILY_DIR, exist_ok=True)
        
    def _load_config(self) -> Dict[str, Any]:
        """加载监控配置"""
        default_config = {
            "version": "1.1.0",
            "execution_time": self.execution_time,
            "execution_days": EXECUTION_DAYS,
            "monitored_tickers": ["518880", "510300", "510500"],  # 默认监控的ETF标的
            "alert_rules": {
                "daily_price_change_threshold": 0.05,  # 单日价格变动超过5%触发警报
                "weekly_price_change_threshold": 0.10,  # 单周价格变动超过10%
                "volume_spike_threshold": 3.0,  # 成交量放大3倍
                "stop_loss_daily": -0.05,  # 单日止损线 -5%
                "stop_loss_total": -0.15,  # 累计止损线 -15%
                "profit_target": 0.10,  # 盈利目标 +10%
                "drawdown_alert": -0.08,  # 回撤警报 -8%
            },
            "tushare_config": {
                "data_source": "fund_daily",  # 使用基金日线数据
                "use_existing_files": True,  # 优先使用已下载的日线文件
                "update_frequency": "daily",  # 每日更新
            },
            "integration": {
                "arena_engine": True,
                "stop_profit_hook": True,
                "synthesizer_signals": True,
                "orchestrator_sync": True  # 与主调度器同步
            }
        }
        
        # 尝试加载用户配置
        config_file = "config/daily_line_monitor.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                # 合并配置
                default_config.update(user_config)
                logger.info(f"已加载用户配置: {config_file}")
            except Exception as e:
                logger.error(f"加载用户配置失败，使用默认配置: {e}")
        else:
            # 如果专用配置不存在，尝试加载旧的盘中监控配置并转换
            old_config_file = "config/intra_day_monitor.json"
            if os.path.exists(old_config_file):
                try:
                    with open(old_config_file, 'r', encoding='utf-8') as f:
                        old_config = json.load(f)
                    # 转换关键配置
                    default_config["monitored_tickers"] = old_config.get("monitored_tickers", 
                                                                        default_config["monitored_tickers"])
                    logger.info(f"已转换旧版配置: {old_config_file}")
                except Exception as e:
                    logger.warning(f"转换旧配置失败: {e}")
                
        return default_config
    
    def load_arena_positions(self) -> List[Dict[str, Any]]:
        """加载演武场持仓"""
        positions = []
        
        try:
            if os.path.exists(ARENA_DB_FILE):
                with open(ARENA_DB_FILE, 'r', encoding='utf-8') as f:
                    arena_data = json.load(f)
                
                # 提取当前持仓
                if 'current_positions' in arena_data:
                    positions = arena_data['current_positions']
                    logger.info(f"加载到 {len(positions)} 个演武场持仓")
                else:
                    logger.warning("演武场数据中没有current_positions字段")
                    
            # 也检查positions目录
            if os.path.exists(POSITIONS_DIR):
                position_files = [f for f in os.listdir(POSITIONS_DIR) 
                                if f.endswith('_position_open.json')]
                
                for p_file in position_files:
                    try:
                        with open(os.path.join(POSITIONS_DIR, p_file), 'r', encoding='utf-8') as f:
                            position_data = json.load(f)
                        if position_data.get('status') == 'active':
                            positions.append(position_data)
                    except Exception as e:
                        logger.error(f"加载持仓文件 {p_file} 失败: {e}")
                        
        except Exception as e:
            logger.error(f"加载演武场持仓失败: {e}")
            
        return positions
    
    def fetch_daily_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """获取日线数据
        
        参数:
            ticker: ETF代码（如518880）
            
        返回:
            日线数据字典，包含最新价格和指标
        """
        try:
            # 确定数据文件路径
            # Tushare适配器将数据保存在 database/ 目录
            data_files = [
                f"database/tushare_{ticker}.json",  # Tushare格式
                f"database/{ticker}.json",  # 原始格式
                f"database/cleaned/tushare_{ticker}_cleaned.json",  # 清洗后数据
            ]
            
            data_file = None
            for file_path in data_files:
                if os.path.exists(file_path):
                    data_file = file_path
                    break
            
            if data_file:
                logger.debug(f"找到 {ticker} 日线数据文件: {data_file}")
                with open(data_file, 'r', encoding='utf-8') as f:
                    daily_data = json.load(f)
                
                # 提取最新数据（假设数据已按日期降序排列）
                if daily_data.get('data') and len(daily_data['data']) > 0:
                    latest_data = daily_data['data'][0]  # 最新的数据
                    
                    # 解析数据格式
                    if 'close' in latest_data:
                        close_price = latest_data.get('close')
                    elif 'nav' in latest_data:
                        close_price = latest_data.get('nav')  # 净值
                    else:
                        # 尝试其他字段
                        close_price = latest_data.get('price') or latest_data.get('value')
                    
                    # 获取日期
                    trade_date = latest_data.get('trade_date') or latest_data.get('date') or latest_data.get('timestamp')
                    
                    # 获取前一天数据用于计算变化
                    prev_data = None
                    if len(daily_data['data']) >= 2:
                        prev_data = daily_data['data'][1]
                    
                    # 计算价格变动
                    price_change_pct = None
                    price_change_abs = None
                    
                    if prev_data and close_price:
                        prev_close = prev_data.get('close') or prev_data.get('nav') or prev_data.get('price') or prev_data.get('value')
                        if prev_close and float(prev_close) > 0:
                            price_change_pct = (float(close_price) - float(prev_close)) / float(prev_close)
                            price_change_abs = float(close_price) - float(prev_close)
                    
                    result = {
                        "ticker": ticker,
                        "trade_date": trade_date,
                        "close": float(close_price) if close_price else None,
                        "open": latest_data.get('open'),
                        "high": latest_data.get('high'),
                        "low": latest_data.get('low'),
                        "volume": latest_data.get('volume') or latest_data.get('vol'),
                        "amount": latest_data.get('amount'),
                        "price_change_pct": price_change_pct,
                        "price_change_abs": price_change_abs,
                        "data_source": data_file,
                        "data_points": len(daily_data.get('data', [])),
                        "fetched_at": datetime.datetime.now().isoformat()
                    }
                    
                    logger.info(f"获取到 {ticker} 日线数据: {trade_date} 收盘价 {close_price}")
                    return result
                else:
                    logger.warning(f"{ticker} 日线数据为空")
            else:
                # 如果没有日线数据文件，尝试调用Tushare API或使用模拟数据
                logger.info(f"没有找到 {ticker} 的日线数据文件")
                return self._generate_mock_daily_data(ticker)
                
        except Exception as e:
            logger.error(f"获取 {ticker} 日线数据失败: {e}", exc_info=True)
            
        return None
    
    def _generate_mock_daily_data(self, ticker: str) -> Dict[str, Any]:
        """生成模拟日线数据（用于测试）"""
        now = datetime.datetime.now()
        base_price = 10.0 + hash(ticker) % 20  # 基于ticker生成基础价格
        
        # 添加一些随机波动
        import random
        price_change = random.uniform(-0.05, 0.05)  # -5%到+5%
        current_price = base_price * (1 + price_change)
        
        return {
            "ticker": ticker,
            "trade_date": now.strftime("%Y%m%d"),
            "close": current_price,
            "open": base_price,
            "high": base_price * 1.03,
            "low": base_price * 0.97,
            "volume": random.randint(100000, 1000000),
            "amount": current_price * random.randint(100000, 1000000),
            "price_change_pct": price_change,
            "price_change_abs": current_price - base_price,
            "data_points": 30,  # 最近30个交易日
            "fetched_at": now.isoformat(),
            "is_mock": True
        }
    
    def check_alert_rules(self, position: Dict[str, Any], daily_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检查日线警报规则
        
        参数:
            position: 持仓信息
            daily_data: 日线数据
            
        返回:
            触发的警报列表
        """
        alerts = []
        ticker = position.get('ticker', 'unknown')
        
        if not daily_data:
            return alerts
            
        # 1. 日线价格变动警报
        price_change_pct = daily_data.get('price_change_pct')
        if price_change_pct is not None:
            threshold = self.config['alert_rules']['daily_price_change_threshold']
            if abs(price_change_pct) >= threshold:
                alerts.append({
                    "type": "daily_price_change",
                    "ticker": ticker,
                    "severity": "high" if abs(price_change_pct) > threshold * 2 else "medium",
                    "value": price_change_pct,
                    "threshold": threshold,
                    "message": f"{ticker} 日价格变动 {price_change_pct:.2%}，超过阈值 {threshold:.0%}",
                    "timestamp": datetime.datetime.now().isoformat()
                })
        
        # 2. 成交量放大警报
        volume = daily_data.get('volume', 0)
        if volume > 0:
            # 简化处理：如果成交量特别大
            if volume > 500000:  # 简化阈值
                alerts.append({
                    "type": "volume_spike",
                    "ticker": ticker,
                    "severity": "medium",
                    "value": volume,
                    "message": f"{ticker} 日成交量异常: {volume:,}",
                    "timestamp": datetime.datetime.now().isoformat()
                })
        
        # 3. 检查止盈止损条件
        stop_profit_alerts = self._check_stop_profit(position, daily_data)
        alerts.extend(stop_profit_alerts)
        
        return alerts
    
    def _check_stop_profit(self, position: Dict[str, Any], daily_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检查日线止盈止损条件"""
        alerts = []
        ticker = position.get('ticker')
        
        if not ticker or not daily_data.get('close'):
            return alerts
            
        # 获取持仓成本
        cost_price = position.get('average_cost')
        if not cost_price:
            return alerts
            
        current_price = daily_data['close']
        
        # 计算盈亏比例
        pnl_pct = (current_price - cost_price) / cost_price
        
        # 检查强制止损条件
        stop_loss_total = self.config['alert_rules']['stop_loss_total']
        if pnl_pct <= stop_loss_total:  # 累计亏损超过阈值
            alerts.append({
                "type": "stop_loss_total",
                "ticker": ticker,
                "severity": "critical",
                "pnl_pct": pnl_pct,
                "threshold": stop_loss_total,
                "current_price": current_price,
                "cost_price": cost_price,
                "message": f"{ticker} 累计亏损达到 {pnl_pct:.2%}，触发强制止损 (阈值: {stop_loss_total:.0%})",
                "timestamp": datetime.datetime.now().isoformat(),
                "action_required": True
            })
        
        # 检查单日止损条件
        daily_change = daily_data.get('price_change_pct', 0)
        stop_loss_daily = self.config['alert_rules']['stop_loss_daily']
        if daily_change <= stop_loss_daily:  # 单日亏损超过阈值
            alerts.append({
                "type": "stop_loss_daily",
                "ticker": ticker,
                "severity": "high",
                "daily_change": daily_change,
                "threshold": stop_loss_daily,
                "message": f"{ticker} 单日下跌 {daily_change:.2%}，接近止损线 (阈值: {stop_loss_daily:.0%})",
                "timestamp": datetime.datetime.now().isoformat(),
                "action_suggested": True
            })
        
        # 检查盈利目标
        profit_target = self.config['alert_rules']['profit_target']
        if pnl_pct >= profit_target:  # 盈利超过目标
            alerts.append({
                "type": "profit_target",
                "ticker": ticker,
                "severity": "medium",
                "pnl_pct": pnl_pct,
                "threshold": profit_target,
                "message": f"{ticker} 盈利达到 {pnl_pct:.2%}，超过盈利目标 {profit_target:.0%}",
                "timestamp": datetime.datetime.now().isoformat(),
                "action_suggested": True
            })
        
        # 检查回撤警报
        drawdown_alert = self.config['alert_rules']['drawdown_alert']
        if daily_change <= drawdown_alert:  # 单日回撤超过阈值
            alerts.append({
                "type": "drawdown_alert",
                "ticker": ticker,
                "severity": "medium",
                "daily_change": daily_change,
                "threshold": drawdown_alert,
                "message": f"{ticker} 单日回撤 {daily_change:.2%}，超过回撤警报线",
                "timestamp": datetime.datetime.now().isoformat()
            })
            
        return alerts
    
    def process_positions(self) -> Dict[str, Any]:
        """处理所有持仓的日线监控"""
        logger.info("开始处理持仓日线监控...")
        
        # 加载持仓
        positions = self.load_arena_positions()
        if not positions:
            logger.warning("没有找到活跃持仓")
            return {"processed": 0, "alerts": [], "execution_mode": "daily_line"}
        
        all_alerts = []
        monitored_tickers = []
        daily_summary = []
        
        for position in positions:
            ticker = position.get('ticker')
            if not ticker:
                continue
                
            monitored_tickers.append(ticker)
            
            # 获取日线数据
            daily_data = self.fetch_daily_data(ticker)
            if not daily_data:
                logger.warning(f"无法获取 {ticker} 的日线数据")
                continue
                
            # 检查警报规则
            alerts = self.check_alert_rules(position, daily_data)
            all_alerts.extend(alerts)
            
            # 生成日线摘要
            summary = {
                "ticker": ticker,
                "trade_date": daily_data.get('trade_date'),
                "close": daily_data.get('close'),
                "price_change_pct": daily_data.get('price_change_pct'),
                "alerts_count": len(alerts),
                "has_critical": any(a.get('severity') == 'critical' for a in alerts),
                "data_source": daily_data.get('data_source', 'unknown')
            }
            daily_summary.append(summary)
            
            if alerts:
                logger.info(f"{ticker} 触发 {len(alerts)} 个日线警报")
        
        # 生成监控报告
        report = {
            "monitor_id": f"daily_line_{int(datetime.datetime.now().timestamp())}",
            "timestamp": datetime.datetime.now().isoformat(),
            "execution_time": self.execution_time,
            "processed_positions": len(positions),
            "monitored_tickers": monitored_tickers,
            "total_alerts": len(all_alerts),
            "critical_alerts": len([a for a in all_alerts if a.get('severity') == 'critical']),
            "alerts": all_alerts,
            "daily_summary": daily_summary,
            "execution_mode": "daily_line"
        }
        
        # 保存报告
        self._save_monitor_report(report)
        
        # 发送严重警报
        critical_alerts = [a for a in all_alerts if a.get('severity') == 'critical']
        if critical_alerts:
            self._send_critical_alerts(critical_alerts)
        
        logger.info(f"日线监控处理完成: {len(positions)} 个持仓, {len(all_alerts)} 个警报")
        return report
    
    def _save_monitor_report(self, report: Dict[str, Any]):
        """保存监控报告"""
        try:
            date_str = datetime.datetime.now().strftime("%Y%m%d")
            report_file = os.path.join(REPORTS_DIR, f"daily_line_report_{date_str}.json")
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
                
            logger.info(f"日线监控报告已保存: {report_file}")
            
            # 同时保存到公共报告目录
            public_report_dir = "reports/daily_line"
            os.makedirs(public_report_dir, exist_ok=True)
            public_report_file = os.path.join(public_report_dir, f"daily_line_report_{date_str}.json")
            with open(public_report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"保存监控报告失败: {e}")
    
    def _send_critical_alerts(self, alerts: List[Dict[str, Any]]):
        """发送严重警报"""
        for alert in alerts:
            self.alerts_queue.put(alert)
            logger.warning(f"⚠️ 严重警报: {alert.get('message')}")
            
            # TODO: 集成实际的通知系统（如邮件、短信、钉钉等）
            # 目前先记录到文件
            alert_file = os.path.join(REPORTS_DIR, f"critical_alert_{int(time.time())}.json")
            try:
                with open(alert_file, 'w', encoding='utf-8') as f:
                    json.dump(alert, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"保存严重警报失败: {e}")
    
    def is_trading_day(self) -> bool:
        """检查是否为交易日"""
        now = datetime.datetime.now()
        weekday_name = now.strftime("%A")  # Monday, Tuesday, etc.
        
        return weekday_name in self.config['execution_days']
    
    def should_execute_now(self) -> bool:
        """检查是否应该现在执行"""
        now = datetime.datetime.now()
        
        # 检查是否为交易日
        if not self.is_trading_day():
            logger.debug(f"今天不是交易日: {now.strftime('%A')}")
            return False
            
        # 检查是否达到执行时间
        current_time_str = now.strftime("%H:%M")
        target_time = self.config['execution_time']
        
        # 简单的时间匹配（精确到分钟）
        return current_time_str == target_time
    
    def monitor_loop(self):
        """监控循环 - 改为每日检查执行时间"""
        logger.info(f"日线监控启动，执行时间: {self.execution_time}")
        
        last_execution_day = None
        
        while self.running:
            try:
                current_time = datetime.datetime.now()
                
                # 检查是否应该执行
                if self.should_execute_now():
                    # 避免同一天重复执行
                    today = current_time.strftime("%Y%m%d")
                    if last_execution_day != today:
                        logger.info(f"到达执行时间 {self.execution_time}，开始日线监控检查")
                        
                        # 执行监控
                        report = self.process_positions()
                        
                        # 记录执行情况
                        last_execution_day = today
                        logger.info(f"日线监控检查完成，发现 {report['total_alerts']} 个警报")
                    else:
                        logger.debug(f"今天已经执行过日线监控，跳过")
                else:
                    # 每分钟检查一次
                    pass
                
                # 每分钟检查一次
                time.sleep(60)
                    
            except Exception as e:
                logger.error(f"监控循环出错: {e}", exc_info=True)
                time.sleep(60)  # 出错后等待1分钟
    
    def start(self):
        """启动监控"""
        if self.running:
            logger.warning("监控已经在运行中")
            return False
            
        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("日线监控已启动（每日模式）")
        return True
    
    def stop(self):
        """停止监控"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=30)
            
        logger.info("日线监控已停止")
    
    def run_once(self):
        """单次运行（用于测试）"""
        logger.info("执行单次日线监控检查")
        return self.process_positions()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='琥珀引擎日线监控模块')
    parser.add_argument('--time', type=str, default=EXECUTION_TIME, 
                       help=f'执行时间（HH:MM），默认: {EXECUTION_TIME}')
    parser.add_argument('--once', action='store_true', help='单次运行，不进入循环')
    parser.add_argument('--daemon', action='store_true', help='以守护进程方式运行')
    parser.add_argument('--test', action='store_true', help='测试模式，使用模拟数据')
    
    args = parser.parse_args()
    
    # 创建监控器
    monitor = DailyLineMonitor(execution_time=args.time)
    
    if args.once:
        # 单次运行
        report = monitor.run_once()
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    elif args.daemon:
        # 守护进程模式
        monitor.start()
        
        try:
            # 保持进程运行
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            monitor.stop()
            print("日线监控已停止")
            return 0
    else:
        # 交互模式
        print(f"日线监控模块 - 执行时间: {args.time}")
        print("可用命令: start, stop, run, status, exit")
        
        monitor.start()
        
        try:
            while True:
                cmd = input("> ").strip().lower()
                
                if cmd == "start":
                    monitor.start()
                elif cmd == "stop":
                    monitor.stop()
                elif cmd == "run":
                    report = monitor.run_once()
                    print(f"执行完成: {report['processed_positions']} 持仓, {report['total_alerts']} 警报")
                elif cmd == "status":
                    print(f"运行状态: {'运行中' if monitor.running else '停止'}")
                elif cmd in ["exit", "quit"]:
                    monitor.stop()
                    break
                else:
                    print("未知命令")
                    
        except KeyboardInterrupt:
            monitor.stop()
            print("日线监控已停止")
            return 0


if __name__ == "__main__":
    sys.exit(main())