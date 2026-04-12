#!/usr/bin/env python3
"""
检查新闻内容完整性
"""

import json
import os

# 读取最新的新闻文件
news_dir = "/home/luckyelite/.openclaw/workspace/amber-engine/database/news"
latest_file = None
latest_time = 0

for filename in os.listdir(news_dir):
    if filename.startswith("news_") and filename.endswith(".json"):
        filepath = os.path.join(news_dir, filename)
        mtime = os.path.getmtime(filepath)
        if mtime > latest_time:
            latest_time = mtime
            latest_file = filepath

if not latest_file:
    print("❌ 未找到新闻文件")
    exit(1)

print(f"📁 检查文件: {latest_file}")
print("=" * 60)

with open(latest_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

metadata = data.get("metadata", {})
news_items = data.get("news", [])

print(f"📊 元数据:")
print(f"   生成时间: {metadata.get('generation_time')}")
print(f"   新闻总数: {metadata.get('total_news')}")
print(f"   使用的源: {', '.join(metadata.get('sources_used', []))}")
print(f"   宏观影响新闻: {metadata.get('macro_impact_news')}")

print(f"\n📈 内容完整性分析:")
print(f"   新闻条目数: {len(news_items)}")

# 分析内容长度
content_lengths = []
news_with_content = 0
news_without_content = 0

for i, item in enumerate(news_items):
    content = item.get("content", "")
    title = item.get("title", "")[:50]
    source = item.get("source", "")
    
    if content and content.strip():
        content_length = len(content)
        content_lengths.append(content_length)
        news_with_content += 1
    else:
        news_without_content += 1
        print(f"   ⚠️  新闻 {i+1} 缺少内容: {title}... ({source})")

if content_lengths:
    avg_length = sum(content_lengths) / len(content_lengths)
    max_length = max(content_lengths)
    min_length = min(content_lengths)
    
    print(f"\n   📊 统计结果:")
    print(f"     有内容的新闻: {news_with_content}/{len(news_items)}")
    print(f"     平均内容长度: {avg_length:.0f} 字符")
    print(f"     最长内容: {max_length} 字符")
    print(f"     最短内容: {min_length} 字符")
    
    # 检查验收标准
    print(f"\n   ✅ 验收标准检查:")
    
    # 1. 新闻条目数 ≥ 10
    if len(news_items) >= 10:
        print(f"     1. 新闻条目数 ≥ 10: ✅ 通过 ({len(news_items)} 条)")
    else:
        print(f"     1. 新闻条目数 ≥ 10: ❌ 失败 ({len(news_items)} 条)")
    
    # 2. 平均内容长度 > 50字
    if avg_length > 50:
        print(f"     2. 平均内容长度 > 50字: ✅ 通过 ({avg_length:.0f} 字符)")
    else:
        print(f"     2. 平均内容长度 > 50字: ❌ 失败 ({avg_length:.0f} 字符)")
    
    # 3. 检查是否有完整的title和content字段
    complete_news = 0
    for item in news_items:
        if item.get("title") and item.get("content"):
            complete_news += 1
    
    if complete_news >= 10:
        print(f"     3. 完整新闻(有标题和内容) ≥ 10条: ✅ 通过 ({complete_news} 条)")
    else:
        print(f"     3. 完整新闻(有标题和内容) ≥ 10条: ❌ 失败 ({complete_news} 条)")
    
else:
    print(f"\n   ❌ 所有新闻都缺少内容字段")

print(f"\n💡 建议:")
if news_without_content > 0:
    print(f"   - 有 {news_without_content} 条新闻缺少内容，需要检查新闻源")
if avg_length < 50:
    print(f"   - 平均内容长度不足50字，需要优化新闻源或内容提取逻辑")
if len(news_items) < 10:
    print(f"   - 新闻条目数不足10条，需要启用更多新闻源")

print(f"\n" + "=" * 60)
print("检查完成")
print("=" * 60)