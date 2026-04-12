#!/usr/bin/env python3
"""
简单测试Tushare新闻接口
"""

import json
import requests
import datetime

# 直接读取secrets.json
try:
    with open('_PRIVATE_DATA/secrets.json', 'r', encoding='utf-8') as f:
        secrets = json.load(f)
        token = secrets.get("TUSHARE_TOKEN")
        print(f"Token: {token[:20]}...")
        
        if token and token != "your_tushare_token_here":
            print("✅ Token有效")
            
            # 测试news/vip接口
            url = "https://api.tushare.pro/v1"
            api_data = {
                "api_name": "news/vip",
                "token": token,
                "params": {
                    "src": "sina",
                    "start_date": (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y%m%d"),
                    "end_date": datetime.datetime.now().strftime("%Y%m%d"),
                    "limit": 5
                },
                "fields": ""
            }
            
            print(f"\n测试接口: news/vip")
            response = requests.post(url, json=api_data, timeout=10)
            result = response.json()
            
            print(f"状态码: {response.status_code}")
            print(f"API返回码: {result.get('code')}")
            print(f"消息: {result.get('msg')}")
            
            if result.get("code") == 0:
                data = result.get("data", {})
                items = data.get("items", [])
                print(f"获取到 {len(items)} 条新闻")
                
                for i, item in enumerate(items[:3], 1):
                    print(f"\n新闻{i}:")
                    print(f"  标题: {item[0] if len(item) > 0 else 'N/A'}")
                    print(f"  内容: {item[1][:100] if len(item) > 1 else 'N/A'}...")
            else:
                print(f"\n❌ 接口错误: {result.get('msg')}")
                
                # 尝试其他接口
                print("\n尝试其他接口...")
                test_apis = ["news", "major_news", "news_sina"]
                
                for api_name in test_apis:
                    api_data["api_name"] = api_name
                    response = requests.post(url, json=api_data, timeout=10)
                    result = response.json()
                    
                    if result.get("code") == 0:
                        print(f"✅ {api_name}: 可用")
                        data = result.get("data", {})
                        items = data.get("items", [])
                        print(f"   获取到 {len(items)} 条新闻")
                        break
                    else:
                        print(f"❌ {api_name}: {result.get('msg')}")
        else:
            print("❌ Token无效或未配置")
            
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()