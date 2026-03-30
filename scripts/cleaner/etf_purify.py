#!/usr/bin/env python3
"""
Cleaner 模块：ETF 数据净化与验伪 - 符合 V1.2.1 标准
标准输出: database/cleaned/etf_index.json, database/cleaned/518880.json 等
"""

import os
import sys
import json
import tempfile
import shutil
import datetime
import time
import re
from decimal import Decimal, ROUND_HALF_UP

# 模块常量
MODULE_NAME = "cleaner_etf_purify"
CLEANED_DIR = "database/cleaned"
TMP_SUFFIX = ".tmp"
INPUT_DIR = "database"
SCHEMA_FILE = "config/schema_cleaned.json"  # 清洗后数据 Schema
MAX_RETRIES = 2
RETRY_DELAY = 3  # 秒

# 清洗配置
DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')
DECIMAL_PLACES = 4
ABNORMAL_CHANGE_THRESHOLD = 10.0  # ±10% 单日波动阈值（除非涨跌停）

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
    # 同时打印到 stdout 便于调试
    print(f"[{timestamp}] [{MODULE_NAME}:ERROR] {code}: {msg}", file=sys.stdout)

def parse_percentage(value_str):
    """解析百分比字符串，如 '+1.23%' 或 '-0.45%'，返回浮点数"""
    if not value_str or value_str.strip() == '':
        return None
    
    try:
        # 移除百分号，转换为浮点数
        cleaned = value_str.strip().rstrip('%')
        return float(cleaned)
    except (ValueError, AttributeError):
        return None

def parse_price(price_str):
    """解析价格字符串，返回 Decimal 对象"""
    if not price_str or price_str.strip() == '':
        return None
    
    try:
        return Decimal(str(price_str).strip())
    except:
        return None

def normalize_date(date_str):
    """标准化日期格式为 YYYY-MM-DD"""
    if not date_str:
        return None
    
    # 尝试解析常见格式
    try:
        # 如果已经是 YYYY-MM-DD 格式，直接返回
        if DATE_PATTERN.match(date_str):
            return date_str
        
        # 尝试解析其他格式（这里可以根据需要扩展）
        # 例如：YYYY/MM/DD, YYYY.MM.DD 等
        # 目前只支持标准格式
        log_warn(f"日期格式不标准: {date_str}")
        return None
    except:
        return None

def normalize_price(price):
    """标准化价格到指定小数位数"""
    if price is None:
        return None
    
    try:
        # 使用 Decimal 进行四舍五入
        quantizer = Decimal('0.' + '0' * (DECIMAL_PLACES - 1) + '1')
        normalized = price.quantize(quantizer, rounding=ROUND_HALF_UP)
        return str(normalized)
    except:
        return str(price)

def forward_fill_missing_prices(history):
    """向前填充缺失的价格数据"""
    if not history:
        return history
    
    # 按日期排序（升序，最早的在前）
    sorted_history = sorted(history, key=lambda x: x.get('date', ''))
    
    last_valid_price = None
    last_valid_change = None
    
    for item in sorted_history:
        price = parse_price(item.get('price'))
        change = parse_percentage(item.get('change'))
        
        # 如果价格缺失或为0，使用前一个有效值
        if price is None or price == 0:
            if last_valid_price is not None:
                item['price'] = normalize_price(last_valid_price)
                item['change'] = f"{0.0:+.2f}%" if last_valid_change is None else f"{last_valid_change:+.2f}%"
                log_warn(f"价格缺失，向前填充: {item.get('date')} = {last_valid_price}")
            else:
                # 没有前值可填充，标记为错误
                log_error("MISSING_DATA", f"历史数据中价格缺失且无前值可填充: {item.get('date')}")
                return None
        else:
            last_valid_price = price
            last_valid_change = change
    
    # 重新按日期降序排序（最新的在前）
    sorted_history.sort(key=lambda x: x.get('date', ''), reverse=True)
    return sorted_history

def detect_abnormal_changes(history):
    """检测异常波动"""
    warnings = []
    
    for i, item in enumerate(history):
        change = parse_percentage(item.get('change'))
        if change is None:
            continue
        
        # 检查是否超过阈值
        if abs(change) > ABNORMAL_CHANGE_THRESHOLD:
            date_str = item.get('date', '未知日期')
            # 检查是否为可能的涨跌停情况（±10% 恰好是阈值）
            if abs(change) >= 9.9 and abs(change) <= 10.1:
                log_warn(f"疑似涨跌停: {date_str} 涨跌幅 {change:.2f}%")
            else:
                warnings.append(f"异常波动: {date_str} 涨跌幅 {change:.2f}% (阈值: ±{ABNORMAL_CHANGE_THRESHOLD}%)")
    
    return warnings

def clean_etf_data(raw_data):
    """清洗单个 ETF 数据"""
    ticker = raw_data.get('ticker', '未知')
    log_info(f"开始清洗 ETF: {ticker}")
    
    # 1. 检查必需字段
    required_fields = ['ticker', 'name', 'nav_history']
    missing = [f for f in required_fields if f not in raw_data]
    if missing:
        log_error("MISSING_REQUIRED_FIELDS", f"缺少必需字段: {missing}")
        return None
    
    # 2. 处理 nav_history
    history = raw_data.get('nav_history', [])
    if not history:
        log_error("EMPTY_HISTORY", f"ETF {ticker} 历史数据为空")
        return None
    
    # 3. 向前填充缺失价格
    cleaned_history = forward_fill_missing_prices(history)
    if cleaned_history is None:
        return None
    
    # 4. 检测异常波动
    abnormal_warnings = detect_abnormal_changes(cleaned_history)
    if abnormal_warnings:
        for warning in abnormal_warnings:
            log_warn(warning)
    
    # 5. 标准化格式
    for item in cleaned_history:
        # 标准化日期
        date_str = item.get('date')
        normalized_date = normalize_date(date_str)
        if normalized_date:
            item['date'] = normalized_date
        else:
            log_error("INVALID_DATE_FORMAT", f"无效日期格式: {date_str}")
            return None
        
        # 标准化价格和涨跌幅
        price = parse_price(item.get('price'))
        if price is not None:
            item['price'] = normalize_price(price)
        
        change = parse_percentage(item.get('change'))
        if change is not None:
            item['change'] = f"{change:+.2f}%"
    
    # 6. 更新当前净值（如果存在）
    cleaned_data = raw_data.copy()
    cleaned_data['nav_history'] = cleaned_history
    
    if 'current_nav' in cleaned_data:
        current_price = parse_price(cleaned_data['current_nav'])
        if current_price is not None:
            cleaned_data['current_nav'] = normalize_price(current_price)
    
    # 7. 添加清洗元数据
    cleaned_data['cleaned_time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cleaned_data['cleaned_by'] = MODULE_NAME
    
    log_info(f"ETF {ticker} 清洗完成，历史记录数: {len(cleaned_history)}")
    return cleaned_data

def clean_etf_index_data(raw_data):
    """清洗 ETF 指数数据（多个 ETF 的集合）"""
    if 'etfs' not in raw_data:
        log_error("INVALID_ETF_INDEX", "ETF 指数数据缺少 'etfs' 字段")
        return None
    
    log_info(f"开始清洗 ETF 指数数据，包含 {len(raw_data['etfs'])} 个 ETF")
    
    cleaned_etfs = []
    failed_count = 0
    
    for etf in raw_data['etfs']:
        cleaned = clean_etf_data(etf)
        if cleaned is not None:
            cleaned_etfs.append(cleaned)
        else:
            failed_count += 1
    
    if failed_count > 0:
        log_warn(f"{failed_count} 个 ETF 清洗失败")
    
    # 如果所有 ETF 都失败，返回 None
    if len(cleaned_etfs) == 0:
        log_error("ALL_ETFS_FAILED", "所有 ETF 清洗失败")
        return None
    
    # 构建清洗后的数据
    cleaned_data = raw_data.copy()
    cleaned_data['etfs'] = cleaned_etfs
    cleaned_data['cleaned_time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cleaned_data['cleaned_by'] = MODULE_NAME
    cleaned_data['cleaned_count'] = len(cleaned_etfs)
    cleaned_data['failed_count'] = failed_count
    
    log_info(f"ETF 指数数据清洗完成，成功: {len(cleaned_etfs)}, 失败: {failed_count}")
    return cleaned_data

def identify_data_type(raw_data):
    """识别数据类型"""
    if 'etfs' in raw_data and isinstance(raw_data['etfs'], list):
        return 'etf_index'
    elif 'ticker' in raw_data and 'nav_history' in raw_data:
        return 'single_etf'
    else:
        return 'non_etf'  # 非ETF数据，跳过清洗

def write_temp_file(data, tmp_path):
    """写入临时文件，确保原子性"""
    try:
        # 创建父目录（如果不存在）
        os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
        
        # 写入临时文件
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write('\n')  # 末尾换行符，便于验证
        
        log_info(f"临时文件已写入: {tmp_path}")
        return True
    except (IOError, OSError, TypeError) as e:
        log_error("FILE_WRITE_FAIL", f"写入临时文件失败: {e}")
        return False

def call_validate(tmp_path, data_type='etf_index'):
    """调用验证脚本（如果存在）"""
    validate_script = "scripts/validate.py"
    if not os.path.exists(validate_script):
        log_warn(f"验证脚本不存在: {validate_script}，跳过验证")
        return True
    
    # 非ETF数据跳过schema验证，只进行基本验证
    if data_type == 'non_etf':
        log_info(f"非ETF数据，跳过schema验证: {tmp_path}")
        cmd = f"python3 {validate_script} --file {tmp_path}"
    else:
        # 检查 schema 文件是否存在
        schema_file = SCHEMA_FILE
        if os.path.exists(schema_file):
            # 添加数值边界检查参数
            cmd = f"python3 {validate_script} --schema {schema_file} --file {tmp_path} --check-boundary"
        else:
            log_warn(f"清洗后数据 Schema 不存在: {schema_file}，使用基本验证")
            cmd = f"python3 {validate_script} --file {tmp_path} --check-boundary"
    
    log_info(f"执行验证: {cmd}")
    exit_code = os.system(cmd)
    
    if exit_code == 0:
        log_info("验证通过")
        return True
    else:
        log_error("VALIDATE_FAIL", f"验证失败，退出码: {exit_code}")
        return False

def atomic_rename(tmp_path, final_path):
    """原子重命名临时文件到最终路径"""
    try:
        shutil.move(tmp_path, final_path)
        log_info(f"原子重命名完成: {final_path}")
        return True
    except (IOError, OSError) as e:
        log_error("ATOMIC_RENAME_FAIL", f"原子重命名失败: {e}")
        # 清理临时文件
        try:
            os.unlink(tmp_path)
        except:
            pass
        return False

def clean_single_file(input_path):
    """清洗单个文件"""
    log_info(f"处理输入文件: {input_path}")
    
    # 读取原始数据
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except Exception as e:
        log_error("FILE_READ_FAIL", f"读取文件失败: {e}")
        return False
    
    # 识别数据类型
    data_type = identify_data_type(raw_data)
    
    # 根据数据类型调用不同的清洗函数
    if data_type == 'etf_index':
        cleaned_data = clean_etf_index_data(raw_data)
    elif data_type == 'single_etf':
        cleaned_data = clean_etf_data(raw_data)
    elif data_type == 'non_etf':
        # 非ETF数据，只添加清洗元数据，不进行深度清洗
        log_info(f"非ETF数据，跳过深度清洗: {input_path}")
        cleaned_data = raw_data.copy()
        cleaned_data['cleaned_time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cleaned_data['cleaned_by'] = MODULE_NAME
    else:
        log_error("UNSUPPORTED_DATA_TYPE", f"不支持的数据类型: {data_type}")
        return False
    
    if cleaned_data is None:
        log_error("CLEANING_FAILED", f"数据清洗失败: {input_path}")
        return False
    
    # 确定输出路径
    filename = os.path.basename(input_path)
    output_filename = filename.replace('.json', '_cleaned.json')
    output_path = os.path.join(CLEANED_DIR, output_filename)
    
    # 临时文件路径
    tmp_path = output_path + TMP_SUFFIX
    
    # 1. 写入临时文件
    if not write_temp_file(cleaned_data, tmp_path):
        return False
    
    # 2. 验证数据
    if not call_validate(tmp_path, data_type):
        # 验证失败，删除临时文件
        try:
            os.unlink(tmp_path)
        except:
            pass
        return False
    
    # 3. 原子重命名
    if not atomic_rename(tmp_path, output_path):
        return False
    
    log_info(f"清洗完成: {input_path} -> {output_path}")
    return True

def main():
    """主函数"""
    log_info("开始执行 ETF 数据清洗")
    
    # 确保输出目录存在
    os.makedirs(CLEANED_DIR, exist_ok=True)
    
    # 获取输入文件列表
    input_files = []
    if os.path.exists(INPUT_DIR):
        for filename in os.listdir(INPUT_DIR):
            if filename.endswith('.json') and not filename.endswith('_cleaned.json'):
                input_path = os.path.join(INPUT_DIR, filename)
                input_files.append(input_path)
    
    if not input_files:
        log_error("NO_INPUT_FILES", f"未找到输入文件: {INPUT_DIR}/*.json")
        return 1
    
    log_info(f"找到 {len(input_files)} 个输入文件")
    
    # 重试逻辑
    success_count = 0
    failed_count = 0
    
    for input_path in input_files:
        for attempt in range(MAX_RETRIES):
            if attempt > 0:
                log_info(f"重试尝试 {attempt}/{MAX_RETRIES}，等待 {RETRY_DELAY} 秒...")
                time.sleep(RETRY_DELAY)
            
            try:
                if clean_single_file(input_path):
                    success_count += 1
                    break  # 成功，跳出重试循环
                else:
                    if attempt == MAX_RETRIES - 1:
                        log_error("CLEANING_FAILED", f"文件清洗失败达到最大重试次数: {input_path}")
                        failed_count += 1
                    continue  # 继续重试
            except Exception as e:
                log_error("UNEXPECTED_ERROR", f"处理文件时发生异常: {e}")
                import traceback
                traceback.print_exc()
                if attempt == MAX_RETRIES - 1:
                    failed_count += 1
    
    # 总结
    if failed_count == 0:
        log_info(f"所有文件清洗成功 ({success_count}/{len(input_files)})")
        return 0
    else:
        log_error("PARTIAL_FAILURE", f"部分文件清洗失败 ({failed_count}/{len(input_files)})")
        return 2

if __name__ == "__main__":
    import time
    exit_code = main()
    sys.exit(exit_code)