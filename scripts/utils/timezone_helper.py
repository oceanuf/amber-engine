#!/usr/bin/env python3
"""
时区统一工具 - 确保所有模块使用 GMT+8 时区
符合 V1.4.1 地基加固专项要求
"""

import datetime
import pytz
from typing import Optional

# 常量定义
TIMEZONE_GMT8 = pytz.timezone('Asia/Shanghai')  # GMT+8
TIMEZONE_UTC = pytz.utc

def get_gmt8_now() -> datetime.datetime:
    """
    获取当前 GMT+8 时间
    """
    utc_now = datetime.datetime.now(pytz.utc)
    gmt8_now = utc_now.astimezone(TIMEZONE_GMT8)
    return gmt8_now

def format_gmt8_timestamp(dt: Optional[datetime.datetime] = None, 
                         format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化 GMT+8 时间戳
    """
    if dt is None:
        dt = get_gmt8_now()
    
    # 确保时区为 GMT+8
    if dt.tzinfo is None:
        dt = TIMEZONE_GMT8.localize(dt)
    elif dt.tzinfo != TIMEZONE_GMT8:
        dt = dt.astimezone(TIMEZONE_GMT8)
    
    return dt.strftime(format_str)

def parse_to_gmt8(date_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime.datetime:
    """
    解析字符串到 GMT+8 时区
    """
    naive_dt = datetime.datetime.strptime(date_str, format_str)
    return TIMEZONE_GMT8.localize(naive_dt)

def get_gmt8_date() -> str:
    """
    获取当前 GMT+8 日期 (YYYY-MM-DD)
    """
    return format_gmt8_timestamp(format_str="%Y-%m-%d")

def get_gmt8_time() -> str:
    """
    获取当前 GMT+8 时间 (HH:MM:SS)
    """
    return format_gmt8_timestamp(format_str="%H:%M:%S")

def ensure_gmt8_timezone() -> None:
    """
    验证当前环境时区设置，如果不是 GMT+8 则发出警告
    """
    import time
    import os
    
    # 检查系统时区
    try:
        system_tz = time.tzname
        env_tz = os.environ.get('TZ', '未设置')
        
        current_time = datetime.datetime.now()
        gmt8_time = get_gmt8_now()
        
        # 如果时间差超过1小时，发出警告
        time_diff = abs((current_time - gmt8_time.replace(tzinfo=None)).total_seconds())
        if time_diff > 3600:  # 1小时
            print(f"[WARN] 时区不一致: 系统时区={system_tz}, 环境TZ={env_tz}")
            print(f"[WARN] 本地时间: {current_time}, GMT+8时间: {gmt8_time}")
            print(f"[WARN] 建议设置 TZ=Asia/Shanghai 环境变量")
    except Exception as e:
        print(f"[WARN] 检查时区时出错: {e}")

def log_with_gmt8(module_name: str, level: str, message: str) -> str:
    """
    生成带 GMT+8 时间戳的日志条目
    """
    timestamp = format_gmt8_timestamp()
    return f"[{timestamp}] [{module_name}:{level}] {message}"

# 测试代码
if __name__ == "__main__":
    print("时区统一工具测试")
    print("=" * 50)
    
    # 验证时区设置
    ensure_gmt8_timezone()
    
    # 测试函数
    print(f"当前GMT+8时间: {get_gmt8_now()}")
    print(f"格式化时间戳: {format_gmt8_timestamp()}")
    print(f"当前日期: {get_gmt8_date()}")
    print(f"当前时间: {get_gmt8_time()}")
    
    # 测试日志函数
    log_entry = log_with_gmt8("test_module", "INFO", "测试日志")
    print(f"日志条目: {log_entry}")
    
    print("=" * 50)
    print("时区工具测试完成")