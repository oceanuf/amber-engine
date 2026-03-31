#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单网络加固测试
验证代理管理器和重试机制的基本功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from network.proxy_manager import ProxyManager
import time
import random

print("=== 简单网络加固测试 ===")

# 创建代理管理器实例
print("1. 创建代理管理器...")
proxy_manager = ProxyManager(max_retries=2, base_delay=1.0)
print(f"   用户代理池: {len(proxy_manager.user_agents)}个")
print(f"   代理池: {len(proxy_manager.proxy_pool)}个")
print(f"   最大重试: {proxy_manager.max_retries}次")

# 测试连通性
print("\n2. 测试网络连通性...")
if proxy_manager.test_connectivity():
    print("✅ 网络连通性测试通过")
else:
    print("❌ 网络连通性测试失败")

# 测试随机头部生成
print("\n3. 测试随机头部生成...")
for i in range(3):
    headers = proxy_manager.get_random_headers()
    print(f"   测试 {i+1}: User-Agent = {headers.get('User-Agent', 'N/A')[:50]}...")

# 测试延迟计算
print("\n4. 测试延迟计算...")
for attempt in range(3):
    delay = proxy_manager.calculate_delay(attempt)
    print(f"   尝试 {attempt+1}: 延迟 = {delay:.2f}秒")

# 测试简单请求
print("\n5. 测试简单请求...")
test_urls = [
    "https://httpbin.org/get",
    "https://httpbin.org/ip",
    "https://httpbin.org/user-agent"
]

success_count = 0
for url in test_urls:
    print(f"\n   测试URL: {url}")
    response = proxy_manager.make_request_with_retry(url, timeout=(5, 10))
    
    if response and response.status_code == 200:
        print(f"   ✅ 请求成功: 状态码 {response.status_code}")
        
        # 显示部分响应内容
        try:
            data = response.json()
            if 'url' in data:
                print(f"       URL: {data['url']}")
            if 'origin' in data:
                print(f"       来源IP: {data['origin']}")
            if 'user-agent' in data:
                print(f"       用户代理: {data['user-agent'][:50]}...")
        except:
            print(f"       响应内容: {response.text[:100]}...")
        
        success_count += 1
    else:
        print(f"   ❌ 请求失败")
        if response:
            print(f"       状态码: {response.status_code}")

print(f"\n=== 测试结果 ===")
print(f"成功请求: {success_count}/{len(test_urls)}")
print(f"成功率: {success_count/len(test_urls):.1%}")

if success_count >= len(test_urls) * 0.7:
    print("✅ 网络加固基本功能测试通过")
    sys.exit(0)
else:
    print("❌ 网络加固基本功能测试失败")
    sys.exit(1)