#!/usr/bin/env python3
"""
数据就绪触发器 - 检测数据净化完成后向评委中控发出READY信号
任务指令 [2616-0411-P0D] Grain 1: 状态检测模块

核心功能:
1. 文件指纹校验: 检查extracted_data/下当日文件的完整性
2. 数据新鲜度检测: 验证文件不是空文件或旧文件
3. 同步/异步决策: 如果数据在18:00断流，触发降级而非无限等待
4. 信号发射: 向评委中控发出READY信号

设计理念:
- 遵循工程诚实: 真实反映数据就绪状态，不掩盖失败
- 利用P0C成果: 当数据不可用时，触发DataFallback降级逻辑
- 支持自动化: 返回明确的退出码，便于cron_manager.sh集成
"""

import os
import sys
import json
import time
import argparse
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import hashlib

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class DataReadyTrigger:
    """
    数据就绪触发器 - 检测数据净化完成状态
    
    验收标准:
    1. 文件指纹校验: 确保抓取的数据不是空文件或旧文件
    2. 数据新鲜度: 必须是当日(T日)的数据
    3. 降级决策: 如果18:00数据断流，触发降级而非无限等待
    4. 信号发射: 通过退出码和日志发出明确的READY信号
    """
    
    def __init__(self, workspace_root: str = None):
        """初始化触发器"""
        if workspace_root is None:
            self.workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        else:
            self.workspace_root = workspace_root
        
        # 关键目录路径
        self.extracted_dir = os.path.join(self.workspace_root, "database", "arena", "extracted_data")
        self.logs_dir = os.path.join(self.workspace_root, "logs", "pipeline")
        self.fallback_marker_file = os.path.join(self.workspace_root, ".AMBER_FALLBACK_ACTIVE")
        
        # 确保目录存在
        os.makedirs(self.extracted_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        
        # 配置参数
        self.max_wait_minutes = 5  # 最大等待时间(分钟) - 避免无限等待
        self.check_interval_seconds = 30  # 检查间隔(秒)
        self.min_file_size_kb = 1  # 最小文件大小(KB)
        
        # 今日日期
        self.today = datetime.now().strftime("%Y-%m-%d")
        
        print(f"📡 DataReadyTrigger 初始化完成")
        print(f"   工作空间: {self.workspace_root}")
        print(f"   提取目录: {self.extracted_dir}")
        print(f"   今日日期: {self.today}")
        print(f"   最大等待: {self.max_wait_minutes}分钟")
        print(f"   最小文件: {self.min_file_size_kb}KB")
    
    def calculate_file_fingerprint(self, file_path: str) -> Dict[str, Any]:
        """
        计算文件指纹 - 多维度验证文件完整性
        
        返回包含以下信息的字典:
        - exists: 文件是否存在
        - size_kb: 文件大小(KB)
        - mtime: 修改时间
        - age_hours: 文件年龄(小时)
        - json_valid: JSON是否有效
        - content_hash: 内容哈希(MD5)
        - data_keys: 数据中的关键字段
        """
        fingerprint = {
            "exists": False,
            "file_path": file_path,
            "size_kb": 0,
            "mtime": None,
            "age_hours": 999,
            "json_valid": False,
            "content_hash": "",
            "data_keys": [],
            "error": None
        }
        
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                fingerprint["error"] = f"文件不存在: {file_path}"
                return fingerprint
            
            fingerprint["exists"] = True
            
            # 获取文件统计信息
            stat_info = os.stat(file_path)
            fingerprint["size_kb"] = stat_info.st_size / 1024
            fingerprint["mtime"] = datetime.fromtimestamp(stat_info.st_mtime).isoformat()
            
            # 计算文件年龄(小时)
            file_age = datetime.now() - datetime.fromtimestamp(stat_info.st_mtime)
            fingerprint["age_hours"] = file_age.total_seconds() / 3600
            
            # 检查文件大小
            if fingerprint["size_kb"] < self.min_file_size_kb:
                fingerprint["error"] = f"文件过小: {fingerprint['size_kb']:.2f}KB < {self.min_file_size_kb}KB"
                return fingerprint
            
            # 读取并验证JSON
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 计算内容哈希
            fingerprint["content_hash"] = hashlib.md5(content.encode('utf-8')).hexdigest()[:8]
            
            # 解析JSON
            data = json.loads(content)
            fingerprint["json_valid"] = True
            
            # 提取关键字段
            fingerprint["data_keys"] = list(data.keys())
            
            # 检查必要的数据字段
            required_fields = ["extraction_date", "report_date", "ticker_count"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                fingerprint["error"] = f"缺少必要字段: {missing_fields}"
            else:
                # 检查数据新鲜度 - 报告日期应该是今天
                report_date = data.get("report_date", "")
                if report_date != self.today:
                    fingerprint["error"] = f"数据非今日: {report_date} != {self.today}"
        
        except json.JSONDecodeError as e:
            fingerprint["error"] = f"JSON解析错误: {e}"
        except Exception as e:
            fingerprint["error"] = f"文件指纹计算错误: {e}"
        
        return fingerprint
    
    def find_today_data_file(self) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        查找今日的数据文件
        
        返回:
            (文件路径, 指纹信息) 或 (None, 错误信息)
        """
        print(f"🔍 查找今日({self.today})的数据文件")
        
        # 获取extracted_data目录下的所有JSON文件
        json_files = []
        for filename in os.listdir(self.extracted_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(self.extracted_dir, filename)
                json_files.append(file_path)
        
        if not json_files:
            return None, {"error": "extracted_data目录下无JSON文件"}
        
        print(f"   发现 {len(json_files)} 个JSON文件")
        
        # 按修改时间排序(最新的优先)
        json_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        # 检查每个文件
        for file_path in json_files:
            fingerprint = self.calculate_file_fingerprint(file_path)
            
            if not fingerprint["exists"]:
                continue
            
            filename = os.path.basename(file_path)
            print(f"   检查文件: {filename}")
            print(f"     大小: {fingerprint['size_kb']:.2f}KB, 年龄: {fingerprint['age_hours']:.1f}小时")
            print(f"     JSON有效: {fingerprint['json_valid']}, 哈希: {fingerprint['content_hash']}")
            
            if fingerprint["error"]:
                print(f"     ❌ 问题: {fingerprint['error']}")
                continue
            
            # 检查是否是今日数据(通过文件名或内容)
            if self.today in filename or fingerprint.get("json_valid", False):
                # 进一步验证内容中的报告日期
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    report_date = data.get("report_date", "")
                    if report_date == self.today:
                        print(f"     ✅ 找到今日数据文件: {filename}")
                        return file_path, fingerprint
                    else:
                        print(f"     ⚠️  文件报告日期不匹配: {report_date} != {self.today}")
                except:
                    print(f"     ⚠️  无法验证文件内容")
        
        return None, {"error": f"未找到今日({self.today})的有效数据文件"}
    
    def wait_for_data_with_timeout(self) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        等待数据就绪，支持超时和降级决策
        
        设计理念: 
        - 如果数据在18:00准时到达，立即处理
        - 如果数据延迟，等待最多5分钟
        - 如果超时后仍无数据，触发降级逻辑
        
        返回:
            (是否就绪, 文件路径, 详细信息)
        """
        print(f"⏳ 等待数据就绪 (超时: {self.max_wait_minutes}分钟)")
        
        start_time = time.time()
        timeout_seconds = self.max_wait_minutes * 60
        
        check_count = 0
        
        while True:
            check_count += 1
            elapsed_seconds = time.time() - start_time
            elapsed_minutes = elapsed_seconds / 60
            
            print(f"\n🔄 第{check_count}次检查 (已等待{elapsed_minutes:.1f}分钟)")
            
            # 尝试查找今日数据文件
            file_path, fingerprint = self.find_today_data_file()
            
            if file_path:
                print(f"✅ 数据就绪! 文件: {os.path.basename(file_path)}")
                return True, file_path, fingerprint
            
            # 检查是否超时
            if elapsed_seconds >= timeout_seconds:
                print(f"⏰ 等待超时 ({self.max_wait_minutes}分钟)")
                print(f"🚨 触发降级决策: 使用P0C的DataFallback机制")
                
                # 触发降级逻辑
                return self.trigger_fallback_mode()
            
            # 等待下一次检查
            print(f"⏳ 数据未就绪，{self.check_interval_seconds}秒后重试...")
            time.sleep(self.check_interval_seconds)
    
    def trigger_fallback_mode(self) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        触发降级模式 - 当数据不可用时使用备用方案
        
        设计理念:
        - 利用[2616-0411-P0C]的DataFallback成果
        - 提供明确的降级信号，让上层知道这是备用数据
        - 记录降级事件用于后续分析
        """
        print("🔄 触发数据降级模式")
        
        # 尝试使用DataFallback模块
        try:
            from scripts.arena.technical_fallback import DataFallback
            
            fallback = DataFallback()
            
            # 尝试获取一些关键股票的数据
            test_tickers = ["510300", "000681", "600633"]
            batch_results = fallback.batch_get_prices(test_tickers, self.today)
            
            success_count = sum(1 for r in batch_results.values() if r.get("success"))
            backup_count = sum(1 for r in batch_results.values() if "[BACKUP_DATA]" in str(r.get("backup_marker", "")))
            
            fallback_info = {
                "mode": "FALLBACK",
                "trigger_time": datetime.now().isoformat(),
                "test_tickers": test_tickers,
                "success_count": success_count,
                "backup_count": backup_count,
                "data_sources": [r.get("data_source", "unknown") for r in batch_results.values() if r.get("success")],
                "note": f"数据未就绪，使用DataFallback降级模式。成功获取{success_count}/{len(test_tickers)}个股票数据，其中{backup_count}个使用备份数据。"
            }
            
            # 虽然数据不完整，但返回降级模式就绪
            # 这允许评委中控在降级模式下工作
            return True, None, fallback_info
            
        except Exception as e:
            print(f"❌ 降级模式失败: {e}")
            
            # 完全失败
            return False, None, {
                "mode": "FAILED",
                "error": str(e),
                "trigger_time": datetime.now().isoformat(),
                "note": "数据未就绪且降级模式失败"
            }
    
    def create_fallback_marker(self) -> bool:
        """
        创建降级标记文件 .AMBER_FALLBACK_ACTIVE
        
        设计理念:
        - 提供物理信号级联，让评委中控感知数据降级状态
        - 标记文件包含创建时间、触发原因等元数据
        - 文件存在即表示系统处于降级运行模式
        
        返回:
            是否成功创建标记
        """
        try:
            marker_data = {
                "marker_type": "AMBER_FALLBACK_ACTIVE",
                "created_at": datetime.now().isoformat(),
                "today": self.today,
                "trigger_reason": "DATA_NOT_READY_TIMEOUT",
                "workspace_root": self.workspace_root,
                "note": "数据就绪检查超时，系统进入降级运行模式。评委中控应避免惩罚性权重调整。"
            }
            
            with open(self.fallback_marker_file, 'w', encoding='utf-8') as f:
                json.dump(marker_data, f, ensure_ascii=False, indent=2)
            
            print(f"📝 创建降级标记文件: {self.fallback_marker_file}")
            print(f"   标记时间: {marker_data['created_at']}")
            print(f"   触发原因: {marker_data['trigger_reason']}")
            
            return True
            
        except Exception as e:
            print(f"❌ 创建降级标记文件失败: {e}")
            return False
    
    def remove_fallback_marker(self) -> bool:
        """
        删除降级标记文件 .AMBER_FALLBACK_ACTIVE
        
        设计理念:
        - 防止状态污染次日逻辑
        - 仅在确保流程完整执行后清理
        - 支持幂等操作（文件不存在时不报错）
        
        返回:
            是否成功删除标记（或标记不存在）
        """
        try:
            if os.path.exists(self.fallback_marker_file):
                os.remove(self.fallback_marker_file)
                print(f"🗑️  删除降级标记文件: {self.fallback_marker_file}")
                return True
            else:
                # 文件不存在，视为成功（幂等）
                return True
        except Exception as e:
            print(f"❌ 删除降级标记文件失败: {e}")
            return False
    
    def check_fallback_marker_exists(self) -> bool:
        """
        检查降级标记文件是否存在
        
        返回:
            标记文件是否存在且有效
        """
        if not os.path.exists(self.fallback_marker_file):
            return False
        
        try:
            # 验证标记文件内容
            with open(self.fallback_marker_file, 'r', encoding='utf-8') as f:
                marker_data = json.load(f)
            
            # 检查必要字段
            required_fields = ["marker_type", "created_at", "today"]
            if not all(field in marker_data for field in required_fields):
                print(f"⚠️  降级标记文件字段不完整: {self.fallback_marker_file}")
                return False
            
            # 检查标记类型
            if marker_data.get("marker_type") != "AMBER_FALLBACK_ACTIVE":
                print(f"⚠️  降级标记文件类型不匹配: {marker_data.get('marker_type')}")
                return False
            
            # 检查日期（防止旧标记污染）
            marker_date = marker_data.get("today", "")
            if marker_date != self.today:
                print(f"⚠️  降级标记文件日期不匹配: {marker_date} != {self.today}")
                return False
            
            return True
            
        except json.JSONDecodeError:
            print(f"❌ 降级标记文件JSON格式错误: {self.fallback_marker_file}")
            return False
        except Exception as e:
            print(f"❌ 检查降级标记文件失败: {e}")
            return False
    
    def send_ready_signal(self, file_path: Optional[str] = None, 
                         metadata: Dict[str, Any] = None) -> int:
        """
        发送READY信号给评委中控
        
        设计理念:
        - 通过退出码传递信号: 0=就绪, 1=失败, 2=降级模式
        - 生成详细的日志文件供后续分析
        - 支持命令行参数传递给评委中控
        
        返回:
            退出码 (0: 成功, 1: 失败, 2: 降级模式)
        """
        # 生成信号日志
        signal_log = {
            "signal": "DATA_READY",
            "timestamp": datetime.now().isoformat(),
            "today": self.today,
            "file_path": file_path,
            "metadata": metadata or {},
            "trigger_mode": "NORMAL" if file_path else "FALLBACK",
            "exit_code": 0 if file_path else 2
        }
        
        # 保存日志
        log_file = os.path.join(self.logs_dir, f"data_ready_signal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(signal_log, f, ensure_ascii=False, indent=2)
        
        print(f"📤 发送READY信号")
        print(f"   模式: {signal_log['trigger_mode']}")
        print(f"   文件: {file_path or '无(降级模式)'}")
        print(f"   日志: {log_file}")
        
        if file_path:
            print(f"✅ 数据就绪，可以启动评委中控")
            # 正常模式：确保没有残留的降级标记
            self.remove_fallback_marker()
            return 0  # 正常就绪
        elif metadata and metadata.get("mode") == "FALLBACK":
            print(f"⚠️  降级模式就绪，使用备用数据")
            # 降级模式：创建物理标记文件
            if self.create_fallback_marker():
                print(f"📝 降级标记已创建: {self.fallback_marker_file}")
            else:
                print(f"⚠️  降级标记创建失败，但继续执行")
            return 2  # 降级模式就绪
        else:
            print(f"❌ 数据未就绪且无降级方案")
            # 失败模式：清理可能存在的旧标记
            self.remove_fallback_marker()
            return 1  # 失败
    
    def run(self, wait_for_data: bool = True) -> int:
        """
        主运行函数
        
        参数:
            wait_for_data: 是否等待数据就绪(True)或立即检查(False)
            
        返回:
            退出码 (0: 成功, 1: 失败, 2: 降级模式)
        """
        print(f"🚀 DataReadyTrigger 启动")
        print(f"   模式: {'等待数据' if wait_for_data else '立即检查'}")
        print(f"   时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if wait_for_data:
            # 等待数据就绪(支持超时和降级)
            data_ready, file_path, metadata = self.wait_for_data_with_timeout()
        else:
            # 立即检查
            file_path, fingerprint = self.find_today_data_file()
            if file_path:
                data_ready, metadata = True, fingerprint
            else:
                # 立即触发降级
                data_ready, file_path, metadata = self.trigger_fallback_mode()
        
        if not data_ready:
            print("❌ 数据就绪检查失败")
            return 1
        
        # 发送READY信号
        exit_code = self.send_ready_signal(file_path, metadata)
        
        print(f"\n🎯 DataReadyTrigger 完成")
        print(f"   退出码: {exit_code}")
        print(f"   时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return exit_code


def main():
    """命令行入口点"""
    parser = argparse.ArgumentParser(description="数据就绪触发器 - 检测数据净化完成后向评委中控发出READY信号")
    parser.add_argument("--no-wait", action="store_true", 
                       help="不等待数据，立即检查并返回结果")
    parser.add_argument("--max-wait", type=int, default=5,
                       help="最大等待时间(分钟)，默认: 5")
    parser.add_argument("--check-interval", type=int, default=30,
                       help="检查间隔(秒)，默认: 30")
    parser.add_argument("--min-size", type=int, default=1,
                       help="最小文件大小(KB)，默认: 1")
    parser.add_argument("--debug", action="store_true",
                       help="调试模式，输出详细信息")
    
    args = parser.parse_args()
    
    # 创建触发器实例
    trigger = DataReadyTrigger()
    
    # 更新配置
    if args.max_wait:
        trigger.max_wait_minutes = args.max_wait
    if args.check_interval:
        trigger.check_interval_seconds = args.check_interval
    if args.min_size:
        trigger.min_file_size_kb = args.min_size
    
    # 运行触发器
    exit_code = trigger.run(wait_for_data=not args.no_wait)
    
    # 退出码映射
    # 0: 数据就绪，正常模式
    # 1: 失败，无数据可用
    # 2: 降级模式就绪
    sys.exit(exit_code)


if __name__ == "__main__":
    main()