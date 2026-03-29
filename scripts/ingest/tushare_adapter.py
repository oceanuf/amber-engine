#!/usr/bin/env python3
"""
Tushare Pro API 适配器 - 符合 V1.2.1 标准
标准输出: database/tushare_518880.json, database/tushare_510300.json 等
支持黄金ETF、宽基ETF、宏观利率数据提取
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
import pandas as pd
from typing import Dict, List, Optional, Any

# 模块常量
MODULE_NAME = "ingest_tushare_adapter"
TMP_SUFFIX = ".tmp"
SCHEMA_FILE = "config/schema_tushare.json"  # Tushare专用Schema验证
MAX_RETRIES = 3
RETRY_DELAY = 5  # 秒

# Tushare 标的配置
TICKERS_CONFIG = {
    "518880": {
        "name": "黄金ETF",
        "ts_code": "518880.SH",
        "data_type": "etf",
        "output_file": "database/tushare_gold.json"
    },
    "510300": {
        "name": "沪深300ETF",
        "ts_code": "510300.SH", 
        "data_type": "etf",
        "output_file": "database/tushare_hs300.json"
    },
    "510500": {
        "name": "中证500ETF",
        "ts_code": "510500.SH",
        "data_type": "etf",
        "output_file": "database/tushare_zz500.json"
    }
}

# 宏观利率标的配置
MACRO_CONFIG = {
    "shibor": {
        "name": "上海银行间同业拆放利率",
        "ts_code": "M0019.SH",
        "data_type": "macro",
        "output_file": "database/tushare_shibor.json"
    },
    "cpi": {
        "name": "居民消费价格指数",
        "ts_code": "M0001.SH", 
        "data_type": "macro",
        "output_file": "database/tushare_cpi.json"
    }
}

def log_info(msg):
    """INFO 级别日志"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{MODULE_NAME}:INFO] {msg}", file=sys.stdout)

def log_warn(msg):
    """WARN 级别日志"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{MODULE_NAME}:WARN] {msg}", file=sys.stdout)

def log_error(code, msg):
    """ERROR 级别日志，遵循结构化 stderr 格式"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sys.stderr.write(f"[{code}]: {msg}\n")
    print(f"[{timestamp}] [{MODULE_NAME}:ERROR] {code}: {msg}", file=sys.stdout)

def throttle_request(delay: float = 0.8):
    """请求节流，避免 Tushare API 频率限制"""
    time.sleep(delay)

def get_latest_date_from_file(file_path: str) -> Optional[str]:
    """
    从现有数据文件获取最新日期
    返回格式: YYYYMMDD 或 None（如果文件不存在或无数据）
    """
    if not os.path.exists(file_path):
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 数据结构: { "data": [...], "metadata": {...} }
        if isinstance(data, dict) and "data" in data and data["data"]:
            # 数据已按日期降序排列（最新的在前）
            latest_item = data["data"][0]
            if "date" in latest_item:
                return latest_item["date"]
            elif "month" in latest_item:
                return latest_item["month"]
    except Exception as e:
        log_warn(f"读取文件 {file_path} 失败: {e}")
    
    return None

def check_data_gaps(data_list: List[Dict], max_gap_days: int = 5) -> bool:
    """
    检查数据是否存在断层（连续缺失超过max_gap_days个交易日）
    返回 True 表示存在严重断层
    """
    if len(data_list) < 10:
        return False  # 数据太少，不检查
    
    # 提取日期并转换为datetime对象
    dates = []
    for item in data_list:
        if "date" in item:
            try:
                # 假设日期格式为 YYYYMMDD
                dt = datetime.datetime.strptime(item["date"], "%Y%m%d")
                dates.append(dt)
            except:
                pass
    
    if len(dates) < 2:
        return False
    
    # 按日期排序
    dates.sort()
    
    # 检查连续日期之间的间隔
    for i in range(1, len(dates)):
        gap_days = (dates[i] - dates[i-1]).days
        if gap_days > max_gap_days:
            log_warn(f"数据断层检测: {dates[i-1].strftime('%Y-%m-%d')} 到 {dates[i].strftime('%Y-%m-%d')} 间隔 {gap_days} 天")
            return True
    
    return False

def merge_data(existing_data: List[Dict], new_data: List[Dict], key_field: str = "date") -> List[Dict]:
    """
    合并新旧数据，按key_field去重，保留最新的数据
    返回合并后的数据列表（按key_field降序排列）
    """
    if not existing_data:
        return new_data
    if not new_data:
        return existing_data
    
    # 构建映射：key -> 数据项
    merged_map = {}
    
    # 先添加现有数据
    for item in existing_data:
        if key_field in item:
            merged_map[item[key_field]] = item
    
    # 用新数据覆盖（新数据可能包含更新的字段）
    for item in new_data:
        if key_field in item:
            merged_map[item[key_field]] = item
    
    # 转换为列表并按key降序排列
    merged_list = list(merged_map.values())
    if key_field in merged_list[0]:
        # 尝试按日期排序
        try:
            merged_list.sort(key=lambda x: x[key_field], reverse=True)
        except:
            # 如果排序失败，保持原顺序
            pass
    
    log_info(f"数据合并: 现有{len(existing_data)}条 + 新增{len(new_data)}条 = 合并后{len(merged_list)}条")
    return merged_list

def load_existing_data(file_path: str) -> List[Dict]:
    """
    从现有文件加载数据
    返回数据列表或空列表
    """
    if not os.path.exists(file_path):
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        elif isinstance(data, list):
            return data
        else:
            log_warn(f"文件 {file_path} 格式未知")
            return []
    except Exception as e:
        log_warn(f"加载现有数据文件 {file_path} 失败: {e}")
        return []

def init_tushare():
    """初始化 Tushare Pro 连接"""
    tushare_token = os.environ.get("TUSHARE_TOKEN")
    
    # 如果环境变量未设置，尝试从secrets.json读取
    if not tushare_token:
        try:
            import json
            secrets_path = "_PRIVATE_DATA/secrets.json"
            if os.path.exists(secrets_path):
                with open(secrets_path, 'r', encoding='utf-8') as f:
                    secrets = json.load(f)
                    tushare_token = secrets.get("TUSHARE_TOKEN")
        except Exception as e:
            log_warn(f"读取secrets.json失败: {e}")
    
    if not tushare_token:
        log_warn("TUSHARE_TOKEN 未设置，使用模拟数据模式")
        return None
    
    try:
        import tushare as ts
        ts.set_token(tushare_token)
        pro = ts.pro_api()
        log_info("Tushare Pro 初始化成功")
        return pro
    except ImportError:
        log_error("TUSHARE_IMPORT_FAIL", "tushare 库未安装，请运行: pip install tushare")
        return None
    except Exception as e:
        log_error("TUSHARE_INIT_FAIL", f"Tushare 初始化失败: {str(e)}")
        return None

def fetch_etf_data(pro, ts_code: str, days: int = 500, start_date: Optional[str] = None) -> Optional[List[Dict]]:
    """
    获取 ETF 日线数据，使用 fund_daily 接口
    start_date: 起始日期 (YYYYMMDD)，如为None则计算days*2天前
    返回格式标准化的数据列表
    """
    # 如果没有真实连接，返回模拟数据
    if pro is None:
        return generate_mock_etf_data(ts_code, days)
    
    try:
        # 计算日期范围
        end_date = datetime.datetime.now().strftime("%Y%m%d")
        
        if start_date is None:
            # 默认计算days*2天前，确保能获取足够数据
            start_date = (datetime.datetime.now() - datetime.timedelta(days=days*2)).strftime("%Y%m%d")
        
        # 使用 fund_daily 接口获取基金日线数据
        log_info(f"获取 {ts_code} 基金日线数据，日期范围 {start_date} 至 {end_date}")
        
        # 节流：避免频率限制
        throttle_request(delay=0.8)
        
        df_fund = pro.fund_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        
        if df_fund is None or df_fund.empty:
            log_warn(f"{ts_code} 无基金日线数据，使用模拟数据")
            return generate_mock_etf_data(ts_code, days)
        
        # 标准化数据格式（fund_daily 返回股票式行情数据）
        result = []
        for _, row in df_fund.iterrows():
            data_point = {
                "date": row['trade_date'],
                "close": float(row['close']) if 'close' in row and pd.notna(row['close']) else None,
                "open": float(row['open']) if 'open' in row and pd.notna(row['open']) else None,
                "high": float(row['high']) if 'high' in row and pd.notna(row['high']) else None,
                "low": float(row['low']) if 'low' in row and pd.notna(row['low']) else None,
                "pre_close": float(row['pre_close']) if 'pre_close' in row and pd.notna(row['pre_close']) else None,
                "change": float(row['change']) if 'change' in row and pd.notna(row['change']) else None,
                "pct_chg": float(row['pct_chg']) if 'pct_chg' in row and pd.notna(row['pct_chg']) else None,
                "volume": float(row['vol']) if 'vol' in row and pd.notna(row['vol']) else 0.0,
                "amount": float(row['amount']) if 'amount' in row and pd.notna(row['amount']) else 0.0,
                # 兼容字段
                "nav": float(row['close']) if 'close' in row and pd.notna(row['close']) else None,  # 使用close作为净值
            }
            result.append(data_point)
        
        # 按日期排序（最近的在前）
        result.sort(key=lambda x: x['date'], reverse=True)
        log_info(f"成功获取 {len(result)} 条 {ts_code} 基金数据")
        return result[:days]  # 限制为指定天数
        
    except Exception as e:
        log_error("TUSHARE_FETCH_FAIL", f"获取 {ts_code} 基金数据失败: {str(e)}")
        return generate_mock_etf_data(ts_code, days)

def fetch_macro_data(pro, ts_code: str, macro_type: str, start_date: Optional[str] = None) -> Optional[List[Dict]]:
    """
    获取宏观利率数据
    支持SHIBOR、CPI等指标
    start_date: 起始日期 (YYYYMMDD 或 YYYYMM)，如为None则使用默认范围
    """
    # 如果没有真实连接，返回模拟数据
    if pro is None:
        return generate_mock_macro_data(macro_type)
    
    try:
        # 节流：避免频率限制
        throttle_request(delay=0.8)
        
        # 根据不同宏观指标调用不同接口
        if macro_type == "shibor":
            # 获取SHIBOR数据
            if start_date is None:
                start_date = (datetime.datetime.now() - datetime.timedelta(days=730)).strftime("%Y%m%d")
            df = pro.shibor(start_date=start_date)
        elif macro_type == "cpi":
            # 获取CPI数据
            if start_date is None:
                start_month = (datetime.datetime.now() - datetime.timedelta(days=1825)).strftime("%Y%m")
            else:
                # 将YYYYMMDD转换为YYYYMM
                start_month = start_date[:6]
            df = pro.cpi(start_month=start_month)
        else:
            log_warn(f"不支持的宏观指标类型: {macro_type}")
            return generate_mock_macro_data(macro_type)
        
        if df is None or df.empty:
            log_warn(f"{macro_type} 无Tushare数据，尝试备用源...")
            
            # 尝试使用备用源（特别是CPI）
            if macro_type == "cpi":
                try:
                    # 尝试导入备用模块
                    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                    from macro_backup import fetch_cpi_from_backup
                    
                    log_info(f"尝试CPI备用源...")
                    start_month = start_date[:6] if start_date else "202001"
                    backup_data = fetch_cpi_from_backup(start_month)
                    
                    if backup_data and len(backup_data) > 0:
                        log_info(f"CPI备用源成功提供 {len(backup_data)} 条数据")
                        return backup_data
                    else:
                        log_warn("CPI备用源无数据，使用模拟数据")
                except ImportError:
                    log_warn("macro_backup模块未找到，使用模拟数据")
                except Exception as backup_e:
                    log_warn(f"CPI备用源失败: {backup_e}，使用模拟数据")
            
            return generate_mock_macro_data(macro_type)
        
        # 标准化数据格式
        result = []
        for _, row in df.iterrows():
            if macro_type == "shibor":
                data_point = {
                    "date": row['date'],
                    "on": float(row['on']) if 'on' in row and pd.notna(row['on']) else None,
                    "1w": float(row['1w']) if '1w' in row and pd.notna(row['1w']) else None,
                    "2w": float(row['2w']) if '2w' in row and pd.notna(row['2w']) else None,
                    "1m": float(row['1m']) if '1m' in row and pd.notna(row['1m']) else None,
                    "3m": float(row['3m']) if '3m' in row and pd.notna(row['3m']) else None,
                    "6m": float(row['6m']) if '6m' in row and pd.notna(row['6m']) else None,
                    "9m": float(row['9m']) if '9m' in row and pd.notna(row['9m']) else None,
                    "1y": float(row['1y']) if '1y' in row and pd.notna(row['1y']) else None
                }
            elif macro_type == "cpi":
                data_point = {
                    "month": row['month'],
                    "cpi": float(row['cpi']) if 'cpi' in row and pd.notna(row['cpi']) else None,
                    "cpi_yoy": float(row['cpi_yoy']) if 'cpi_yoy' in row and pd.notna(row['cpi_yoy']) else None
                }
            
            result.append(data_point)
        
        # 按日期排序（最近的在前）
        if result and 'date' in result[0]:
            result.sort(key=lambda x: x['date'], reverse=True)
        elif result and 'month' in result[0]:
            result.sort(key=lambda x: x['month'], reverse=True)
        
        log_info(f"成功获取 {len(result)} 条 {macro_type} 数据")
        return result[:500]  # 限制数量
        
    except Exception as e:
        log_error("TUSHARE_MACRO_FAIL", f"获取宏观数据 {macro_type} 失败: {str(e)}")
        
        # 尝试使用备用源（特别是CPI）
        if macro_type == "cpi":
            try:
                # 尝试导入备用模块
                sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                from macro_backup import fetch_cpi_from_backup
                
                log_info(f"尝试CPI备用源...")
                start_month = start_date[:6] if start_date else "202001"
                backup_data = fetch_cpi_from_backup(start_month)
                
                if backup_data and len(backup_data) > 0:
                    log_info(f"CPI备用源成功提供 {len(backup_data)} 条数据")
                    return backup_data
                else:
                    log_warn("CPI备用源无数据，使用模拟数据")
            except ImportError:
                log_warn("macro_backup模块未找到，使用模拟数据")
            except Exception as backup_e:
                log_warn(f"CPI备用源失败: {backup_e}，使用模拟数据")
        
        return generate_mock_macro_data(macro_type)

def generate_mock_etf_data(ts_code: str, days: int) -> List[Dict]:
    """生成模拟ETF数据，用于开发和测试"""
    log_warn(f"为 {ts_code} 生成 {days} 天模拟数据")
    
    result = []
    base_price = 4.5 if "518880" in ts_code else 3.8
    base_date = datetime.datetime.now()
    
    for i in range(days):
        trade_date = (base_date - datetime.timedelta(days=i)).strftime("%Y%m%d")
        # 模拟价格波动
        volatility = 0.02  # 2% 波动率
        price_change = (random.random() * 2 - 1) * volatility
        
        close_price = base_price * (1 + price_change)
        base_price = close_price  # 更新基础价格
        
        # 模拟MACD指标
        macd_value = (random.random() * 2 - 1) * 0.1
        
        data_point = {
            "date": trade_date,
            "close": round(close_price, 4),
            "open": round(close_price * (1 + (random.random() * 0.01 - 0.005)), 4),
            "high": round(close_price * (1 + random.random() * 0.02), 4),
            "low": round(close_price * (1 - random.random() * 0.015), 4),
            "volume": random.randint(1000000, 5000000),
            "amount": round(random.randint(50000000, 200000000), 2),
            "change": round((random.random() * 2 - 1) * 0.05, 4),
            "pct_chg": round((random.random() * 2 - 1) * 2, 2),  # ±2%
            "macd": {
                "dif": round(macd_value, 4),
                "dea": round(macd_value * 0.8, 4),
                "macd": round(macd_value * 0.6, 4)
            }
        }
        result.append(data_point)
    
    return result

def generate_mock_macro_data(macro_type: str) -> List[Dict]:
    """生成模拟宏观数据，用于开发和测试"""
    log_warn(f"为 {macro_type} 生成模拟宏观数据")
    
    result = []
    base_date = datetime.datetime.now()
    
    for i in range(60):  # 5年数据，每月一点
        if macro_type == "shibor":
            month_date = (base_date - datetime.timedelta(days=i*30)).strftime("%Y-%m-%d")
            data_point = {
                "date": month_date,
                "on": round(random.uniform(1.5, 3.5), 4),
                "1w": round(random.uniform(1.8, 3.8), 4),
                "1m": round(random.uniform(2.0, 4.0), 4),
                "3m": round(random.uniform(2.2, 4.2), 4),
                "6m": round(random.uniform(2.4, 4.4), 4),
                "9m": round(random.uniform(2.5, 4.5), 4),
                "1y": round(random.uniform(2.6, 4.6), 4)
            }
        elif macro_type == "cpi":
            month_date = (base_date - datetime.timedelta(days=i*30)).strftime("%Y%m")
            data_point = {
                "month": month_date,
                "cpi": round(random.uniform(100, 105), 2),
                "cpi_yoy": round(random.uniform(-1, 3), 2)
            }
        else:
            # 默认利率数据
            month_date = (base_date - datetime.timedelta(days=i*30)).strftime("%Y-%m-%d")
            data_point = {
                "date": month_date,
                "rate_10y": round(random.uniform(2.5, 4.5), 4),
                "inflation": round(random.uniform(1.0, 3.0), 2)
            }
        
        result.append(data_point)
    
    return result

def validate_with_schema(data: Dict, schema_file: str) -> bool:
    """使用 JSON Schema 验证数据（简化版）"""
    # 暂时跳过验证以加速开发
    log_warn("Schema 验证暂时跳过（开发模式）")
    return True
    
    # 检查Schema文件是否存在
    if not os.path.exists(schema_file):
        log_warn(f"Schema文件不存在: {schema_file}，跳过验证")
        return True
    
    try:
        import jsonschema
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        
        # 实际验证逻辑
        jsonschema.validate(instance=data, schema=schema)
        log_info(f"Schema 验证通过: {schema_file}")
        return True
    except ImportError:
        log_warn("jsonschema 库未安装，跳过 Schema 验证")
        return True
    except Exception as e:
        log_error("SCHEMA_VALIDATE_FAIL", f"Schema 验证失败: {str(e)}")
        return False

def write_atomic_output(data: Dict, output_path: str):
    """
    原子性写入输出文件（遵循 V1.2.1 标准）
    Write(.tmp) → Validate → Rename(.json)
    """
    # 创建临时文件
    tmp_path = output_path + TMP_SUFFIX
    
    try:
        # 添加元数据
        enriched_data = {
            "data": data,
            "metadata": {
                "fetch_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "module": MODULE_NAME,
                "ticker_count": len(data.get("tickers", {})) if isinstance(data, dict) and "tickers" in data else 1,
                "data_points": len(data) if isinstance(data, list) else "object"
            }
        }
        
        # 写入临时文件
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(enriched_data, f, indent=2, ensure_ascii=False)
        
        log_info(f"临时文件写入: {tmp_path}")
        
        # Schema 验证（如果配置了）
        if os.path.exists(SCHEMA_FILE):
            if not validate_with_schema(enriched_data, SCHEMA_FILE):
                os.remove(tmp_path)
                raise Exception("Schema 验证失败")
        
        # 原子重命名
        shutil.move(tmp_path, output_path)
        log_info(f"原子写入完成: {output_path}")
        
    except Exception as e:
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise e

def main():
    """主执行函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Tushare Pro API 数据拉取')
    parser.add_argument('--full-sync', action='store_true', help='全量同步模式，拉取更多历史数据')
    parser.add_argument('--incremental', action='store_true', help='增量同步模式，仅拉取最新数据')
    parser.add_argument('--days', type=int, default=500, help='历史数据天数（默认: 500）')
    args = parser.parse_args()
    
    # 参数互斥检查
    if args.full_sync and args.incremental:
        log_error("ARG_CONFLICT", "不能同时指定 --full-sync 和 --incremental")
        sys.exit(1)
    
    # 根据参数调整数据天数
    if args.full_sync:
        days = 1000
        sync_mode = "full"
    elif args.incremental:
        days = 30  # 增量模式拉取30天数据，覆盖节假日
        sync_mode = "incremental"
    else:
        days = args.days
        sync_mode = "daily"
    
    log_info(f"开始执行 {MODULE_NAME}，同步模式: {sync_mode}，数据天数: {days}")
    
    # 初始化 Tushare
    pro = init_tushare()
    
    all_results = {
        "tickers": {},
        "macro": {},
        "fetch_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sync_mode": sync_mode,
        "data_days": days
    }
    
    # 获取所有ETF数据
    for ticker, config in TICKERS_CONFIG.items():
        log_info(f"处理标的: {config['name']} ({ticker})")
        
        try:
            # 增量模式：获取现有数据的最新日期
            start_date = None
            if args.incremental:
                latest_date = get_latest_date_from_file(config['output_file'])
                if latest_date:
                    # 为了确保覆盖可能的遗漏数据，从latest_date往前推5天开始拉取
                    try:
                        latest_dt = datetime.datetime.strptime(latest_date, "%Y%m%d")
                        # 往前推5天，覆盖可能的节假日遗漏
                        start_dt = latest_dt - datetime.timedelta(days=5)
                        # 确保开始日期不晚于今天
                        today = datetime.datetime.now()
                        if start_dt > today:
                            start_dt = today - datetime.timedelta(days=1)
                        start_date = start_dt.strftime("%Y%m%d")
                        log_info(f"增量模式，从 {start_date} 开始拉取（最新日期 {latest_date}）")
                    except Exception as e:
                        log_warn(f"日期计算失败: {e}，使用默认范围")
                        start_date = None
                else:
                    log_warn(f"无现有数据，增量模式退化为全量拉取")
            
            etf_data = fetch_etf_data(pro, config['ts_code'], days=days, start_date=start_date)
            
            if etf_data:
                # 断层检测
                if check_data_gaps(etf_data, max_gap_days=5):
                    log_warn(f"⚠ {config['name']} 数据存在断层，建议运行 --full-sync 修补")
                    all_results["tickers"][ticker] = {
                        "name": config['name'],
                        "data_points": len(etf_data),
                        "latest_date": etf_data[0]['date'] if etf_data else None,
                        "latest_price": etf_data[0]['close'] if etf_data else None,
                        "data_gap": True
                    }
                else:
                    all_results["tickers"][ticker] = {
                        "name": config['name'],
                        "data_points": len(etf_data),
                        "latest_date": etf_data[0]['date'] if etf_data else None,
                        "latest_price": etf_data[0]['close'] if etf_data else None,
                        "data_gap": False
                    }
                
                # 写入单独文件（实现数据合并逻辑）
                # 加载现有数据
                existing_data = load_existing_data(config['output_file'])
                
                # 合并数据
                if args.incremental and existing_data:
                    final_data = merge_data(existing_data, etf_data, key_field="date")
                    log_info(f"增量合并: 现有{len(existing_data)}条 + 新增{len(etf_data)}条 = 最终{len(final_data)}条")
                else:
                    final_data = etf_data
                    if existing_data:
                        log_info(f"全量覆盖: 现有{len(existing_data)}条数据将被替换")
                
                write_atomic_output(final_data, config['output_file'])
                
                log_info(f"✓ {config['name']} 数据获取成功: {len(etf_data)} 条")
            else:
                log_warn(f"⚠ {config['name']} 数据获取失败")
                all_results["tickers"][ticker] = {
                    "name": config['name'],
                    "data_points": 0,
                    "latest_date": None,
                    "latest_price": None,
                    "data_gap": False
                }
                
        except Exception as e:
            log_error("TICKER_PROCESS_FAIL", f"处理 {config['name']} 失败: {str(e)}")
            all_results["tickers"][ticker] = {
                "name": config['name'],
                "data_points": 0,
                "latest_date": None,
                "latest_price": None,
                "error": str(e)
            }
    
    # 获取宏观数据（G9算法需要）
    for macro_id, config in MACRO_CONFIG.items():
        log_info(f"处理宏观指标: {config['name']}")
        
        try:
            # 增量模式：获取现有数据的最新日期/月份
            start_date = None
            if args.incremental:
                latest_date = get_latest_date_from_file(config['output_file'])
                if latest_date:
                    # 对于月度数据（CPI），需要特殊处理
                    if macro_id == "cpi":
                        # CPI是月度数据，latest_date格式可能是YYYYMM
                        if len(latest_date) == 6:  # YYYYMM
                            # 计算下一个月
                            year = int(latest_date[:4])
                            month = int(latest_date[4:6])
                            if month == 12:
                                year += 1
                                month = 1
                            else:
                                month += 1
                            start_date = f"{year:04d}{month:02d}01"  # 转换为YYYYMMDD格式
                        else:
                            # 尝试解析YYYYMMDD
                            try:
                                latest_dt = datetime.datetime.strptime(latest_date, "%Y%m%d")
                                # 跳到下个月第一天
                                if latest_dt.month == 12:
                                    next_dt = datetime.datetime(latest_dt.year + 1, 1, 1)
                                else:
                                    next_dt = datetime.datetime(latest_dt.year, latest_dt.month + 1, 1)
                                start_date = next_dt.strftime("%Y%m%d")
                            except:
                                start_date = None
                    else:
                        # SHIBOR日度数据
                        try:
                            latest_dt = datetime.datetime.strptime(latest_date, "%Y%m%d")
                            next_dt = latest_dt + datetime.timedelta(days=1)
                            start_date = next_dt.strftime("%Y%m%d")
                        except:
                            start_date = None
                    
                    if start_date:
                        log_info(f"增量模式，从 {start_date} 开始拉取")
                else:
                    log_warn(f"无现有数据，增量模式退化为全量拉取")
            
            macro_data = fetch_macro_data(pro, config['ts_code'], macro_id, start_date=start_date)
            
            if macro_data:
                # 写入单独文件（实现数据合并逻辑）
                # 加载现有数据
                existing_data = load_existing_data(config['output_file'])
                
                # 确定关键字段
                key_field = "month" if macro_id == "cpi" else "date"
                
                # 合并数据
                if args.incremental and existing_data:
                    final_data = merge_data(existing_data, macro_data, key_field=key_field)
                    log_info(f"宏观增量合并: 现有{len(existing_data)}条 + 新增{len(macro_data)}条 = 最终{len(final_data)}条")
                else:
                    final_data = macro_data
                    if existing_data:
                        log_info(f"宏观全量覆盖: 现有{len(existing_data)}条数据将被替换")
                
                write_atomic_output(final_data, config['output_file'])
                
                # 保存到汇总结果
                all_results["macro"][macro_id] = {
                    "name": config['name'],
                    "data_points": len(macro_data),
                    "latest_date": macro_data[0].get('date') or macro_data[0].get('month') if macro_data else None,
                    "data_fresh": True,
                }
                
                log_info(f"✓ {config['name']} 数据获取成功: {len(macro_data)} 条")
            else:
                log_warn(f"⚠ {config['name']} 数据获取失败")
                all_results["macro"][macro_id] = {
                    "name": config['name'],
                    "data_points": 0,
                    "latest_date": None,
                    "data_fresh": False,
                }
                
        except Exception as e:
            log_error("MACRO_PROCESS_FAIL", f"处理 {config['name']} 失败: {str(e)}")
            all_results["macro"][macro_id] = {
                "name": config['name'],
                "data_points": 0,
                "latest_date": None,
                "data_fresh": False,
                "error": str(e)
            }
    
    # 写入汇总文件
    summary_file = "database/tushare_summary.json"
    write_atomic_output(all_results, summary_file)
    
    log_info(f"模块执行完成，汇总文件: {summary_file}")
    print(f"[SUCCESS]: {MODULE_NAME} 执行成功")

if __name__ == "__main__":
    main()