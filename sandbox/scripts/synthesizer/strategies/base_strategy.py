#!/usr/bin/env python3
"""
BaseStrategy - 算法策略基类
所有具体算法策略都应继承此基类
"""

import abc
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
import datetime
import statistics


class BaseStrategy(abc.ABC):
    """策略算法基类"""
    
    def __init__(self, name: str, description: str = ""):
        """
        初始化策略
        
        Args:
            name: 策略名称
            description: 策略描述
        """
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"Strategy.{name}")
        
    @abc.abstractmethod
    def analyze(self, 
                ticker: str,
                history_data: Dict[str, Any],
                analysis_data: Optional[Dict[str, Any]] = None,
                global_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        分析函数 - 必须由子类实现
        
        Args:
            ticker: 标的代码
            history_data: 历史数据 (来自 history_*.json)
            analysis_data: 分析数据 (来自 analysis_*.json，可选)
            global_params: 全局参数配置
            
        Returns:
            Dict包含:
                - hit: bool (是否命中)
                - score: float (得分 0-100)
                - confidence: float (置信度 0-1)
                - signals: List[str] (信号列表)
                - metadata: Dict (元数据)
        """
        pass
    
    @abc.abstractmethod
    def get_required_history_days(self) -> int:
        """
        获取所需历史数据天数
        
        Returns:
            所需的最小历史数据天数
        """
        pass
    
    def calculate_price_deviation_percentile(self, 
                                           current_price: float,
                                           reference_price: float,
                                           historical_deviations: List[float]) -> float:
        """
        计算价格偏离的历史百分位
        
        Args:
            current_price: 当前价格
            reference_price: 参考价格 (如均线)
            historical_deviations: 历史偏离值列表
            
        Returns:
            百分位 (0-1)，表示当前偏离在历史中的位置
        """
        if not historical_deviations:
            return 0.5  # 无历史数据，返回中位数
            
        current_deviation = ((current_price - reference_price) / reference_price) * 100
        
        # 计算当前偏离在历史分布中的百分位
        sorted_deviations = sorted(historical_deviations)
        count_below = sum(1 for d in sorted_deviations if d < current_deviation)
        percentile = count_below / len(sorted_deviations)
        
        return percentile
    
    def calculate_z_score(self, value: float, values: List[float]) -> float:
        """
        计算Z分数 (标准化分数)
        
        Args:
            value: 当前值
            values: 历史值列表
            
        Returns:
            Z分数
        """
        if len(values) < 2:
            return 0.0
            
        mean = statistics.mean(values)
        if len(values) == 1:
            std = 0.0
        else:
            std = statistics.stdev(values)
        
        if std == 0:
            return 0.0
            
        return (value - mean) / std
    
    def get_latest_price(self, history_data: Dict[str, Any]) -> Optional[float]:
        """获取最新价格"""
        if "history" not in history_data or not history_data["history"]:
            return None
            
        latest = history_data["history"][0]  # 历史数据按日期降序排列
        return latest.get("price")
    
    def get_historical_prices(self, history_data: Dict[str, Any], days: int = 250) -> List[float]:
        """获取历史价格序列"""
        if "history" not in history_data:
            return []
            
        prices = []
        for item in history_data["history"][:days]:
            price = item.get("price")
            if price is not None:
                prices.append(price)
                
        return prices
    
    def calculate_moving_average(self, prices: List[float], window: int) -> Optional[float]:
        """计算移动平均线"""
        if len(prices) < window:
            return None
            
        return statistics.mean(prices[:window])
    
    def validate_data_sufficiency(self, history_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        验证数据是否充足
        
        Returns:
            (是否充足, 错误消息)
        """
        if "history" not in history_data:
            return False, "历史数据缺少'history'字段"
            
        if not history_data["history"]:
            return False, "历史数据为空"
            
        required_days = self.get_required_history_days()
        if len(history_data["history"]) < required_days:
            return False, f"历史数据不足，需要{required_days}天，实际{len(history_data['history'])}天"
            
        return True, "数据充足"
    
    def create_result(self, 
                     hit: bool,
                     score: float,
                     confidence: float = 0.5,
                     signals: Optional[List[str]] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        创建标准化结果
        
        Args:
            hit: 是否命中
            score: 得分 (0-100)
            confidence: 置信度 (0-1)
            signals: 信号列表
            metadata: 元数据
            
        Returns:
            标准化结果字典
        """
        result = {
            "hit": hit,
            "score": max(0.0, min(100.0, score)),
            "confidence": max(0.0, min(1.0, confidence)),
            "signals": signals or [],
            "metadata": metadata or {},
            "strategy_name": self.name,
            "analysis_time": datetime.datetime.now().isoformat()
        }
        
        return result