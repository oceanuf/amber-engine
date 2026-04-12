#!/usr/bin/env python3
"""
直接测试Tushare API
"""

import json
import requests
import datetime

# 读取token
with open('_PRIVATE_DATA/secrets.json', 'r', encoding='utf-8') as f:
    secrets = json.load(f)
    token = secrets.get("TUSHARE_TOKEN")
    print(f"Token: {token[:20]}...")

url = "https://api.tushare.pro/v1"

# 测试多个可能的接口
test_cases = [
    ("news", {"src": "sina", "start_date": "20260411", "end_date": "20260412", "limit": 5}),
    ("news_sina", {"start_date": "20260411", "end_date": "20260412", "limit": 5}),
    ("news_163", {"start_date": "20260411", "end_date": "20260412", "limit": 5}),
    ("news_sohu", {"start_date": "20260411", "end_date": "20260412", "limit": 5}),
    ("news_qq", {"start_date": "20260411", "end_date": "20260412", "limit": 5}),
    ("news_cctv", {"start_date": "20260411", "end_date": "20260412", "limit": 5}),
    ("news_jin10", {"start_date": "20260411", "end_date": "20260412", "limit": 5}),
    ("news_wallstreetcn", {"start_date": "20260411", "end_date": "20260412", "limit": 5}),
    ("news_eastmoney", {"start_date": "20260411", "end_date": "20260412", "limit": 5}),
    ("news_ifeng", {"start_date": "20260411", "end_date": "20260412", "limit": 5}),
]

print("测试Tushare新闻接口...")
print("=" * 60)

available_apis = []

for api_name, params in test_cases:
    try:
        api_data = {
            "api_name": api_name,
            "token": token,
            "params": params,
            "fields": ""
        }
        
        response = requests.post(url, json=api_data, timeout=10)
        
        # 打印原始响应前100个字符用于调试
        raw_text = response.text[:100]
        print(f"\n{api_name}:")
        print(f"  状态码: {response.status_code}")
        print(f"  响应预览: {raw_text}...")
        
        if response.status_code == 200:
            try:
                result = response.json()
                code = result.get("code")
                msg = result.get("msg")
                
                print(f"  API返回码: {code}")
                print(f"  消息: {msg}")
                
                if code == 0:
                    data = result.get("data", {})
                    items = data.get("items", [])
                    print(f"  ✅ 可用 - 获取到 {len(items)} 条新闻")
                    available_apis.append((api_name, len(items)))
                    
                    # 显示第一条新闻的标题
                    if items and len(items) > 0:
                        first_item = items[0]
                        if len(first_item) > 0:
                            print(f"  示例标题: {first_item[0][:50]}...")
                else:
                    print(f"  ❌ 不可用: {msg}")
            except json.JSONDecodeError as e:
                print(f"  ❌ JSON解析错误: {e}")
        else:
            print(f"  ❌ HTTP错误: {response.status_code}")
            
    except Exception as e:
        print(f"  ❌ 请求异常: {e}")

print("\n" + "=" * 60)
print("测试结果汇总:")
print("=" * 60)

if available_apis:
    print("✅ 可用的接口:")
    for api_name, count in available_apis:
        print(f"  - {api_name}: {count} 条新闻")
    
    # 推荐最佳接口
    best_api = max(available_apis, key=lambda x: x[1])
    print(f"\n💡 推荐使用: {best_api[0]} (获取到 {best_api[1]} 条新闻)")
else:
    print("❌ 未找到可用的Tushare新闻接口")
    print("   可能需要检查Token权限或尝试其他接口名")