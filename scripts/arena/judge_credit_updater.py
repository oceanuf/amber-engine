#!/usr/bin/env python3
"""
评委诚信档案自动化更新模块
根据演武场实战结果，自动更新G1-G11算法的信用评分
符合架构师Gemini"评委诚信档案"要求
"""

import os
import sys
import json
import datetime
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

@dataclass
class JudgeCreditConfig:
    """评委诚信配置"""
    # 信用分计算参数
    hit_rate_weight: float = 0.7  # 命中率权重
    dd_contribution_weight: float = 0.3  # 回撤贡献度权重
    min_hit_rate_threshold: float = 0.30  # 最低命中率阈值
    max_dd_contribution_allowed: int = 3  # 最大允许回撤贡献次数
    
    # 观察期参数
    inspection_mode_threshold: int = 20  # 进入观察模式的天数阈值
    credit_score_threshold: float = 50.0  # 信用分阈值
    
    # 权重限制参数
    inspection_mode_weight_cap: float = 0.05  # 观察模式最大权重
    normal_mode_weight_cap: float = 0.30  # 正常模式最大权重
    min_weight: float = 0.01  # 最低权重 (防止算法被彻底遗忘)

@dataclass
class TradeRecord:
    """交易记录"""
    trade_date: str
    ticker: str
    action: str  # buy/sell
    algorithms: List[str]  # 推荐的算法列表
    entry_score: float  # 入場评分
    exit_score: Optional[float] = None  # 出场评分
    holding_days: Optional[int] = None  # 持有天数
    return_rate: Optional[float] = None  # 收益率
    stop_loss_triggered: bool = False  # 是否触发止损
    stop_loss_type: Optional[str] = None  # 止损类型
    trade_reason: Optional[str] = None  # 交易原因

@dataclass
class AlgorithmPerformance:
    """算法绩效数据"""
    algorithm_id: str
    algorithm_name: str
    
    # 命中率统计
    high_score_recommendations: int = 0  # 高分推荐次数 (评分≥80)
    entered_team1: int = 0  # 进入1队次数
    hit_rate: float = 0.0  # 命中率
    
    # 回撤贡献统计
    total_recommendations: int = 0  # 总推荐次数
    triggered_stop_loss: int = 0  # 触发止损次数
    dd_contribution_ratio: float = 0.0  # 回撤贡献比例
    
    # 收益率统计
    avg_return_rate: float = 0.0  # 平均收益率
    positive_return_count: int = 0  # 正收益次数
    negative_return_count: int = 0  # 负收益次数
    
    # 信用状态
    credit_score: float = 50.0  # 信用分 (0-100)
    inspection_status: str = "normal"  # normal/monitoring/inspection
    consecutive_low_days: int = 0  # 连续低信用天数
    weight_restriction: str = "none"  # 权重限制类型
    
    last_evaluation_date: str = ""
    next_evaluation_date: str = ""

class JudgeCreditUpdater:
    """评委信用更新器"""
    
    def __init__(self, config: Optional[JudgeCreditConfig] = None):
        self.config = config or JudgeCreditConfig()
        self.credit_file = "database/arena/judge_credit_ledger.json"
        self.trade_records_file = "database/arena/trade_records.json"
        self.fallback_marker_file = ".AMBER_FALLBACK_ACTIVE"
        self.initialized = False
        self.fallback_mode_active = False
        
    def initialize(self):
        """初始化信用系统"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.credit_file), exist_ok=True)
            
            # 加载或初始化信用档案
            if os.path.exists(self.credit_file):
                with open(self.credit_file, 'r', encoding='utf-8') as f:
                    self.credit_data = json.load(f)
                logger.info(f"✅ 加载信用档案: {self.credit_file}")
            else:
                self.credit_data = self._initialize_credit_data()
                self._save_credit_data()
                logger.info(f"✅ 初始化信用档案: {self.credit_file}")
            
            # 加载交易记录
            if os.path.exists(self.trade_records_file):
                with open(self.trade_records_file, 'r', encoding='utf-8') as f:
                    self.trade_records = json.load(f)
                logger.info(f"✅ 加载交易记录: {len(self.trade_records)}条")
            else:
                self.trade_records = []
                logger.info("✅ 初始化空交易记录")
            
            self.initialized = True
            
            # 检查是否处于降级模式
            self.fallback_mode_active = self._check_fallback_marker()
            if self.fallback_mode_active:
                logger.warning("⚠️  检测到降级标记，启用信用保护熔断机制")
                logger.warning(f"   标记文件: {self.fallback_marker_file}")
                logger.warning("   惩罚性权重调整将被跳过")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 信用系统初始化失败: {e}")
            return False
    
    def _check_fallback_marker(self) -> bool:
        """
        检查降级标记文件是否存在且有效
        
        返回:
            是否处于降级模式
        """
        try:
            if not os.path.exists(self.fallback_marker_file):
                return False
            
            # 验证标记文件内容
            with open(self.fallback_marker_file, 'r', encoding='utf-8') as f:
                marker_data = json.load(f)
            
            # 检查必要字段
            required_fields = ["marker_type", "created_at", "today"]
            if not all(field in marker_data for field in required_fields):
                logger.warning(f"⚠️  降级标记文件字段不完整: {self.fallback_marker_file}")
                return False
            
            # 检查标记类型
            if marker_data.get("marker_type") != "AMBER_FALLBACK_ACTIVE":
                logger.warning(f"⚠️  降级标记文件类型不匹配: {marker_data.get('marker_type')}")
                return False
            
            # 检查日期（防止旧标记污染）
            marker_date = marker_data.get("today", "")
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            if marker_date != today:
                logger.warning(f"⚠️  降级标记文件日期不匹配: {marker_date} != {today}")
                return False
            
            logger.info(f"✅ 检测到有效的降级标记: {self.fallback_marker_file}")
            logger.info(f"   创建时间: {marker_data.get('created_at')}")
            logger.info(f"   触发原因: {marker_data.get('trigger_reason', 'unknown')}")
            
            return True
            
        except json.JSONDecodeError:
            logger.error(f"❌ 降级标记文件JSON格式错误: {self.fallback_marker_file}")
            return False
        except Exception as e:
            logger.error(f"❌ 检查降级标记文件失败: {e}")
            return False
    
    def _initialize_credit_data(self) -> Dict:
        """初始化信用数据"""
        # G1-G11算法基础信息
        algorithms = {}
        
        algorithm_names = {
            "G1": "橡皮筋阈值策略",
            "G2": "双重动量策略",
            "G3": "波动率挤压策略",
            "G4": "分红保护垫策略",
            "G5": "周线RSI屏障",
            "G6": "Z分数偏离算法",
            "G7": "三重均线交叉",
            "G8": "缩量回踩算法",
            "G9": "实际利率锚点",
            "G10": "量价背离策略",
            "G11": "政策感知因子"
        }
        
        for algo_id, algo_name in algorithm_names.items():
            algorithms[algo_id] = {
                "algorithm_id": algo_id,
                "algorithm_name": algo_name,
                "credit_score": 75.0,  # 初始信用分
                "hit_rate": {
                    "total_high_score_recommendations": 0,
                    "entered_team1": 0,
                    "hit_rate": 0.0,
                    "last_30_days_trend": "stable"
                },
                "drawdown_contribution": {
                    "total_recommendations": 0,
                    "triggered_stop_loss": 0,
                    "dd_contribution_ratio": 0.0,
                    "last_stop_loss_date": None
                },
                "inspection_status": "normal",
                "consecutive_low_days": 0,
                "weight_restriction": "none",
                "last_evaluation_date": datetime.datetime.now().strftime('%Y-%m-%d')
            }
        
        return {
            "schema_version": "1.0.0",
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat(),
            "credit_system_config": asdict(self.config),
            "algorithms_credit": algorithms,
            "evaluation_history": [],
            "inspection_mode_algorithms": [],
            "system_status": "🟢 Normal"
        }
    
    def _save_credit_data(self):
        """保存信用数据"""
        try:
            self.credit_data["updated_at"] = datetime.datetime.now().isoformat()
            
            with open(self.credit_file, 'w', encoding='utf-8') as f:
                json.dump(self.credit_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 信用数据已保存: {self.credit_file}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 信用数据保存失败: {e}")
            return False
    
    def add_trade_record(self, record: TradeRecord):
        """添加交易记录"""
        if not self.initialized:
            if not self.initialize():
                raise RuntimeError("信用系统未初始化")
        
        try:
            # 转换为字典格式
            record_dict = asdict(record)
            
            # 添加到交易记录
            self.trade_records.append(record_dict)
            
            # 保存交易记录
            with open(self.trade_records_file, 'w', encoding='utf-8') as f:
                json.dump(self.trade_records, f, ensure_ascii=False, indent=2)
            
            logger.info(f"📝 添加交易记录: {record.ticker} ({record.action})")
            return True
            
        except Exception as e:
            logger.error(f"❌ 添加交易记录失败: {e}")
            return False
    
    def update_credit_scores(self, evaluation_date: Optional[str] = None):
        """更新信用评分"""
        if not self.initialized:
            if not self.initialize():
                raise RuntimeError("信用系统未初始化")
        
        try:
            if evaluation_date is None:
                evaluation_date = datetime.datetime.now().strftime('%Y-%m-%d')
            
            logger.info(f"🔍 开始更新信用评分: {evaluation_date}")
            
            # 分析交易记录，更新算法绩效
            self._analyze_trade_records(evaluation_date)
            
            # 计算信用分
            self._calculate_credit_scores()
            
            # 检查是否触发观察模式
            self._check_inspection_mode()
            
            # 更新评估历史
            self._update_evaluation_history(evaluation_date)
            
            # 保存更新后的信用数据
            self._save_credit_data()
            
            logger.info("✅ 信用评分更新完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 信用评分更新失败: {e}")
            return False
    
    def _analyze_trade_records(self, evaluation_date: str):
        """分析交易记录，更新算法绩效"""
        # 获取最近30天的交易记录
        cutoff_date = (datetime.datetime.strptime(evaluation_date, '%Y-%m-%d') - 
                      datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        
        recent_trades = [
            t for t in self.trade_records 
            if t.get('trade_date', '') >= cutoff_date
        ]
        
        logger.info(f"   分析最近30天交易记录: {len(recent_trades)}条")
        
        # 为每个算法初始化统计
        algo_stats = {}
        for algo_id in self.credit_data["algorithms_credit"].keys():
            algo_stats[algo_id] = {
                "high_score_recommendations": 0,
                "entered_team1": 0,
                "total_recommendations": 0,
                "triggered_stop_loss": 0,
                "return_rates": [],
                "positive_returns": 0,
                "negative_returns": 0
            }
        
        # 分析每笔交易
        for trade in recent_trades:
            algorithms = trade.get('algorithms', [])
            entry_score = trade.get('entry_score', 0)
            stop_loss_triggered = trade.get('stop_loss_triggered', False)
            return_rate = trade.get('return_rate', 0)
            
            for algo_id in algorithms:
                if algo_id in algo_stats:
                    stats = algo_stats[algo_id]
                    
                    # 总推荐次数
                    stats["total_recommendations"] += 1
                    
                    # 高分推荐 (评分≥80)
                    if entry_score >= 80:
                        stats["high_score_recommendations"] += 1
                        
                        # 检查是否进入1队 (这里需要与演武场队列关联)
                        # 简化处理: 如果有收益率数据且为正，认为进入1队
                        if return_rate is not None and return_rate > 0:
                            stats["entered_team1"] += 1
                    
                    # 止损触发
                    if stop_loss_triggered:
                        stats["triggered_stop_loss"] += 1
                    
                    # 收益率统计
                    if return_rate is not None:
                        stats["return_rates"].append(return_rate)
                        if return_rate > 0:
                            stats["positive_returns"] += 1
                        else:
                            stats["negative_returns"] += 1
        
        # 更新信用数据中的算法绩效
        for algo_id, stats in algo_stats.items():
            if algo_id in self.credit_data["algorithms_credit"]:
                algo_data = self.credit_data["algorithms_credit"][algo_id]
                
                # 更新命中率
                high_rec = stats["high_score_recommendations"]
                entered = stats["entered_team1"]
                
                hit_rate = 0.0
                if high_rec > 0:
                    hit_rate = entered / high_rec
                
                algo_data["hit_rate"].update({
                    "total_high_score_recommendations": high_rec,
                    "entered_team1": entered,
                    "hit_rate": hit_rate,
                    "last_30_days_trend": self._determine_trend(algo_id, hit_rate)
                })
                
                # 更新回撤贡献
                total_rec = stats["total_recommendations"]
                stop_loss = stats["triggered_stop_loss"]
                
                dd_ratio = 0.0
                if total_rec > 0:
                    dd_ratio = stop_loss / total_rec
                
                last_stop_loss = None
                if stop_loss > 0:
                    # 查找最近一次止损日期
                    for trade in recent_trades:
                        if (algo_id in trade.get('algorithms', []) and 
                            trade.get('stop_loss_triggered', False)):
                            last_stop_loss = trade.get('trade_date')
                            break
                
                algo_data["drawdown_contribution"].update({
                    "total_recommendations": total_rec,
                    "triggered_stop_loss": stop_loss,
                    "dd_contribution_ratio": dd_ratio,
                    "last_stop_loss_date": last_stop_loss
                })
                
                # 更新收益率统计
                return_rates = stats["return_rates"]
                avg_return = 0.0
                if return_rates:
                    avg_return = np.mean(return_rates)
                
                # 这里可以添加更多收益率统计字段
                
    def _determine_trend(self, algo_id: str, current_hit_rate: float) -> str:
        """确定命中率趋势"""
        # 简化实现: 基于当前命中率判断趋势
        if current_hit_rate >= 0.4:
            return "improving"
        elif current_hit_rate >= 0.3:
            return "stable"
        else:
            return "declining"
    
    def _calculate_credit_scores(self):
        """计算信用分"""
        
        # 检查是否处于降级模式
        if self.fallback_mode_active:
            logger.warning("⚠️  降级模式激活，跳过惩罚性信用分调整")
            logger.warning("   所有算法信用分将保持当前值或仅进行非惩罚性更新")
            
            # 在降级模式下，只更新评估日期，不调整信用分
            for algo_id, algo_data in self.credit_data["algorithms_credit"].items():
                algo_data["last_evaluation_date"] = datetime.datetime.now().strftime('%Y-%m-%d')
                
                # 记录降级模式下的特殊标记
                if "fallback_mode_notes" not in algo_data:
                    algo_data["fallback_mode_notes"] = []
                
                algo_data["fallback_mode_notes"].append({
                    "date": datetime.datetime.now().strftime('%Y-%m-%d'),
                    "action": "credit_score_frozen",
                    "reason": "AMBER_FALLBACK_ACTIVE marker detected",
                    "original_score": algo_data.get("credit_score", 75.0)
                })
            
            return
        
        # 正常模式：执行完整的信用分计算
        for algo_id, algo_data in self.credit_data["algorithms_credit"].items():
            hit_rate = algo_data["hit_rate"]["hit_rate"]
            dd_ratio = algo_data["drawdown_contribution"]["dd_contribution_ratio"]
            
            # 计算基础信用分
            # 命中率贡献
            hit_rate_score = min(100, hit_rate * 100 * self.config.hit_rate_weight)
            
            # 回撤贡献 (负向)
            dd_score = max(0, 100 - (dd_ratio * 100 * self.config.dd_contribution_weight))
            
            # 综合信用分
            credit_score = (hit_rate_score + dd_score) / 2
            
            # 应用历史平滑
            previous_score = algo_data.get("credit_score", 75.0)
            smoothed_score = 0.7 * previous_score + 0.3 * credit_score
            
            # 在降级模式下，信用分不应下降，只允许上升或保持
            # 但我们已经在上面的if语句中处理了降级模式，所以这里总是正常模式
            algo_data["credit_score"] = smoothed_score
            algo_data["last_evaluation_date"] = datetime.datetime.now().strftime('%Y-%m-%d')
            
            # 检查连续低信用天数
            if smoothed_score < self.config.credit_score_threshold:
                algo_data["consecutive_low_days"] = algo_data.get("consecutive_low_days", 0) + 1
            else:
                algo_data["consecutive_low_days"] = 0
    
    def _check_inspection_mode(self):
        """检查是否触发观察模式"""
        
        # 检查是否处于降级模式
        if self.fallback_mode_active:
            logger.warning("⚠️  降级模式激活，跳过观察模式触发")
            logger.warning("   所有算法将保持当前观察状态，不触发新的观察模式")
            
            # 在降级模式下，保持当前状态，不触发新的观察模式
            inspection_algorithms = self.credit_data.get("inspection_mode_algorithms", [])
            
            # 记录降级模式下的特殊标记
            for algo_id, algo_data in self.credit_data["algorithms_credit"].items():
                if "fallback_mode_notes" not in algo_data:
                    algo_data["fallback_mode_notes"] = []
                
                algo_data["fallback_mode_notes"].append({
                    "date": datetime.datetime.now().strftime('%Y-%m-%d'),
                    "action": "inspection_mode_frozen",
                    "reason": "AMBER_FALLBACK_ACTIVE marker detected",
                    "original_status": algo_data.get("inspection_status", "normal")
                })
            
            self.credit_data["inspection_mode_algorithms"] = inspection_algorithms
            
            # 系统状态标记为降级模式
            self.credit_data["system_status"] = "🟠 Fallback Mode"
            
            return
        
        # 正常模式：执行完整的观察模式检查
        inspection_algorithms = []
        
        for algo_id, algo_data in self.credit_data["algorithms_credit"].items():
            credit_score = algo_data["credit_score"]
            consecutive_low_days = algo_data["consecutive_low_days"]
            
            # 检查是否触发观察模式
            if (credit_score < self.config.credit_score_threshold and 
                consecutive_low_days >= self.config.inspection_mode_threshold):
                
                algo_data["inspection_status"] = "inspection"
                algo_data["weight_restriction"] = "capped"
                inspection_algorithms.append(algo_id)
                
                logger.warning(f"⚠️  算法 {algo_id} 进入观察模式")
                
            elif credit_score < self.config.credit_score_threshold:
                algo_data["inspection_status"] = "monitoring"
                algo_data["weight_restriction"] = "monitoring"
                
            else:
                algo_data["inspection_status"] = "normal"
                algo_data["weight_restriction"] = "none"
        
        self.credit_data["inspection_mode_algorithms"] = inspection_algorithms
        
        # 更新系统状态
        if inspection_algorithms:
            self.credit_data["system_status"] = "🟡 Monitoring"
        else:
            self.credit_data["system_status"] = "🟢 Normal"
    
    def _update_evaluation_history(self, evaluation_date: str):
        """更新评估历史"""
        evaluation_record = {
            "date": evaluation_date,
            "total_algorithms": len(self.credit_data["algorithms_credit"]),
            "inspection_mode_count": len(self.credit_data["inspection_mode_algorithms"]),
            "average_credit_score": 0,
            "top_performer": "",
            "bottom_performer": "",
            "actions_taken": "Credit scores updated"
        }
        
        # 计算平均信用分
        scores = [algo["credit_score"] for algo in self.credit_data["algorithms_credit"].values()]
        if scores:
            evaluation_record["average_credit_score"] = np.mean(scores)
            
            # 找出表现最好和最差的算法
            sorted_algorithms = sorted(
                self.credit_data["algorithms_credit"].items(),
                key=lambda x: x[1]["credit_score"],
                reverse=True
            )
            
            if sorted_algorithms:
                evaluation_record["top_performer"] = sorted_algorithms[0][0]
                evaluation_record["bottom_performer"] = sorted_algorithms[-1][0]
        
        # 添加到历史记录
        self.credit_data["evaluation_history"].append(evaluation_record)
        
        # 保持历史记录长度
        max_history = 30
        if len(self.credit_data["evaluation_history"]) > max_history:
            self.credit_data["evaluation_history"] = self.credit_data["evaluation_history"][-max_history:]
    
    def get_algorithm_weight_limits(self, algo_id: str) -> Tuple[float, float]:
        """获取算法权重限制"""
        if not self.initialized:
            if not self.initialize():
                return (self.config.min_weight, self.config.normal_mode_weight_cap)
        
        if algo_id not in self.credit_data["algorithms_credit"]:
            return (self.config.min_weight, self.config.normal_mode_weight_cap)
        
        algo_data = self.credit_data["algorithms_credit"][algo_id]
        inspection_status = algo_data["inspection_status"]
        
        if inspection_status == "inspection":
            # 观察模式: 权重严格限制
            return (self.config.min_weight, self.config.inspection_mode_weight_cap)
        elif inspection_status == "monitoring":
            # 监控模式: 中等限制
            return (self.config.min_weight, self.config.normal_mode_weight_cap * 0.5)
        else:
            # 正常模式: 正常限制
            return (self.config.min_weight, self.config.normal_mode_weight_cap)
    
    def get_credit_report(self) -> Dict:
        """获取信用报告"""
        if not self.initialized:
            if not self.initialize():
                return {"error": "Credit system not initialized"}
        
        return {
            "report_date": datetime.datetime.now().isoformat(),
            "system_status": self.credit_data["system_status"],
            "total_algorithms": len(self.credit_data["algorithms_credit"]),
            "inspection_mode_count": len(self.credit_data["inspection_mode_algorithms"]),
            "inspection_algorithms": self.credit_data["inspection_mode_algorithms"],
            "average_credit_score": np.mean([algo["credit_score"] for algo in self.credit_data["algorithms_credit"].values()]),
            "algorithms_summary": {
                algo_id: {
                    "credit_score": algo_data["credit_score"],
                    "hit_rate": algo_data["hit_rate"]["hit_rate"],
                    "dd_ratio": algo_data["drawdown_contribution"]["dd_contribution_ratio"],
                    "inspection_status": algo_data["inspection_status"],
                    "weight_restriction": algo_data["weight_restriction"]
                }
                for algo_id, algo_data in self.credit_data["algorithms_credit"].items()
            }
        }

# 测试函数
def test_judge_credit_updater():
    """测试评委信用更新器"""
    print("🧪 测试评委信用更新器...")
    
    updater = JudgeCreditUpdater()
    
    # 初始化
    if not updater.initialize():
        print("❌ 初始化失败")
        return False
    
    print("✅ 信用系统初始化成功")
    
    # 添加测试交易记录
    test_record = TradeRecord(
        trade_date="2026-04-08",
        ticker="000681",
        action="buy",
        algorithms=["G11", "G6", "G2"],
        entry_score=78.42,
        exit_score=None,
        holding_days=0,
        return_rate=None,
        stop_loss_triggered=False,
        trade_reason="演武场首秀入选"
    )
    
    if updater.add_trade_record(test_record):
        print("✅ 测试交易记录添加成功")
    
    # 更新信用评分
    if updater.update_credit_scores("2026-04-09"):
        print("✅ 信用评分更新成功")
    
    # 获取信用报告
    report = updater.get_credit_report()
    print(f"📋 信用报告生成成功")
    print(f"   系统状态: {report['system_status']}")
    print(f"   平均信用分: {report['average_credit_score']:.2f}")
    print(f"   观察模式算法: {len(report['inspection_algorithms'])}个")
    
    # 显示算法信用分示例
    print("\n🎯 算法信用分示例:")
    for algo_id, summary in list(report["algorithms_summary"].items())[:3]:
        print(f"   {algo_id}: {summary['credit_score']:.1f}分 ({summary['inspection_status']})")
    
    return True

def main():
    """评委信用更新器主函数，支持自动化模式"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="评委信用更新器 - 根据演武场实战结果自动更新算法信用评分",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--auto", action="store_true",
                       help="自动化模式，静默执行并返回状态码，适合cron调度")
    parser.add_argument("--signal", type=str, default="AUTO",
                       help="触发信号类型: AUTO(自动)/MANUAL(手动)/FORCE(强制)")
    parser.add_argument("--date", type=str, default=None,
                       help="指定评估日期(YYYY-MM-DD)，默认使用今日")
    parser.add_argument("--output", type=str, default="algorithm_weights_history.json",
                       help="权重历史记录输出文件，默认: algorithm_weights_history.json")
    parser.add_argument("--verbose", action="store_true",
                       help="详细输出模式，显示更多信息")
    parser.add_argument("--test", action="store_true",
                       help="测试模式，运行原测试函数")
    
    args = parser.parse_args()
    
    # 测试模式
    if args.test:
        success = test_judge_credit_updater()
        return 0 if success else 1
    
    # 自动化模式设置
    if args.auto:
        # 静默执行，减少输出
        import logging
        logging.getLogger().setLevel(logging.WARNING)
    else:
        # 正常模式，显示横幅
        print("⚖️  评委信用更新器启动")
        print(f"   模式: {'自动化(静默)' if args.auto else '交互'}")
        print(f"   信号: {args.signal}")
        print(f"   日期: {args.date or '今日'}")
        print(f"   输出: {args.output}")
    
    try:
        # 创建更新器实例
        updater = JudgeCreditUpdater()
        
        # 初始化信用系统
        if not updater.initialize():
            if not args.auto:
                print("❌ 信用系统初始化失败")
            return 1
        
        if not args.auto:
            print("✅ 信用系统初始化成功")
        
        # 确定评估日期
        evaluation_date = args.date or datetime.datetime.now().strftime("%Y-%m-%d")
        
        # 更新信用评分
        if not updater.update_credit_scores(evaluation_date):
            if not args.auto:
                print(f"❌ 信用评分更新失败，日期: {evaluation_date}")
            return 2
        
        if not args.auto:
            print(f"✅ 信用评分更新成功，日期: {evaluation_date}")
        
        # 获取信用报告
        report = updater.get_credit_report()
        if "error" in report:
            if not args.auto:
                print(f"❌ 获取信用报告失败: {report['error']}")
            return 3
        
        # 生成算法权重数据
        algorithm_weights = {}
        for algo_id, algo_data in updater.credit_data.get("algorithms_credit", {}).items():
            # 基于信用分计算权重
            credit_score = algo_data.get("credit_score", 50.0)
            inspection_status = algo_data.get("inspection_status", "normal")
            
            # 权重计算逻辑: 信用分越高，权重越大
            base_weight = credit_score / 100.0  # 0-1范围
            
            # 根据观察状态调整权重
            if inspection_status == "inspection":
                base_weight *= 0.1  # 观察模式权重大幅降低
            elif inspection_status == "monitoring":
                base_weight *= 0.5  # 监控模式权重适中
            
            # 归一化处理
            algorithm_weights[algo_id] = round(base_weight, 4)
        
        # 归一化权重，使总和为1
        total_weight = sum(algorithm_weights.values())
        if total_weight > 0:
            algorithm_weights = {k: round(v/total_weight, 4) for k, v in algorithm_weights.items()}
        
        # 构建权重历史记录
        weights_history = {
            "report_date": evaluation_date,
            "generation_time": datetime.datetime.now().isoformat(),
            "signal_type": args.signal,
            "execution_mode": "auto" if args.auto else "manual",
            "fallback_mode_active": updater.fallback_mode_active,
            "total_algorithms": len(algorithm_weights),
            "algorithm_weights": algorithm_weights,
            "credit_report_summary": {
                "average_credit_score": report.get("average_credit_score", 0.0),
                "inspection_mode_count": len(report.get("inspection_algorithms", [])),
                "system_status": report.get("system_status", "unknown")
            }
        }
        
        # 如果处于降级模式，添加特殊标记
        if updater.fallback_mode_active:
            weights_history["fallback_mode_note"] = "信用保护熔断激活：惩罚性权重调整被跳过"
            weights_history["fallback_marker_file"] = updater.fallback_marker_file
        
        # 保存权重历史记录
        output_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "database", "arena", args.output
        )
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(weights_history, f, ensure_ascii=False, indent=2)
        
        if not args.auto:
            print(f"✅ 算法权重历史记录已保存: {output_path}")
            print(f"   生成时间: {weights_history['generation_time']}")
            print(f"   算法数量: {weights_history['total_algorithms']}")
            print(f"   平均信用分: {weights_history['credit_report_summary']['average_credit_score']:.2f}")
            
            # 显示权重示例
            print("\n🎯 算法权重示例(前5个):")
            for algo_id, weight in list(algorithm_weights.items())[:5]:
                print(f"   {algo_id}: {weight:.4f}")
        
        # 返回成功
        return 0
        
    except Exception as e:
        if not args.auto:
            print(f"❌ 评委信用更新器执行异常: {e}")
            import traceback
            traceback.print_exc()
        return 99


if __name__ == "__main__":
    # 支持旧版测试模式
    import sys
    if len(sys.argv) == 1:
        # 无参数时运行测试
        success = test_judge_credit_updater()
        if success:
            print("\n✅ 评委信用更新器测试通过")
        else:
            print("\n❌ 评委信用更新器测试失败")
        sys.exit(0 if success else 1)
    else:
        # 有参数时运行主函数
        exit_code = main()
        sys.exit(exit_code)