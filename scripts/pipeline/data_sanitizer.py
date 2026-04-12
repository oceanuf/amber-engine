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


class CandidateAuditor:
    """候选池审计器 - 对候选股票进行生存状态检查"""
    
    def __init__(self, tushare_token: Optional[str] = None, debug: bool = False):
        """初始化审计器"""
        self.logger = setup_logging()
        self.debug = debug
        self.tushare_token = tushare_token or self._load_tushare_token()
        self.tushare_initialized = False
        
        # 拦截标准配置
        self.interception_rules = {
            "hard_remove": {
                "suspended": True,           # 停牌
                "st_stock": True,            # ST/*ST股票
                "daily_limit": True,         # 已封涨跌停（无法买入）
                "delisting_warning": True,   # 退市警示
                "low_liquidity": True,       # 日成交额 < 5000万
                "min_volume": 50000000,      # 5000万成交额阈值（单位：元）
                "min_turnover": 0.001        # 最低换手率阈值
            },
            "soft_warning": {
                "missing_financials": True,  # 财务数据缺失
                "data_inconsistency": True,  # 数据不一致
                "high_volatility": True      # 高波动率警告
            }
        }
        
        # 审计结果存储
        self.audit_results = []
        self.removed_candidates = []
        self.warning_candidates = []
        self.passed_candidates = []
        
        # 尝试初始化Tushare
        self._init_tushare()
        
        self.logger.info(f"候选池审计器初始化完成，Tushare可用: {self.tushare_initialized}")
    
    def _load_tushare_token(self) -> Optional[str]:
        """加载Tushare令牌"""
        # 1. 尝试从环境变量获取
        token = os.getenv("TUSHARE_TOKEN")
        if token:
            self.logger.info("✅ 从环境变量加载Tushare Token")
            return token
        
        # 2. 尝试从secrets.json获取
        secrets_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "_PRIVATE_DATA", "secrets.json"
        )
        
        try:
            if os.path.exists(secrets_file):
                with open(secrets_file, 'r', encoding='utf-8') as f:
                    secrets = json.load(f)
                    token = secrets.get("TUSHARE_TOKEN")
                    if token and token != "your_tushare_token_here":
                        self.logger.info("✅ 从secrets.json加载Tushare Token")
                        return token
        except Exception as e:
            self.logger.warning(f"读取secrets.json失败: {e}")
        
        self.logger.warning("⚠️  未找到Tushare Token，部分审计功能将受限")
        return None
    
    def _init_tushare(self):
        """初始化Tushare API"""
        if not self.tushare_token:
            self.logger.warning("无Tushare Token，跳过初始化")
            return
        
        try:
            import tushare as ts
            ts.set_token(self.tushare_token)
            self.pro = ts.pro_api()
            self.tushare_initialized = True
            self.logger.info("✅ Tushare API初始化成功")
        except ImportError:
            self.logger.error("❌ Tushare包未安装，请运行: pip install tushare")
        except Exception as e:
            self.logger.error(f"❌ Tushare初始化失败: {e}")
    
    def get_stock_status(self, ticker: str) -> Dict[str, Any]:
        """
        获取股票实时状态
        
        使用Tushare的daily_basic和pro_bar接口
        """
        if not self.tushare_initialized:
            return {"error": "Tushare未初始化", "ticker": ticker}
        
        try:
            import tushare as ts
            
            status = {
                "ticker": ticker,
                "timestamp": datetime.datetime.now().isoformat(),
                "checks_passed": 0,
                "checks_total": 0,
                "issues": [],
                "data_quality": "unknown"
            }
            
            # 1. 使用daily_basic获取基本状态
            try:
                df_basic = self.pro.daily_basic(
                    ts_code=ticker, 
                    trade_date=datetime.datetime.now().strftime("%Y%m%d")
                )
                
                if df_basic is not None and not df_basic.empty:
                    # 获取第一条记录
                    record = df_basic.iloc[0]
                    
                    status.update({
                        "trade_status": record.get("trade_status", "未知"),
                        "turnover_rate": record.get("turnover_rate", 0.0),  # 换手率
                        "volume_ratio": record.get("volume_ratio", 0.0),    # 量比
                        "pe": record.get("pe", 0.0),                        # 市盈率
                        "pe_ttm": record.get("pe_ttm", 0.0),                # 市盈率(TTM)
                        "pb": record.get("pb", 0.0),                        # 市净率
                        "ps": record.get("ps", 0.0),                        # 市销率
                        "ps_ttm": record.get("ps_ttm", 0.0),                # 市销率(TTM)
                        "total_share": record.get("total_share", 0.0),      # 总股本
                        "float_share": record.get("float_share", 0.0),      # 流通股本
                        "free_share": record.get("free_share", 0.0),        # 自由流通股本
                        "total_mv": record.get("total_mv", 0.0),            # 总市值
                        "circ_mv": record.get("circ_mv", 0.0),              # 流通市值
                        "vol": record.get("vol", 0.0),                      # 成交量
                        "amount": record.get("amount", 0.0),                # 成交额
                    })
                    
                    # 检查停牌
                    if record.get("trade_status") == "停牌":
                        status["issues"].append({"type": "suspended", "message": "股票停牌"})
                    
                    # 检查ST状态
                    if "ST" in ticker or "*ST" in ticker:
                        status["issues"].append({"type": "st_stock", "message": "ST/*ST股票"})
                    
                    # 检查成交额
                    amount = record.get("amount", 0.0)
                    if amount < self.interception_rules["hard_remove"]["min_volume"]:
                        status["issues"].append({
                            "type": "low_liquidity", 
                            "message": f"成交额不足: {amount:.0f}元 < {self.interception_rules['hard_remove']['min_volume']}元"
                        })
                    
                    # 检查换手率
                    turnover_rate = record.get("turnover_rate", 0.0)
                    if turnover_rate < self.interception_rules["hard_remove"]["min_turnover"]:
                        status["issues"].append({
                            "type": "low_turnover",
                            "message": f"换手率过低: {turnover_rate:.4f} < {self.interception_rules['hard_remove']['min_turnover']}"
                        })
                    
                    status["data_quality"] = "good"
                else:
                    status["issues"].append({"type": "no_data", "message": "无当日交易数据"})
                    status["data_quality"] = "poor"
                    
            except Exception as e:
                self.logger.warning(f"获取{daily_basic}数据失败: {e}")
                status["issues"].append({"type": "api_error", "message": f"daily_basic API错误: {e}"})
            
            # 2. 使用pro_bar获取价格数据（检查涨跌停）
            try:
                df_bar = ts.pro_bar(
                    ts_code=ticker,
                    asset='E',
                    adj='qfq',
                    start_date=(datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y%m%d"),
                    end_date=datetime.datetime.now().strftime("%Y%m%d")
                )
                
                if df_bar is not None and not df_bar.empty:
                    latest = df_bar.iloc[0]
                    
                    status.update({
                        "open": latest.get("open", 0.0),
                        "high": latest.get("high", 0.0),
                        "low": latest.get("low", 0.0),
                        "close": latest.get("close", 0.0),
                        "pre_close": latest.get("pre_close", 0.0),
                        "change": latest.get("change", 0.0),
                        "pct_chg": latest.get("pct_chg", 0.0),
                        "vol": latest.get("vol", 0.0),
                        "amount": latest.get("amount", 0.0)
                    })
                    
                    # 检查涨跌停
                    pct_chg = latest.get("pct_chg", 0.0)
                    if abs(pct_chg) >= 9.8:  # 接近涨跌停
                        status["issues"].append({
                            "type": "daily_limit", 
                            "message": f"涨跌停状态: {pct_chg:.2f}%"
                        })
                    
                else:
                    status["issues"].append({"type": "no_price_data", "message": "无价格数据"})
                    
            except Exception as e:
                self.logger.warning(f"获取pro_bar数据失败: {e}")
                status["issues"].append({"type": "api_error", "message": f"pro_bar API错误: {e}"})
            
            # 统计检查结果
            status["checks_total"] = len(self.interception_rules["hard_remove"]) + len(self.interception_rules["soft_warning"])
            status["checks_passed"] = status["checks_total"] - len(status["issues"])
            
            return status
            
        except Exception as e:
            self.logger.error(f"获取股票状态失败 {ticker}: {e}")
            return {
                "ticker": ticker,
                "error": str(e),
                "timestamp": datetime.datetime.now().isoformat(),
                "checks_passed": 0,
                "checks_total": 0,
                "issues": [{"type": "system_error", "message": f"系统错误: {e}"}],
                "data_quality": "error"
            }
    
    def load_candidate_pool(self, candidate_file: Optional[str] = None) -> List[Dict]:
        """
        加载候选池
        
        支持多个来源:
        1. data/stage/candidate_list_T.json
        2. reports/candidates/candidate_generation_today.json
        3. 手动指定文件路径
        """
        candidate_sources = []
        
        if candidate_file:
            candidate_sources.append(candidate_file)
        else:
            # 默认搜索路径
            default_sources = [
                os.path.join("data", "stage", "candidate_list_T.json"),
                os.path.join("reports", "candidates", "candidate_generation_today.json"),
                os.path.join("reports", "candidates", "candidate_generation_*.json")
            ]
            
            for source in default_sources:
                if "*" in source:
                    import glob
                    files = glob.glob(source)
                    candidate_sources.extend(files)
                elif os.path.exists(source):
                    candidate_sources.append(source)
        
        all_candidates = []
        
        for source in candidate_sources:
            try:
                with open(source, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 解析不同格式
                candidates = []
                if isinstance(data, list):
                    candidates = data
                elif isinstance(data, dict):
                    # 从报告格式中提取候选
                    if "candidate_profiles" in data:
                        candidates = data["candidate_profiles"]
                    elif "detailed_results" in data:
                        candidates = data["detailed_results"]
                    elif "candidates" in data:
                        candidates = data["candidates"]
                    else:
                        # 尝试将所有值视为候选
                        for key, value in data.items():
                            if isinstance(value, dict) and "stock_code" in value:
                                candidates.append(value)
                
                self.logger.info(f"从 {source} 加载 {len(candidates)} 个候选")
                all_candidates.extend(candidates)
                
            except Exception as e:
                self.logger.warning(f"加载候选文件失败 {source}: {e}")
        
        # 去重（基于stock_code）
        unique_candidates = []
        seen_codes = set()
        
        for candidate in all_candidates:
            code = candidate.get("stock_code") or candidate.get("ticker") or candidate.get("code")
            if code and code not in seen_codes:
                seen_codes.add(code)
                unique_candidates.append(candidate)
        
        self.logger.info(f"去重后候选总数: {len(unique_candidates)}")
        return unique_candidates
    
    def audit_candidate(self, candidate: Dict) -> Dict:
        """审计单个候选"""
        # 提取股票代码
        ticker = candidate.get("stock_code") or candidate.get("ticker") or candidate.get("code")
        
        if not ticker:
            return {
                "candidate": candidate,
                "status": "invalid",
                "reason": "无股票代码",
                "audit_time": datetime.datetime.now().isoformat(),
                "issues": [{"type": "missing_code", "message": "候选缺少股票代码"}]
            }
        
        # 获取股票状态
        stock_status = self.get_stock_status(ticker)
        
        # 判断是否通过审计
        issues = stock_status.get("issues", [])
        
        # 区分硬剔除和软警告
        hard_issues = [issue for issue in issues if issue.get("type") in [
            "suspended", "st_stock", "daily_limit", "delisting_warning", 
            "low_liquidity", "low_turnover", "no_data"
        ]]
        
        soft_issues = [issue for issue in issues if issue.get("type") in [
            "missing_financials", "data_inconsistency", "high_volatility",
            "api_error", "system_error"
        ]]
        
        audit_result = {
            "candidate": candidate,
            "ticker": ticker,
            "stock_status": stock_status,
            "audit_time": datetime.datetime.now().isoformat(),
            "hard_issues": hard_issues,
            "soft_issues": soft_issues,
            "total_issues": len(issues),
            "data_quality": stock_status.get("data_quality", "unknown")
        }
        
        # 决定审计结果
        if hard_issues:
            audit_result["status"] = "removed"
            audit_result["reason"] = f"硬剔除: {', '.join([issue['type'] for issue in hard_issues])}"
        elif soft_issues:
            audit_result["status"] = "warning"
            audit_result["reason"] = f"警告: {', '.join([issue['type'] for issue in soft_issues])}"
        else:
            audit_result["status"] = "passed"
            audit_result["reason"] = "通过所有检查"
        
        return audit_result
    
    def batch_audit_candidates(self, candidates: List[Dict]) -> List[Dict]:
        """批量审计候选"""
        self.logger.info(f"开始批量审计 {len(candidates)} 个候选")
        
        audit_results = []
        
        for i, candidate in enumerate(candidates):
            try:
                result = self.audit_candidate(candidate)
                audit_results.append(result)
                
                # 分类存储
                if result["status"] == "removed":
                    self.removed_candidates.append(result)
                elif result["status"] == "warning":
                    self.warning_candidates.append(result)
                elif result["status"] == "passed":
                    self.passed_candidates.append(result)
                
                if (i + 1) % 10 == 0:
                    self.logger.info(f"审计进度: {i+1}/{len(candidates)}")
                    
            except Exception as e:
                self.logger.error(f"审计候选失败: {candidate}, 错误: {e}")
                audit_results.append({
                    "candidate": candidate,
                    "status": "error",
                    "reason": f"审计异常: {e}",
                    "audit_time": datetime.datetime.now().isoformat()
                })
        
        self.logger.info(f"批量审计完成: 通过 {len(self.passed_candidates)}, "
                        f"警告 {len(self.warning_candidates)}, "
                        f"剔除 {len(self.removed_candidates)}")
        
        return audit_results
    
    def generate_audit_report(self, audit_results: List[Dict]) -> Dict:
        """生成审计报告"""
        report = {
            "metadata": {
                "report_type": "候选池审计报告",
                "generated_by": "CandidateAuditor",
                "generation_time": datetime.datetime.now().isoformat(),
                "total_candidates": len(audit_results),
                "passed_count": len(self.passed_candidates),
                "warning_count": len(self.warning_candidates),
                "removed_count": len(self.removed_candidates),
                "pass_rate": len(self.passed_candidates) / len(audit_results) if audit_results else 0
            },
            "summary": {
                "interception_rules": self.interception_rules,
                "tushare_available": self.tushare_initialized,
                "data_sources_searched": [
                    "data/stage/candidate_list_T.json",
                    "reports/candidates/candidate_generation_today.json"
                ]
            },
            "detailed_results": {
                "passed": self.passed_candidates[:20],  # 只保留前20个详细结果
                "warnings": self.warning_candidates[:10],
                "removed": self.removed_candidates[:10]
            },
            "recommendations": [
                "硬剔除的候选不应进入后续共振分析",
                "警告的候选需要人工复核",
                "建议定期更新拦截规则以适应市场变化"
            ]
        }
        
        return report
    
    def save_audit_report(self, report: Dict, output_dir: Optional[str] = None) -> str:
        """保存审计报告"""
        if output_dir is None:
            output_dir = os.path.join("reports", "sanitization")
        
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"candidate_audit_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"审计报告已保存: {filepath}")
            
            # 同时保存今日最新报告
            today_file = os.path.join(output_dir, "candidate_audit_today.json")
            with open(today_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"今日审计报告已更新: {today_file}")
            
            return filepath
            
        except Exception as e:
            self.logger.error(f"保存审计报告失败: {e}")
            return ""
    
    def run_audit(self, candidate_file: Optional[str] = None) -> Dict:
        """运行完整的审计流程"""
        self.logger.info("🚀 启动候选池审计...")
        
        # 1. 加载候选池
        candidates = self.load_candidate_pool(candidate_file)
        
        if not candidates:
            self.logger.warning("⚠️  无候选股票需要审计")
            return {
                "success": False,
                "message": "无候选股票需要审计",
                "audit_time": datetime.datetime.now().isoformat()
            }
        
        # 2. 批量审计
        audit_results = self.batch_audit_candidates(candidates)
        
        # 3. 生成报告
        report = self.generate_audit_report(audit_results)
        
        # 4. 保存报告
        report_file = self.save_audit_report(report)
        
        # 5. 输出摘要
        summary = report["metadata"]
        self.logger.info(f"📊 审计完成: 总共 {summary['total_candidates']} 个候选, "
                        f"通过 {summary['passed_count']} ({summary['pass_rate']*100:.1f}%), "
                        f"警告 {summary['warning_count']}, "
                        f"剔除 {summary['removed_count']}")
        
        return {
            "success": True,
            "total_candidates": summary["total_candidates"],
            "passed_count": summary["passed_count"],
            "warning_count": summary["warning_count"],
            "removed_count": summary["removed_count"],
            "pass_rate": summary["pass_rate"],
            "report_file": report_file,
            "audit_time": datetime.datetime.now().isoformat()
        }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='数据抗干扰清洗器与候选池审计')
    
    # 原有清洗功能参数
    parser.add_argument('--file', '-f', help='单个JSON文件路径')
    parser.add_argument('--directory', '-d', help='包含JSON文件的目录路径')
    parser.add_argument('--reference', '-r', help='参考价格文件路径（用于多源校验）')
    
    # 新增候选审计功能参数
    parser.add_argument('--audit-candidates', '-a', action='store_true', 
                       help='审计候选池（默认搜索data/stage/和reports/candidates/）')
    parser.add_argument('--candidate-file', '-c', help='指定候选池文件路径')
    
    parser.add_argument('--debug', action='store_true', help='调试模式')
    
    args = parser.parse_args()
    
    # 检查参数组合
    has_clean_task = args.file or args.directory
    has_audit_task = args.audit_candidates
    
    if not has_clean_task and not has_audit_task:
        parser.error("必须指定以下任务之一:\n"
                    "  --file/-f 或 --directory/-d: 数据清洗任务\n"
                    "  --audit-candidates/-a: 候选池审计任务")
    
    if has_clean_task and has_audit_task:
        parser.error("不能同时执行清洗任务和审计任务，请分开执行")
    
    # 执行清洗任务
    if has_clean_task:
        sanitizer = DataSanitizer(debug=args.debug)
        
        if args.file:
            sanitizer.sanitize_file(args.file, args.reference)
            sanitizer.save_audit_report()
        elif args.directory:
            sanitizer.sanitize_directory(args.directory, args.reference)
    
    # 执行审计任务
    elif has_audit_task:
        auditor = CandidateAuditor(debug=args.debug)
        result = auditor.run_audit(args.candidate_file)
        
        if result["success"]:
            print(f"\n✅ 候选池审计完成!")
            print(f"   总共候选: {result['total_candidates']}")
            print(f"   通过数量: {result['passed_count']}")
            print(f"   警告数量: {result['warning_count']}")
            print(f"   剔除数量: {result['removed_count']}")
            print(f"   通过率: {result['pass_rate']*100:.1f}%")
            print(f"   报告文件: {result['report_file']}")
            
            # 信号级联：只有当有通过的候选时才发出DATA_READY_FOR_JUDGE信号
            if result["passed_count"] > 0:
                print(f"\n🚀 信号级联: DATA_READY_FOR_JUDGE (有{result['passed_count']}个健康候选)")
                # 这里可以添加实际信号触发逻辑
            else:
                print(f"\n⚠️  信号阻断: 无健康候选，阻止向评委中控传递")
        else:
            print(f"\n❌ 候选池审计失败: {result['message']}")

if __name__ == '__main__':
    main()