#!/usr/bin/env python3
"""
数据获取模块 - 集成AkShare和Tushare
"""

import pandas as pd
import numpy as np
import akshare as ak
import tushare as ts
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class DataFetcher:
    """数据获取类"""
    
    def __init__(self):
        self.ts_token = None
        self.init_tushare()
    
    def init_tushare(self):
        """初始化Tushare，优先从环境变量，其次从secrets.json"""
        try:
            import os
            import json
            
            # 1. 优先从环境变量获取
            token = os.getenv('TUSHARE_TOKEN', '')
            
            # 2. 如果环境变量没有，从secrets.json获取
            if not token:
                secrets_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                    '_PRIVATE_DATA', 'secrets.json'
                )
                if os.path.exists(secrets_path):
                    try:
                        with open(secrets_path, 'r', encoding='utf-8') as f:
                            secrets = json.load(f)
                            token = secrets.get('TUSHARE_TOKEN', '')
                            if token:
                                logger.info(f"从secrets.json加载Tushare Token (长度:{len(token)})")
                    except Exception as e:
                        logger.warning(f"读取secrets.json失败: {e}")
            
            if token:
                ts.set_token(token)
                self.ts_token = token
                logger.info(f"Tushare初始化成功，Token: {token[:10]}...")
            else:
                logger.warning("未找到TUSHARE_TOKEN，Tushare功能受限")
        except Exception as e:
            logger.error(f"Tushare初始化失败: {e}")
    
    def get_stock_history_akshare(self, ticker, days=60):
        """
        使用AkShare获取股票历史数据
        
        Args:
            ticker: 股票代码 (带后缀，如'000681.SZ')
            days: 需要的历史天数
        """
        try:
            # 确定市场后缀
            if ticker.startswith('6'):
                symbol = ticker + '.SH'
            else:
                symbol = ticker + '.SZ'
            
            # 计算日期范围
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days*2)).strftime('%Y%m%d')  # 多取一些
            
            # 获取日线数据
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date)
            
            if df.empty:
                logger.warning(f"AkShare未返回数据: {ticker}")
                return None
            
            # 处理数据
            df = df.sort_values('日期', ascending=False).reset_index(drop=True)
            df = df.head(days)  # 取最近days天
            
            # 提取价格序列
            prices = df['收盘'].astype(float).tolist()
            dates = df['日期'].tolist()
            
            # 返回格式化数据
            return {
                'ticker': ticker,
                'prices': prices,
                'dates': dates,
                'volume': df['成交量'].astype(float).tolist() if '成交量' in df.columns else [],
                'amount': df['成交额'].astype(float).tolist() if '成交额' in df.columns else []
            }
            
        except Exception as e:
            logger.error(f"AkShare获取数据失败 {ticker}: {e}")
            return None
    
    def get_stock_history_tushare(self, ticker, days=60):
        """
        使用Tushare获取股票历史数据
        """
        if not self.ts_token:
            logger.warning("Tushare未初始化，跳过")
            return None
        
        try:
            import tushare as ts
            
            # 计算日期范围
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days*2)).strftime('%Y%m%d')
            
            # 获取数据
            df = ts.pro_bar(ts_code=ticker, start_date=start_date, end_date=end_date)
            
            if df.empty:
                return None
            
            df = df.sort_values('trade_date', ascending=False).reset_index(drop=True)
            df = df.head(days)
            
            prices = df['close'].astype(float).tolist()
            dates = df['trade_date'].tolist()
            
            return {
                'ticker': ticker,
                'prices': prices,
                'dates': dates,
                'volume': df['vol'].astype(float).tolist() if 'vol' in df.columns else [],
                'amount': df['amount'].astype(float).tolist() if 'amount' in df.columns else []
            }
            
        except Exception as e:
            logger.error(f"Tushare获取数据失败 {ticker}: {e}")
            return None
    
    def get_stock_history(self, ticker, days=60):
        """
        获取股票历史数据，优先使用AkShare
        """
        # 先尝试AkShare
        data = self.get_stock_history_akshare(ticker, days)
        
        if data is None:
            # 回退到Tushare
            data = self.get_stock_history_tushare(ticker, days)
        
        if data is None:
            logger.warning(f"无法获取{ticker}的历史数据，返回模拟数据")
            data = self.get_mock_history(ticker, days)
        
        return data
    
    def get_mock_history(self, ticker, days=60):
        """生成模拟历史数据"""
        import random
        
        base_price = 10.0
        prices = []
        
        for i in range(days):
            change = random.uniform(-0.03, 0.03)
            base_price = base_price * (1 + change)
            prices.append(base_price)
        
        prices.reverse()  # 最新价格在前
        
        return {
            'ticker': ticker,
            'prices': prices,
            'dates': [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days)][::-1],
            'volume': [random.randint(1000000, 5000000) for _ in range(days)],
            'amount': [prices[i] * random.randint(1000000, 5000000) for i in range(days)]
        }
    
    def get_industry_stocks(self, industries):
        """
        获取行业股票列表
        
        Args:
            industries: 行业列表 ['汽车零部件', '机器人', ...]
        """
        try:
            # 获取行业分类 (简化实现)
            # 这里应该调用AkShare的行业分类接口
            # 暂时返回模拟数据
            
            simulated_stocks = []
            
            # 汽车零部件
            if any('汽车' in ind for ind in industries):
                simulated_stocks.extend([
                    {'code': '600741', 'name': '华域汽车', 'industry': '汽车零部件'},
                    {'code': '000338', 'name': '潍柴动力', 'industry': '汽车零部件'},
                    {'code': '601238', 'name': '广汽集团', 'industry': '汽车零部件'},
                    {'code': '000625', 'name': '长安汽车', 'industry': '汽车零部件'},
                    {'code': '600066', 'name': '宇通客车', 'industry': '汽车零部件'},
                ])
            
            # 机器人/低空经济
            if any('机器人' in ind or '低空' in ind for ind in industries):
                simulated_stocks.extend([
                    {'code': '002008', 'name': '大族激光', 'industry': '机器人'},
                    {'code': '300024', 'name': '机器人', 'industry': '机器人'},
                    {'code': '002689', 'name': '远大智能', 'industry': '机器人'},
                    {'code': '300161', 'name': '华中数控', 'industry': '机器人'},
                    {'code': '002527', 'name': '新时达', 'industry': '机器人'},
                ])
            
            return simulated_stocks
            
        except Exception as e:
            logger.error(f"获取行业股票失败: {e}")
            return []
    
    def get_stock_basic_info(self, ticker):
        """获取股票基本信息"""
        try:
            # 使用AkShare获取基本信息
            if ticker.startswith('6'):
                symbol = ticker + '.SH'
            else:
                symbol = ticker + '.SZ'
            
            # 获取股票详情
            stock_info = ak.stock_individual_info_em(symbol=symbol)
            
            if not stock_info.empty:
                info_dict = stock_info.set_index('item')['value'].to_dict()
                return info_dict
            else:
                return {}
                
        except Exception as e:
            logger.error(f"获取股票基本信息失败 {ticker}: {e}")
            return {}


# 全局实例
fetcher = DataFetcher()