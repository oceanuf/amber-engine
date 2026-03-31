#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据指挥官模块 - 三位一体数据冗余矩阵
文档编号: AE-DATA-001-V1.0
依据: [2614-044号]首席架构师战略构想
功能: 实现Tushare/AkShare双源热备，动态健康评分
"""

import json
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from enum import Enum
import hashlib

# 导入网络加固模块
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from network.proxy_manager import proxy_manager, anti_block

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataSource(Enum):
    """数据源枚举"""
    AKSHARE = "akshare"      # 高频捕获源
    TUSHARE = "tushare"      # 权威低频源
    BAOSTOCK = "baostock"    # 备用轻量源
    YAHOO = "yahoo"          # 美股数据源
    LOCAL_CACHE = "cache"    # 本地缓存


class DataType(Enum):
    """数据类型枚举"""
    REAL_TIME = "real_time"      # 实时行情
    HISTORICAL = "historical"    # 历史K线
    FINANCIAL = "financial"      # 财务数据
    SENTIMENT = "sentiment"      # 市场情绪
    FUND_FLOW = "fund_flow"      # 资金流向


class HealthStatus(Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"          # 健康 (成功率 > 90%)
    DEGRADED = "degraded"        # 降级 (成功率 70-90%)
    UNSTABLE = "unstable"        # 不稳定 (成功率 50-70%)
    FAILING = "failing"          # 失败 (成功率 < 50%)
    OFFLINE = "offline"          # 离线


class DataOrchestrator:
    """数据指挥官 - 管理多数据源调度"""
    
    def __init__(self, config_path: str = None):
        """
        初始化数据指挥官
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.data_sources = self._initialize_data_sources()
        self.health_scores = {}  # 数据源健康分
        self.request_history = {}  # 请求历史记录
        self.cache = {}  # 内存缓存
        
        # 初始化健康监控
        self._initialize_health_monitoring()
        
        logger.info("数据指挥官初始化完成")
    
    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        default_config = {
            "data_sources": {
                "akshare": {
                    "enabled": True,
                    "priority": 1,  # 高频捕获源
                    "retry_count": 3,
                    "timeout": 30,
                    "rate_limit": 5  # 每分钟请求限制
                },
                "tushare": {
                    "enabled": True,
                    "priority": 2,  # 权威低频源
                    "retry_count": 2,
                    "timeout": 60,
                    "rate_limit": 2
                },
                "baostock": {
                    "enabled": True,
                    "priority": 3,  # 备用源
                    "retry_count": 3,
                    "timeout": 45,
                    "rate_limit": 3
                }
            },
            "cache": {
                "enabled": True,
                "ttl_minutes": 60,  # 缓存有效期(分钟)
                "max_size_mb": 100   # 最大缓存大小(MB)
            },
            "health_check": {
                "interval_minutes": 5,  # 健康检查间隔
                "success_threshold": 0.9,  # 健康阈值
                "degraded_threshold": 0.7   # 降级阈值
            }
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    # 合并配置
                    default_config.update(user_config)
                    logger.info(f"从 {config_path} 加载配置")
            except Exception as e:
                logger.warning(f"加载配置文件失败: {e}, 使用默认配置")
        
        return default_config
    
    def _initialize_data_sources(self) -> Dict[str, Dict]:
        """初始化数据源配置"""
        data_sources = {}
        
        for source_name, config in self.config["data_sources"].items():
            if config.get("enabled", False):
                data_sources[source_name] = {
                    "config": config,
                    "last_used": None,
                    "success_count": 0,
                    "failure_count": 0,
                    "total_requests": 0,
                    "last_success": None,
                    "last_failure": None
                }
        
        logger.info(f"初始化数据源: {list(data_sources.keys())}")
        return data_sources
    
    def _initialize_health_monitoring(self):
        """初始化健康监控"""
        for source_name in self.data_sources:
            self.health_scores[source_name] = {
                "score": 100.0,  # 初始健康分
                "status": HealthStatus.HEALTHY,
                "last_check": datetime.now(),
                "trend": "stable"  # stable/improving/declining
            }
            self.request_history[source_name] = []
    
    def calculate_health_score(self, source_name: str) -> float:
        """
        计算数据源健康分
        
        Args:
            source_name: 数据源名称
            
        Returns:
            健康分 (0-100)
        """
        if source_name not in self.data_sources:
            return 0.0
        
        source_data = self.data_sources[source_name]
        
        # 基础成功率计算
        total = source_data["total_requests"]
        if total == 0:
            return 100.0  # 未使用过，默认健康
        
        success_rate = source_data["success_count"] / total
        
        # 时间衰减因子 (最近成功率权重更高)
        recency_factor = 1.0
        if source_data["last_success"]:
            hours_since_success = (datetime.now() - source_data["last_success"]).total_seconds() / 3600
            recency_factor = max(0.5, 1.0 - (hours_since_success / 24))  # 24小时内衰减
        
        # 响应时间因子
        response_time_factor = 1.0
        # TODO: 实际实现时需要记录响应时间
        
        # 计算综合健康分
        base_score = success_rate * 100
        health_score = base_score * recency_factor * response_time_factor
        
        return min(100.0, max(0.0, health_score))
    
    def update_health_status(self, source_name: str):
        """更新数据源健康状态"""
        health_score = self.calculate_health_score(source_name)
        
        # 确定状态
        if health_score >= 90:
            status = HealthStatus.HEALTHY
        elif health_score >= 70:
            status = HealthStatus.DEGRADED
        elif health_score >= 50:
            status = HealthStatus.UNSTABLE
        elif health_score > 0:
            status = HealthStatus.FAILING
        else:
            status = HealthStatus.OFFLINE
        
        # 更新趋势
        old_score = self.health_scores[source_name]["score"]
        if health_score > old_score + 5:
            trend = "improving"
        elif health_score < old_score - 5:
            trend = "declining"
        else:
            trend = "stable"
        
        # 更新健康记录
        self.health_scores[source_name] = {
            "score": health_score,
            "status": status,
            "last_check": datetime.now(),
            "trend": trend
        }
        
        logger.debug(f"数据源 {source_name} 健康状态更新: 分数={health_score:.1f}, 状态={status.value}, 趋势={trend}")
    
    def record_request(self, source_name: str, success: bool, response_time: float = None):
        """记录请求结果"""
        if source_name not in self.data_sources:
            logger.warning(f"未知数据源: {source_name}")
            return
        
        source_data = self.data_sources[source_name]
        
        # 更新统计数据
        source_data["total_requests"] += 1
        if success:
            source_data["success_count"] += 1
            source_data["last_success"] = datetime.now()
        else:
            source_data["failure_count"] += 1
            source_data["last_failure"] = datetime.now()
        
        source_data["last_used"] = datetime.now()
        
        # 记录历史
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "response_time": response_time
        }
        self.request_history[source_name].append(history_entry)
        
        # 保持历史记录长度
        if len(self.request_history[source_name]) > 100:
            self.request_history[source_name] = self.request_history[source_name][-100:]
        
        # 更新健康状态
        self.update_health_status(source_name)
    
    def select_data_source(self, data_type: DataType, symbol: str = None) -> str:
        """
        选择最优数据源
        
        Args:
            data_type: 数据类型
            symbol: 股票代码
            
        Returns:
            选中的数据源名称
        """
        available_sources = []
        
        for source_name, source_data in self.data_sources.items():
            config = source_data["config"]
            
            # 检查是否启用
            if not config.get("enabled", False):
                continue
            
            # 检查健康状态
            health_info = self.health_scores.get(source_name, {})
            status = health_info.get("status")
            
            # 根据健康状态调整优先级
            if status == HealthStatus.HEALTHY:
                priority_multiplier = 1.0
            elif status == HealthStatus.DEGRADED:
                priority_multiplier = 0.7
            elif status == HealthStatus.UNSTABLE:
                priority_multiplier = 0.4
            elif status == HealthStatus.FAILING:
                priority_multiplier = 0.1
            else:  # OFFLINE
                continue
            
            # 计算综合优先级
            base_priority = config.get("priority", 1)
            health_score = health_info.get("score", 0)
            
            # 考虑数据源对特定数据类型的适配性
            type_factor = self._get_type_factor(source_name, data_type)
            
            # 综合评分
            score = base_priority * priority_multiplier * (health_score / 100) * type_factor
            
            available_sources.append({
                "name": source_name,
                "score": score,
                "priority": base_priority,
                "health_score": health_score,
                "status": status
            })
        
        if not available_sources:
            logger.warning("没有可用的数据源")
            return None
        
        # 按评分排序
        available_sources.sort(key=lambda x: x["score"], reverse=True)
        
        selected = available_sources[0]
        logger.info(f"选择数据源: {selected['name']} (评分: {selected['score']:.2f}, 健康分: {selected['health_score']:.1f})")
        
        return selected["name"]
    
    def _get_type_factor(self, source_name: str, data_type: DataType) -> float:
        """获取数据源对特定数据类型的适配因子"""
        # 默认适配因子
        type_factors = {
            DataSource.AKSHARE.value: {
                DataType.REAL_TIME.value: 1.0,
                DataType.HISTORICAL.value: 0.9,
                DataType.FINANCIAL.value: 0.8,
                DataType.SENTIMENT.value: 0.7,
                DataType.FUND_FLOW.value: 0.9
            },
            DataSource.TUSHARE.value: {
                DataType.REAL_TIME.value: 0.7,
                DataType.HISTORICAL.value: 1.0,
                DataType.FINANCIAL.value: 1.0,
                DataType.SENTIMENT.value: 0.6,
                DataType.FUND_FLOW.value: 0.8
            },
            DataSource.BAOSTOCK.value: {
                DataType.REAL_TIME.value: 0.5,
                DataType.HISTORICAL.value: 0.9,
                DataType.FINANCIAL.value: 0.3,
                DataType.SENTIMENT.value: 0.2,
                DataType.FUND_FLOW.value: 0.1
            }
        }
        
        return type_factors.get(source_name, {}).get(data_type.value, 0.5)
    
    def get_stock_data(self, symbol: str, data_type: DataType, **kwargs) -> Optional[Any]:
        """
        获取股票数据 - 主入口方法
        
        Args:
            symbol: 股票代码
            data_type: 数据类型
            **kwargs: 其他参数
            
        Returns:
            数据结果
        """
        # 检查缓存
        cache_key = self._generate_cache_key(symbol, data_type, kwargs)
        cached_data = self._get_from_cache(cache_key)
        
        if cached_data is not None:
            logger.info(f"从缓存获取数据: {symbol} - {data_type.value}")
            return cached_data
        
        # 选择数据源
        selected_source = self.select_data_source(data_type, symbol)
        
        if not selected_source:
            logger.error(f"无法为 {symbol} - {data_type.value} 选择数据源")
            return None
        
        # 执行数据获取
        start_time = time.time()
        success = False
        result = None
        
        try:
            # 使用对抗性技能保护执行
            result = anti_block.execute_with_protection(
                self._fetch_from_source,
                selected_source,
                symbol,
                data_type,
                **kwargs
            )
            
            success = result is not None
            response_time = time.time() - start_time
            
        except Exception as e:
            logger.error(f"从 {selected_source} 获取数据失败: {e}")
            response_time = time.time() - start_time
            success = False
        
        # 记录请求结果
        self.record_request(selected_source, success, response_time)
        
        if success and result is not None:
            # 缓存结果
            self._save_to_cache(cache_key, result)
            
            # 数据指纹校验
            data_hash = self._calculate_data_hash(result)
            logger.info(f"数据获取成功: {symbol} - {data_type.value}, 大小: {len(str(result))} 字节, 指纹: {data_hash[:8]}")
            
            return result
        else:
            # 失败时尝试备用数据源
            logger.warning(f"主数据源 {selected_source} 失败，尝试备用数据源")
            return self._try_backup_sources(symbol, data_type, selected_source, **kwargs)
    
    def _fetch_from_source(self, source_name: str, symbol: str, data_type: DataType, **kwargs) -> Optional[Any]:
        """从指定数据源获取数据"""
        # 这里应该实现具体的数据获取逻辑
        # 由于时间关系，先实现框架，具体实现需要根据实际数据源API
        
        logger.info(f"从 {source_name} 获取数据: {symbol} - {data_type.value}")
        
        # 模拟数据获取
        time.sleep(0.5)  # 模拟网络延迟
        
        # 返回模拟数据
        mock_data = {
            "symbol": symbol,
            "data_type": data_type.value,
            "source": source_name,
            "timestamp": datetime.now().isoformat(),
            "data": f"模拟数据 from {source_name}"
        }
        
        return mock_data
    
    def _try_backup_sources(self, symbol: str, data_type: DataType, failed_source: str, **kwargs) -> Optional[Any]:
        """尝试备用数据源"""
        backup_sources = []
        
        for source_name, source_data in self.data_sources.items():
            if source_name == failed_source:
                continue
            
            config = source_data["config"]
            if not config.get("enabled", False):
                continue
            
            health_info = self.health_scores.get(source_name, {})
            if health_info.get("status") == HealthStatus.OFFLINE:
                continue
            
            backup_sources.append(source_name)
        
        # 按健康分排序
        backup_sources.sort(key=lambda x: self.health_scores.get(x, {}).get("score", 0), reverse=True)
        
        for backup_source in backup_sources:
            logger.info(f"尝试备用数据源: {backup_source}")
            
            try:
                result = self._fetch_from_source(backup_source, symbol, data_type, **kwargs)
                
                if result is not None:
                    # 记录成功
                    self.record_request(backup_source, True, 1.0)
                    
                    # 缓存结果
                    cache_key = self._generate_cache_key(symbol, data_type, kwargs)
                    self._save_to_cache(cache_key, result)
                    
                    logger.info(f"备用数据源 {backup_source} 成功获取数据")
                    return result
                    
            except Exception as e:
                logger.warning(f"备用数据源 {backup_source} 失败: {e}")
                self.record_request(backup_source, False, 1.0)
        
        logger.error(f"所有数据源均失败: {symbol} - {data_type.value}")
        return None
    
    def _generate_cache_key(self, symbol: str, data_type: DataType, params: Dict) -> str:
        """生成缓存键"""
        param_str = json.dumps(params, sort_keys=True)
        key_str = f"{symbol}:{data_type.value}:{param_str}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """从缓存获取数据"""
        if not self.config["cache"]["enabled"]:
            return None
        
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            
            # 检查是否过期
            ttl_minutes = self.config["cache"]["ttl_minutes"]
            cache_time = cache_entry["timestamp"]
            age_minutes = (datetime.now() - cache_time).total_seconds() / 60
            
            if age_minutes <= ttl_minutes:
                logger.debug(f"缓存命中: {cache_key}, 年龄: {age_minutes:.1f}分钟")
                return cache_entry["data"]
            else:
                logger.debug(f"缓存过期: {cache_key}, 年龄: {age_minutes:.1f}分钟")
                del self.cache[cache_key]
        
        return None
    
    def _save_to_cache(self, cache_key: str, data: Any):
        """保存数据到缓存"""
        if not self.config["cache"]["enabled"]:
            return
        
        self.cache[cache_key] = {
            "timestamp": datetime.now(),
            "data": data
        }
        
        # 清理过期缓存
        self._cleanup_cache()
    
    def _cleanup_cache(self):
        """清理缓存"""
        ttl_minutes = self.config["cache"]["ttl_minutes"]
        now = datetime.now()
        
        expired_keys = []
        for key, entry in self.cache.items():
            age_minutes = (now - entry["timestamp"]).total_seconds() / 60
            if age_minutes > ttl_minutes:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.debug(f"清理了 {len(expired_keys)} 个过期缓存")
    
    def _calculate_data_hash(self, data: Any) -> str:
        """计算数据指纹"""
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def get_health_report(self) -> Dict:
        """获取健康报告"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "data_sources": {},
            "overall_health": "healthy",
            "recommendations": []
        }
        
        # 收集各数据源状态
        for source_name, health_info in self.health_scores.items():
            source_data = self.data_sources.get(source_name, {})
            
            report["data_sources"][source_name] = {
                "health_score": health_info["score"],
                "status": health_info["status"].value,
                "trend": health_info["trend"],
                "total_requests": source_data.get("total_requests", 0),
                "success_rate": source_data.get("success_count", 0) / max(1, source_data.get("total_requests", 1)),
                "last_success": source_data.get("last_success"),
                "last_failure": source_data.get("last_failure")
            }
        
        # 计算整体健康状态
        healthy_count = sum(1 for info in report["data_sources"].values() 
                          if info["status"] in ["healthy", "degraded"])
        total_count = len(report["data_sources"])
        
        if total_count == 0:
            report["overall_health"] = "unknown"
        elif healthy_count == total_count:
            report["overall_health"] = "healthy"
        elif healthy_count >= total_count * 0.7:
            report["overall_health"] = "degraded"
        else:
            report["overall_health"] = "unhealthy"
        
        # 生成建议
        for source_name, info in report["data_sources"].items():
            if info["status"] in ["unstable", "failing", "offline"]:
                report["recommendations"].append(
                    f"数据源 {source_name} 状态不佳 ({info['status']})，建议检查网络或切换备用源"
                )
        
        return report
    
    def run_health_check(self):
        """运行健康检查"""
        logger.info("开始健康检查...")
        
        test_symbols = ["000001", "600519", "300750"]  # 测试股票
        
        for source_name in self.data_sources:
            config = self.data_sources[source_name]["config"]
            
            if not config.get("enabled", False):
                continue
            
            # 测试数据获取
            try:
                test_result = self._fetch_from_source(
                    source_name, 
                    test_symbols[0], 
                    DataType.HISTORICAL,
                    start_date="20250101",
                    end_date="20250110"
                )
                
                success = test_result is not None
                self.record_request(source_name, success, 1.0)
                
                if success:
                    logger.info(f"数据源 {source_name} 健康检查通过")
                else:
                    logger.warning(f"数据源 {source_name} 健康检查失败")
                    
            except Exception as e:
                logger.error(f"数据源 {source_name} 健康检查异常: {e}")
                self.record_request(source_name, False, 1.0)
        
        logger.info("健康检查完成")


# 全局实例
data_orchestrator = DataOrchestrator()


if __name__ == "__main__":
    print("=== 数据指挥官测试 ===")
    
    # 创建实例
    orchestrator = DataOrchestrator()
    
    # 运行健康检查
    orchestrator.run_health_check()
    
    # 获取健康报告
    report = orchestrator.get_health_report()
    print(f"整体健康状态: {report['overall_health']}")
    
    for source_name, info in report["data_sources"].items():
        print(f"  {source_name}: 分数={info['health_score']:.1f}, 状态={info['status']}, 成功率={info['success_rate']:.1%}")
    
    # 测试数据获取
    print("\n=== 测试数据获取 ===")
    
    test_cases = [
        ("000001", DataType.HISTORICAL, {"start_date": "20250101", "end_date": "20250110"}),
        ("600519", DataType.REAL_TIME, {}),
        ("300750", DataType.FINANCIAL, {})
    ]
    
    for symbol, data_type, params in test_cases:
        print(f"\n获取 {symbol} 的 {data_type.value} 数据...")
        
        data = orchestrator.get_stock_data(symbol, data_type, **params)
        
        if data:
            print(f"  成功获取数据，来源: {data.get('source', 'unknown')}")
            print(f"  数据指纹: {orchestrator._calculate_data_hash(data)[:8]}")
        else:
            print("  获取数据失败")
    
    print("\n=== 测试完成 ===")