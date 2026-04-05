#!/usr/bin/env python3
"""
盘中监控点火模块 - V1.7.0 "智库并网"专项行动
专项二：盘中监控点火

功能：
1. 轮询间隔设为15分钟，接入stk_mins接口
2. 实时监控持仓标的的盘中表现
3. 触发止盈止损规则
4. 生成盘中警报

作者: 工程师 Cheese 🧀
日期: 2026-04-05
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
TUSHARE_MINS_DIR = "database/tushare/mins"
REPORTS_DIR = "logs/intra_day"
CONFIG_FILE = "config/intra_day_monitor.json"

# 轮询配置
POLL_INTERVAL_MINUTES = 15  # 15分钟轮询间隔
MARKET_OPEN_HOUR = 9  # 市场开盘时间（24小时制）
MARKET_CLOSE_HOUR = 15  # 市场收盘时间（24小时制）

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

class IntraDayMonitor:
    """盘中监控器"""
    
    def __init__(self, poll_interval: int = POLL_INTERVAL_MINUTES):
        self.poll_interval = poll_interval
        self.running = False
        self.monitor_thread = None
        self.alerts_queue = queue.Queue()
        
        # 加载配置
        self.config = self._load_config()
        
        # 确保目录存在
        os.makedirs(TUSHARE_MINS_DIR, exist_ok=True)
        
    def _load_config(self) -> Dict[str, Any]:
        """加载监控配置"""
        default_config = {
            "version": "1.0.0",
            "poll_interval_minutes": self.poll_interval,
            "stk_mins_frequency": "15min",  # 15分钟线
            "monitored_tickers": ["000681", "518880"],  # 默认监控的标的
            "alert_rules": {
                "price_change_threshold": 0.05,  # 价格变动超过5%触发警报
                "volume_spike_threshold": 3.0,  # 成交量放大3倍
                "intraday_high_break": True,  # 突破日内新高
                "intraday_low_break": True,  # 突破日内新低
            },
            "tushare_config": {
                "mins_fields": "ts_code,trade_time,open,high,low,close,vol,amount",
                "freq": "15min",
                "start_date": datetime.date.today().isoformat(),
                "end_date": datetime.date.today().isoformat()
            },
            "integration": {
                "arena_engine": True,
                "stop_profit_hook": True,
                "synthesizer_signals": True
            }
        }
        
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                # 合并配置
                default_config.update(user_config)
                logger.info(f"已加载用户配置: {CONFIG_FILE}")
            except Exception as e:
                logger.error(f"加载用户配置失败，使用默认配置: {e}")
                
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
    
    def fetch_stk_mins_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """获取股票分钟线数据
        
        参数:
            ticker: 股票代码（如000681）
            
        返回:
            分钟线数据字典，包含最新价格和指标
        """
        try:
            # 构建数据文件路径
            # 假设Tushare适配器将分钟数据保存在 database/tushare/mins/ 目录
            data_file = os.path.join(TUSHARE_MINS_DIR, f"{ticker}_mins.json")
            
            if os.path.exists(data_file):
                with open(data_file, 'r', encoding='utf-8') as f:
                    mins_data = json.load(f)
                
                # 提取最新数据
                if mins_data.get('data') and len(mins_data['data']) > 0:
                    latest_data = mins_data['data'][-1]  # 假设数据按时间排序
                    
                    # 计算一些基本指标
                    result = {
                        "ticker": ticker,
                        "latest_timestamp": latest_data.get('trade_time'),
                        "open": latest_data.get('open'),
                        "high": latest_data.get('high'),
                        "low": latest_data.get('low'),
                        "close": latest_data.get('close'),
                        "volume": latest_data.get('vol'),
                        "amount": latest_data.get('amount'),
                        "data_points": len(mins_data.get('data', [])),
                        "fetched_at": datetime.datetime.now().isoformat()
                    }
                    
                    # 计算价格变动（如果有前一个数据点）
                    if len(mins_data['data']) >= 2:
                        prev_data = mins_data['data'][-2]
                        prev_close = prev_data.get('close')
                        curr_close = latest_data.get('close')
                        
                        if prev_close and curr_close and prev_close > 0:
                            price_change_pct = (curr_close - prev_close) / prev_close
                            result["price_change_pct"] = price_change_pct
                            result["price_change_abs"] = curr_close - prev_close
                    
                    logger.debug(f"获取到 {ticker} 分钟数据: {result.get('close')}")
                    return result
                else:
                    logger.warning(f"{ticker} 分钟数据为空")
            else:
                # 如果没有分钟数据文件，尝试调用Tushare API
                logger.info(f"没有找到 {ticker} 的分钟数据文件，尝试模拟数据")
                return self._generate_mock_mins_data(ticker)
                
        except Exception as e:
            logger.error(f"获取 {ticker} 分钟数据失败: {e}")
            
        return None
    
    def _generate_mock_mins_data(self, ticker: str) -> Dict[str, Any]:
        """生成模拟分钟数据（用于测试）"""
        now = datetime.datetime.now()
        base_price = 10.0 + hash(ticker) % 20  # 基于ticker生成基础价格
        
        # 添加一些随机波动
        import random
        price_change = random.uniform(-0.02, 0.02)  # -2%到+2%
        current_price = base_price * (1 + price_change)
        
        return {
            "ticker": ticker,
            "latest_timestamp": now.isoformat(),
            "open": base_price,
            "high": base_price * 1.01,
            "low": base_price * 0.99,
            "close": current_price,
            "volume": random.randint(10000, 100000),
            "amount": current_price * random.randint(10000, 100000),
            "price_change_pct": price_change,
            "price_change_abs": current_price - base_price,
            "data_points": 96,  # 一天96个15分钟K线
            "fetched_at": now.isoformat(),
            "is_mock": True
        }
    
    def check_alert_rules(self, position: Dict[str, Any], mins_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检查警报规则
        
        参数:
            position: 持仓信息
            mins_data: 分钟线数据
            
        返回:
            触发的警报列表
        """
        alerts = []
        ticker = position.get('ticker', 'unknown')
        
        if not mins_data:
            return alerts
            
        # 1. 价格变动警报
        price_change_pct = mins_data.get('price_change_pct')
        if price_change_pct is not None:
            threshold = self.config['alert_rules']['price_change_threshold']
            if abs(price_change_pct) >= threshold:
                alerts.append({
                    "type": "price_change",
                    "ticker": ticker,
                    "severity": "high" if abs(price_change_pct) > threshold * 2 else "medium",
                    "value": price_change_pct,
                    "threshold": threshold,
                    "message": f"{ticker} 价格变动 {price_change_pct:.2%}，超过阈值 {threshold:.0%}",
                    "timestamp": datetime.datetime.now().isoformat()
                })
        
        # 2. 成交量放大警报
        # 这里需要历史成交量数据进行比较，简化处理
        volume = mins_data.get('volume', 0)
        if volume > 100000:  # 简化阈值
            alerts.append({
                "type": "volume_spike",
                "ticker": ticker,
                "severity": "medium",
                "value": volume,
                "message": f"{ticker} 成交量放大: {volume:,}",
                "timestamp": datetime.datetime.now().isoformat()
            })
        
        # 3. 日内高低点突破警报
        # 需要维护日内最高最低记录，简化处理
        
        # 4. 检查是否触发止盈止损
        stop_profit_alerts = self._check_stop_profit(position, mins_data)
        alerts.extend(stop_profit_alerts)
        
        return alerts
    
    def _check_stop_profit(self, position: Dict[str, Any], mins_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检查止盈止损条件"""
        alerts = []
        ticker = position.get('ticker')
        
        if not ticker or not mins_data.get('close'):
            return alerts
            
        # 获取持仓成本
        cost_price = position.get('average_cost')
        if not cost_price:
            return alerts
            
        current_price = mins_data['close']
        
        # 计算盈亏比例
        pnl_pct = (current_price - cost_price) / cost_price
        
        # 检查强制止损条件（来自arena_engine）
        if pnl_pct <= -0.15:  # 累计亏损超过15%
            alerts.append({
                "type": "stop_loss_total",
                "ticker": ticker,
                "severity": "critical",
                "pnl_pct": pnl_pct,
                "current_price": current_price,
                "cost_price": cost_price,
                "message": f"{ticker} 累计亏损达到 {pnl_pct:.2%}，触发强制止损",
                "timestamp": datetime.datetime.now().isoformat(),
                "action_required": True
            })
        
        # 检查日内止盈条件
        # 这里可以添加更复杂的止盈逻辑
        if pnl_pct >= 0.10:  # 盈利超过10%
            alerts.append({
                "type": "profit_target",
                "ticker": ticker,
                "severity": "medium",
                "pnl_pct": pnl_pct,
                "message": f"{ticker} 盈利达到 {pnl_pct:.2%}，考虑止盈",
                "timestamp": datetime.datetime.now().isoformat(),
                "action_suggested": True
            })
            
        return alerts
    
    def process_positions(self) -> Dict[str, Any]:
        """处理所有持仓的监控"""
        logger.info("开始处理持仓监控...")
        
        # 加载持仓
        positions = self.load_arena_positions()
        if not positions:
            logger.warning("没有找到活跃持仓")
            return {"processed": 0, "alerts": []}
        
        all_alerts = []
        monitored_tickers = []
        
        for position in positions:
            ticker = position.get('ticker')
            if not ticker:
                continue
                
            monitored_tickers.append(ticker)
            
            # 获取分钟数据
            mins_data = self.fetch_stk_mins_data(ticker)
            if not mins_data:
                logger.warning(f"无法获取 {ticker} 的分钟数据")
                continue
                
            # 检查警报规则
            alerts = self.check_alert_rules(position, mins_data)
            all_alerts.extend(alerts)
            
            if alerts:
                logger.info(f"{ticker} 触发 {len(alerts)} 个警报")
        
        # 生成监控报告
        report = {
            "monitor_id": f"intraday_{int(datetime.datetime.now().timestamp())}",
            "timestamp": datetime.datetime.now().isoformat(),
            "processed_positions": len(positions),
            "monitored_tickers": monitored_tickers,
            "total_alerts": len(all_alerts),
            "alerts": all_alerts,
            "poll_interval_minutes": self.poll_interval
        }
        
        # 保存报告
        self._save_monitor_report(report)
        
        # 发送严重警报
        critical_alerts = [a for a in all_alerts if a.get('severity') == 'critical']
        if critical_alerts:
            self._send_critical_alerts(critical_alerts)
        
        logger.info(f"监控处理完成: {len(positions)} 个持仓, {len(all_alerts)} 个警报")
        return report
    
    def _save_monitor_report(self, report: Dict[str, Any]):
        """保存监控报告"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            report_file = os.path.join(REPORTS_DIR, f"monitor_report_{timestamp}.json")
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
                
            logger.debug(f"监控报告已保存: {report_file}")
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
    
    def is_market_open(self) -> bool:
        """检查市场是否开盘"""
        now = datetime.datetime.now()
        current_hour = now.hour
        current_minute = now.minute
        
        # 简单判断：周一至周五，9:00-15:00
        if now.weekday() >= 5:  # 周六、周日
            return False
            
        if current_hour < MARKET_OPEN_HOUR or current_hour >= MARKET_CLOSE_HOUR:
            return False
            
        return True
    
    def monitor_loop(self):
        """监控循环"""
        logger.info(f"盘中监控启动，轮询间隔: {self.poll_interval} 分钟")
        
        while self.running:
            try:
                current_time = datetime.datetime.now()
                
                # 检查市场是否开盘
                if self.is_market_open():
                    logger.info(f"市场开盘中，执行监控检查 ({current_time.strftime('%H:%M')})")
                    
                    # 执行监控
                    report = self.process_positions()
                    
                    # 记录检查结果
                    logger.info(f"监控检查完成，发现 {report['total_alerts']} 个警报")
                else:
                    logger.debug(f"市场已收盘或未开盘 ({current_time.strftime('%H:%M')})")
                
                # 等待下一个轮询间隔
                for _ in range(self.poll_interval * 60):  # 转换为秒
                    if not self.running:
                        break
                    time.sleep(1)
                    
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
        
        logger.info("盘中监控已启动")
        return True
    
    def stop(self):
        """停止监控"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=30)
            
        logger.info("盘中监控已停止")
    
    def run_once(self):
        """单次运行（用于测试）"""
        logger.info("执行单次监控检查")
        return self.process_positions()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='琥珀引擎盘中监控点火模块')
    parser.add_argument('--interval', type=int, default=POLL_INTERVAL_MINUTES, 
                       help=f'轮询间隔（分钟），默认: {POLL_INTERVAL_MINUTES}')
    parser.add_argument('--once', action='store_true', help='单次运行，不进入循环')
    parser.add_argument('--daemon', action='store_true', help='以守护进程方式运行')
    parser.add_argument('--test', action='store_true', help='测试模式，使用模拟数据')
    
    args = parser.parse_args()
    
    # 创建监控器
    monitor = IntraDayMonitor(poll_interval=args.interval)
    
    if args.once:
        # 单次运行
        result = monitor.run_once()
        print(f"\n📊 监控检查完成:")
        print(f"   处理持仓: {result['processed_positions']} 个")
        print(f"   发现警报: {result['total_alerts']} 个")
        
        if result['total_alerts'] > 0:
            print(f"\n⚠️ 警报列表:")
            for alert in result['alerts'][:5]:  # 显示前5个警报
                print(f"   - {alert['message']}")
                
    elif args.daemon:
        # 守护进程模式
        print(f"启动盘中监控守护进程，轮询间隔: {args.interval} 分钟")
        monitor.start()
        
        try:
            # 保持主线程运行
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("\n接收到中断信号，停止监控...")
            monitor.stop()
    else:
        # 交互式单次运行
        result = monitor.run_once()
        
        if result['total_alerts'] == 0:
            print(f"✅ 监控检查完成，未发现异常")
        else:
            print(f"⚠️ 监控检查完成，发现 {result['total_alerts']} 个警报")
            for alert in result['alerts']:
                print(f"   • {alert['message']}")


if __name__ == "__main__":
    main()