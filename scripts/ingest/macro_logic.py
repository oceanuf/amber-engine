#!/usr/bin/env python3
"""
Ingest module for macroeconomic indicators - 符合 V1.2.1 标准
负责 M2、CPI 等宏观流动性指标（周/月更新频率）
标准输出: database/macro_indicators.json
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
MODULE_NAME = "ingest_macro_logic"
OUTPUT_FILE = "database/macro_indicators.json"
TMP_SUFFIX = ".tmp"
SCHEMA_FILE = "config/schema_macro.json"  # 验证用
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

def fetch_macro_data():
    """
    获取宏观经济指标数据（模拟实现）
    返回M2、CPI、PPI、PMI等关键指标
    """
    # 模拟 API 密钥检查
    api_key = os.environ.get("MACRO_API_KEY")
    if not api_key:
        log_warn("MACRO_API_KEY 未设置，使用模拟数据")
    
    # 模拟网络延迟
    time.sleep(0.4)
    
    # 模拟随机故障（测试错误处理）
    if random.random() < 0.1:  # 10% 概率模拟网络超时
        raise ConnectionError("模拟网络超时")
    
    # 当前时间戳
    current_time = datetime.datetime.now()
    fetch_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
    
    # 生成最近12个月的数据（月度指标）
    monthly_data = []
    for i in range(12):
        month_date = current_time - datetime.timedelta(days=30*i)
        month_str = month_date.strftime("%Y-%m")
        
        # 月度宏观经济指标
        monthly_data.append({
            "month": month_str,
            "m2_growth": f"{random.uniform(8.0, 10.5):.1f}%",  # M2同比增长
            "cpi": f"{random.uniform(1.5, 3.2):.1f}%",         # 居民消费价格指数
            "ppi": f"{random.uniform(-1.5, 2.5):.1f}%",        # 工业生产者出厂价格指数
            "pmi": f"{random.uniform(48.5, 52.5):.1f}",        # 采购经理指数
            "industrial_growth": f"{random.uniform(4.0, 8.5):.1f}%",  # 工业增加值增速
            "retail_sales_growth": f"{random.uniform(5.0, 10.0):.1f}%",  # 社会消费品零售总额增速
        })
    
    # 按月份降序排序
    monthly_data.sort(key=lambda x: x["month"], reverse=True)
    
    # 最新季度数据
    latest_quarter = {
        "quarter": "2026-Q1",
        "gdp_growth": f"{random.uniform(4.8, 5.5):.1f}%",
        "gdp_size": f"{random.uniform(120, 130):.1f}万亿元",
        "investment_growth": f"{random.uniform(3.5, 6.5):.1f}%",
        "export_growth": f"{random.uniform(2.0, 8.0):.1f}%",
        "import_growth": f"{random.uniform(1.5, 7.5):.1f}%",
    }
    
    # 金融流动性指标（周度）
    liquidity_indicators = {
        "shibor_overnight": f"{random.uniform(1.5, 2.5):.3f}%",
        "shibor_1w": f"{random.uniform(1.8, 2.8):.3f}%",
        "shibor_1m": f"{random.uniform(2.0, 3.0):.3f}%",
        "dr007": f"{random.uniform(1.8, 2.5):.3f}%",  # 存款类机构7天质押式回购利率
        "lpr_1y": "3.45%",  # 贷款市场报价利率1年期
        "lpr_5y": "4.20%",  # 贷款市场报价利率5年期
        "reserve_ratio": "7.0%",  # 存款准备金率
    }
    
    # 政策与市场情绪
    policy_indicators = {
        "monetary_policy_stance": "稳健中性",
        "fiscal_policy_stance": "积极有为",
        "risk_appetite": random.choice(["低", "中", "高"]),
        "liquidity_condition": random.choice(["宽松", "适度", "偏紧"]),
        "inflation_outlook": random.choice(["可控", "温和", "压力上升"]),
    }
    
    # 构建最终数据结构
    data = {
        "fetch_time": fetch_time,  # 抓取时间戳
        "data_period": {
            "latest_month": monthly_data[0]["month"] if monthly_data else "2026-03",
            "latest_quarter": latest_quarter["quarter"],
            "update_frequency": "月度更新，季度修正"
        },
        "monthly_indicators": monthly_data,
        "quarterly_indicators": latest_quarter,
        "liquidity_indicators": liquidity_indicators,
        "policy_indicators": policy_indicators,
        "data_source": "模拟数据 - 待接入国家统计局、央行数据",
        "data_quality": "模拟",
        "notes": "实际数据需从官方统计机构获取，此处为演示数据"
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
    log_info("开始执行宏观经济指标数据提取")
    
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
            log_info("获取宏观经济指标数据...")
            data = fetch_macro_data()
            
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
                log_info("宏观经济指标数据提取成功完成")
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