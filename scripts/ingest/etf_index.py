#!/usr/bin/env python3
"""
Ingest module for broad-based ETF indices - 符合 V1.2.1 标准
负责沪深 300、中证 500 等宽基 ETF 数据
标准输出: database/etf_index.json
"""

import os
import sys
import json
import tempfile
import shutil
import datetime
import time
import random

# 模块常量
MODULE_NAME = "ingest_etf_index"
OUTPUT_FILE = "database/etf_index.json"
TMP_SUFFIX = ".tmp"
SCHEMA_FILE = "config/schema_etf_index.json"  # 验证用
MAX_RETRIES = 3
RETRY_DELAY = 5  # 秒

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

def fetch_etf_data():
    """
    获取宽基 ETF 数据（模拟实现）
    返回主要宽基ETF的当前数据
    """
    # 模拟 API 密钥检查
    api_key = os.environ.get("ETF_API_KEY")
    if not api_key:
        log_warn("ETF_API_KEY 未设置，使用模拟数据")
    
    # 模拟网络延迟
    time.sleep(0.3)
    
    # 模拟随机故障（测试错误处理）
    if random.random() < 0.1:  # 10% 概率模拟网络超时
        raise ConnectionError("模拟网络超时")
    
    # 主要宽基ETF列表
    etf_list = [
        {"ticker": "510300", "name": "华泰柏瑞沪深300ETF", "index_name": "沪深300"},
        {"ticker": "510500", "name": "南方中证500ETF", "index_name": "中证500"},
        {"ticker": "159919", "name": "嘉实沪深300ETF", "index_name": "沪深300"},
        {"ticker": "159915", "name": "易方达创业板ETF", "index_name": "创业板指"},
        {"ticker": "588000", "name": "华夏上证科创板50ETF", "index_name": "科创50"},
        {"ticker": "510050", "name": "华夏上证50ETF", "index_name": "上证50"},
        {"ticker": "512100", "name": "南方中证1000ETF", "index_name": "中证1000"},
    ]
    
    # 当前时间戳
    current_time = datetime.datetime.now()
    fetch_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
    
    # 为每个ETF生成数据
    etf_data = []
    for etf in etf_list:
        # 基础价格（模拟）
        base_price = {
            "510300": 3.850, "510500": 5.620, "159919": 3.845,
            "159915": 2.150, "588000": 0.980, "510050": 2.560,
            "512100": 2.310
        }.get(etf["ticker"], 1.000)
        
        # 当日价格波动
        today_price = base_price + random.uniform(-0.02, 0.03)
        change_percent = (today_price - base_price) / base_price * 100
        
        # 生成最近5天的历史数据
        nav_history = []
        for i in range(5):
            date = current_time - datetime.timedelta(days=i)
            price = base_price + random.uniform(-0.05, 0.05)
            change = random.uniform(-0.5, 0.5)
            nav_history.append({
                "date": date.strftime("%Y-%m-%d"),
                "price": f"{price:.3f}",
                "change": f"{change:+.2f}%"
            })
        
        # 按日期降序排序
        nav_history.sort(key=lambda x: x["date"], reverse=True)
        
        etf_data.append({
            "ticker": etf["ticker"],
            "name": etf["name"],
            "index_name": etf["index_name"],
            "current_nav": f"{today_price:.3f}",
            "daily_change": f"{change_percent:+.2f}%",
            "ytd_return": f"{random.uniform(-5.0, 15.0):+.2f}%",
            "volume": f"{random.randint(100, 1000)}万手",
            "nav_history": nav_history,
            "last_updated": fetch_time  # 数据本身的时间戳
        })
    
    # 构建最终数据结构
    data = {
        "fetch_time": fetch_time,  # 抓取时间戳
        "data_source": "模拟数据 - 待接入真实API",
        "etf_count": len(etf_data),
        "etfs": etf_data
    }
    
    return data

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

def call_validate(tmp_path):
    """调用验证脚本"""
    validate_script = "scripts/validate.py"
    if not os.path.exists(validate_script):
        log_warn(f"验证脚本不存在: {validate_script}，跳过验证")
        return True
    
    # 检查 schema 文件是否存在
    if os.path.exists(SCHEMA_FILE):
        cmd = f"python3 {validate_script} --schema {SCHEMA_FILE} --file {tmp_path} --check-boundary"
    else:
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

def main():
    """主函数"""
    log_info("开始执行宽基 ETF 数据提取")
    
    # 检查输出目录是否存在
    output_dir = os.path.dirname(OUTPUT_FILE)
    if not os.path.exists(output_dir):
        log_info(f"创建输出目录: {output_dir}")
        os.makedirs(output_dir, exist_ok=True)
    
    # 临时文件路径
    tmp_path = OUTPUT_FILE + TMP_SUFFIX
    
    # 重试逻辑
    for attempt in range(MAX_RETRIES):
        try:
            if attempt > 0:
                log_info(f"重试尝试 {attempt}/{MAX_RETRIES}，等待 {RETRY_DELAY} 秒...")
                time.sleep(RETRY_DELAY)
            
            # 1. 获取数据
            log_info("获取宽基ETF数据...")
            data = fetch_etf_data()
            
            # 2. 写入临时文件
            log_info("写入临时文件...")
            if not write_temp_file(data, tmp_path):
                continue  # 重试
            
            # 3. 验证数据
            log_info("验证数据...")
            if not call_validate(tmp_path):
                # 验证失败，删除临时文件
                try:
                    os.unlink(tmp_path)
                except:
                    pass
                # 如果是 schema 不匹配，不应该重试
                if os.path.exists(SCHEMA_FILE):
                    log_error("SCHEMA_MISMATCH", "数据与 schema 不匹配，需要人工介入")
                    return 102  # Schema校验失败退出码
                continue  # 其他验证失败可重试
            
            # 4. 原子重命名
            log_info("执行原子重命名...")
            if atomic_rename(tmp_path, OUTPUT_FILE):
                log_info("宽基 ETF 数据提取成功完成")
                return 0  # 成功
            
        except ConnectionError as e:
            log_error("NET_TIMEOUT", f"网络超时: {e}")
            if attempt == MAX_RETRIES - 1:
                log_error("NET_TIMEOUT", f"达到最大重试次数 ({MAX_RETRIES})")
                return 101  # 网络超时退出码
            continue
        except Exception as e:
            log_error("UNKNOWN_ERROR", f"未预料的错误: {e}")
            import traceback
            traceback.print_exc()
            return 1  # 一般错误退出码
    
    # 所有重试都失败
    log_error("MAX_RETRIES_EXCEEDED", "所有重试尝试均失败")
    return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)