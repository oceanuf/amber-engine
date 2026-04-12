#!/usr/bin/env python3
"""
测试修复后的news_sentinel.py
"""

import os
import sys
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入修复后的模块
from scripts.pipeline.news_sentinel import NewsSentinel, NewsSource

print("测试修复后的news_sentinel.py")
print("=" * 60)

# 测试1: 检查新闻源配置
print("\n1. 检查新闻源配置:")
sentinel = NewsSentinel()

print(f"新闻源数量: {len(sentinel.news_sources)}")
print(f"启用的新闻源: {sum(1 for s in sentinel.news_sources if s.enabled)}")

for i, source in enumerate(sentinel.news_sources):
    if source.enabled:
        print(f"  {i+1}. {source.name} ({source.type}) - 权重: {source.weight}, 频率限制: {source.rate_limit_seconds}秒")

# 测试2: 检查Tushare接口配置
print("\n2. 检查Tushare接口配置:")
tushare_source = None
for source in sentinel.news_sources:
    if source.type == "tushare" and source.enabled:
        tushare_source = source
        break

if tushare_source:
    print(f"  ✅ 找到Tushare新闻源: {tushare_source.name}")
    print(f"     接口URL: {tushare_source.url}")
    print(f"     频率限制: {tushare_source.rate_limit_seconds}秒 (约{tushare_source.rate_limit_seconds/60:.1f}分钟)")
    
    if tushare_source.rate_limit_seconds >= 1800:
        print(f"     ✅ 频率限制合理 (≥30分钟，符合每小时最多2次限制)")
    else:
        print(f"     ⚠️  频率限制可能过短")
else:
    print("  ❌ 未找到启用的Tushare新闻源")

# 测试3: 检查Akshare新闻源
print("\n3. 检查Akshare新闻源:")
akshare_source = None
for source in sentinel.news_sources:
    if source.type == "akshare" and source.enabled:
        akshare_source = source
        break

if akshare_source:
    print(f"  ✅ 找到Akshare新闻源: {akshare_source.name}")
    print(f"     权重: {akshare_source.weight}")
    print(f"     频率限制: {akshare_source.rate_limit_seconds}秒")
else:
    print("  ❌ 未找到启用的Akshare新闻源")

# 测试4: 检查方法是否存在
print("\n4. 检查方法完整性:")
methods_to_check = [
    "fetch_from_tushare",
    "fetch_from_rss", 
    "fetch_from_akshare",
    "fetch_news",
    "analyze_news",
    "save_news"
]

for method_name in methods_to_check:
    if hasattr(sentinel, method_name):
        print(f"  ✅ {method_name}: 存在")
    else:
        print(f"  ❌ {method_name}: 不存在")

# 测试5: 检查Tushare Token
print("\n5. 检查Tushare Token:")
token = sentinel.tushare_token
if token and token != "your_tushare_token_here":
    print(f"  ✅ Tushare Token已配置: {token[:20]}...")
else:
    print("  ⚠️  Tushare Token未配置或无效")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)

# 建议
print("\n💡 下一步建议:")
print("1. 运行 `python3 scripts/pipeline/news_sentinel.py` 测试接口联通性")
print("2. 检查生成的JSON文件内容完整性")
print("3. 验证新闻条目数量是否≥10条")
print("4. 检查content字段平均字数是否>50字")