#!/usr/bin/env python3
"""
最终测试Tushare API - 带频率控制
"""

import json
import requests
import datetime
import time

# 读取token
with open('_PRIVATE_DATA/secrets.json', 'r', encoding='utf-8') as f:
    secrets = json.load(f)
    token = secrets.get("TUSHARE_TOKEN")
    print(f"Token: {token[:20]}...")

url = "https://api.tushare.pro/v1"

print("等待60秒以避免频率限制...")
time.sleep(60)

print("测试Tushare新闻接口...")
print("=" * 60)

# 测试news接口
api_name = "news"
params = {
    "src": "sina",
    "start_date": "20260411",
    "end_date": "20260412",
    "limit": 10
}

try:
    api_data = {
        "api_name": api_name,
        "token": token,
        "params": params,
        "fields": "title,content,pub_time,src"
    }
    
    response = requests.post(url, json=api_data, timeout=10)
    
    print(f"\n{api_name}:")
    print(f"  状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        code = result.get("code")
        msg = result.get("msg")
        
        print(f"  API返回码: {code}")
        print(f"  消息: {msg}")
        
        if code == 0:
            data = result.get("data", {})
            items = data.get("items", [])
            fields = data.get("fields", [])
            
            print(f"  ✅ 成功!")
            print(f"  字段: {fields}")
            print(f"  获取到 {len(items)} 条新闻")
            
            # 显示新闻详情
            for i, item in enumerate(items[:5], 1):
                print(f"\n  新闻{i}:")
                for j, field in enumerate(fields):
                    if j < len(item):
                        value = item[j]
                        if field == "content" and value:
                            print(f"    {field}: {value[:100]}...")
                        else:
                            print(f"    {field}: {value}")
            
            # 检查内容完整性
            total_chars = 0
            news_with_content = 0
            
            for item in items:
                if len(item) > 1 and item[1]:  # content字段
                    content = item[1]
                    total_chars += len(content)
                    news_with_content += 1
            
            if news_with_content > 0:
                avg_chars = total_chars / news_with_content
                print(f"\n  内容完整性统计:")
                print(f"    有内容的新闻: {news_with_content}/{len(items)}")
                print(f"    平均内容长度: {avg_chars:.0f} 字符")
                
                if avg_chars > 50:
                    print(f"    ✅ 内容完整性达标 (>50字符)")
                else:
                    print(f"    ⚠️  内容完整性不足 (<50字符)")
            else:
                print(f"\n  ⚠️  所有新闻都缺少content字段")
                
        else:
            print(f"  ❌ 接口错误")
            
    else:
        print(f"  ❌ HTTP错误: {response.status_code}")
        
except Exception as e:
    print(f"  ❌ 请求异常: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)