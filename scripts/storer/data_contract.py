#!/usr/bin/env python3
"""
数据契约模块 - 标准数据访问层
为评委层提供统一、快速、可靠的数据访问接口
符合架构师Gemini"200ms内返回纯净张量"要求
"""

import os
import sys
import json
import time
import datetime
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, asdict
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DataContractConfig:
    """数据契约配置"""
    response_time_limit_ms: int = 200  # 响应时间限制 (毫秒)
    data_accuracy_required: float = 0.99  # 数据准确率要求
    max_retry_count: int = 3  # 最大重试次数
    cache_enabled: bool = True  # 缓存启用
    cache_ttl_seconds: int = 300  # 缓存TTL (秒)

@dataclass
class FeatureRequest:
    """特征请求"""
    ticker: str  # 标的代码
    factor_name: str  # 因子名称
    start_date: Optional[str] = None  # 开始日期 (YYYY-MM-DD)
    end_date: Optional[str] = None  # 结束日期 (YYYY-MM-DD)
    frequency: str = "daily"  # 频率: daily, weekly, monthly
    require_benchmark: bool = False  # 是否需要基准数据

@dataclass
class FeatureResponse:
    """特征响应"""
    success: bool  # 是否成功
    data: Optional[np.ndarray] = None  # 数据张量
    metadata: Optional[Dict] = None  # 元数据
    error_code: str = ""  # 错误代码
    error_message: str = ""  # 错误信息
    response_time_ms: float = 0.0  # 响应时间 (毫秒)
    data_source: str = ""  # 数据源
    quality_score: float = 1.0  # 数据质量评分 (0-1)

class DataContract:
    """数据契约主类"""
    
    # 因子到数据源的映射
    FACTOR_SOURCE_MAPPING = {
        # 价格类因子
        "price": "tushare_daily",
        "volume": "tushare_daily",
        "high": "tushare_daily",
        "low": "tushare_daily",
        "close": "tushare_daily",
        "open": "tushare_daily",
        
        # 技术指标因子
        "ma5": "tushare_technical",
        "ma20": "tushare_technical",
        "ma60": "tushare_technical",
        "rsi": "tushare_technical",
        "macd": "tushare_technical",
        "boll": "tushare_technical",
        "kdj": "tushare_technical",
        
        # 财务因子
        "pe": "tushare_financial",
        "pb": "tushare_financial",
        "roe": "tushare_financial",
        "dividend_yield": "tushare_financial",
        "revenue_growth": "tushare_financial",
        
        # 宏观因子
        "cpi": "macro_data",
        "ppi": "macro_data",
        "m2": "macro_data",
        "interest_rate": "macro_data",
        "exchange_rate": "macro_data",
        
        # 市场情绪因子
        "turnover_rate": "market_sentiment",
        "market_cap": "market_sentiment",
        "advance_decline": "market_sentiment",
        "volatility": "market_sentiment",
        
        # G12-G15超级理论家专用因子
        "sector_capital_flow": "capital_flow",  # G12 能量潮汐
        "policy_semantic_score": "policy_analysis",  # G13 政策语义向量
        "option_iv_spread": "derivatives",  # G14 波动率挤压2.0
        "cnh_a50_correlation": "global_markets",  # G15 跨市场关联
    }
    
    # 数据源优先级 (从上到下尝试)
    SOURCE_PRIORITY = [
        "tushare_daily",
        "tushare_technical",
        "tushare_financial",
        "macro_data",
        "market_sentiment",
        "capital_flow",
        "policy_analysis",
        "derivatives",
        "global_markets",
        "fallback_cache"
    ]
    
    def __init__(self, config: Optional[DataContractConfig] = None):
        """
        初始化数据契约
        
        参数:
            config: 数据契约配置，如果为None则使用默认配置
        """
        self.config = config or DataContractConfig()
        self.cache = {}  # 简单内存缓存
        self.cache_timestamps = {}
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time_ms": 0.0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        # 初始化数据源适配器
        self.adapters = self._initialize_adapters()
        
        logger.info(f"✅ 数据契约初始化完成")
        logger.info(f"   响应时间限制: {self.config.response_time_limit_ms}ms")
        logger.info(f"   数据准确率要求: {self.config.data_accuracy_required * 100}%")
    
    def _initialize_adapters(self) -> Dict[str, Any]:
        """初始化数据源适配器"""
        adapters = {}
        
        # 这里应该初始化实际的数据源适配器
        # 暂时使用占位符
        for source in self.SOURCE_PRIORITY:
            adapters[source] = {
                "available": True,
                "last_check": datetime.datetime.now(),
                "error_count": 0
            }
        
        return adapters
    
    def get_feature(self, request: FeatureRequest) -> FeatureResponse:
        """
        获取特征数据 (核心接口)
        
        参数:
            request: 特征请求
            
        返回:
            FeatureResponse: 特征响应
        """
        start_time = time.time()
        self.stats["total_requests"] += 1
        
        # 检查缓存
        cache_key = self._generate_cache_key(request)
        if self.config.cache_enabled and self._check_cache(cache_key):
            cached_data = self.cache[cache_key]
            self.stats["cache_hits"] += 1
            
            response_time = (time.time() - start_time) * 1000
            response = FeatureResponse(
                success=True,
                data=cached_data["data"],
                metadata=cached_data["metadata"],
                response_time_ms=response_time,
                data_source="cache",
                quality_score=0.95  # 缓存数据质量稍低
            )
            
            self.stats["successful_requests"] += 1
            self._update_stats(response_time)
            return response
        
        self.stats["cache_misses"] += 1
        
        try:
            # 确定数据源
            data_source = self._determine_data_source(request.factor_name)
            
            # 获取数据
            data_result = self._fetch_from_source(data_source, request)
            
            if data_result["success"]:
                # 数据验证
                validation_result = self._validate_data(data_result["data"], request)
                
                if validation_result["valid"]:
                    # 转换为张量
                    tensor_data = self._convert_to_tensor(data_result["data"])
                    
                    # 缓存数据
                    if self.config.cache_enabled:
                        self._cache_data(cache_key, tensor_data, data_result["metadata"])
                    
                    response_time = (time.time() - start_time) * 1000
                    
                    # 检查响应时间
                    if response_time > self.config.response_time_limit_ms:
                        logger.warning(f"⚠️  响应时间超限: {response_time:.1f}ms > {self.config.response_time_limit_ms}ms")
                    
                    response = FeatureResponse(
                        success=True,
                        data=tensor_data,
                        metadata=data_result["metadata"],
                        response_time_ms=response_time,
                        data_source=data_source,
                        quality_score=validation_result["quality_score"]
                    )
                    
                    self.stats["successful_requests"] += 1
                    
                else:
                    # 数据验证失败
                    response = FeatureResponse(
                        success=False,
                        error_code="DATA_VALIDATION_FAILED",
                        error_message=f"数据验证失败: {validation_result['reason']}",
                        response_time_ms=(time.time() - start_time) * 1000,
                        data_source=data_source,
                        quality_score=validation_result["quality_score"]
                    )
                    self.stats["failed_requests"] += 1
                    
            else:
                # 数据获取失败
                response = FeatureResponse(
                    success=False,
                    error_code="DATA_FETCH_FAILED",
                    error_message=f"数据获取失败: {data_result['error']}",
                    response_time_ms=(time.time() - start_time) * 1000,
                    data_source=data_source
                )
                self.stats["failed_requests"] += 1
                
        except Exception as e:
            # 异常情况
            response_time = (time.time() - start_time) * 1000
            response = FeatureResponse(
                success=False,
                error_code="DATA_LAYER_FAILURE",
                error_message=f"数据层异常: {str(e)}",
                response_time_ms=response_time,
                data_source="unknown"
            )
            self.stats["failed_requests"] += 1
            logger.error(f"❌ 数据契约异常: {e}", exc_info=True)
        
        self._update_stats(response.response_time_ms)
        return response
    
    def _generate_cache_key(self, request: FeatureRequest) -> str:
        """生成缓存键"""
        key_parts = [
            request.ticker,
            request.factor_name,
            request.start_date or "all",
            request.end_date or "now",
            request.frequency
        ]
        return ":".join(key_parts)
    
    def _check_cache(self, cache_key: str) -> bool:
        """检查缓存"""
        if cache_key not in self.cache:
            return False
        
        cache_age = time.time() - self.cache_timestamps[cache_key]
        if cache_age > self.config.cache_ttl_seconds:
            # 缓存过期
            del self.cache[cache_key]
            del self.cache_timestamps[cache_key]
            return False
        
        return True
    
    def _cache_data(self, cache_key: str, data: np.ndarray, metadata: Dict):
        """缓存数据"""
        self.cache[cache_key] = {
            "data": data,
            "metadata": metadata,
            "timestamp": datetime.datetime.now().isoformat()
        }
        self.cache_timestamps[cache_key] = time.time()
    
    def _determine_data_source(self, factor_name: str) -> str:
        """确定数据源"""
        # 查找映射
        for key in self.FACTOR_SOURCE_MAPPING:
            if key in factor_name.lower():
                return self.FACTOR_SOURCE_MAPPING[key]
        
        # 默认返回tushare_daily
        return "tushare_daily"
    
    def _fetch_from_source(self, data_source: str, request: FeatureRequest) -> Dict:
        """从数据源获取数据"""
        # 这里应该实现实际的数据获取逻辑
        # 目前使用模拟数据
        
        if data_source == "tushare_daily":
            # 模拟日线数据
            dates = pd.date_range(end=datetime.datetime.now(), periods=100, freq='D')
            prices = np.random.normal(100, 10, 100).cumsum()  # 随机游走
            volumes = np.random.randint(1000000, 10000000, 100)
            
            data = {
                "dates": dates,
                "values": prices if "price" in request.factor_name else volumes,
                "ticker": request.ticker,
                "factor": request.factor_name
            }
            
            return {
                "success": True,
                "data": data,
                "metadata": {
                    "source": "tushare_daily",
                    "count": 100,
                    "date_range": f"{dates[0].date()} to {dates[-1].date()}",
                    "quality": "simulated"
                },
                "error": None
            }
        
        elif data_source in ["capital_flow", "policy_analysis", "derivatives", "global_markets"]:
            # G12-G15专用数据源 - 返回空数据但标记为成功
            # 实际实现时需要集成相应数据源
            return {
                "success": True,
                "data": {"ticker": request.ticker, "factor": request.factor_name, "values": []},
                "metadata": {
                    "source": data_source,
                    "count": 0,
                    "quality": "not_implemented",
                    "warning": f"数据源 {data_source} 尚未实现，返回空数据"
                },
                "error": None
            }
        
        else:
            # 其他数据源失败
            return {
                "success": False,
                "data": None,
                "metadata": None,
                "error": f"数据源 {data_source} 不可用"
            }
    
    def _validate_data(self, data: Any, request: FeatureRequest) -> Dict:
        """验证数据质量"""
        if data is None:
            return {"valid": False, "reason": "数据为空", "quality_score": 0.0}
        
        # 检查数据完整性
        if isinstance(data, dict) and "values" in data:
            values = data["values"]
            if len(values) == 0:
                return {"valid": False, "reason": "数据长度为零", "quality_score": 0.0}
            
            # 检查NaN值
            if hasattr(values, '__iter__'):
                nan_count = sum(1 for v in values if pd.isna(v))
                if nan_count > 0:
                    quality = 1.0 - (nan_count / len(values))
                    return {"valid": True, "reason": f"包含{nan_count}个NaN值", "quality_score": quality}
            
            return {"valid": True, "reason": "数据验证通过", "quality_score": 1.0}
        
        return {"valid": False, "reason": "数据格式不正确", "quality_score": 0.0}
    
    def _convert_to_tensor(self, data: Any) -> np.ndarray:
        """转换为张量"""
        if isinstance(data, dict) and "values" in data:
            values = data["values"]
            if hasattr(values, '__iter__'):
                return np.array(values, dtype=np.float32)
        
        # 默认返回空数组
        return np.array([], dtype=np.float32)
    
    def _update_stats(self, response_time_ms: float):
        """更新统计信息"""
        total_successful = self.stats["successful_requests"]
        current_avg = self.stats["avg_response_time_ms"]
        
        if total_successful > 0:
            self.stats["avg_response_time_ms"] = (
                (current_avg * (total_successful - 1) + response_time_ms) / total_successful
            )
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        success_rate = 0
        if self.stats["total_requests"] > 0:
            success_rate = self.stats["successful_requests"] / self.stats["total_requests"]
        
        cache_hit_rate = 0
        total_cache_attempts = self.stats["cache_hits"] + self.stats["cache_misses"]
        if total_cache_attempts > 0:
            cache_hit_rate = self.stats["cache_hits"] / total_cache_attempts
        
        return {
            **self.stats,
            "success_rate": success_rate,
            "cache_hit_rate": cache_hit_rate,
            "config": asdict(self.config),
            "timestamp": datetime.datetime.now().isoformat()
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time_ms": 0.0,
            "cache_hits": 0,
            "cache_misses": 0
        }

# 全局数据契约实例
_global_data_contract = None

def get_data_contract(config: Optional[DataContractConfig] = None) -> DataContract:
    """获取全局数据契约实例"""
    global _global_data_contract
    if _global_data_contract is None:
        _global_data_contract = DataContract(config)
    return _global_data_contract

def get_feature(ticker: str, factor_name: str, **kwargs) -> FeatureResponse:
    """
    便捷函数：获取特征数据
    
    参数:
        ticker: 标的代码
        factor_name: 因子名称
        **kwargs: 其他参数传递给FeatureRequest
        
    返回:
        FeatureResponse: 特征响应
    """
    request = FeatureRequest(ticker=ticker, factor_name=factor_name, **kwargs)
    contract = get_data_contract()
    return contract.get_feature(request)

# 测试函数
def test_data_contract():
    """测试数据契约"""
    print("🧪 测试数据契约...")
    
    contract = DataContract()
    
    # 测试价格数据
    request = FeatureRequest(
        ticker="000001",
        factor_name="close",
        start_date="2026-01-01",
        end_date="2026-04-08"
    )
    
    response = contract.get_feature(request)
    
    print(f"   请求: {request.ticker} - {request.factor_name}")
    print(f"   成功: {response.success}")
    print(f"   响应时间: {response.response_time_ms:.1f}ms")
    print(f"   数据源: {response.data_source}")
    print(f"   质量评分: {response.quality_score:.2f}")
    
    if response.success and response.data is not None:
        print(f"   数据形状: {response.data.shape}")
        print(f"   数据示例: {response.data[:5] if len(response.data) > 5 else response.data}")
    
    # 测试统计信息
    stats = contract.get_stats()
    print(f"\n📊 统计信息:")
    print(f"   总请求: {stats['total_requests']}")
    print(f"   成功率: {stats['success_rate']:.2%}")
    print(f"   平均响应时间: {stats['avg_response_time_ms']:.1f}ms")
    print(f"   缓存命中率: {stats['cache_hit_rate']:.2%}")
    
    return response.success

if __name__ == "__main__":
    success = test_data_contract()
    if success:
        print("\n✅ 数据契约测试通过")
    else:
        print("\n❌ 数据契约测试失败")