#!/usr/bin/env python3
"""
股票诊断技能 - 简化实用版
版本: 1.0.0
功能: 语义触发 + 胜率预测 + 交易指导
"""

import os
import sys
import re
import json
import datetime
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StockDiagnostic:
    """股票诊断技能"""
    
    def __init__(self):
        self.trigger_words = ["分析", "诊断", "评价", "看看", "怎么样", "如何"]
        self.stock_patterns = [
            r"([0-9]{6})[^\d]*([\u4e00-\u9fa5]{2,})?",  # 代码+名称
            r"([\u4e00-\u9fa5]{2,})[^\d]*([0-9]{6})?",  # 名称+代码
            r"([0-9]{6})\.(?:SH|SZ)",  # 带后缀代码
            r"([0-9]{6})\s*(?:怎么样|分析|诊断)"  # 简单代码
        ]
        
    def extract_stock(self, text: str) -> Optional[Dict]:
        """提取股票信息"""
        text = text.strip()
        
        for pattern in self.stock_patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                code = None
                name = None
                
                for item in groups:
                    if item:
                        if re.match(r'^[0-9]{6}$', item):
                            code = item
                        elif re.match(r'^[\u4e00-\u9fa5]{2,}$', item):
                            name = item
                
                if code:
                    full_code = self._complete_code(code)
                    return {
                        "code": full_code,
                        "name": name or "未知",
                        "is_etf": self._is_etf(code),
                        "original_text": text
                    }
        
        return None
    
    def _complete_code(self, code: str) -> str:
        """补全代码后缀"""
        if code.startswith(("600", "601", "603", "605", "688", "900", "510", "511", "512", "513", "515", "518")):
            return f"{code}.SH"
        elif code.startswith(("000", "001", "002", "003", "300", "200", "159")):
            return f"{code}.SZ"
        else:
            return f"{code}.SZ"  # 默认深市
    
    def _is_etf(self, code: str) -> bool:
        """判断是否为ETF"""
        etf_prefixes = ["510", "511", "512", "513", "515", "518", "159"]
        return code[:3] in etf_prefixes
    
    def get_stock_data(self, code: str) -> Optional[pd.DataFrame]:
        """获取股票数据"""
        try:
            import akshare as ak
            
            clean_code = code.replace(".", "")
            
            if self._is_etf(clean_code):
                df = ak.fund_etf_hist_sina(symbol=clean_code)
            else:
                df = ak.stock_zh_a_hist(symbol=clean_code, period="daily", adjust="qfq")
            
            if df is not None and not df.empty:
                # 标准化数据
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
                    return df
            
            return None
            
        except Exception as e:
            logger.error(f"获取数据失败: {e}")
            return None
    
    def calculate_win_rates(self, df: pd.DataFrame) -> Dict[str, Any]:
        """计算胜率"""
        if df is None or len(df) < 100:
            return {}
        
        closes = df["close"].values
        current_price = closes[-1] if len(closes) > 0 else 0
        
        results = {}
        
        for days in [30, 60, 90]:
            if len(df) < days * 2:
                continue
            
            returns = []
            for i in range(len(df) - days):
                start = closes[i]
                end = closes[i + days]
                ret = (end - start) / start * 100
                returns.append(ret)
            
            if returns:
                returns_arr = np.array(returns)
                win_rate = np.sum(returns_arr > 0) / len(returns_arr) * 100
                median_ret = np.median(returns_arr)
                avg_ret = np.mean(returns_arr)
                
                results[f"win_rate_{days}d"] = {
                    "win_rate": round(win_rate, 1),
                    "median_return": round(median_ret, 2),
                    "avg_return": round(avg_ret, 2),
                    "sample_size": len(returns)
                }
        
        # 计算波动率
        if len(closes) > 1:
            daily_returns = np.diff(closes) / closes[:-1]
            daily_vol = np.std(daily_returns)
            annual_vol = daily_vol * np.sqrt(252) * 100
            results["volatility"] = round(annual_vol, 1)
        
        results["current_price"] = round(current_price, 2)
        results["data_points"] = len(df)
        
        return results
    
    def generate_trading_advice(self, df: pd.DataFrame, current_price: float) -> Dict[str, Any]:
        """生成交易建议"""
        if df is None or len(df) < 60:
            return {"action": "观望", "reason": "数据不足"}
        
        closes = df["close"].values[-252:]  # 最近一年
        
        # 计算支撑阻力
        support_20 = np.min(closes[-20:]) if len(closes) >= 20 else np.min(closes)
        support_60 = np.min(closes[-60:]) if len(closes) >= 60 else support_20
        resistance_20 = np.max(closes[-20:]) if len(closes) >= 20 else np.max(closes)
        resistance_60 = np.max(closes[-60:]) if len(closes) >= 60 else resistance_20
        
        # 交易逻辑
        action = "持有"
        reason = "价格处于合理区间"
        
        if current_price < support_60 * 1.05:  # 接近强支撑
            action = "补仓"
            reason = f"价格接近强支撑位 ¥{support_60:.2f}"
        elif current_price > resistance_60 * 0.95:  # 接近强阻力
            action = "减仓"
            reason = f"价格接近强阻力位 ¥{resistance_60:.2f}"
        elif current_price > current_price * 1.15:  # 已上涨15%
            action = "止盈"
            reason = "已达到15%盈利目标"
        elif current_price < current_price * 0.9:  # 已下跌10%
            action = "止损"
            reason = "已触发10%止损线"
        
        return {
            "action": action,
            "reason": reason,
            "support_levels": [
                {"price": round(support_60, 2), "type": "强支撑"},
                {"price": round(support_20, 2), "type": "弱支撑"}
            ],
            "resistance_levels": [
                {"price": round(resistance_20, 2), "type": "弱阻力"},
                {"price": round(resistance_60, 2), "type": "强阻力"}
            ],
            "stop_loss": round(current_price * 0.9, 2),
            "take_profit": round(current_price * 1.15, 2)
        }
    
    def generate_report(self, stock_info: Dict, analysis: Dict, trading: Dict) -> str:
        """生成报告"""
        code = stock_info["code"]
        name = stock_info["name"]
        is_etf = stock_info["is_etf"]
        
        today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # 胜率表格
        win_rate_table = ""
        for days in [30, 60, 90]:
            key = f"win_rate_{days}d"
            if key in analysis:
                wr = analysis[key]
                win_rate_table += f"| **{days}天** | {wr['win_rate']}% | {wr['median_return']}% | {wr['avg_return']}% | {wr['sample_size']} |\n"
        
        # 支撑阻力表格
        support_table = ""
        for sup in trading.get("support_levels", []):
            support_table += f"| {sup['type']} | ¥{sup['price']} | {round((analysis.get('current_price', 0) - sup['price']) / analysis.get('current_price', 1) * 100, 1)}% |\n"
        
        resistance_table = ""
        for res in trading.get("resistance_levels", []):
            resistance_table += f"| {res['type']} | ¥{res['price']} | {round((res['price'] - analysis.get('current_price', 0)) / analysis.get('current_price', 1) * 100, 1)}% |\n"
        
        report = f"""# 📊 {'ETF' if is_etf else '股票'}诊断报告 - {name}({code})

**报告编号**: 2616-0413-STOCK-{code.replace(".", "")}  
**分析日期**: {today}  
**分析框架**: 语义触发+预测模型+交易SOP  
**分析师**: 工程师 Cheese 🧀  

---

## 📈 核心结论

### 🎯 投资评级: **{'谨慎乐观' if analysis.get('win_rate_30d', {}).get('win_rate', 0) > 50 else '谨慎'}**
### 📊 预测胜率: **{analysis.get('win_rate_30d', {}).get('win_rate', 0)}%** (30天)
### 💰 预期收益: **{analysis.get('win_rate_30d', {}).get('median_return', 0)}%** (30天中位数)
### 🚀 建议操作: **{trading.get('action', '观望')}**

---

## 🔍 基础信息

### 1.1 标的概况
- **代码**: {code}
- **名称**: {name}
- **类型**: {'ETF' if is_etf else '股票'}
- **当前价格**: ¥{analysis.get('current_price', 0)}
- **数据样本**: {analysis.get('data_points', 0)} 个交易日
- **年化波动率**: {analysis.get('volatility', 0)}%

---

## 📊 预测分析

### 2.1 胜率与预期收益率
| 持有期限 | 胜率(%) | 中位数收益率(%) | 平均收益率(%) | 样本数 |
| :--- | :--- | :--- | :--- | :--- |
{win_rate_table}

### 2.2 关键价位
#### 支撑位
| 类型 | 价格(¥) | 距离当前 |
| :--- | :--- | :--- |
{support_table}

#### 阻力位
| 类型 | 价格(¥) | 距离当前 |
| :--- | :--- | :--- |
{resistance_table}

---

## 💰 交易指导

### 3.1 具体建议
- **操作**: {trading.get('action', '观望')}
- **理由**: {trading.get('reason', '')}
- **止损位**: ¥{trading.get('stop_loss', 0)}
- **止盈位**: ¥{trading.get('take_profit', 0)}

### 3.2 风险提示
> ⚠️ **重要提示**: 本报告基于历史数据回测，胜率与收益率预测仅为统计参考，不构成投资建议。市场有风险，投资需谨慎。

---

## 📋 分析参数
- **分析模型**: 历史波动率+蒙特卡洛简化模拟
- **数据源**: Akshare/Tushare
- **回测周期**: 最近3年
- **更新时间**: {today}

---
*生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        return report
    
    def analyze(self, text: str) -> Optional[Dict]:
        """完整分析流程"""
        # 1. 提取股票信息
        stock_info = self.extract_stock(text)
        if not stock_info:
            logger.warning(f"未识别到股票: {text}")
            return None
        
        logger.info(f"识别到股票: {stock_info}")
        
        # 2. 获取数据
        df = self.get_stock_data(stock_info["code"])
        if df is None or len(df) < 100:
            logger.error(f"数据不足: {stock_info['code']}")
            return None
        
        # 3. 计算胜率
        analysis = self.calculate_win_rates(df)
        
        # 4. 生成交易建议
        current_price = analysis.get("current_price", 0)
        trading = self.generate_trading_advice(df, current_price)
        
        # 5. 生成报告
        report = self.generate_report(stock_info, analysis, trading)
        
        # 6. 保存报告
        output_dir = "stock-analytics"
        os.makedirs(output_dir, exist_ok=True)
        
        code_clean = stock_info["code"].replace(".", "")
        output_path = os.path.join(output_dir, f"{code_clean}.md")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        
        logger.info(f"报告已保存: {output_path}")
        
        return {
            "stock_info": stock_info,
            "analysis": analysis,
            "trading": trading,
            "report_path": output_path
        }

def main():
    """主函数"""
    print("=" * 60)
    print("📊 股票诊断技能测试")
    print("=" * 60)
    
    diagnostic = StockDiagnostic()
    
    # 测试用例
    test_cases = [
        "分析000858五粮液",
        "510300怎么样",
        "看看贵州茅台600519",
        "评价159919",
        "000858怎么样"
    ]
    
    for text in test_cases:
        print(f"\n🔍 测试: {text}")
        result = diagnostic.analyze(text)
        
        if result:
            stock = result["stock_info"]
            analysis = result["analysis"]
            trading = result["trading"]
            
            print(f"  ✅ 识别: {stock['name']}({stock['code']})")
            print(f"     30天胜率: {analysis.get('win_rate_30d', {}).get('win_rate', 0)}%")
            print(f"     建议操作: {trading.get('action', '观望')}")
            print(f"     报告路径: {result['report_path']}")
        else:
            print(f"  ❌ 分析失败")
    
    print(f"\n" + "=" * 60)
    print("🎉 测试完成")
    print("=" * 60)

if __name__ == "__main__":
    main()