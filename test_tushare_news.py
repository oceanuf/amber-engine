#!/usr/bin/env python3
"""
测试Tushare新闻接口
"""

import os
import sys
import json
import requests
import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载Tushare Token
SECRETS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                           "_PRIVATE_DATA", "secrets.json")

def load_tushare_token():
    """加载Tushare Token"""
    try:
        if os.path.exists(SECRETS_FILE):
            with open(SECRETS_FILE, 'r', encoding='utf-8') as f:
                secrets = json.load(f)
                token = secrets.get("TUSHARE_TOKEN")
                if token and token != "your_tushare_token_here":
                    print(f"✅ 从secrets.json加载Tushare Token: {token[:10]}...")
                    return token
        
        # 尝试环境变量
        token = os.getenv("TUSHARE_TOKEN")
        if token:
            print(f"✅ 从环境变量加载Tushare Token: {token[:10]}...")
            return token
        
        print("❌ 未找到Tushare Token")
        return None
    except Exception as e:
        print(f"❌ 加载Tushare Token失败: {e}")
        return None

def test_tushare_api(api_name, params=None):
    """测试Tushare API接口"""
    token = load_tushare_token()
    if not token:
        return None
    
    url = "https://api.tushare.pro/v1"
    
    api_data = {
        "api_name": api_name,
        "token": token,
        "params": params or {},
        "fields": ""
    }
    
    print(f"\n🔍 测试Tushare接口: {api_name}")
    print(f"   参数: {params}")
    
    try:
        response = requests.post(url, json=api_data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"   状态码: {response.status_code}")
            print(f"   API返回码: {result.get('code')}")
            print(f"   消息: {result.get('msg')}")
            
            if result.get("code") == 0:
                data = result.get("data", {})
                items = data.get("items", [])
                fields = data.get("fields", [])
                print(f"   字段: {fields}")
                print(f"   数据条数: {len(items)}")
                
                # 显示前3条数据
                for i, item in enumerate(items[:3], 1):
                    print(f"   数据{i}: {item}")
                
                return result
            else:
                print(f"   ❌ API错误: {result.get('msg')}")
                return result
        else:
            print(f"   ❌ HTTP错误: {response.status_code}")
            return None
    except Exception as e:
        print(f"   ❌ 请求异常: {e}")
        return None

def main():
    """主函数"""
    print("=" * 60)
    print("📰 Tushare新闻接口测试")
    print("=" * 60)
    
    # 测试可能的新闻接口
    test_cases = [
        {
            "name": "news/vip",
            "api_name": "news/vip",
            "params": {
                "src": "sina",
                "start_date": (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y%m%d"),
                "end_date": datetime.datetime.now().strftime("%Y%m%d"),
                "limit": 5
            }
        },
        {
            "name": "news",
            "api_name": "news",
            "params": {
                "src": "sina",
                "start_date": (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y%m%d"),
                "end_date": datetime.datetime.now().strftime("%Y%m%d"),
                "limit": 5
            }
        },
        {
            "name": "major_news",
            "api_name": "major_news",
            "params": {
                "src": "sina",
                "start_date": (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y%m%d"),
                "end_date": datetime.datetime.now().strftime("%Y%m%d"),
                "limit": 5
            }
        },
        {
            "name": "news_sina",
            "api_name": "news_sina",
            "params": {
                "start_date": (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y%m%d"),
                "end_date": datetime.datetime.now().strftime("%Y%m%d"),
                "limit": 5
            }
        }
    ]
    
    results = {}
    
    for test_case in test_cases:
        result = test_tushare_api(test_case["api_name"], test_case["params"])
        results[test_case["name"]] = result
    
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    for name, result in results.items():
        if result and result.get("code") == 0:
            data = result.get("data", {})
            items = data.get("items", [])
            print(f"✅ {name}: 成功获取 {len(items)} 条数据")
        elif result:
            print(f"❌ {name}: API错误 - {result.get('msg')}")
        else:
            print(f"❌ {name}: 请求失败")
    
    print("\n" + "=" * 60)
    print("💡 建议")
    print("=" * 60)
    
    # 找出可用的接口
    available_apis = []
    for name, result in results.items():
        if result and result.get("code") == 0:
            available_apis.append(name)
    
    if available_apis:
        print(f"✅ 可用的接口: {', '.join(available_apis)}")
        print(f"   建议使用: {available_apis[0]}")
    else:
        print("❌ 未找到可用的Tushare新闻接口")
        print("   可能需要检查Token权限或尝试其他接口")

if __name__ == "__main__":
    main()