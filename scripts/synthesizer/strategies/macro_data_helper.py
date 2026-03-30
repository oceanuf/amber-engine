#!/usr/bin/env python3
"""
宏观数据辅助模块 - 提供CPI数据软降级功能
[2614-027] 架构师指令 - 宏观数据"软降级"配置
"""

import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime


class MacroDataHelper:
    """宏观数据辅助类，提供多级降级数据获取"""
    
    @staticmethod
    def get_cpi_data() -> Dict[str, Any]:
        """
        获取CPI数据，支持多级降级：
        1. 优先：Tushare API实时数据
        2. 降级：config/macro_base.json静态数据
        3. 最后：database/macro_indicators.json模拟数据
        
        Returns:
            CPI数据字典，包含最新CPI值和历史数据
        """
        cpi_data = {
            "latest_cpi": 2.8,  # 默认值，单位：%
            "latest_month": "2026-03",
            "cpi_yoy": 2.8,  # 同比
            "data_source": "default",
            "data_quality": "simulated",
            "historical_data": []
        }
        
        # 第一级降级：尝试从config/macro_base.json获取静态数据
        static_cpi = MacroDataHelper._get_static_cpi_data()
        if static_cpi and "latest_cpi" in static_cpi:
            cpi_data.update(static_cpi)
            cpi_data["data_source"] = "static_backup"
            cpi_data["data_quality"] = "historical"
            return cpi_data
        
        # 第二级降级：尝试从database/macro_indicators.json获取模拟数据
        simulated_cpi = MacroDataHelper._get_simulated_cpi_data()
        if simulated_cpi and "latest_cpi" in simulated_cpi:
            cpi_data.update(simulated_cpi)
            cpi_data["data_source"] = "simulated"
            cpi_data["data_quality"] = "simulated"
            return cpi_data
        
        return cpi_data
    
    @staticmethod
    def _get_static_cpi_data() -> Optional[Dict[str, Any]]:
        """从config/macro_base.json获取静态CPI数据"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), "../../../config/macro_base.json")
            if not os.path.exists(config_path):
                return None
            
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if "cpi" not in data or not data["cpi"]:
                return None
            
            # 获取最新的CPI数据
            cpi_list = data["cpi"]
            latest_cpi = cpi_list[0]  # 假设列表按时间倒序排列
            
            # 计算最新CPI值（转换为百分比）
            latest_cpi_value = latest_cpi.get("cpi_yoy", 1.4)  # 默认1.4%
            
            # 准备历史数据
            historical_data = []
            for item in cpi_list[:12]:  # 最近12个月
                historical_data.append({
                    "month": item["month"],
                    "cpi": item.get("cpi", 100),
                    "cpi_yoy": item.get("cpi_yoy", 0)
                })
            
            return {
                "latest_cpi": latest_cpi_value,
                "latest_month": latest_cpi["month"],
                "cpi_yoy": latest_cpi_value,
                "historical_data": historical_data,
                "update_time": data.get("update_time", "unknown"),
                "source": data.get("source", "macro_backup.py")
            }
            
        except Exception as e:
            print(f"[MacroDataHelper:WARN] 获取静态CPI数据失败: {e}")
            return None
    
    @staticmethod
    def _get_simulated_cpi_data() -> Optional[Dict[str, Any]]:
        """从database/macro_indicators.json获取模拟CPI数据"""
        try:
            db_path = os.path.join(os.path.dirname(__file__), "../../../database/macro_indicators.json")
            if not os.path.exists(db_path):
                return None
            
            with open(db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if "monthly_indicators" not in data or not data["monthly_indicators"]:
                return None
            
            # 获取最新的月度指标
            monthly_indicators = data["monthly_indicators"]
            latest_month = monthly_indicators[0]
            
            # 解析CPI值（字符串格式，如"2.8%"）
            cpi_str = latest_month.get("cpi", "2.8%")
            cpi_value = float(cpi_str.replace("%", ""))
            
            # 准备历史数据
            historical_data = []
            for item in monthly_indicators[:6]:  # 最近6个月
                cpi_str = item.get("cpi", "2.8%")
                cpi_val = float(cpi_str.replace("%", ""))
                historical_data.append({
                    "month": item["month"],
                    "cpi": 100 + cpi_val,  # 转换为指数形式
                    "cpi_yoy": cpi_val
                })
            
            return {
                "latest_cpi": cpi_value,
                "latest_month": latest_month["month"],
                "cpi_yoy": cpi_value,
                "historical_data": historical_data,
                "update_time": data.get("fetch_time", "unknown"),
                "source": data.get("data_source", "simulated")
            }
            
        except Exception as e:
            print(f"[MacroDataHelper:WARN] 获取模拟CPI数据失败: {e}")
            return None
    
    @staticmethod
    def get_treasury_yield_with_inflation() -> Dict[str, Any]:
        """
        获取考虑通胀的美债收益率数据
        
        实际利率 = 名义利率 - 通胀率
        
        Returns:
            美债收益率数据，包含实际利率计算
        """
        # 获取CPI数据
        cpi_data = MacroDataHelper.get_cpi_data()
        current_inflation = cpi_data["latest_cpi"]
        
        # 模拟美债名义收益率（单位：%）
        # 实际中应从金融数据API获取
        simulated_nominal_yield = 2.15  # 10年期美债名义收益率
        
        # 计算实际利率
        real_yield = simulated_nominal_yield - current_inflation
        
        return {
            "nominal_yield": simulated_nominal_yield,
            "inflation_rate": current_inflation,
            "real_yield": real_yield,
            "data_source": cpi_data["data_source"],
            "data_quality": cpi_data["data_quality"],
            "calculation_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "notes": f"实际利率计算: {simulated_nominal_yield}% - {current_inflation}% = {real_yield}%"
        }
    
    @staticmethod
    def get_gold_macro_analysis(gold_price: float) -> Dict[str, Any]:
        """
        获取黄金宏观分析数据
        
        Args:
            gold_price: 当前黄金价格
            
        Returns:
            黄金宏观分析结果
        """
        # 获取利率数据
        yield_data = MacroDataHelper.get_treasury_yield_with_inflation()
        real_yield = yield_data["real_yield"]
        
        # 计算黄金吸引力
        # 实际利率下降 → 黄金吸引力上升（负相关）
        gold_attractiveness = 100 - (real_yield * 10)  # 简化公式
        
        # 限制在0-100范围内
        gold_attractiveness = max(0, min(100, gold_attractiveness))
        
        # 判断信号强度
        if gold_attractiveness >= 70:
            signal_strength = "strong_bullish"
            signal_desc = "宏观利好: 实际利率极低，黄金吸引力强"
        elif gold_attractiveness >= 50:
            signal_strength = "bullish"
            signal_desc = "宏观利好: 实际利率较低，黄金有吸引力"
        elif gold_attractiveness >= 30:
            signal_strength = "neutral"
            signal_desc = "宏观中性: 实际利率适中"
        else:
            signal_strength = "bearish"
            signal_desc = "宏观利空: 实际利率较高，黄金吸引力弱"
        
        return {
            "gold_price": gold_price,
            "nominal_yield": yield_data["nominal_yield"],
            "inflation_rate": yield_data["inflation_rate"],
            "real_yield": real_yield,
            "gold_attractiveness": gold_attractiveness,
            "signal_strength": signal_strength,
            "signal_description": signal_desc,
            "data_source": yield_data["data_source"],
            "data_quality": yield_data["data_quality"],
            "calculation_notes": yield_data["notes"]
        }


# 测试函数
if __name__ == "__main__":
    print("=== 宏观数据辅助模块测试 ===")
    
    # 测试CPI数据获取
    cpi_data = MacroDataHelper.get_cpi_data()
    print(f"1. CPI数据:")
    print(f"   最新CPI: {cpi_data['latest_cpi']}%")
    print(f"   数据月份: {cpi_data['latest_month']}")
    print(f"   数据来源: {cpi_data['data_source']}")
    print(f"   数据质量: {cpi_data['data_quality']}")
    
    # 测试利率数据获取
    yield_data = MacroDataHelper.get_treasury_yield_with_inflation()
    print(f"\n2. 美债收益率数据:")
    print(f"   名义收益率: {yield_data['nominal_yield']}%")
    print(f"   通胀率: {yield_data['inflation_rate']}%")
    print(f"   实际利率: {yield_data['real_yield']}%")
    print(f"   计算说明: {yield_data['notes']}")
    
    # 测试黄金宏观分析
    gold_price = 9.656  # 示例价格
    gold_analysis = MacroDataHelper.get_gold_macro_analysis(gold_price)
    print(f"\n3. 黄金宏观分析 (价格: {gold_price}):")
    print(f"   黄金吸引力: {gold_analysis['gold_attractiveness']:.1f}")
    print(f"   信号强度: {gold_analysis['signal_strength']}")
    print(f"   信号描述: {gold_analysis['signal_description']}")
    
    print(f"\n=== 测试完成 ===")