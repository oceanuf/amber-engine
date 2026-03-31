#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流示例 - 展示如何使用技能索引
文档编号: AE-WORKFLOW-001-V1.0
目的: 演示"先查表，后动手"的工作原则
"""

import os
import sys

def read_skills_index():
    """读取技能索引文件"""
    index_path = os.path.join(os.path.dirname(__file__), '..', 'SKILLS_INDEX.md')
    
    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        print(f"错误: 技能索引文件未找到: {index_path}")
        print("请确保SKILLS_INDEX.md文件存在于工作空间根目录")
        return None

def find_skill_by_keyword(content, keyword):
    """根据关键词查找技能"""
    lines = content.split('\n')
    found_skills = []
    
    for i, line in enumerate(lines):
        if keyword.lower() in line.lower():
            # 获取上下文
            start = max(0, i - 2)
            end = min(len(lines), i + 3)
            context = '\n'.join(lines[start:end])
            found_skills.append(context)
    
    return found_skills

def demonstrate_workflow(task_description):
    """演示工作流决策过程"""
    print("=" * 60)
    print(f"任务描述: {task_description}")
    print("=" * 60)
    
    # 第一步: 查阅技能索引
    print("\n📋 第一步: 查阅技能索引 (SKILLS_INDEX.md)")
    content = read_skills_index()
    
    if not content:
        return
    
    # 根据任务类型提取关键词
    keywords = []
    if "A股" in task_description or "股票" in task_description:
        keywords.extend(["AkShare", "A股", "股票"])
    if "美股" in task_description:
        keywords.extend(["Us-Stock", "美股"])
    if "新闻" in task_description or "舆情" in task_description:
        keywords.extend(["News", "新闻", "舆情"])
    if "报告" in task_description or "研报" in task_description:
        keywords.extend(["Report", "报告", "研报"])
    if "自动化" in task_description or "爬虫" in task_description:
        keywords.extend(["Playwright", "自动化", "爬虫"])
    
    print(f"提取的关键词: {keywords}")
    
    # 查找相关技能
    print("\n🔍 第二步: 查找相关技能")
    all_found = []
    for keyword in keywords:
        found = find_skill_by_keyword(content, keyword)
        if found:
            all_found.extend(found)
    
    # 去重并显示
    unique_found = []
    seen = set()
    for skill in all_found:
        if skill not in seen:
            seen.add(skill)
            unique_found.append(skill)
    
    if unique_found:
        print(f"找到 {len(unique_found)} 个相关技能:")
        for i, skill in enumerate(unique_found[:5], 1):  # 只显示前5个
            print(f"\n{i}. {skill}")
        
        if len(unique_found) > 5:
            print(f"\n... 还有 {len(unique_found) - 5} 个相关技能")
    else:
        print("未找到相关技能，可能需要开发新功能或使用通用技能")
    
    # 第三步: 构建工作流
    print("\n🔄 第三步: 构建工作流")
    
    # 根据任务类型推荐工作流
    if any(kw in task_description for kw in ["A股", "股票", "数据"]):
        print("推荐工作流: 数据获取 → 分析处理 → 报告生成")
        print("  1. 数据获取: AkShare-Stock (A股数据)")
        print("  2. 分析处理: 使用现有算法库 (G1-G10)")
        print("  3. 报告生成: Research-Paper-Writer → Word/DOCX")
        
    elif "新闻" in task_description or "舆情" in task_description:
        print("推荐工作流: 新闻收集 → 情感分析 → 报告生成")
        print("  1. 新闻收集: Market-News-Analyst + CCTV-News-Fetcher")
        print("  2. 情感分析: Sentiment-Analysis")
        print("  3. 报告生成: Summarize → Research-Paper-Writer")
        
    elif "自动化" in task_description or "爬虫" in task_description:
        print("推荐工作流: 网页自动化 → 数据提取 → 数据处理")
        print("  1. 网页自动化: Playwright-MCP")
        print("  2. 数据提取: 自定义解析逻辑")
        print("  3. 数据处理: 集成到现有数据管道")
        
    else:
        print("通用工作流: 问题分析 → 技能选择 → 执行验证")
        print("  1. 问题分析: 明确需求和约束")
        print("  2. 技能选择: 查阅SKILLS_INDEX.md选择合适技能")
        print("  3. 执行验证: 测试技能组合效果")
    
    # 第四步: 检查使用禁令
    print("\n🚫 第四步: 检查使用禁令")
    print("需要避免的行为:")
    print("  1. 禁手动爬虫: 优先使用AkShare或Playwright")
    print("  2. 禁重复解析: 优先使用Summarize等文本处理技能")
    print("  3. 禁盲目同步: 必须通过API-Tester验证后才能同步到生产")
    
    print("\n✅ 工作流规划完成")

def main():
    """主函数"""
    print("琥珀引擎工作流决策演示")
    print("=" * 60)
    
    # 示例任务
    example_tasks = [
        "获取A股平安银行的历史K线数据和财务数据",
        "分析今日美股市场新闻和舆情",
        "自动化抓取某网站的金融数据",
        "生成一份包含A股和美股分析的每日市场报告"
    ]
    
    print("示例任务:")
    for i, task in enumerate(example_tasks, 1):
        print(f"{i}. {task}")
    
    print("\n" + "=" * 60)
    
    # 演示第一个任务
    demonstrate_workflow(example_tasks[0])
    
    print("\n" + "=" * 60)
    print("工作流决策演示完成")
    print("\n关键要点:")
    print("1. 每次任务前必须查阅SKILLS_INDEX.md")
    print("2. 遵循'先查表，后动手'原则")
    print("3. 避免违反使用禁令")
    print("4. 合理组合技能构建工作流")

if __name__ == "__main__":
    main()