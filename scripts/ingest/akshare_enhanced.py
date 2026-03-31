#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKShare增强版 - 集成对抗性设计和数据指挥官
文档编号: AE-AKSHARE-001-V1.0
依据: [2614-044号]首席架构师战略构想
功能: 解决RemoteDisconnected问题，实现工业级重试机制
"""

import akshare as ak
import pandas as pd
import time
import logging
import random
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import json
import hashlib

# 导入数据指挥官和网络加固模块
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from network.proxy_manager import proxy_manager, anti_block
from ingest.data_orchestrator import DataOrchestrator, DataType

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AKShareEnhanced:
    """AKShare增强版 - 工业级数据获取"""
    
    def __init__(self, max_retries: int = 3, use_proxy: bool = True):
        """
        初始化AKShare增强版
        
        Args:
            max_retries: 最大重试次数
            use_proxy: 是否使用代理
        """
        self.max_retries = max_retries
        self.use_proxy = use_proxy
        self.data_orchestrator = DataOrchestrator()
        
        # 请求统计
        self.request_stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "avg_response_time": 0
        }
        
        # 缓存配置
        self.cache_enabled = True
        self.cache_ttl = 300  # 5分钟
        
        logger.info(f"AKShare增强版初始化完成，最大重试: {max_retries}, 使用代理: {use_proxy}")
    
    def _execute_with_retry(self, func, *args, **kwargs) -> Optional[Any]:
        """
        带重试机制的执行函数
        
        Args:
            func: 要执行的AKShare函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            执行结果或None
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                
                # 执行前延迟 - 模拟人类行为
                if attempt > 0:
                    delay = 2 ** attempt + random.uniform(0.5, 1.5)
                    logger.debug(f"重试 {attempt+1}/{self.max_retries}，延迟 {delay:.2f}秒")
                    time.sleep(delay)
                
                # 使用对抗性技能保护执行
                result = anti_block.execute_with_protection(func, *args, **kwargs)
                
                response_time = time.time() - start_time
                
                # 更新统计
                self.request_stats["total"] += 1
                self.request_stats["success"] += 1
                self.request_stats["avg_response_time"] = (
                    self.request_stats["avg_response_time"] * (self.request_stats["success"] - 1) + response_time
                ) / self.request_stats["success"]
                
                logger.info(f"请求成功 (尝试 {attempt+1}): 响应时间 {response_time:.2f}秒")
                return result
                
            except Exception as e:
                last_error = e
                response_time = time.time() - start_time if 'start_time' in locals() else 0
                
                # 更新统计
                self.request_stats["total"] += 1
                self.request_stats["failed"] += 1
                
                error_type = type(e).__name__
                error_msg = str(e)
                
                logger.warning(f"请求失败 (尝试 {attempt+1}/{self.max_retries}): {error_type}: {error_msg}")
                
                # 检查是否为网络错误
                if self._is_network_error(error_type, error_msg):
                    logger.warning("检测到网络错误，将尝试使用代理")
                    # TODO: 实现代理切换逻辑
                
                # 如果是最后一次尝试，记录详细错误
                if attempt == self.max_retries - 1:
                    logger.error(f"所有重试均失败: {error_type}: {error_msg}")
        
        return None
    
    def _is_network_error(self, error_type: str, error_msg: str) -> bool:
        """判断是否为网络错误"""
        network_error_keywords = [
            "Connection",
            "Timeout",
            "RemoteDisconnected",
            "网络",
            "socket",
            "HTTP",
            "SSL"
        ]
        
        error_str = f"{error_type} {error_msg}".lower()
        return any(keyword.lower() in error_str for keyword in network_error_keywords)
    
    def _generate_cache_key(self, func_name: str, *args, **kwargs) -> str:
        """生成缓存键"""
        args_str = json.dumps(args, sort_keys=True, default=str)
        kwargs_str = json.dumps(kwargs, sort_keys=True, default=str)
        key_str = f"{func_name}:{args_str}:{kwargs_str}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get_stock_spot(self, symbol: str = None) -> Optional[pd.DataFrame]:
        """
        获取股票实时行情（增强版）
        
        Args:
            symbol: 股票代码或板块名称，None表示获取全部
            
        Returns:
            实时行情DataFrame
        """
        cache_key = self._generate_cache_key("stock_zh_a_spot_em", symbol)
        
        # 检查缓存
        if self.cache_enabled:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                logger.info(f"从缓存获取实时行情: {symbol or '全部'}")
                return cached
        
        logger.info(f"获取实时行情: {symbol or '全部'}")
        
        # 注意：stock_zh_a_spot_em() 不接受参数
        result = self._execute_with_retry(ak.stock_zh_a_spot_em)
        
        # 如果指定了symbol，进行过滤
        if result is not None and symbol:
            # 尝试根据symbol过滤数据
            if symbol == "北证A股":
                # 北证A股有特殊处理
                result = result[result['名称'].str.contains('北证', na=False)]
            else:
                # 其他情况，尝试匹配代码或名称
                mask = (result['代码'] == symbol) | (result['名称'].str.contains(symbol, na=False))
                result = result[mask]
        
        if result is not None and self.cache_enabled:
            self._save_to_cache(cache_key, result)
        
        return result
    
    def get_stock_hist(self, symbol: str, period: str = "daily", 
                      start_date: str = None, end_date: str = None,
                      adjust: str = "qfq") -> Optional[pd.DataFrame]:
        """
        获取股票历史K线数据（增强版）
        
        Args:
            symbol: 股票代码
            period: 周期 (daily, weekly, monthly)
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            adjust: 复权类型 (qfq: 前复权, hfq: 后复权, 空: 不复权)
            
        Returns:
            历史K线DataFrame
        """
        # 设置默认日期
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
        
        if start_date is None:
            # 默认获取最近30天数据
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
        
        cache_key = self._generate_cache_key(
            "stock_zh_a_hist", 
            symbol, period, start_date, end_date, adjust
        )
        
        # 检查缓存
        if self.cache_enabled:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                logger.info(f"从缓存获取历史K线: {symbol} {period} {start_date}-{end_date}")
                return cached
        
        logger.info(f"获取历史K线: {symbol} {period} {start_date}-{end_date}")
        
        result = self._execute_with_retry(
            ak.stock_zh_a_hist,
            symbol=symbol,
            period=period,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust
        )
        
        if result is not None and self.cache_enabled:
            self._save_to_cache(cache_key, result)
        
        return result
    
    def get_financial_data(self, symbol: str, indicator: str = "按报告期") -> Optional[pd.DataFrame]:
        """
        获取财务数据（增强版）
        
        Args:
            symbol: 股票代码
            indicator: 指标类型
            
        Returns:
            财务数据DataFrame
        """
        cache_key = self._generate_cache_key("stock_financial_abstract_ths", symbol, indicator)
        
        # 检查缓存
        if self.cache_enabled:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                logger.info(f"从缓存获取财务数据: {symbol} {indicator}")
                return cached
        
        logger.info(f"获取财务数据: {symbol} {indicator}")
        
        result = self._execute_with_retry(
            ak.stock_financial_abstract_ths,
            symbol=symbol,
            indicator=indicator
        )
        
        if result is not None and self.cache_enabled:
            self._save_to_cache(cache_key, result)
        
        return result
    
    def get_board_industry(self) -> Optional[pd.DataFrame]:
        """
        获取行业板块行情（增强版）
        
        Returns:
            行业板块DataFrame
        """
        cache_key = self._generate_cache_key("stock_board_industry_name_em")
        
        # 检查缓存
        if self.cache_enabled:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                logger.info("从缓存获取行业板块行情")
                return cached
        
        logger.info("获取行业板块行情")
        
        result = self._execute_with_retry(ak.stock_board_industry_name_em)
        
        if result is not None and self.cache_enabled:
            self._save_to_cache(cache_key, result)
        
        return result
    
    def get_fund_flow(self, stock: str, market: str = "sh", 
                     symbol: str = None) -> Optional[pd.DataFrame]:
        """
        获取资金流向（增强版）
        
        Args:
            stock: 股票代码
            market: 市场 (sh, sz)
            symbol: 资金类型
            
        Returns:
            资金流向DataFrame
        """
        cache_key = self._generate_cache_key("stock_individual_fund_flow", stock, market, symbol)
        
        # 检查缓存
        if self.cache_enabled:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                logger.info(f"从缓存获取资金流向: {stock} {market}")
                return cached
        
        logger.info(f"获取资金流向: {stock} {market}")
        
        result = self._execute_with_retry(
            ak.stock_individual_fund_flow,
            stock=stock,
            market=market,
            symbol=symbol
        )
        
        if result is not None and self.cache_enabled:
            self._save_to_cache(cache_key, result)
        
        return result
    
    def get_lhb_detail(self, date: str = None) -> Optional[pd.DataFrame]:
        """
        获取龙虎榜详情（增强版）
        
        Args:
            date: 日期 (YYYYMMDD)，None表示最新
            
        Returns:
            龙虎榜DataFrame
        """
        if date is None:
            date = datetime.now().strftime("%Y%m%d")
        
        cache_key = self._generate_cache_key("stock_lhb_detail_em", date)
        
        # 检查缓存
        if self.cache_enabled:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                logger.info(f"从缓存获取龙虎榜: {date}")
                return cached
        
        logger.info(f"获取龙虎榜: {date}")
        
        result = self._execute_with_retry(ak.stock_lhb_detail_em, date=date)
        
        if result is not None and self.cache_enabled:
            self._save_to_cache(cache_key, result)
        
        return result
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """从缓存获取数据（简化版）"""
        # TODO: 实现完整的缓存系统
        return None
    
    def _save_to_cache(self, cache_key: str, data: Any):
        """保存数据到缓存（简化版）"""
        # TODO: 实现完整的缓存系统
        pass
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        success_rate = 0
        if self.request_stats["total"] > 0:
            success_rate = self.request_stats["success"] / self.request_stats["total"]
        
        return {
            "total_requests": self.request_stats["total"],
            "successful_requests": self.request_stats["success"],
            "failed_requests": self.request_stats["failed"],
            "success_rate": success_rate,
            "avg_response_time": self.request_stats["avg_response_time"],
            "cache_enabled": self.cache_enabled,
            "max_retries": self.max_retries
        }
    
    def test_connectivity(self) -> bool:
        """测试连通性"""
        logger.info("测试AKShare连通性...")
        
        test_cases = [
            ("获取实时行情样本", lambda: self.get_stock_spot("北证A股")),
            ("获取历史K线样本", lambda: self.get_stock_hist("000001", "daily", "20250101", "20250110")),
            ("获取行业板块", lambda: self.get_board_industry())
        ]
        
        results = []
        
        for test_name, test_func in test_cases:
            try:
                logger.info(f"执行测试: {test_name}")
                result = test_func()
                
                if result is not None:
                    logger.info(f"测试通过: {test_name}, 数据行数: {len(result)}")
                    results.append(True)
                else:
                    logger.warning(f"测试失败: {test_name}, 返回None")
                    results.append(False)
                    
            except Exception as e:
                logger.error(f"测试异常: {test_name}, 错误: {e}")
                results.append(False)
        
        success_count = sum(results)
        total_count = len(results)
        
        logger.info(f"连通性测试完成: {success_count}/{total_count} 通过")
        return success_count >= total_count * 0.5  # 至少50%通过


# 全局实例
akshare_enhanced = AKShareEnhanced()


if __name__ == "__main__":
    print("=== AKShare增强版测试 ===")
    
    # 创建实例
    akshare = AKShareEnhanced(max_retries=3, use_proxy=True)
    
    # 测试连通性
    if akshare.test_connectivity():
        print("✅ 连通性测试通过")
    else:
        print("⚠️ 连通性测试部分失败")
    
    # 测试各功能
    print("\n=== 测试各功能 ===")
    
    # 1. 测试实时行情
    print("1. 测试实时行情...")
    spot_data = akshare.get_stock_spot()
    if spot_data is not None:
        print(f"  成功获取 {len(spot_data)} 只股票实时行情")
        print(f"  数据列: {list(spot_data.columns[:5])}...")
    else:
        print("  获取实时行情失败")
    
    # 2. 测试历史K线
    print("\n2. 测试历史K线...")
    hist_data = akshare.get_stock_hist("000001", "daily", "20250101", "20250115")
    if hist_data is not None:
        print(f"  成功获取平安银行 {len(hist_data)} 条日K线")
        print(f"  最新数据:")
        print(hist_data[['日期', '开盘', '收盘', '最高', '最低']].tail(3))
    else:
        print("  获取历史K线失败")
    
    # 3. 测试行业板块
    print("\n3. 测试行业板块...")
    industry_data = akshare.get_board_industry()
    if industry_data is not None:
        print(f"  成功获取 {len(industry_data)} 个行业板块")
        print(f"  热门板块:")
        print(industry_data[['板块名称', '涨跌幅', '总市值']].head(3))
    else:
        print("  获取行业板块失败")
    
    # 4. 测试资金流向
    print("\n4. 测试资金流向...")
    fund_flow = akshare.get_fund_flow("000001", "sz")
    if fund_flow is not None:
        print(f"  成功获取资金流向数据")
        print(f"  数据形状: {fund_flow.shape}")
    else:
        print("  获取资金流向失败")
    
    # 5. 测试龙虎榜
    print("\n5. 测试龙虎榜...")
    lhb_data = akshare.get_lhb_detail("20250110")
    if lhb_data is not None:
        print(f"  成功获取龙虎榜数据")
        print(f"  上榜股票数: {len(lhb_data)}")
    else:
        print("  获取龙虎榜失败")
    
    # 获取统计信息
    print("\n=== 统计信息 ===")
    stats = akshare.get_stats()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.3f}")
        else:
            print(f"  {key}: {value}")
    
    print("\n=== 测试完成 ===")