#!/usr/bin/env python3
"""
数据抗干扰清洗器 - 符合 V1.2.1 标准
为 Tushare 数据抓取层加装"前置防火墙"，确保进入共振引擎的数据经过严格清洗与横向校验。

核心功能:
1. 波动率熔断器: 单日价格波动超过 ±11%（除新股外）判定为异常干扰
2. 多源交叉校验: 对比 tushare_data 与本地 last_nav_price，若偏差 > 20% 且无市场公告支持，强制触发 DataFallback
3. 清洗报告生成: 每次抓取后生成 clean_audit_YYYYMMDD.json
4. 降级挂接: 当清洗器拦截异常数据时，无缝调用 technical_fallback.py

输出:
- 清洗后的数据文件（保留原路径，添加 _cleaned 后缀或覆盖原文件）
- 清洗审计报告: database/logs/clean_audit_YYYYMMDD.json
"""

import os
import sys
import json
import logging
import datetime
import argparse
import math
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# 导入技术降级模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from scripts.arena.technical_fallback import DataFallback
    TECHNICAL_FALLBACK_AVAILABLE = True
except ImportError:
    TECHNICAL_FALLBACK_AVAILABLE = False
    print("[WARN] technical_fallback 模块不可用，降级功能将受限")

# 模块常量
MODULE_NAME = "data_sanitizer"
LOG_DIR = "logs"
CLEAN_AUDIT_DIR = os.path.join("database", "logs")
MAX_VOLATILITY_THRESHOLD = 11.0  # 最大波动率阈值 ±11%
PRICE_DEVIATION_THRESHOLD = 20.0  # 价格偏差阈值 20%
MIN_HISTORY_DAYS_FOR_VOLATILITY_CHECK = 30  # 新股判定阈值（少于30天历史数据视为新股）

def setup_logging():
    """配置日志"""
    log_format = "%(asctime)s [%(levelname)s] %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_format)
    return logging.getLogger(MODULE_NAME)

def ensure_directories():
    """确保必要的目录存在"""
    os.makedirs(CLEAN_AUDIT_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

class DataSanitizer:
    """数据清洗器核心类"""
    
    def __init__(self, debug: bool = False):
        self.logger = setup_logging()
        self.debug = debug
        self.audit_records = []
        self.ensure_directories()
        
        # 初始化数据降级模块（如果可用）
        self.data_fallback = None
        if TECHNICAL_FALLBACK_AVAILABLE:
            try:
                self.data_fallback = DataFallback()
                self.logger.info("DataFallback 降级模块已加载")
            except Exception as e:
                self.logger.warning(f"DataFallback 初始化失败: {e}")
        else:
            self.logger.warning("DataFallback 降级模块不可用")
    
    def ensure_directories(self):
        """确保必要的目录存在"""
        ensure_directories()
    
    def load_json_file(self, file_path: str) -> Optional[Dict]:
        """加载JSON文件，处理各种格式"""
        if not os.path.exists(file_path):
            self.logger.error(f"文件不存在: {file_path}")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, dict):
                self.logger.error(f"文件格式错误: {file_path}，期望字典类型")
                return None
            
            return data
        except Exception as e:
            self.logger.error(f"加载文件失败 {file_path}: {e}")
            return None
    
    def extract_price_data(self, data: Dict) -> Tuple[List[Dict], Optional[str]]:
        """
        从数据中提取价格信息，支持多种数据结构
        
        返回: (价格数据列表, 股票代码)
        """
        price_data = []
        ticker = None
        
        # 尝试从metadata或数据中提取股票代码
        if "metadata" in data and "ticker" in data["metadata"]:
            ticker = data["metadata"]["ticker"]
        elif "ticker" in data:
            ticker = data["ticker"]
        
        # 尝试提取价格数据
        if "data" in data and isinstance(data["data"], list):
            # Tushare 格式: {"data": [{"date": "...", "close": ..., "pct_chg": ...}, ...]}
            price_data = data["data"]
        elif "nav_history" in data and isinstance(data["nav_history"], list):
            # 清洗后格式: {"nav_history": [{"date": "...", "price": "...", "change": "..."}, ...]}
            price_data = data["nav_history"]
        elif isinstance(data.get("history"), list):
            # 其他可能格式
            price_data = data["history"]
        elif isinstance(data, list):
            # 如果整个文件就是价格数据列表
            price_data = data
        
        return price_data, ticker
    
    def check_volatility_outlier(self, price_data: List[Dict], ticker: str) -> List[Dict]:
        """
        检查波动率异常
        单日价格波动超过 ±11%（除新股外）判定为异常干扰
        
        返回: 异常记录列表
        """
        anomalies = []
        
        if len(price_data) < 2:
            self.logger.info(f"{ticker}: 数据不足，跳过波动率检查")
            return anomalies
        
        # 新股检查：少于 MIN_HISTORY_DAYS_FOR_VOLATILITY_CHECK 天数据视为新股
        is_new_stock = len(price_data) < MIN_HISTORY_DAYS_FOR_VOLATILITY_CHECK
        if is_new_stock:
            self.logger.info(f"{ticker}: 新股（{len(price_data)} 天数据），放宽波动率检查")
        
        for i, item in enumerate(price_data):
            # 尝试从不同字段获取涨跌幅
            pct_change = None
            
            # 字段名可能不同
            if "pct_chg" in item:
                pct_change = item["pct_chg"]
            elif "change" in item and isinstance(item["change"], (int, float)):
                pct_change = item["change"]
            elif "change" in item and isinstance(item["change"], str):
                # 字符串格式如 "+0.27%"
                try:
                    change_str = item["change"].strip()
                    if change_str.endswith('%'):
                        pct_change = float(change_str.rstrip('%'))
                except:
                    pass
            
            if pct_change is not None:
                abs_change = abs(pct_change)
                if abs_change > MAX_VOLATILITY_THRESHOLD and not is_new_stock:
                    anomaly = {
                        "ticker": ticker or "unknown",
                        "date": item.get("date", f"index_{i}"),
                        "pct_change": pct_change,
                        "threshold": MAX_VOLATILITY_THRESHOLD,
                        "reason": f"单日波动率 {pct_change:.2f}% 超过阈值 ±{MAX_VOLATILITY_THRESHOLD}%",
                        "type": "volatility_outlier"
                    }
                    anomalies.append(anomaly)
                    self.logger.warning(f"波动率异常: {ticker} 于 {item.get('date')} 波动 {pct_change:.2f}%")
        
        return anomalies
    
    def check_price_deviation(self, tushare_data: Dict, reference_price: float, ticker: str) -> List[Dict]:
        """
        多源交叉校验
        对比 tushare_data 与本地 last_nav_price，若偏差 > 20% 且无市场公告支持，强制触发 DataFallback
        
        返回: 异常记录列表
        """
        anomalies = []
        
        # 从 Tushare 数据中提取最新价格
        price_data, _ = self.extract_price_data(tushare_data)
        if not price_data:
            self.logger.warning(f"{ticker}: 无法从 Tushare 数据中提取价格信息")
            return anomalies
        
        # 获取最新价格（假设数据按日期降序排列）
        latest_item = price_data[0]
        tushare_price = None
        
        # 尝试从不同字段获取价格
        for field in ["close", "price", "nav"]:
            if field in latest_item:
                try:
                    tushare_price = float(latest_item[field])
                    break
                except (ValueError, TypeError):
                    continue
        
        if tushare_price is None:
            self.logger.warning(f"{ticker}: 无法从 Tushare 数据中提取最新价格")
            return anomalies
        
        if reference_price <= 0:
            self.logger.warning(f"{ticker}: 参考价格无效: {reference_price}")
            return anomalies
        
        # 计算偏差百分比
        deviation_pct = abs(tushare_price - reference_price) / reference_price * 100
        
        if deviation_pct > PRICE_DEVIATION_THRESHOLD:
            anomaly = {
                "ticker": ticker,
                "date": latest_item.get("date", "latest"),
                "tushare_price": tushare_price,
                "reference_price": reference_price,
                "deviation_pct": deviation_pct,
                "threshold": PRICE_DEVIATION_THRESHOLD,
                "reason": f"价格偏差 {deviation_pct:.2f}% 超过阈值 {PRICE_DEVIATION_THRESHOLD}%",
                "type": "price_deviation"
            }
            anomalies.append(anomaly)
            self.logger.warning(f"价格偏差异常: {ticker} Tushare价格={tushare_price}, 参考价格={reference_price}, 偏差={deviation_pct:.2f}%")
        
        return anomalies
    
    def check_zero_or_null_prices(self, price_data: List[Dict], ticker: str) -> List[Dict]:
        """
        检查零值或空值
        
        返回: 异常记录列表
        """
        anomalies = []
        
        for i, item in enumerate(price_data):
            # 检查关键价格字段
            price_fields = ["close", "price", "nav"]
            has_valid_price = False
            
            for field in price_fields:
                if field in item:
                    value = item[field]
                    if value is None:
                        continue
                    
                    try:
                        float_val = float(value)
                        if float_val > 0:
                            has_valid_price = True
                            break
                    except (ValueError, TypeError):
                        continue
            
            if not has_valid_price:
                anomaly = {
                    "ticker": ticker or "unknown",
                    "date": item.get("date", f"index_{i}"),
                    "reason": "价格字段为零、空或无效",
                    "type": "zero_or_null_price"
                }
                anomalies.append(anomaly)
                self.logger.warning(f"零值/空值异常: {ticker} 于 {item.get('date')} 价格无效")
        
        return anomalies
    
    def apply_fallback_for_anomalies(self, anomalies: List[Dict], ticker: str, original_data: Dict) -> Dict:
        """
        对异常数据应用降级逻辑
        使用 technical_fallback.py 提取历史镜像
        
        返回: 降级后的数据
        """
        if not anomalies:
            return original_data
        
        if not self.data_fallback:
            self.logger.error(f"{ticker}: 无法应用降级逻辑，DataFallback 不可用")
            return original_data
        
        self.logger.info(f"{ticker}: 检测到 {len(anomalies)} 个异常，尝试降级处理")
        
        try:
            # 提取股票代码用于降级查询
            fallback_ticker = ticker or self.extract_ticker_from_data(original_data)
            if not fallback_ticker:
                self.logger.error("无法提取股票代码用于降级")
                return original_data
            
            # 使用 DataFallback 获取降级数据
            fallback_result = self.data_fallback.get_price(fallback_ticker)
            
            if fallback_result.get("success", False):
                self.logger.info(f"{ticker}: 降级成功，使用备用数据")
                
                # 创建降级标记的数据结构
                fallback_data = {
                    **original_data,
                    "fallback_applied": True,
                    "fallback_reason": f"检测到 {len(anomalies)} 个数据异常",
                    "fallback_anomalies": anomalies,
                    "fallback_source": fallback_result.get("source", "unknown"),
                    "fallback_timestamp": datetime.datetime.now().isoformat()
                }
                
                # 如果降级数据包含价格信息，尝试合并
                if "price" in fallback_result:
                    # 更新最新价格（简化处理）
                    price_data, _ = self.extract_price_data(original_data)
                    if price_data and len(price_data) > 0:
                        # 更新最新数据点
                        latest_item = price_data[0].copy()
                        latest_item["close"] = fallback_result["price"]
                        latest_item["price"] = fallback_result["price"]
                        latest_item["nav"] = fallback_result["price"]
                        
                        if "data" in fallback_data:
                            fallback_data["data"][0] = latest_item
                
                return fallback_data
            else:
                self.logger.warning(f"{ticker}: 降级失败: {fallback_result.get('error', '未知错误')}")
                return original_data
                
        except Exception as e:
            self.logger.error(f"{ticker}: 降级处理异常: {e}")
            return original_data
    
    def extract_ticker_from_data(self, data: Dict) -> Optional[str]:
        """从数据中提取股票代码"""
        if "metadata" in data and "ticker" in data["metadata"]:
            return data["metadata"]["ticker"]
        elif "ticker" in data:
            return data["ticker"]
        
        # 尝试从文件名推断
        return None
    
    def generate_audit_report(self, anomalies: List[Dict], file_path: str, ticker: str):
        """生成清洗审计报告"""
        if not anomalies:
            return
        
        audit_record = {
            "timestamp": datetime.datetime.now().isoformat(),
            "file": file_path,
            "ticker": ticker,
            "anomaly_count": len(anomalies),
            "anomalies": anomalies,
            "checks_performed": [
                "volatility_outlier",
                "price_deviation", 
                "zero_or_null_prices"
            ]
        }
        
        self.audit_records.append(audit_record)
        
        # 同时输出到日志
        self.logger.info(f"审计记录: {ticker} 发现 {len(anomalies)} 个异常")
    
    def save_audit_report(self):
        """保存清洗审计报告到文件"""
        if not self.audit_records:
            self.logger.info("无异常记录，不生成审计报告")
            return
        
        today = datetime.datetime.now().strftime("%Y%m%d")
        audit_file = os.path.join(CLEAN_AUDIT_DIR, f"clean_audit_{today}.json")
        
        try:
            # 加载现有审计报告（如果存在）
            existing_records = []
            if os.path.exists(audit_file):
                with open(audit_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    if isinstance(existing_data, list):
                        existing_records = existing_data
            
            # 合并记录
            all_records = existing_records + self.audit_records
            
            with open(audit_file, 'w', encoding='utf-8') as f:
                json.dump(all_records, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"审计报告已保存: {audit_file} ({len(self.audit_records)} 条新记录)")
        except Exception as e:
            self.logger.error(f"保存审计报告失败: {e}")
    
    def sanitize_file(self, file_path: str, reference_price_file: Optional[str] = None) -> bool:
        """
        清洗单个数据文件
        
        返回: 是否成功
        """
        self.logger.info(f"开始清洗: {file_path}")
        
        # 加载数据
        data = self.load_json_file(file_path)
        if data is None:
            return False
        
        # 提取价格数据和股票代码
        price_data, ticker = self.extract_price_data(data)
        if not price_data:
            self.logger.warning(f"{file_path}: 无价格数据，跳过清洗")
            return True
        
        all_anomalies = []
        
        # 1. 检查波动率异常
        volatility_anomalies = self.check_volatility_outlier(price_data, ticker or "unknown")
        all_anomalies.extend(volatility_anomalies)
        
        # 2. 检查零值/空值
        zero_price_anomalies = self.check_zero_or_null_prices(price_data, ticker or "unknown")
        all_anomalies.extend(zero_price_anomalies)
        
        # 3. 多源交叉校验（如果提供参考价格文件）
        if reference_price_file and os.path.exists(reference_price_file):
            reference_data = self.load_json_file(reference_price_file)
            if reference_data:
                # 尝试从参考文件中提取最新价格
                ref_price_data, _ = self.extract_price_data(reference_data)
                if ref_price_data and len(ref_price_data) > 0:
                    latest_ref = ref_price_data[0]
                    reference_price = None
                    
                    for field in ["close", "price", "nav", "current_nav"]:
                        if field in latest_ref:
                            try:
                                reference_price = float(latest_ref[field])
                                break
                            except (ValueError, TypeError):
                                continue
                    
                    if reference_price:
                        price_deviation_anomalies = self.check_price_deviation(
                            data, reference_price, ticker or "unknown"
                        )
                        all_anomalies.extend(price_deviation_anomalies)
        
        # 生成审计报告
        self.generate_audit_report(all_anomalies, file_path, ticker or "unknown")
        
        # 如果有异常，尝试应用降级逻辑
        if all_anomalies:
            cleaned_data = self.apply_fallback_for_anomalies(all_anomalies, ticker or "unknown", data)
            
            # 保存清洗后的数据（添加 _cleaned 后缀）
            cleaned_file = file_path.replace('.json', '_cleaned.json')
            try:
                with open(cleaned_file, 'w', encoding='utf-8') as f:
                    json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
                self.logger.info(f"清洗后数据已保存: {cleaned_file}")
            except Exception as e:
                self.logger.error(f"保存清洗后数据失败: {e}")
                
                # 如果保存失败，至少尝试添加清洗标记到原数据
                data["sanitization_applied"] = True
                data["sanitization_anomalies"] = all_anomalies
                data["sanitization_timestamp"] = datetime.datetime.now().isoformat()
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                self.logger.info(f"原数据已添加清洗标记: {file_path}")
        else:
            self.logger.info(f"{file_path}: 无异常，数据清洁")
            
            # 即使无异常，也添加清洁标记
            data["sanitization_applied"] = True
            data["sanitization_status"] = "clean"
            data["sanitization_timestamp"] = datetime.datetime.now().isoformat()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        return True
    
    def sanitize_directory(self, directory: str, reference_price_file: Optional[str] = None):
        """清洗目录下的所有JSON文件"""
        if not os.path.exists(directory):
            self.logger.error(f"目录不存在: {directory}")
            return
        
        json_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.json') and not file.endswith('_cleaned.json'):
                    json_files.append(os.path.join(root, file))
        
        self.logger.info(f"发现 {len(json_files)} 个JSON文件需要清洗")
        
        success_count = 0
        for i, file_path in enumerate(json_files, 1):
            self.logger.info(f"处理文件 {i}/{len(json_files)}: {file_path}")
            if self.sanitize_file(file_path, reference_price_file):
                success_count += 1
        
        # 保存审计报告
        self.save_audit_report()
        
        self.logger.info(f"清洗完成: {success_count}/{len(json_files)} 个文件成功处理")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='数据抗干扰清洗器')
    parser.add_argument('--file', '-f', help='单个JSON文件路径')
    parser.add_argument('--directory', '-d', help='包含JSON文件的目录路径')
    parser.add_argument('--reference', '-r', help='参考价格文件路径（用于多源校验）')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    
    args = parser.parse_args()
    
    if not args.file and not args.directory:
        parser.error("必须指定 --file 或 --directory")
    
    sanitizer = DataSanitizer(debug=args.debug)
    
    if args.file:
        sanitizer.sanitize_file(args.file, args.reference)
        sanitizer.save_audit_report()
    elif args.directory:
        sanitizer.sanitize_directory(args.directory, args.reference)

if __name__ == '__main__':
    main()