#!/usr/bin/env python3
"""
Ingest module for market sentiment indicators - 符合 V1.2.1 标准
负责恐慌指数或市场热度抓取
标准输出: database/sentiment_indicators.json
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
MODULE_NAME = "ingest_sentiment_monitor"
OUTPUT_FILE = "database/sentiment_indicators.json"
TMP_SUFFIX = ".tmp"
SCHEMA_FILE = "config/schema_sentiment.json"  # 验证用
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

def fetch_sentiment_data():
    """
    获取市场情绪指标数据（模拟实现）
    返回恐慌指数、市场热度、情绪分数等
    """
    # 模拟 API 密钥检查
    api_key = os.environ.get("SENTIMENT_API_KEY")
    if not api_key:
        log_warn("SENTIMENT_API_KEY 未设置，使用模拟数据")
    
    # 模拟网络延迟
    time.sleep(0.3)
    
    # 模拟随机故障（测试错误处理）
    if random.random() < 0.1:  # 10% 概率模拟网络超时
        raise ConnectionError("模拟网络超时")
    
    # 当前时间戳
    current_time = datetime.datetime.now()
    fetch_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
    
    # 基础市场数据
    market_conditions = {
        "shanghai_composite": {
            "index": "上证指数",
            "current": f"{random.uniform(3000, 3200):.2f}",
            "change": f"{random.uniform(-1.5, 2.5):+.2f}%",
            "volume": f"{random.randint(3000, 5000)}亿元"
        },
        "shenzhen_component": {
            "index": "深证成指",
            "current": f"{random.uniform(9500, 10500):.2f}",
            "change": f"{random.uniform(-1.8, 2.8):+.2f}%",
            "volume": f"{random.randint(4000, 6000)}亿元"
        },
        "chinese_50": {
            "index": "创业板指",
            "current": f"{random.uniform(1800, 2200):.2f}",
            "change": f"{random.uniform(-2.5, 3.5):+.2f}%",
            "volume": f"{random.randint(1500, 2500)}亿元"
        }
    }
    
    # 恐慌指数 (VIX 类似物)
    fear_greed_index = random.randint(20, 80)  # 0-100, 0=极度恐慌, 100=极度贪婪
    
    # 情绪分数 (综合指标)
    sentiment_score = random.randint(30, 70)  # 0-100, 越高越乐观
    
    # 市场热度指标
    market_heat = {
        "turnover_rate": f"{random.uniform(0.8, 2.5):.2f}%",  # 换手率
        "advance_decline_ratio": f"{random.uniform(0.5, 2.0):.2f}",  # 涨跌比
        "limit_up_count": random.randint(30, 150),  # 涨停家数
        "limit_down_count": random.randint(5, 50),  # 跌停家数
        "volume_concentration": f"{random.uniform(30, 70):.1f}%",  # 成交量集中度
    }
    
    # 资金流向
    capital_flow = {
        "northbound_sh": f"{random.uniform(-50, 100):+.1f}亿元",  # 沪股通
        "northbound_sz": f"{random.uniform(-30, 80):+.1f}亿元",  # 深股通
        "main_inflow": f"{random.uniform(-100, 300):+.1f}亿元",  # 主力资金流入
        "retail_inflow": f"{random.uniform(-200, 200):+.1f}亿元",  # 散户资金流入
        "sector_rotation": random.choice(["金融", "科技", "消费", "周期", "均衡"])
    }
    
    # 波动率指标
    volatility_indicators = {
        "historical_volatility_30d": f"{random.uniform(15, 35):.1f}%",
        "implied_volatility": f"{random.uniform(18, 40):.1f}%",
        "volatility_index": f"{random.uniform(20, 45):.1f}",
        "max_drawdown_30d": f"{random.uniform(5, 15):.1f}%",
        "sharpe_ratio_30d": f"{random.uniform(0.5, 2.5):.2f}",
    }
    
    # 社交媒体情绪
    social_sentiment = {
        "weibo_finance_buzz": random.randint(5000, 20000),  # 微博财经话题热度
        "eastmoney_comments_sentiment": random.choice(["偏空", "中性", "偏多"]),
        "stock_forum_activity": f"{random.uniform(60, 95):.1f}%",  # 股票论坛活跃度
        "news_sentiment_score": random.randint(40, 80),  # 新闻情绪分数
        "search_volume_index": random.randint(50, 150),  # 搜索量指数
    }
    
    # 技术指标情绪
    technical_sentiment = {
        "rsi_14": random.randint(30, 70),  # 相对强弱指数
        "macd_signal": random.choice(["金叉", "死叉", "中性"]),
        "bollinger_band_position": random.choice(["上轨", "中轨", "下轨"]),
        "moving_average_alignment": random.choice(["多头排列", "空头排列", "纠结"]),
        "support_resistance_level": random.choice(["强支撑", "弱支撑", "强阻力", "弱阻力"]),
    }
    
    # 构建最终数据结构
    data = {
        "fetch_time": fetch_time,  # 抓取时间戳
        "market_conditions": market_conditions,
        "fear_greed_index": fear_greed_index,
        "sentiment_score": sentiment_score,
        "sentiment_level": (
            "极度恐慌" if fear_greed_index < 25 else
            "恐慌" if fear_greed_index < 40 else
            "中性" if fear_greed_index < 60 else
            "贪婪" if fear_greed_index < 75 else "极度贪婪"
        ),
        "market_heat": market_heat,
        "capital_flow": capital_flow,
        "volatility_indicators": volatility_indicators,
        "social_sentiment": social_sentiment,
        "technical_sentiment": technical_sentiment,
        "composite_indicators": {
            "risk_appetite": random.randint(30, 80),  # 风险偏好指数
            "market_stability": random.randint(40, 90),  # 市场稳定度
            "liquidity_score": random.randint(50, 95),  # 流动性评分
            "momentum_strength": random.randint(20, 85),  # 动量强度
        },
        "data_source": "模拟数据 - 待接入东方财富、同花顺、新浪财经等",
        "update_frequency": "每日更新",
        "data_quality": "模拟",
        "notes": "情绪指标为综合多个数据源计算得出，实际数据需接入实时API"
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
        cmd = f"python3 {validate_script} --schema {SCHEMA_FILE} --file {tmp_path}"
    else:
        cmd = f"python3 {validate_script} --file {tmp_path}"
    
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
    log_info("开始执行市场情绪指标数据提取")
    
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
            log_info("获取市场情绪指标数据...")
            data = fetch_sentiment_data()
            
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
                log_info("市场情绪指标数据提取成功完成")
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