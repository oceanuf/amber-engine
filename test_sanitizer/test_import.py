#!/usr/bin/env python3
"""测试data_sanitizer导入和基本功能"""

import sys
import os

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from scripts.pipeline.data_sanitizer import DataSanitizer
    print("✅ DataSanitizer 导入成功")
    
    # 测试初始化
    sanitizer = DataSanitizer(debug=True)
    print("✅ DataSanitizer 初始化成功")
    
    # 测试加载文件
    test_file = "test_tushare.json"
    import json
    data = sanitizer.load_json_file(test_file)
    if data:
        print("✅ 文件加载成功")
        
        # 测试数据提取
        price_data, ticker = sanitizer.extract_price_data(data)
        print(f"✅ 数据提取成功: {len(price_data)} 条价格数据, ticker={ticker}")
        
        # 测试波动率检查
        anomalies = sanitizer.check_volatility_outlier(price_data, ticker)
        print(f"✅ 波动率检查: 发现 {len(anomalies)} 个异常")
        for anomaly in anomalies:
            print(f"   - {anomaly['reason']}")
    else:
        print("❌ 文件加载失败")
        
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"❌ 其他错误: {e}")
    import traceback
    traceback.print_exc()