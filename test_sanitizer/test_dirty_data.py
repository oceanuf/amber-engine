#!/usr/bin/env python3
"""测试脏数据注入检测"""

import sys
import os
import json

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.pipeline.data_sanitizer import DataSanitizer

def test_dirty_data():
    """测试脏数据检测"""
    print("🧪 开始脏数据注入测试")
    
    # 初始化清洗器
    sanitizer = DataSanitizer(debug=True)
    
    # 测试文件
    test_file = "dirty_data.json"
    
    # 加载数据
    data = sanitizer.load_json_file(test_file)
    if not data:
        print("❌ 无法加载测试文件")
        return False
    
    print("✅ 测试文件加载成功")
    
    # 提取价格数据
    price_data, ticker = sanitizer.extract_price_data(data)
    if not price_data:
        print("❌ 无法提取价格数据")
        return False
    
    print(f"✅ 提取到 {len(price_data)} 条价格数据, ticker={ticker}")
    
    # 检查零值异常
    zero_anomalies = sanitizer.check_zero_or_null_prices(price_data, ticker)
    
    if zero_anomalies:
        print(f"✅ 成功检测到 {len(zero_anomalies)} 个零值/空值异常")
        for anomaly in zero_anomalies:
            print(f"   - {anomaly['reason']} (日期: {anomaly['date']})")
        
        # 测试降级逻辑
        print("🔄 测试降级逻辑...")
        try:
            cleaned_data = sanitizer.apply_fallback_for_anomalies(zero_anomalies, ticker, data)
            
            if cleaned_data.get("fallback_applied", False):
                print("✅ 降级逻辑成功应用")
                print(f"   降级原因: {cleaned_data.get('fallback_reason', '未知')}")
                print(f"   降级源: {cleaned_data.get('fallback_source', '未知')}")
                
                # 检查清洗后数据文件
                cleaned_file = test_file.replace('.json', '_cleaned.json')
                if os.path.exists(cleaned_file):
                    print(f"✅ 清洗后文件已生成: {cleaned_file}")
                    
                    # 加载并检查清洗后数据
                    with open(cleaned_file, 'r', encoding='utf-8') as f:
                        cleaned_content = json.load(f)
                    
                    if cleaned_content.get("sanitization_applied", False):
                        print("✅ 清洗标记已添加")
                    
                    # 检查价格是否被修复（理论上降级模块可能会提供价格）
                    price_data_cleaned, _ = sanitizer.extract_price_data(cleaned_content)
                    if price_data_cleaned and len(price_data_cleaned) > 0:
                        latest_price = price_data_cleaned[0]
                        close_price = latest_price.get("close")
                        if close_price and float(close_price) > 0:
                            print(f"✅ 价格已修复: {close_price}")
                        else:
                            print("⚠️  价格可能仍为零，降级模块可能未提供替代价格")
                else:
                    print("⚠️  清洗后文件未生成，但降级逻辑已应用")
            else:
                print("⚠️  降级逻辑未应用（可能DataFallback不可用或失败）")
            
        except Exception as e:
            print(f"❌ 降级逻辑异常: {e}")
            import traceback
            traceback.print_exc()
        
        return True
    else:
        print("❌ 未检测到零值异常（测试失败）")
        return False

def test_volatility_anomaly():
    """测试波动率异常检测"""
    print("\n🧪 开始波动率异常测试")
    
    # 使用之前的测试文件（包含12%波动的）
    test_file = "test_tushare.json"
    
    sanitizer = DataSanitizer(debug=True)
    data = sanitizer.load_json_file(test_file)
    
    if not data:
        print("❌ 无法加载测试文件")
        return False
    
    price_data, ticker = sanitizer.extract_price_data(data)
    
    # 检查波动率异常
    volatility_anomalies = sanitizer.check_volatility_outlier(price_data, ticker)
    
    if volatility_anomalies:
        print(f"✅ 成功检测到 {len(volatility_anomalies)} 个波动率异常")
        for anomaly in volatility_anomalies:
            print(f"   - {anomaly['reason']} (日期: {anomaly['date']})")
        return True
    else:
        print("❌ 未检测到波动率异常")
        return False

def main():
    """主测试"""
    print("=" * 60)
    print("数据清洗器集成测试")
    print("=" * 60)
    
    # 测试1: 脏数据检测
    test1_pass = test_dirty_data()
    
    # 测试2: 波动率异常检测
    test2_pass = test_volatility_anomaly()
    
    print("\n" + "=" * 60)
    print("测试结果汇总:")
    print(f"  脏数据检测: {'✅ 通过' if test1_pass else '❌ 失败'}")
    print(f"  波动率异常检测: {'✅ 通过' if test2_pass else '❌ 失败'}")
    
    if test1_pass and test2_pass:
        print("\n🎉 所有集成测试通过!")
        return 0
    else:
        print("\n⚠️  部分测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())