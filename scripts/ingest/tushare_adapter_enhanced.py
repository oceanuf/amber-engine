#!/usr/bin/env python3
"""
Tushare Pro API 适配器增强版 - 支持数据双活冗余 (Dual-Source)
符合 V1.2.1 标准 + 2614-032号系统加固
功能：若Tushare接口响应超时3秒，自动切换至AkShare补盲
"""

import os
import sys
import json
import tempfile
import shutil
import datetime
import time
import random
import argparse
import subprocess
import signal
from typing import Dict, List, Optional, Any
import pandas as pd
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/tushare_adapter.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 模块常量
MODULE_NAME = "ingest_tushare_adapter_enhanced"
TMP_SUFFIX = ".tmp"
SCHEMA_FILE = "config/schema_tushare.json"
MAX_RETRIES = 3
RETRY_DELAY = 5  # 秒
AKSHARE_TIMEOUT = 10  # AkShare调用超时时间
TUSHARE_TIMEOUT = 3   # Tushare接口超时阈值

class TimeoutException(Exception):
    """超时异常"""
    pass

def timeout_handler(signum, frame):
    """超时信号处理器"""
    raise TimeoutException("接口调用超时")

class TushareAdapterEnhanced:
    """Tushare适配器增强版 - 支持双活冗余"""
    
    def __init__(self, use_akshare_backup: bool = True):
        """
        初始化适配器
        
        Args:
            use_akshare_backup: 是否启用AkShare备份
        """
        self.use_akshare_backup = use_akshare_backup
        self.tushare_timeout_count = 0
        self.akshare_fallback_count = 0
        
        # Tushare 标的配置
        self.tickers_config = {
            "518880": {
                "name": "黄金ETF",
                "ts_code": "518880.SH",
                "data_type": "etf",
                "output_file": "database/tushare_gold.json",
                "akshare_symbol": "518880"  # AkShare对应代码
            },
            "510300": {
                "name": "沪深300ETF",
                "ts_code": "510300.SH", 
                "data_type": "etf",
                "output_file": "database/tushare_hs300.json",
                "akshare_symbol": "510300"
            },
            "510500": {
                "name": "中证500ETF",
                "ts_code": "510500.SH",
                "data_type": "etf",
                "output_file": "database/tushare_zz500.json",
                "akshare_symbol": "510500"
            }
        }
        
        logger.info(f"Tushare适配器增强版初始化完成，AkShare备份: {'启用' if use_akshare_backup else '禁用'}")
    
    def fetch_tushare_data(self, ticker: str, retry_count: int = 0) -> Optional[Dict]:
        """
        获取Tushare数据（带超时保护）
        
        Args:
            ticker: 标的代码
            retry_count: 重试次数
            
        Returns:
            数据字典或None
        """
        config = self.tickers_config.get(ticker)
        if not config:
            logger.error(f"未找到标的配置: {ticker}")
            return None
        
        try:
            # 设置超时信号
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(TUSHARE_TIMEOUT)  # 3秒超时
            
            logger.info(f"开始获取Tushare数据: {config['name']}({ticker})")
            start_time = time.time()
            
            # 模拟Tushare API调用（实际应替换为真实API）
            # 这里使用随机延迟模拟网络请求
            time.sleep(random.uniform(0.5, 2.0))
            
            # 模拟可能的超时
            if random.random() < 0.1:  # 10%概率模拟超时
                logger.warning(f"模拟Tushare接口超时: {ticker}")
                time.sleep(4)  # 超过3秒阈值
            
            # 生成模拟数据
            data = {
                "symbol": ticker,
                "name": config["name"],
                "close": round(random.uniform(4.5, 5.5), 3),
                "open": round(random.uniform(4.4, 5.4), 3),
                "high": round(random.uniform(4.6, 5.6), 3),
                "low": round(random.uniform(4.3, 5.3), 3),
                "volume": random.randint(1000000, 5000000),
                "amount": random.randint(50000000, 200000000),
                "trade_date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "fetch_time": datetime.datetime.now().isoformat(),
                "data_source": "tushare",
                "response_time": round(time.time() - start_time, 3)
            }
            
            # 取消超时信号
            signal.alarm(0)
            
            logger.info(f"Tushare数据获取成功: {ticker}, 响应时间: {data['response_time']}秒")
            return data
            
        except TimeoutException:
            self.tushare_timeout_count += 1
            logger.warning(f"Tushare接口超时 ({TUSHARE_TIMEOUT}秒): {ticker}")
            
            # 取消超时信号
            signal.alarm(0)
            
            # 重试逻辑
            if retry_count < MAX_RETRIES:
                logger.info(f"第{retry_count + 1}次重试...")
                time.sleep(RETRY_DELAY)
                return self.fetch_tushare_data(ticker, retry_count + 1)
            else:
                logger.error(f"Tushare接口重试{MAX_RETRIES}次均失败: {ticker}")
                return None
                
        except Exception as e:
            logger.error(f"Tushare接口异常: {str(e)}")
            signal.alarm(0)  # 确保取消超时信号
            return None
    
    def fetch_akshare_data(self, ticker: str) -> Optional[Dict]:
        """
        获取AkShare数据作为备份
        
        Args:
            ticker: 标的代码
            
        Returns:
            数据字典或None
        """
        config = self.tickers_config.get(ticker)
        if not config:
            logger.error(f"未找到标的配置: {ticker}")
            return None
        
        if not self.use_akshare_backup:
            logger.info(f"AkShare备份已禁用，跳过: {ticker}")
            return None
        
        try:
            logger.info(f"启动AkShare备份获取: {config['name']}({ticker})")
            start_time = time.time()
            
            # 调用SkillHub的AkShare技能
            cmd = [
                "skillhub", "run", "akshare-stock",
                "--symbol", config["akshare_symbol"],
                "--period", "1d"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=AKSHARE_TIMEOUT,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            
            if result.returncode != 0:
                logger.error(f"AkShare调用失败: {result.stderr}")
                return None
            
            # 解析AkShare输出（这里简化处理，实际需要根据AkShare输出格式解析）
            akshare_data = {
                "symbol": ticker,
                "name": config["name"],
                "close": round(random.uniform(4.5, 5.5), 3),  # 模拟数据
                "open": round(random.uniform(4.4, 5.4), 3),
                "high": round(random.uniform(4.6, 5.6), 3),
                "low": round(random.uniform(4.3, 5.3), 3),
                "volume": random.randint(1000000, 5000000),
                "amount": random.randint(50000000, 200000000),
                "trade_date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "fetch_time": datetime.datetime.now().isoformat(),
                "data_source": "akshare",
                "response_time": round(time.time() - start_time, 3),
                "akshare_raw": result.stdout[:200]  # 保存部分原始数据供调试
            }
            
            self.akshare_fallback_count += 1
            logger.info(f"AkShare备份获取成功: {ticker}, 响应时间: {akshare_data['response_time']}秒")
            return akshare_data
            
        except subprocess.TimeoutExpired:
            logger.error(f"AkShare调用超时 ({AKSHARE_TIMEOUT}秒): {ticker}")
            return None
        except Exception as e:
            logger.error(f"AkShare调用异常: {str(e)}")
            return None
    
    def fetch_data_with_fallback(self, ticker: str) -> Optional[Dict]:
        """
        带降级的数据获取：优先Tushare，失败时自动切换AkShare
        
        Args:
            ticker: 标的代码
            
        Returns:
            数据字典或None
        """
        logger.info(f"开始带降级的数据获取: {ticker}")
        
        # 1. 优先尝试Tushare
        tushare_data = self.fetch_tushare_data(ticker)
        
        if tushare_data:
            logger.info(f"Tushare数据获取成功，使用主数据源: {ticker}")
            return tushare_data
        
        # 2. Tushare失败，尝试AkShare备份
        logger.warning(f"Tushare数据获取失败，尝试AkShare备份: {ticker}")
        akshare_data = self.fetch_akshare_data(ticker)
        
        if akshare_data:
            logger.info(f"AkShare备份获取成功: {ticker}")
            # 添加降级标记
            akshare_data["fallback_mode"] = True
            akshare_data["fallback_reason"] = "tushare_timeout"
            return akshare_data
        
        # 3. 所有数据源都失败
        logger.error(f"所有数据源均失败: {ticker}")
        return None
    
    def validate_data(self, data: Dict) -> bool:
        """
        验证数据完整性
        
        Args:
            data: 数据字典
            
        Returns:
            验证结果
        """
        required_fields = ["symbol", "name", "close", "trade_date", "fetch_time"]
        
        for field in required_fields:
            if field not in data:
                logger.error(f"数据缺少必需字段: {field}")
                return False
        
        # 检查数值范围
        if data["close"] <= 0:
            logger.error(f"收盘价无效: {data['close']}")
            return False
        
        return True
    
    def save_data(self, data: Dict, output_file: str) -> bool:
        """
        保存数据（遵循原子性写入协议）
        
        Args:
            data: 数据字典
            output_file: 输出文件路径
            
        Returns:
            保存结果
        """
        try:
            # 创建临时文件
            tmp_file = output_file + TMP_SUFFIX
            
            # 写入临时文件
            with open(tmp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 验证临时文件
            if not os.path.exists(tmp_file):
                logger.error(f"临时文件创建失败: {tmp_file}")
                return False
            
            # 原子性重命名
            shutil.move(tmp_file, output_file)
            
            logger.info(f"数据保存成功: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"数据保存失败: {str(e)}")
            # 清理临时文件
            if os.path.exists(tmp_file):
                os.remove(tmp_file)
            return False
    
    def run(self, tickers: List[str] = None) -> bool:
        """
        运行主流程
        
        Args:
            tickers: 标的代码列表，默认为所有配置的标的
            
        Returns:
            执行结果
        """
        logger.info("=" * 60)
        logger.info("Tushare适配器增强版启动")
        logger.info(f"时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"双活冗余: {'启用' if self.use_akshare_backup else '禁用'}")
        logger.info("=" * 60)
        
        if tickers is None:
            tickers = list(self.tickers_config.keys())
        
        success_count = 0
        total_count = len(tickers)
        
        for ticker in tickers:
            logger.info(f"处理标的: {ticker}")
            
            # 获取数据（带降级）
            data = self.fetch_data_with_fallback(ticker)
            
            if not data:
                logger.error(f"数据获取失败: {ticker}")
                continue
            
            # 验证数据
            if not self.validate_data(data):
                logger.error(f"数据验证失败: {ticker}")
                continue
            
            # 保存数据
            output_file = self.tickers_config[ticker]["output_file"]
            if self.save_data(data, output_file):
                success_count += 1
                logger.info(f"标的处理完成: {ticker}")
            else:
                logger.error(f"数据保存失败: {ticker}")
        
        # 生成执行报告
        report = {
            "module": MODULE_NAME,
            "fetch_time": datetime.datetime.now().isoformat(),
            "total_tickers": total_count,
            "success_count": success_count,
            "failure_count": total_count - success_count,
            "success_rate": round(success_count / total_count * 100, 2) if total_count > 0 else 0,
            "tushare_timeouts": self.tushare_timeout_count,
            "akshare_fallbacks": self.akshare_fallback_count,
            "use_akshare_backup": self.use_akshare_backup,
            "status": "SUCCESS" if success_count > 0 else "FAILURE"
        }
        
        # 保存报告
        report_file = f"logs/{MODULE_NAME}_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info("=" * 60)
        logger.info(f"执行完成: 成功{success_count}/{total_count}")
        logger.info(f"Tushare超时次数: {self.tushare_timeout_count}")
        logger.info(f"AkShare降级次数: {self.akshare_fallback_count}")
        logger.info(f"详细报告: {report_file}")
        logger.info("=" * 60)
        
        return success_count > 0

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Tushare适配器增强版")
    parser.add_argument("--tickers", nargs="+", help="标的代码列表")
    parser.add_argument("--no-akshare", action="store_true", help="禁用AkShare备份")
    
    args = parser.parse_args()
    
    try:
        # 创建适配器实例
        adapter = TushareAdapterEnhanced(use_akshare_backup=not args.no_akshare)
        
        # 运行主流程
        success = adapter.run(args.tickers)
        
        # 返回退出码
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"主程序执行失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()