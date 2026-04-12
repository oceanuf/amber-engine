#!/usr/bin/env python3
"""
股票诊断技能 (Stock Advisor Skill)
版本: 1.0.0
描述: 基于语义触发与预测模型的股票/ETF诊断系统
功能:
  1. 语义识别: 支持"代码/名称 + 怎么样/分析/评价"格式
  2. 代码补全: 自动补全A股代码后缀(.SZ/.SH)
  3. 数据获取: 从Tushare/Akshare获取历史数据
  4. 预测分析: 计算30/60/90天胜率与预期收益率
  5. 交易指导: 提供补仓/减仓/止损/止盈建议
  6. 报告生成: 自动保存至stock-analytics/[代码].md
"""

import os
import sys
import re
import json
import datetime
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StockAdvisorSkill:
    """股票诊断技能主类"""
    
    def __init__(self):
        """初始化技能"""
        self.trigger_patterns = self._load_trigger_patterns()
        self.stock_cache = {}
        
        logger.info("股票诊断技能初始化完成")
    
    def _load_trigger_patterns(self) -> List[Dict]:
        """加载触发模式"""
        patterns = [
            # 格式: [代码][名称] + 怎么样/分析/评价
            {
                "pattern": r"(?:分析|诊断|评价|看看)?\s*([0-9]{6})([^\d\s]{2,})?\s*(?:怎么样|如何|表现)?",
                "type": "code_first"
            },
            {
                "pattern": r"([^\d\s]{2,})([0-9]{6})?\s*(?:怎么样|分析|诊断|评价)",
                "type": "name_first"
            },
            # ETF格式
            {
                "pattern": r"(?:分析|看看)?\s*([0-9]{6})\.(?:SH|SZ|ETF|etf)\s*(?:怎么样|如何)",
                "type": "etf_code"
            },
            # 简单格式
            {
                "pattern": r"([0-9]{6})\s*(?:怎么样|分析)",
                "type": "simple_code"
            }
        ]
        return patterns
    
    def extract_stock_info(self, text: str) -> Optional[Dict]:
        """从文本中提取股票信息"""
        text = text.strip()
        
        for pattern_info in self.trigger_patterns:
            pattern = pattern_info["pattern"]
            match_type = pattern_info["type"]
            
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                logger.info(f"匹配到模式: {match_type}, 文本: {text}")
                
                if match_type == "code_first":
                    code = match.group(1)
                    name = match.group(2) if match.group(2) else None
                elif match_type == "name_first":
                    name = match.group(1)
                    code = match.group(2) if match.group(2) else None
                elif match_type == "etf_code":
                    code = match.group(1)
                    name = None
                    # 标记为ETF
                    return {"code": code, "name": name, "is_etf": True}
                elif match_type == "simple_code":
                    code = match.group(1)
                    name = None
                else:
                    continue
                
                # 补全代码后缀
                full_code = self._complete_stock_code(code)
                
                return {
                    "code": full_code,
                    "name": name,
                    "is_etf": self._is_etf_code(code),
                    "original_text": text,
                    "match_type": match_type
                }
        
        logger.warning(f"未匹配到股票信息: {text}")
        return None
    
    def _complete_stock_code(self, code: str) -> str:
        """补全股票代码后缀"""
        if not code or len(code) != 6:
            return code
        
        # 常见A股代码规则
        # 沪市: 600, 601, 603, 605, 688 (科创板), 900 (B股)
        # 深市: 000, 001, 002, 003, 300 (创业板), 200 (B股)
        # 北交所: 430, 831, 832, 833, 834, 835, 836, 837, 838, 839, 870, 871, 872, 873, 874, 875, 876, 877, 878, 879
        
        prefix = code[:3]
        
        if prefix in ["600", "601", "603", "605", "688", "900"]:
            return f"{code}.SH"
        elif prefix in ["000", "001", "002", "003", "300", "200"]:
            return f"{code}.SZ"
        elif prefix in ["510", "511", "512", "513", "515", "518"]:  # ETF
            return f"{code}.SH"
        elif prefix in ["159"]:  # 深市ETF
            return f"{code}.SZ"
        else:
            # 默认深市
            return f"{code}.SZ"
    
    def _is_etf_code(self, code: str) -> bool:
        """判断是否为ETF代码"""
        if not code or len(code) != 6:
            return False
        
        etf_prefixes = ["510", "511", "512", "513", "515", "518", "159"]
        return code[:3] in etf_prefixes
    
    def get_stock_data(self, stock_info: Dict) -> Optional[pd.DataFrame]:
        """获取股票历史数据"""
        code = stock_info["code"]
        
        # 检查缓存
        if code in self.stock_cache:
            logger.info(f"从缓存获取数据: {code}")
            return self.stock_cache[code]
        
        try:
            # 尝试使用Akshare
            import akshare as ak
            
            # 获取日线数据
            if stock_info.get("is_etf", False):
                # ETF数据
                df = ak.fund_etf_hist_sina(symbol=code.replace(".", ""))
            else:
                # 股票数据
                df = ak.stock_zh_a_hist(symbol=code.replace(".", ""), period="daily", adjust="qfq")
            
            if df is not None and not df.empty:
                # 标准化列名
                df.columns = [col.strip() for col in df.columns]
                
                # 确保有日期和收盘价列
                date_col = None
                close_col = None
                
                for col in df.columns:
                    if "日期" in col or "date" in col.lower():
                        date_col = col
                    if "收盘" in col or "close" in col.lower():
                        close_col = col
                
                if date_col and close_col:
                    df = df[[date_col, close_col]].copy()
                    df.columns = ["date", "close"]
                    df["date"] = pd.to_datetime(df["date"])
                    df = df.sort_values("date").reset_index(drop=True)
                    
                    # 缓存数据
                    self.stock_cache[code] = df
                    
                    logger.info(f"获取到 {code} 的 {len(df)} 条历史数据")
                    return df
                else:
                    logger.error(f"数据列名不标准: {df.columns.tolist()}")
                    return None
            else:
                logger.error(f"未获取到数据: {code}")
                return None
                
        except ImportError:
            logger.error("Akshare库未安装，请运行: pip install akshare")
            return None
        except Exception as e:
            logger.error(f"获取股票数据失败: {e}")
            return None
    
    def calculate_win_rate(self, df: pd.DataFrame, days: int = 30) -> Dict[str, float]:
        """计算持有胜率与预期收益率"""
        if df is None or len(df) < days * 5:  # 至少需要5倍的数据
            return {"win_rate": 0.0, "median_return": 0.0, "avg_return": 0.0}
        
        try:
            closes = df["close"].values
            returns = []
            
            # 计算所有可能的持有期收益率
            for i in range(len(df) - days):
                start_price = closes[i]
                end_price = closes[i + days]
                return_pct = (end_price - start_price) / start_price * 100
                returns.append(return_pct)
            
            if not returns:
                return {"win_rate": 0.0, "median_return": 0.0, "avg_return": 0.0}
            
            returns_array = np.array(returns)
            
            # 计算胜率（正收益的概率）
            win_rate = np.sum(returns_array > 0) / len(returns_array) * 100
            
            # 计算中位数收益率
            median_return = np.median(returns_array)
            
            # 计算平均收益率
            avg_return = np.mean(returns_array)
            
            # 计算波动率（年化）
            daily_returns = np.diff(closes) / closes[:-1]
            if len(daily_returns) > 0:
                daily_volatility = np.std(daily_returns)
                annual_volatility = daily_volatility * np.sqrt(252) * 100  # 年化波动率百分比
            else:
                annual_volatility = 0.0
            
            return {
                "win_rate": round(win_rate, 1),
                "median_return": round(median_return, 2),
                "avg_return": round(avg_return, 2),
                "volatility": round(annual_volatility, 1),
                "sample_size": len(returns)
            }
            
        except Exception as e:
            logger.error(f"计算胜率失败: {e}")
            return {"win_rate": 0.0, "median_return": 0.0, "avg_return": 0.0}
    
    def generate_trading_advice(self, df: pd.DataFrame, current_price: float) -> Dict[str, Any]:
        """生成交易建议"""
        if df is None or len(df) < 60:  # 至少需要60天数据
            return {
                "action": "观望",
                "support_levels": [],
                "resistance_levels": [],
                "stop_loss": 0,
                "take_profit": 0
            }
        
        try:
            closes = df["close"].values[-252:]  # 最近一年数据
            
            # 计算支撑位和阻力位
            # 使用最近20天的低点作为弱支撑
            weak_support = np.min(closes[-20:]) if len(closes) >= 20 else np.min(closes)
            
            # 使用最近60天的低点作为强支撑
            strong_support = np.min(closes[-60:]) if len(closes) >= 60 else weak_support
            
            # 使用最近20天的高点作为弱阻力
            weak_resistance = np.max(closes[-20:]) if len(closes) >= 20 else np.max(closes)
            
            # 使用最近60天的高点作为强阻力
            strong_resistance = np.max(closes[-60:]) if len(closes) >= 60 else weak_resistance
            
            # 计算止损位（基于ATR或百分比）
            atr = self._calculate_atr(df) if len(df) >= 14 else 0
            if atr > 0:
                stop_loss = current_price - 2 * atr
            else:
                stop_loss = current_price * 0.9  # 10%止损
            
            # 计算止盈位
            take_profit = current_price * 1.15  # 15%止盈
            
            # 生成交易动作建议
            action = "持有"
            if current_price < strong_support * 1.02:  # 价格接近强支撑
                action = "补仓"
            elif current_price > strong_resistance * 0.98:  # 价格接近强阻力
                action = "减仓"
            elif current_price > take_profit:
                action = "止盈"
            elif current_price < stop_loss:
                action = "止损"
            
            return {
                "action": action,
                "support_levels": [
                    {"level": round(strong_support, 2), "type": "强支撑", "distance_pct": round((current_price - strong_support) / current_price * 100, 1)},
                    {"level": round(weak_support, 2), "type": "弱支撑", "distance_pct": round((current_price - weak_support) / current_price * 100, 1)}
                ],
                "resistance_levels": [
                    {"level": round(weak_resistance, 2), "type": "弱阻力", "distance_pct": round((weak_resistance - current_price) / current_price * 100, 1)},
                    {"level": round(strong_resistance, 2), "type": "强阻力", "distance_pct": round((strong_resistance - current_price) / current_price * 100, 1)}
                ],
                "stop_loss": round(stop_loss, 2),
                "take_profit": round(take_profit, 2),
                "current_price": round(current_price, 2)
            }
            
        except Exception as e:
            logger.error(f"生成交易建议失败: {e}")
            return {
                "action": "观望",
                "support_levels": [],
                "resistance_levels": [],
                "stop_loss": 0,
                "take_profit": 0
            }
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """计算平均真实波幅(ATR)"""
        try:
            if len(df) < period + 1:
                return 0.0
            
            # 需要高、低、收盘价数据
            # 这里简化处理，使用收盘价的波动
            closes = df["close"].values
            tr_values = []
            
            for i in range(1, len(closes)):
                tr = abs(closes[i] - closes[i-1])
                tr_values.append(tr)
            
            if len(tr_values) >= period:
                atr = np.mean(tr_values[-period:])
                return atr
            else:
                return np.mean(tr_values) if tr_values else 0.0
                
        except Exception as e:
            logger.error(f"计算ATR失败: {e}")
            return 0.0
    
    def generate_report(self, stock_info: Dict, analysis_results: Dict) -> str:
        """生成分析报告"""
        code = stock_info["code"]
        name = stock_info.get("name", "未知")
        is_etf = stock_info.get("is_etf", False)
        
        today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # 报告头部
        report = f"""# 📊 {'ETF' if is_etf else '股票'}诊断报告 - {name}({code})

**报告编号**: 2616-0413-STOCK-{code.replace(".", "")}  
**分析日期**: {today}  
**分析框架**: 语义触发+预测模型+交易SOP  
**分析工具**: 琥珀引擎股票诊断技能 v1.0  
**分析师**: 工程师 Cheese 🧀  

---

## 📈 核心结论

### 🎯 投资评级: **{analysis_results.get('rating', '待定')}**
### 📊 预测胜率: **{analysis_results.get('win_rate_30d', {}).get('win_rate', 0)}%** (30天)
### 💰 预期收益: **{analysis_results.get('win_rate_30d', {}).get('median_return', 0)}%** (30天中位数)
### 🚀 建议操作: **{analysis_results.get('trading_advice', {}).get('action', '观望')}**

---

## 🔍 一、基础信息

### 1.1 标的概况
- **代码**: {code}
- **名称**: {name if name else '待查询'}
- **类型**: {'ETF' if is_etf else '股票'}
- **分析触发**: {stock_info.get('original_text', '未知')}
- **数据样本**: {analysis_results.get('data_points', 0)} 个交易日

### 1.2 当前状态
- **最新价格**: ¥{analysis_results.get('trading_advice', {}).get('current_price', 0)}
- **分析时间**: {today}
- **数据新鲜度**: {analysis_results.get('data_recency', '今日')}

---

## 📊 二、预测分析

### 2.1 胜率与预期收益率
| 持有期限 | 胜率(%) | 中位数收益率(%) | 平均收益率(%) | 样本数 |
| :--- | :--- | :--- | :--- | :--- |
| **30天** | {analysis_results.get('win_rate_30d', {}).get('win_rate', 0)} | {analysis_results.get('win_rate_30d', {}).get('median_return', 0)} | {analysis_results.get('win_rate_30d', {}).get('avg_return', 0)} | {analysis_results.get('win_rate_30d', {}).get('sample_size', 0)} |
| **60天** | {analysis_results.get('win_rate_60d', {}).get('win_rate', 0)} | {analysis_results.get('win_rate_60d',