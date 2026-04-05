#!/usr/bin/env python3
"""
V1.7.0 "智库并网"专项行动调度器
统一调度三个专项任务执行

专项一：每日简报看板 (18:00)
专项二：盘中监控点火 (15分钟轮询)
专项三：算法骨架重构 (每周一次)

作者: 工程师 Cheese 🧀
日期: 2026-04-05
"""

import os
import sys
import json
import datetime
import time
import threading
import logging
import subprocess
import schedule
from typing import Dict, List, Any, Optional
import signal

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置路径
LOG_DIR = "logs/v170_orchestrator"
CONFIG_FILE = "config/v170_orchestrator.json"
STATUS_FILE = "logs/v170_orchestrator/status.json"

# 配置日志
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, f"orchestrator_{datetime.date.today().isoformat()}.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class V170Orchestrator:
    """V1.7.0 专项行动调度器"""
    
    def __init__(self):
        self.running = False
        self.scheduler_thread = None
        self.config = self._load_config()
        self.task_status = {}
        
        # 确保状态目录存在
        os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
        
        # 设置信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _load_config(self) -> Dict[str, Any]:
        """加载调度器配置"""
        default_config = {
            "version": "1.0.0",
            "name": "V1.7.0 '智库并网'专项行动调度器",
            "mission_control": {
                "专项一": {
                    "name": "每日简报看板",
                    "script": "scripts/briefing/daily_briefing.py",
                    "schedule": "18:00",
                    "enabled": True,
                    "args": ["--mock-llm"],  # 测试期间使用模拟LLM
                    "timeout": 600,  # 10分钟超时
                    "retry_attempts": 3
                },
                "专项二": {
                    "name": "盘中监控点火",
                    "script": "scripts/arena/intra_day_monitor.py",
                    "schedule": "15min",  # 15分钟轮询
                    "enabled": True,
                    "args": ["--daemon"],
                    "timeout": 300,
                    "market_hours_only": True,
                    "start_delay": 30  # 启动后30秒开始
                },
                "专项三": {
                    "name": "算法骨架重构",
                    "script": "scripts/synthesizer/ir_optimizer.py",
                    "schedule": "weekly",  # 每周一运行
                    "enabled": True,
                    "args": ["--lookback", "90", "--method", "ir_weighted"],
                    "timeout": 1800,  # 30分钟超时
                    "day_of_week": "monday",
                    "time_of_day": "02:00"
                }
            },
            "monitoring": {
                "health_check_interval": 300,  # 5分钟健康检查
                "status_update_interval": 60,  # 每分钟更新状态
                "alert_on_failure": True,
                "max_consecutive_failures": 3
            },
            "integration": {
                "existing_orchestrator": True,
                "notify_on_completion": True,
                "generate_reports": True,
                "log_to_central": True
            },
            "metadata": {
                "created_date": "2026-04-05",
                "created_by": "工程师 Cheese 🧀",
                "mission": "V1.7.0 '智库并网'专项行动",
                "last_updated": datetime.datetime.now().isoformat()
            }
        }
        
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                # 深度合并配置
                self._deep_update(default_config, user_config)
                logger.info(f"已加载用户配置: {CONFIG_FILE}")
            except Exception as e:
                logger.error(f"加载用户配置失败，使用默认配置: {e}")
                
        return default_config
    
    def _deep_update(self, target: Dict, source: Dict):
        """深度更新字典"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
    
    def _signal_handler(self, signum, frame):
        """信号处理函数"""
        logger.info(f"接收到信号 {signum}，正在停止调度器...")
        self.stop()
    
    def load_task_status(self):
        """加载任务状态"""
        try:
            if os.path.exists(STATUS_FILE):
                with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                    self.task_status = json.load(f)
            else:
                self.task_status = {}
        except Exception as e:
            logger.error(f"加载任务状态失败: {e}")
            self.task_status = {}
    
    def save_task_status(self):
        """保存任务状态"""
        try:
            with open(STATUS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.task_status, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存任务状态失败: {e}")
    
    def update_task_status(self, mission_id: str, status: str, 
                          details: Optional[Dict[str, Any]] = None):
        """更新任务状态"""
        if mission_id not in self.task_status:
            self.task_status[mission_id] = {}
        
        self.task_status[mission_id].update({
            "last_update": datetime.datetime.now().isoformat(),
            "status": status,
            "details": details or {}
        })
        
        self.save_task_status()
        logger.info(f"任务 {mission_id} 状态更新: {status}")
    
    def is_market_open(self) -> bool:
        """检查市场是否开盘"""
        now = datetime.datetime.now()
        current_hour = now.hour
        current_minute = now.minute
        
        # 简单判断：周一至周五，9:00-15:00
        if now.weekday() >= 5:  # 周六、周日
            return False
            
        market_open_hour = 9
        market_close_hour = 15
        
        if current_hour < market_open_hour or current_hour >= market_close_hour:
            return False
            
        return True
    
    def run_mission_one(self):
        """执行专项一：每日简报看板"""
        mission_id = "专项一"
        mission_config = self.config['mission_control'][mission_id]
        
        if not mission_config['enabled']:
            logger.info(f"{mission_id} 已禁用，跳过执行")
            return
        
        logger.info(f"开始执行 {mission_id}: {mission_config['name']}")
        
        try:
            # 构建命令
            script_path = mission_config['script']
            args = mission_config.get('args', [])
            
            cmd = [sys.executable, script_path] + args
            
            # 执行命令
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=mission_config.get('timeout', 600)
            )
            end_time = time.time()
            
            # 记录结果
            execution_details = {
                "start_time": datetime.datetime.fromtimestamp(start_time).isoformat(),
                "end_time": datetime.datetime.fromtimestamp(end_time).isoformat(),
                "duration_seconds": end_time - start_time,
                "return_code": result.returncode,
                "stdout": result.stdout[-1000:],  # 只保留最后1000字符
                "stderr": result.stderr[-500:] if result.stderr else ""
            }
            
            if result.returncode == 0:
                status = "success"
                logger.info(f"{mission_id} 执行成功，耗时: {execution_details['duration_seconds']:.2f}秒")
            else:
                status = "failed"
                logger.error(f"{mission_id} 执行失败，返回码: {result.returncode}")
                logger.error(f"错误输出: {result.stderr}")
            
            self.update_task_status(mission_id, status, execution_details)
            
            # 如果有重试机制
            if status == "failed" and mission_config.get('retry_attempts', 0) > 0:
                self._retry_mission(mission_id, mission_config)
                
        except subprocess.TimeoutExpired:
            logger.error(f"{mission_id} 执行超时")
            self.update_task_status(mission_id, "timeout", {
                "error": "执行超时",
                "timeout_seconds": mission_config.get('timeout', 600)
            })
        except Exception as e:
            logger.error(f"{mission_id} 执行异常: {e}")
            self.update_task_status(mission_id, "error", {
                "error": str(e)
            })
    
    def run_mission_two(self):
        """执行专项二：盘中监控点火"""
        mission_id = "专项二"
        mission_config = self.config['mission_control'][mission_id]
        
        if not mission_config['enabled']:
            logger.info(f"{mission_id} 已禁用，跳过执行")
            return
        
        # 检查是否只在交易时间运行
        if mission_config.get('market_hours_only', True) and not self.is_market_open():
            logger.debug(f"{mission_id}: 非交易时间，跳过执行")
            return
        
        logger.info(f"开始执行 {mission_id}: {mission_config['name']}")
        
        try:
            # 专项二以守护进程方式运行，这里只是触发单次检查
            script_path = mission_config['script']
            
            # 移除--daemon参数，改为单次运行
            args = [arg for arg in mission_config.get('args', []) if arg != '--daemon']
            args.append('--once')  # 单次运行
            
            cmd = [sys.executable, script_path] + args
            
            # 执行命令
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=mission_config.get('timeout', 300)
            )
            end_time = time.time()
            
            # 记录结果
            execution_details = {
                "start_time": datetime.datetime.fromtimestamp(start_time).isoformat(),
                "end_time": datetime.datetime.fromtimestamp(end_time).isoformat(),
                "duration_seconds": end_time - start_time,
                "return_code": result.returncode,
                "stdout": result.stdout[-1000:] if result.stdout else "",
                "stderr": result.stderr[-500:] if result.stderr else "",
                "market_open": self.is_market_open()
            }
            
            if result.returncode == 0:
                status = "success"
                # 解析输出，提取警报数量
                try:
                    output = result.stdout
                    if "发现警报" in output:
                        # 尝试提取警报数量
                        import re
                        match = re.search(r'发现警报[:：]\s*(\d+)', output)
                        if match:
                            execution_details['alerts_found'] = int(match.group(1))
                except:
                    pass
                    
                logger.info(f"{mission_id} 执行成功，耗时: {execution_details['duration_seconds']:.2f}秒")
            else:
                status = "failed"
                logger.error(f"{mission_id} 执行失败，返回码: {result.returncode}")
            
            self.update_task_status(mission_id, status, execution_details)
            
        except subprocess.TimeoutExpired:
            logger.error(f"{mission_id} 执行超时")
            self.update_task_status(mission_id, "timeout", {
                "error": "执行超时",
                "timeout_seconds": mission_config.get('timeout', 300)
            })
        except Exception as e:
            logger.error(f"{mission_id} 执行异常: {e}")
            self.update_task_status(mission_id, "error", {
                "error": str(e)
            })
    
    def run_mission_three(self):
        """执行专项三：算法骨架重构"""
        mission_id = "专项三"
        mission_config = self.config['mission_control'][mission_id]
        
        if not mission_config['enabled']:
            logger.info(f"{mission_id} 已禁用，跳过执行")
            return
        
        # 检查是否在指定的星期几运行
        day_of_week = mission_config.get('day_of_week', 'monday').lower()
        today_weekday = datetime.datetime.now().strftime('%A').lower()
        
        if day_of_week != today_weekday:
            logger.debug(f"{mission_id}: 今天不是{day_of_week}，跳过执行")
            return
        
        logger.info(f"开始执行 {mission_id}: {mission_config['name']}")
        
        try:
            # 构建命令
            script_path = mission_config['script']
            args = mission_config.get('args', [])
            
            cmd = [sys.executable, script_path] + args
            
            # 执行命令
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=mission_config.get('timeout', 1800)
            )
            end_time = time.time()
            
            # 记录结果
            execution_details = {
                "start_time": datetime.datetime.fromtimestamp(start_time).isoformat(),
                "end_time": datetime.datetime.fromtimestamp(end_time).isoformat(),
                "duration_seconds": end_time - start_time,
                "return_code": result.returncode,
                "stdout": result.stdout[-2000:] if result.stdout else "",
                "stderr": result.stderr[-1000:] if result.stderr else ""
            }
            
            if result.returncode == 0:
                status = "success"
                # 尝试解析输出，提取关键指标
                try:
                    output = result.stdout
                    if "预期组合IR" in output:
                        import re
                        match = re.search(r'预期组合IR[:：]\s*([\d.]+)', output)
                        if match:
                            execution_details['expected_portfolio_ir'] = float(match.group(1))
                except:
                    pass
                    
                logger.info(f"{mission_id} 执行成功，耗时: {execution_details['duration_seconds']:.2f}秒")
            else:
                status = "failed"
                logger.error(f"{mission_id} 执行失败，返回码: {result.returncode}")
                logger.error(f"错误输出: {result.stderr}")
            
            self.update_task_status(mission_id, status, execution_details)
            
        except subprocess.TimeoutExpired:
            logger.error(f"{mission_id} 执行超时")
            self.update_task_status(mission_id, "timeout", {
                "error": "执行超时",
                "timeout_seconds": mission_config.get('timeout', 1800)
            })
        except Exception as e:
            logger.error(f"{mission_id} 执行异常: {e}")
            self.update_task_status(mission_id, "error", {
                "error": str(e)
            })
    
    def _retry_mission(self, mission_id: str, mission_config: Dict[str, Any]):
        """重试任务"""
        retry_attempts = mission_config.get('retry_attempts', 0)
        current_attempt = self.task_status.get(mission_id, {}).get('retry_count', 0)
        
        if current_attempt < retry_attempts:
            current_attempt += 1
            logger.info(f"{mission_id} 第 {current_attempt} 次重试")
            
            # 更新重试计数
            if mission_id not in self.task_status:
                self.task_status[mission_id] = {}
            self.task_status[mission_id]['retry_count'] = current_attempt
            self.save_task_status()
            
            # 等待后重试
            time.sleep(60)  # 等待1分钟
            
            # 重新执行任务
            if mission_id == "专项一":
                self.run_mission_one()
            elif mission_id == "专项二":
                self.run_mission_two()
            elif mission_id == "专项三":
                self.run_mission_three()
    
    def setup_schedule(self):
        """设置定时任务"""
        mission_config = self.config['mission_control']
        
        # 专项一：每日18:00
        if mission_config['专项一']['enabled']:
            schedule_time = mission_config['专项一'].get('schedule', '18:00')
            schedule.every().day.at(schedule_time).do(self.run_mission_one)
            logger.info(f"专项一 定时任务设置: 每天 {schedule_time}")
        
        # 专项二：每15分钟（或自定义间隔）
        if mission_config['专项二']['enabled']:
            schedule_interval = mission_config['专项二'].get('schedule', '15min')
            
            if schedule_interval.endswith('min'):
                minutes = int(schedule_interval[:-3])
                schedule.every(minutes).minutes.do(self.run_mission_two)
                logger.info(f"专项二 定时任务设置: 每 {minutes} 分钟")
            else:
                # 默认15分钟
                schedule.every(15).minutes.do(self.run_mission_two)
                logger.info(f"专项二 定时任务设置: 每 15 分钟")
        
        # 专项三：每周一02:00
        if mission_config['专项三']['enabled']:
            day_of_week = mission_config['专项三'].get('day_of_week', 'monday')
            time_of_day = mission_config['专项三'].get('time_of_day', '02:00')
            
            # 映射星期几
            day_map = {
                'monday': schedule.every().monday,
                'tuesday': schedule.every().tuesday,
                'wednesday': schedule.every().wednesday,
                'thursday': schedule.every().thursday,
                'friday': schedule.every().friday,
                'saturday': schedule.every().saturday,
                'sunday': schedule.every().sunday
            }
            
            if day_of_week.lower() in day_map:
                day_map[day_of_week.lower()].at(time_of_day).do(self.run_mission_three)
                logger.info(f"专项三 定时任务设置: 每周{day_of_week} {time_of_day}")
            else:
                # 默认周一
                schedule.every().monday.at(time_of_day).do(self.run_mission_three)
                logger.info(f"专项三 定时任务设置: 每周一 {time_of_day}")
        
        # 健康检查
        health_check_interval = self.config['monitoring']['health_check_interval']
        schedule.every(health_check_interval).seconds.do(self.health_check)
        logger.info(f"健康检查定时任务: 每 {health_check_interval} 秒")
    
    def health_check(self):
        """健康检查"""
        logger.debug("执行健康检查")
        
        # 检查任务状态
        for mission_id in self.config['mission_control']:
            if mission_id in self.task_status:
                status = self.task_status[mission_id].get('status')
                last_update = self.task_status[mission_id].get('last_update')
                
                if status == 'failed' and last_update:
                    # 检查失败是否超过一定时间
                    try:
                        last_update_time = datetime.datetime.fromisoformat(last_update)
                        time_since_failure = (datetime.datetime.now() - last_update_time).total_seconds()
                        
                        # 如果失败超过1小时，记录警告
                        if time_since_failure > 3600:
                            logger.warning(f"{mission_id} 已失败超过1小时")
                    except:
                        pass
        
        # 保存健康检查记录
        health_status = {
            "timestamp": datetime.datetime.now().isoformat(),
            "running": self.running,
            "active_missions": len([m for m in self.config['mission_control'].values() if m['enabled']]),
            "task_status_summary": {
                mission_id: self.task_status.get(mission_id, {}).get('status', 'unknown')
                for mission_id in self.config['mission_control']
            }
        }
        
        try:
            health_file = os.path.join(LOG_DIR, "health_check.json")
            health_history = []
            
            if os.path.exists(health_file):
                with open(health_file, 'r', encoding='utf-8') as f:
                    try:
                        health_history = json.load(f)
                        if not isinstance(health_history, list):
                            health_history = []
                    except:
                        health_history = []
            
            health_history.append(health_status)
            
            # 只保留最近100条记录
            with open(health_file, 'w', encoding='utf-8') as f:
                json.dump(health_history[-100:], f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"保存健康检查记录失败: {e}")
    
    def scheduler_loop(self):
        """调度器循环"""
        logger.info("调度器循环启动")
        
        # 设置定时任务
        self.setup_schedule()
        
        # 专项二启动延迟
        mission_two_config = self.config['mission_control']['专项二']
        if mission_two_config['enabled']:
            start_delay = mission_two_config.get('start_delay', 30)
            logger.info(f"专项二将在 {start_delay} 秒后开始执行")
            time.sleep(start_delay)
            self.run_mission_two()  # 立即执行一次
        
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                logger.error(f"调度器循环出错: {e}", exc_info=True)
                time.sleep(10)
        
        logger.info("调度器循环结束")
    
    def start(self):
        """启动调度器"""
        if self.running:
            logger.warning("调度器已经在运行中")
            return False
        
        logger.info("=" * 60)
        logger.info("V1.7.0 '智库并网'专项行动调度器启动")
        logger.info("=" * 60)
        
        # 加载任务状态
        self.load_task_status()
        
        # 启动调度器线程
        self.running = True
        self.scheduler_thread = threading.Thread(target=self.scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("调度器已启动")
        return True
    
    def stop(self):
        """停止调度器"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=30)
        
        logger.info("调度器已停止")
    
    def run_once(self):
        """单次运行所有任务（测试用）"""
        logger.info("执行单次运行所有任务")
        
        # 加载任务状态
        self.load_task_status()
        
        # 执行所有任务
        self.run_mission_one()
        self.run_mission_two()
        self.run_mission_three()
        
        # 生成执行报告
        self._generate_execution_report()
    
    def _generate_execution_report(self):
        """生成执行报告"""
        try:
            report = {
                "report_id": f"v170_execution_{int(datetime.datetime.now().timestamp())}",
                "generation_date": datetime.date.today().isoformat(),
                "generation_time": datetime.datetime.now().isoformat(),
                "mission_summary": {},
                "overall_status": "unknown",
                "metadata": {
                    "version": "1.0.0",
                    "author": "工程师 Cheese 🧀",
                    "mission": "V1.7.0 '智库并网'专项行动",
                    "report_type": "single_execution"
                }
            }
            
            # 汇总任务状态
            success_count = 0
            total_count = 0
            
            for mission_id in self.config['mission_control']:
                if mission_id in self.task_status:
                    status = self.task_status[mission_id].get('status', 'unknown')
                    report['mission_summary'][mission_id] = {
                        "status": status,
                        "last_update": self.task_status[mission_id].get('last_update'),
                        "details": self.task_status[mission_id].get('details', {})
                    }
                    
                    if status == 'success':
                        success_count += 1
                    total_count += 1
            
            # 确定总体状态
            if total_count == 0:
                report['overall_status'] = 'no_tasks'
            elif success_count == total_count:
                report['overall_status'] = 'all_success'
            elif success_count == 0:
                report['overall_status'] = 'all_failed'
            else:
                report['overall_status'] = 'partial_success'
            
            report['success_count'] = success_count
            report['total_count'] = total_count
            
            # 保存报告
            report_dir = "reports/v170_execution"
            os.makedirs(report_dir, exist_ok=True)
            
            report_file = os.path.join(report_dir, f"execution_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.json")
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"执行报告已保存: {report_file}")
            
            return report
            
        except Exception as e:
            logger.error(f"生成执行报告失败: {e}")
            return None


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='V1.7.0 "智库并网"专项行动调度器')
    parser.add_argument('--once', action='store_true', help='单次运行所有任务，不进入调度循环')
    parser.add_argument('--daemon', action='store_true', help='以守护进程方式运行')
    parser.add_argument('--test', action='store_true', help='测试模式')
    parser.add_argument('--mission', type=str, choices=['1', '2', '3', 'all'], 
                       help='运行特定专项: 1=每日简报, 2=盘中监控, 3=算法重构, all=所有')
    
    args = parser.parse_args()
    
    # 创建调度器
    orchestrator = V170Orchestrator()
    
    if args.test:
        print("测试模式启用，调整配置...")
        # 修改配置为测试模式
        orchestrator.config['mission_control']['专项一']['args'] = ['--mock', '--mock-llm']
        orchestrator.config['mission_control']['专项二']['market_hours_only'] = False
        orchestrator.config['mission_control']['专项三']['enabled'] = True
    
    if args.mission:
        print(f"运行专项 {args.mission}...")
        
        if args.mission == '1' or args.mission == 'all':
            orchestrator.run_mission_one()
        
        if args.mission == '2' or args.mission == 'all':
            orchestrator.run_mission_two()
        
        if args.mission == '3' or args.mission == 'all':
            orchestrator.run_mission_three()
        
        # 生成报告
        orchestrator._generate_execution_report()
        
    elif args.once:
        print("单次运行所有任务...")
        orchestrator.run_once()
        
    elif args.daemon:
        print("以守护进程方式运行调度器...")
        orchestrator.start()
        
        try:
            # 保持主线程运行
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("\n接收到中断信号，停止调度器...")
            orchestrator.stop()
    else:
        print("交互式单次运行...")
        orchestrator.run_once()


if __name__ == "__main__":
    main()