#!/usr/bin/env python3
"""
Storer 模块：数据入库与标准化存储 - 符合 V1.2.1 标准
标准输出: database/history_<ticker>.json (长期历史文件)
"""

import os
import sys
import json
import shutil
import datetime
import time
from decimal import Decimal, ROUND_HALF_UP

# 模块常量
MODULE_NAME = "storer_vault_storer"
CLEANED_DIR = "database/cleaned"
HISTORY_DIR = "database"
BACKUP_DIR = "_PRIVATE_DATA/backups"
TMP_SUFFIX = ".tmp"
BAK_SUFFIX = ".bak"
MAX_RETRIES = 2
RETRY_DELAY = 3  # 秒

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

def ensure_directories():
    """确保必要的目录存在"""
    os.makedirs(HISTORY_DIR, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    log_info(f"确保目录存在: {HISTORY_DIR}, {BACKUP_DIR}")

def create_backup(filepath):
    """创建备份文件（写前备份策略）"""
    if not os.path.exists(filepath):
        log_warn(f"文件不存在，无需备份: {filepath}")
        return True
    
    try:
        # 生成备份文件名（带时间戳）
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        basename = os.path.basename(filepath)
        backup_name = f"{basename}.{timestamp}{BAK_SUFFIX}"
        backup_path = os.path.join(BACKUP_DIR, backup_name)
        
        shutil.copy2(filepath, backup_path)
        
        # 设置备份文件权限为 600
        os.chmod(backup_path, 0o600)
        
        log_info(f"创建备份: {filepath} -> {backup_path}")
        return True
    except Exception as e:
        log_error("BACKUP_FAIL", f"创建备份失败: {e}")
        return False

def secure_file_permissions(filepath):
    """设置文件权限为 600（仅所有者可读写）"""
    try:
        os.chmod(filepath, 0o600)
        log_info(f"设置文件权限为 600: {filepath}")
        return True
    except Exception as e:
        log_error("PERMISSION_FAIL", f"设置文件权限失败: {e}")
        return False

def load_json_file(filepath):
    """加载 JSON 文件"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        log_info(f"加载文件成功: {filepath}")
        return data
    except Exception as e:
        log_error("FILE_LOAD_FAIL", f"加载文件失败: {e}")
        return None

def save_json_file(data, filepath, tmp_path):
    """保存 JSON 文件（原子写入协议）"""
    try:
        # 写入临时文件
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write('\n')  # 末尾换行符
        
        log_info(f"写入临时文件: {tmp_path}")
        
        # 验证临时文件（基本完整性检查）
        if not validate_json_file(tmp_path):
            os.unlink(tmp_path)
            return False
        
        # 原子重命名
        shutil.move(tmp_path, filepath)
        log_info(f"原子重命名完成: {filepath}")
        
        # 设置文件权限
        if not secure_file_permissions(filepath):
            return False
        
        return True
    except Exception as e:
        log_error("FILE_SAVE_FAIL", f"保存文件失败: {e}")
        # 清理临时文件
        try:
            os.unlink(tmp_path)
        except:
            pass
        return False

def validate_json_file(filepath):
    """验证 JSON 文件基本完整性"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 基本验证：必须是字典
        if not isinstance(data, dict):
            log_error("INVALID_JSON_FORMAT", f"JSON 数据必须是对象: {filepath}")
            return False
        
        # 检查必需字段（对于长期历史文件）
        if "ticker" not in data:
            log_error("MISSING_TICKER", f"缺少 ticker 字段: {filepath}")
            return False
        
        log_info(f"JSON 文件验证通过: {filepath}")
        return True
    except json.JSONDecodeError as e:
        log_error("INVALID_JSON", f"JSON 语法错误: {e}")
        return False
    except Exception as e:
        log_error("VALIDATE_FAIL", f"验证失败: {e}")
        return False

def merge_history_data(cleaned_data, existing_history):
    """
    合并清洗后数据到现有历史记录
    
    策略：
    1. 如果日期已存在，跳过（避免重复）
    2. 如果日期不存在，追加到历史记录
    3. 按日期降序排序（最新的在前）
    """
    ticker = cleaned_data.get('ticker', '未知')
    log_info(f"开始合并历史数据: {ticker}")
    
    # 提取清洗后的历史记录
    cleaned_history = cleaned_data.get('nav_history', [])
    if not cleaned_history:
        log_error("EMPTY_CLEANED_HISTORY", f"清洗后历史记录为空: {ticker}")
        return None
    
    # 初始化或获取现有历史记录
    if existing_history is None:
        # 新文件，创建基础结构
        history_data = {
            "ticker": ticker,
            "name": cleaned_data.get('name', ''),
            "history": [],
            "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "created_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source_module": MODULE_NAME
        }
        existing_dates = set()
    else:
        # 现有文件，使用现有结构
        history_data = existing_history
        if "history" not in history_data:
            history_data["history"] = []
        existing_dates = {item.get('date') for item in history_data["history"] if item.get('date')}
    
    # 统计信息
    added_count = 0
    skipped_count = 0
    
    # 合并逻辑
    for item in cleaned_history:
        date_str = item.get('date')
        if not date_str:
            log_warn(f"历史记录缺少日期字段，跳过")
            continue
        
        # 检查日期是否已存在
        if date_str in existing_dates:
            skipped_count += 1
            log_info(f"日期已存在，跳过: {date_str}")
            continue
        
        # 添加到历史记录
        history_data["history"].append(item)
        existing_dates.add(date_str)
        added_count += 1
        log_info(f"添加新历史记录: {date_str}")
    
    # 按日期降序排序（最新的在前）
    history_data["history"].sort(key=lambda x: x.get('date', ''), reverse=True)
    
    # 更新最后更新时间
    history_data["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    history_data["update_count"] = history_data.get("update_count", 0) + 1
    
    log_info(f"合并完成: {ticker}, 新增: {added_count}, 跳过: {skipped_count}, 总数: {len(history_data['history'])}")
    return history_data

def process_single_etf(cleaned_data, history_path):
    """处理单个 ETF 数据"""
    ticker = cleaned_data.get('ticker', '未知')
    log_info(f"处理 ETF: {ticker}")
    
    # 1. 创建备份（如果历史文件存在）
    if os.path.exists(history_path):
        if not create_backup(history_path):
            log_error("BACKUP_REQUIRED", f"备份失败，停止处理: {ticker}")
            return False
    else:
        log_info(f"历史文件不存在，将创建新文件: {history_path}")
    
    # 2. 加载现有历史数据（如果存在）
    existing_history = None
    if os.path.exists(history_path):
        existing_history = load_json_file(history_path)
        if existing_history is None:
            log_error("HISTORY_LOAD_FAIL", f"加载历史文件失败: {history_path}")
            return False
    
    # 3. 合并数据
    merged_data = merge_history_data(cleaned_data, existing_history)
    if merged_data is None:
        log_error("MERGE_FAIL", f"数据合并失败: {ticker}")
        return False
    
    # 4. 准备临时文件路径
    tmp_path = history_path + TMP_SUFFIX
    
    # 5. 保存合并后的数据（原子写入）
    if not save_json_file(merged_data, history_path, tmp_path):
        log_error("SAVE_FAIL", f"保存合并数据失败: {ticker}")
        return False
    
    log_info(f"ETF 数据处理成功: {ticker}")
    return True

def process_etf_index(cleaned_data, base_path):
    """处理 ETF 指数数据（多个 ETF 的集合）"""
    if 'etfs' not in cleaned_data:
        log_error("INVALID_ETF_INDEX", f"ETF 指数数据缺少 'etfs' 字段")
        return False
    
    etfs = cleaned_data.get('etfs', [])
    log_info(f"处理 ETF 指数数据，包含 {len(etfs)} 个 ETF")
    
    success_count = 0
    failed_count = 0
    
    for etf in etfs:
        ticker = etf.get('ticker')
        if not ticker:
            log_warn(f"ETF 缺少 ticker 字段，跳过")
            failed_count += 1
            continue
        
        # 为每个 ETF 创建历史文件路径
        history_path = os.path.join(HISTORY_DIR, f"history_{ticker}.json")
        
        if process_single_etf(etf, history_path):
            success_count += 1
        else:
            failed_count += 1
    
    log_info(f"ETF 指数数据处理完成，成功: {success_count}, 失败: {failed_count}")
    return failed_count == 0

def identify_data_type(cleaned_data):
    """识别数据类型"""
    if 'etfs' in cleaned_data and isinstance(cleaned_data['etfs'], list):
        return 'etf_index'
    elif 'ticker' in cleaned_data and 'nav_history' in cleaned_data:
        return 'single_etf'
    else:
        return 'unknown'

def process_cleaned_file(cleaned_path):
    """处理单个清洗后文件"""
    log_info(f"处理清洗后文件: {cleaned_path}")
    
    # 1. 加载清洗后数据
    cleaned_data = load_json_file(cleaned_path)
    if cleaned_data is None:
        log_error("CLEANED_DATA_LOAD_FAIL", f"加载清洗后数据失败: {cleaned_path}")
        return False
    
    # 2. 识别数据类型
    data_type = identify_data_type(cleaned_data)
    
    # 3. 根据数据类型处理
    if data_type == 'etf_index':
        # ETF 指数数据，为每个 ETF 创建单独的历史文件
        base_path = os.path.join(HISTORY_DIR, "etf_index")
        return process_etf_index(cleaned_data, base_path)
    
    elif data_type == 'single_etf':
        # 单个 ETF 数据
        ticker = cleaned_data.get('ticker', 'unknown')
        history_path = os.path.join(HISTORY_DIR, f"history_{ticker}.json")
        return process_single_etf(cleaned_data, history_path)
    
    else:
        log_error("UNSUPPORTED_DATA_TYPE", f"不支持的数据类型: {data_type}")
        return False

def main():
    """主函数"""
    log_info("开始执行数据入库任务")
    
    # 确保目录存在
    ensure_directories()
    
    # 获取清洗后文件列表
    cleaned_files = []
    if os.path.exists(CLEANED_DIR):
        for filename in os.listdir(CLEANED_DIR):
            if filename.endswith('_cleaned.json'):
                cleaned_path = os.path.join(CLEANED_DIR, filename)
                cleaned_files.append(cleaned_path)
    
    if not cleaned_files:
        log_error("NO_CLEANED_FILES", f"未找到清洗后文件: {CLEANED_DIR}/*_cleaned.json")
        return 1
    
    log_info(f"找到 {len(cleaned_files)} 个清洗后文件")
    
    # 重试逻辑
    success_count = 0
    failed_count = 0
    
    for cleaned_path in cleaned_files:
        for attempt in range(MAX_RETRIES):
            if attempt > 0:
                log_info(f"重试尝试 {attempt}/{MAX_RETRIES}，等待 {RETRY_DELAY} 秒...")
                time.sleep(RETRY_DELAY)
            
            try:
                if process_cleaned_file(cleaned_path):
                    success_count += 1
                    break  # 成功，跳出重试循环
                else:
                    if attempt == MAX_RETRIES - 1:
                        log_error("PROCESS_FAILED", f"文件处理失败达到最大重试次数: {cleaned_path}")
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
        log_info(f"所有文件入库成功 ({success_count}/{len(cleaned_files)})")
        return 0
    else:
        log_error("PARTIAL_FAILURE", f"部分文件入库失败 ({failed_count}/{len(cleaned_files)})")
        return 2

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)