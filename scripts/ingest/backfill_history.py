#!/usr/bin/env python3
"""
历史数据暴力回填脚本 - 为个股补充完整历史数据
目标：解决数据贫血问题，支持深蓝算法计算历史百分位
"""

import os
import sys
import json
import tempfile
import shutil
import datetime
import time
import logging
from typing import Dict, List, Any, Optional
import tushare as ts
import pandas as pd

# 配置
TUSHARE_TOKEN = os.environ.get("TUSHARE_TOKEN", "")
if not TUSHARE_TOKEN:
    # 尝试从 secrets.json 加载
    try:
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        secrets_path = "_PRIVATE_DATA/secrets.json"
        if os.path.exists(secrets_path):
            with open(secrets_path, 'r', encoding='utf-8') as f:
                secrets = json.load(f)
                TUSHARE_TOKEN = secrets.get("TUSHARE_TOKEN", "")
    except:
        pass

if not TUSHARE_TOKEN:
    print("[ERR]: TUSHARE_TOKEN 未配置", file=sys.stderr)
    sys.exit(1)

# 初始化 Tushare Pro
ts.set_token(TUSHARE_TOKEN)
pro = ts.pro_api()

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("backfill_history")

def ensure_directory(path: str):
    """确保目录存在"""
    os.makedirs(os.path.dirname(path), exist_ok=True)

def atomic_write(data: Dict, output_path: str, schema_validation: bool = True):
    """
    原子性写入文件（遵循 V1.2.1 协议）
    """
    # 创建临时文件
    temp_path = output_path + ".tmp"
    
    try:
        # 写入临时文件
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # 简单的数据验证
        if schema_validation:
            # 检查必要字段
            if "ticker" not in data:
                raise ValueError("缺少 ticker 字段")
            if "history" not in data:
                raise ValueError("缺少 history 字段")
            if not isinstance(data["history"], list):
                raise ValueError("history 必须是列表")
            
            # 检查历史数据格式
            for item in data["history"][:10]:  # 抽样检查
                if "date" not in item or "price" not in item:
                    raise ValueError("历史记录缺少 date 或 price 字段")
        
        # 验证通过，重命名
        shutil.move(temp_path, output_path)
        logger.info(f"数据已原子写入: {output_path}")
        
    except Exception as e:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)
        logger.error(f"原子写入失败: {e}")
        raise

def fetch_daily_data(ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取日线复权数据
    """
    logger.info(f"获取 {ts_code} 日线数据: {start_date} 到 {end_date}")
    
    try:
        # 使用 pro.daily 获取日线数据（前复权）
        df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        
        if df.empty:
            logger.warning(f"{ts_code} 日线数据为空")
            return df
        
        # 按日期排序（升序）
        df = df.sort_values('trade_date')
        
        logger.info(f"获取到 {len(df)} 条日线记录")
        return df
        
    except Exception as e:
        logger.error(f"获取日线数据失败: {e}")
        raise

def convert_to_history_format(df: pd.DataFrame, ticker: str, name: str) -> Dict:
    """
    将 Tushare DataFrame 转换为系统历史数据格式
    """
    if df.empty:
        return {
            "ticker": ticker,
            "name": name,
            "history": []
        }
    
    # 按日期降序排列（最新的在前）
    df = df.sort_values('trade_date', ascending=False)
    
    history = []
    for _, row in df.iterrows():
        # 计算涨跌幅
        if row['pre_close'] > 0:
            change_pct = ((row['close'] - row['pre_close']) / row['pre_close']) * 100
            change_str = f"{change_pct:.2f}%"
        else:
            change_str = "0.00%"
        
        history.append({
            "date": row['trade_date'],  # 格式: YYYYMMDD
            "price": round(row['close'], 4),
            "change": change_str
        })
    
    return {
        "ticker": ticker,
        "name": name,
        "history": history,
        "total_records": len(history),
        "date_range": {
            "start": df['trade_date'].iloc[-1],  # 最旧日期
            "end": df['trade_date'].iloc[0]      # 最新日期
        },
        "last_updated": datetime.datetime.now().isoformat()
    }

def backfill_stock(ticker: str, name: str, days: int = 250):
    """
    回填个股历史数据
    
    Args:
        ticker: 股票代码 (如 000681)
        name: 股票名称
        days: 需要回填的交易天数
    """
    # 计算日期范围
    end_date = datetime.datetime.now().strftime("%Y%m%d")
    
    # 估算开始日期（大约250个交易日 ≈ 365天）
    start_date_obj = datetime.datetime.now() - datetime.timedelta(days=365)
    start_date = start_date_obj.strftime("%Y%m%d")
    
    ts_code = f"{ticker}.SZ" if ticker.startswith("00") else f"{ticker}.SH"
    
    logger.info(f"开始回填 {ticker}({name}) 历史数据，目标 {days} 个交易日")
    logger.info(f"TS代码: {ts_code}, 日期范围: {start_date} 到 {end_date}")
    
    try:
        # 获取日线数据
        df_daily = fetch_daily_data(ts_code, start_date, end_date)
        
        if df_daily.empty:
            logger.error(f"未获取到 {ticker} 的历史数据")
            return False
        
        # 转换为系统格式
        history_data = convert_to_history_format(df_daily, ticker, name)
        
        # 检查数据量是否足够
        actual_days = len(history_data["history"])
        if actual_days < days:
            logger.warning(f"数据不足: 需要{days}天，实际{actual_days}天")
            # 继续处理，但记录警告
        
        # 输出文件路径
        output_path = f"database/history_{ticker}.json"
        
        # 原子写入
        atomic_write(history_data, output_path)
        
        logger.info(f"回填完成: {ticker}, 共{actual_days}条记录")
        logger.info(f"数据范围: {history_data['date_range']['start']} 到 {history_data['date_range']['end']}")
        
        # 输出摘要
        print(f"\n📊 {ticker} {name} 回填完成")
        print(f"   记录数: {actual_days}")
        print(f"   日期范围: {history_data['date_range']['start']} - {history_data['date_range']['end']}")
        print(f"   最新价格: {history_data['history'][0]['price'] if history_data['history'] else 'N/A'}")
        print(f"   存储位置: {output_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"回填失败: {e}")
        return False

def main():
    """主函数"""
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description="历史数据回填工具")
    parser.add_argument("--ticker", required=True, help="股票代码 (如 000681)")
    parser.add_argument("--name", required=True, help="股票名称 (如 视觉中国)")
    parser.add_argument("--days", type=int, default=250, help="目标交易天数 (默认: 250)")
    parser.add_argument("--output", help="输出文件路径 (默认: database/history_<ticker>.json)")
    
    args = parser.parse_args()
    
    # 执行回填
    success = backfill_stock(args.ticker, args.name, args.days)
    
    if success:
        logger.info("回填任务成功完成")
        sys.exit(0)
    else:
        logger.error("回填任务失败")
        sys.exit(1)

if __name__ == "__main__":
    main()