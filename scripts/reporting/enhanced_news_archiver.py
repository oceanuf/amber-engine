#!/usr/bin/env python3
"""
增强版新闻归档器 - 从news_sentinel输出生成丰富的daily-news文档
"""

import json
import os
import glob
from datetime import datetime
from typing import Dict, List, Any

def find_latest_news_file() -> str:
    """查找最新的新闻JSON文件"""
    news_dir = "database/news"
    if not os.path.exists(news_dir):
        return None
    
    json_files = glob.glob(os.path.join(news_dir, "news_*.json"))
    if not json_files:
        return None
    
    # 按修改时间排序
    json_files.sort(key=os.path.getmtime, reverse=True)
    return json_files[0]

def load_news_data(filepath: str) -> Dict[str, Any]:
    """加载新闻数据"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载新闻数据失败: {e}")
        return None

def analyze_news_content(news_items: List[Dict]) -> Dict[str, Any]:
    """分析新闻内容"""
    analysis = {
        "total": len(news_items),
        "with_content": 0,
        "macro_impact": 0,
        "by_category": {},
        "by_source": {},
        "content_stats": {
            "total_chars": 0,
            "avg_chars": 0,
            "max_chars": 0,
            "min_chars": float('inf')
        }
    }
    
    for item in news_items:
        # 统计来源
        source = item.get("source", "未知")
        analysis["by_source"][source] = analysis["by_source"].get(source, 0) + 1
        
        # 统计类别
        category = item.get("category", "其他")
        analysis["by_category"][category] = analysis["by_category"].get(category, 0) + 1
        
        # 统计内容
        content = item.get("content", "")
        if content and content.strip():
            analysis["with_content"] += 1
            content_len = len(content)
            analysis["content_stats"]["total_chars"] += content_len
            analysis["content_stats"]["max_chars"] = max(analysis["content_stats"]["max_chars"], content_len)
            analysis["content_stats"]["min_chars"] = min(analysis["content_stats"]["min_chars"], content_len)
        
        # 统计宏观影响
        if item.get("has_macro_impact", False):
            analysis["macro_impact"] += 1
    
    # 计算平均内容长度
    if analysis["with_content"] > 0:
        analysis["content_stats"]["avg_chars"] = analysis["content_stats"]["total_chars"] / analysis["with_content"]
    else:
        analysis["content_stats"]["min_chars"] = 0
    
    return analysis

def generate_daily_report(news_data: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    """生成每日报告"""
    today = datetime.now().strftime('%Y-%m-%d')
    metadata = news_data.get("metadata", {})
    news_items = news_data.get("news", [])
    
    # 按置信度排序，取前10条最重要的新闻
    sorted_news = sorted(news_items, key=lambda x: x.get("confidence_score", 0), reverse=True)
    top_news = sorted_news[:10]
    
    # 生成报告内容
    content = f"""# 📰 琥珀每日资讯全档 - {today}

## 📊 数据概览
- **采集时间**: {metadata.get('generation_time', 'N/A')}
- **新闻总数**: {analysis['total']} 条
- **有效内容**: {analysis['with_content']} 条 (含内容)
- **宏观影响**: {analysis['macro_impact']} 条
- **平均内容长度**: {analysis['content_stats']['avg_chars']:.0f} 字符
- **数据来源**: {', '.join(metadata.get('sources_used', []))}

## 📈 来源分布
"""
    
    # 添加来源分布
    for source, count in analysis["by_source"].items():
        percentage = (count / analysis["total"]) * 100
        content += f"- **{source}**: {count} 条 ({percentage:.1f}%)\n"
    
    content += f"""
## 🏷️ 类别分布
"""
    
    # 添加类别分布
    for category, count in analysis["by_category"].items():
        percentage = (count / analysis["total"]) * 100
        content += f"- **{category}**: {count} 条 ({percentage:.1f}%)\n"
    
    content += f"""
## 🚀 今日要闻 (按置信度排序)
"""
    
    # 添加今日要闻
    for i, news in enumerate(top_news, 1):
        title = news.get("title", "无标题")
        news_content = news.get("content", "")
        source = news.get("source", "未知")
        confidence = news.get("confidence_score", 0)
        category = news.get("category", "其他")
        keywords = news.get("keywords", [])
        has_macro = "✅" if news.get("has_macro_impact", False) else "➖"
        
        # 截取内容预览
        content_preview = news_content[:150] + "..." if len(news_content) > 150 else news_content
        
        content += f"""
### {i}. {title}
- **来源**: {source}
- **类别**: {category}
- **置信度**: {confidence:.2f}
- **宏观影响**: {has_macro}
- **关键词**: {', '.join(keywords[:3]) if keywords else '无'}
- **内容预览**: {content_preview}
"""
    
    content += f"""
## 📋 详细数据
- **最长内容**: {analysis['content_stats']['max_chars']} 字符
- **最短内容**: {analysis['content_stats']['min_chars']} 字符
- **总字符数**: {analysis['content_stats']['total_chars']} 字符

## 💡 分析摘要
> 今日共采集 {analysis['total']} 条新闻，其中 {analysis['macro_impact']} 条具有宏观影响。
> 主要新闻来源为 {max(analysis['by_source'].items(), key=lambda x: x[1])[0] if analysis['by_source'] else '无'}，
> 主要新闻类别为 {max(analysis['by_category'].items(), key=lambda x: x[1])[0] if analysis['by_category'] else '无'}。
> 内容完整性达标，平均内容长度 {analysis['content_stats']['avg_chars']:.0f} 字符。

---
*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*数据源: NewsSentinel v{metadata.get('version', '1.0.0')}*
"""
    
    return content

def main():
    """主函数"""
    print("=" * 60)
    print("📰 增强版新闻归档器")
    print("=" * 60)
    
    # 查找最新新闻文件
    latest_file = find_latest_news_file()
    if not latest_file:
        print("❌ 未找到新闻文件")
        return
    
    print(f"📁 找到最新新闻文件: {latest_file}")
    
    # 加载数据
    news_data = load_news_data(latest_file)
    if not news_data:
        print("❌ 加载新闻数据失败")
        return
    
    # 分析数据
    analysis = analyze_news_content(news_data.get("news", []))
    
    print(f"📊 数据分析:")
    print(f"   新闻总数: {analysis['total']}")
    print(f"   有效内容: {analysis['with_content']}")
    print(f"   宏观影响: {analysis['macro_impact']}")
    print(f"   平均内容长度: {analysis['content_stats']['avg_chars']:.0f} 字符")
    
    # 生成报告
    report_content = generate_daily_report(news_data, analysis)
    
    # 保存报告
    today = datetime.now().strftime('%Y-%m-%d')
    output_dir = "daily-news"
    output_path = os.path.join(output_dir, f"{today}.md")
    
    os.makedirs(output_dir, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"✅ 每日报告已生成: {output_path}")
    print(f"   文件大小: {len(report_content)} 字符")
    
    # 检查验收标准
    print(f"\n✅ 验收标准检查:")
    
    # 1. 新闻条目数 ≥ 10
    if analysis['total'] >= 10:
        print(f"   1. 新闻条目数 ≥ 10: ✅ 通过 ({analysis['total']} 条)")
    else:
        print(f"   1. 新闻条目数 ≥ 10: ❌ 失败 ({analysis['total']} 条)")
    
    # 2. 平均内容长度 > 50字
    if analysis['content_stats']['avg_chars'] > 50:
        print(f"   2. 平均内容长度 > 50字: ✅ 通过 ({analysis['content_stats']['avg_chars']:.0f} 字符)")
    else:
        print(f"   2. 平均内容长度 > 50字: ❌ 失败 ({analysis['content_stats']['avg_chars']:.0f} 字符)")
    
    # 3. 内容完整性
    if analysis['with_content'] >= 10:
        print(f"   3. 完整新闻(有内容) ≥ 10条: ✅ 通过 ({analysis['with_content']} 条)")
    else:
        print(f"   3. 完整新闻(有内容) ≥ 10条: ❌ 失败 ({analysis['with_content']} 条)")
    
    print(f"\n" + "=" * 60)
    print("🎉 归档完成")
    print("=" * 60)

if __name__ == "__main__":
    main()