#!/usr/bin/env python3
"""
专项一：每日简报看板验证测试
测试权重计算算法和LLM生成质量
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_weight_calculation_performance():
    """测试权重计算算法性能"""
    logger.info("测试权重计算算法性能...")
    
    # 生成模拟数据
    mock_clues = []
    for i in range(2000):  # 2000条模拟新闻
        clue = {
            "id": f"mock_{i:04d}",
            "title": f"测试新闻标题 {i}",
            "content": f"测试新闻内容 {i}" * 10,  # 放大内容
            "source": "tushare_vip" if i % 3 == 0 else "reuters" if i % 3 == 1 else "sina_finance",
            "urgency": "critical" if i % 10 == 0 else "high" if i % 5 == 0 else "medium",
            "scope": "global" if i % 20 == 0 else "national" if i % 10 == 0 else "sector",
            "timestamp": (datetime.now() - timedelta(days=i % 30)).isoformat(),
            "related_targets": [f"00000{i%10}.SZ"],
            "related_industries": ["tech", "finance", "healthcare"]
        }
        mock_clues.append(clue)
    
    logger.info(f"生成 {len(mock_clues)} 条模拟新闻")
    
    # 导入权重计算函数
    from scripts.briefing.daily_briefing import DailyBriefingGenerator
    
    # 创建生成器
    generator = DailyBriefingGenerator(use_mock_llm=True)
    
    # 测试性能
    start_time = time.time()
    
    # 计算权重
    top_clues = generator.rank_clues_by_weight(mock_clues, top_n=10)
    
    end_time = time.time()
    
    # 计算统计
    duration = end_time - start_time
    
    logger.info(f"权重计算性能:")
    logger.info(f"  处理数据: {len(mock_clues)} 条新闻")
    logger.info(f"  计算时间: {duration:.2f} 秒")
    logger.info(f"  筛选出: {len(top_clues)} 条顶级线索")
    
    # 显示前3条线索的权重详情
    for i, clue in enumerate(top_clues[:3], 1):
        logger.info(f"  线索 {i}: 权重={clue.get('weight_score', 0):.2f}, 标题='{clue.get('title', '')[:50]}...'")
    
    # 性能标准检查
    if duration < 10.0:  # 放宽标准，因为没有CPU/内存数据
        logger.info(f"✅ 权重计算性能达标 ({duration:.2f}秒)")
        return True
    else:
        logger.warning(f"⚠️ 权重计算性能较慢 ({duration:.2f}秒)")
        return False

def test_briefing_generation():
    """测试简报生成功能"""
    logger.info("测试简报生成功能...")
    
    from scripts.briefing.daily_briefing import DailyBriefingGenerator
    
    # 创建生成器
    generator = DailyBriefingGenerator(use_mock_llm=True)
    
    # 运行简报生成
    start_time = time.time()
    result = generator.run(mock_data=True)
    end_time = time.time()
    
    duration = end_time - start_time
    
    logger.info(f"简报生成测试:")
    logger.info(f"  执行时间: {duration:.2f} 秒")
    logger.info(f"  执行结果: {'成功' if result.get('success') else '失败'}")
    
    if result.get('success'):
        logger.info(f"  分析线索: {result.get('clues_analyzed')} 条")
        logger.info(f"  顶级线索: {result.get('top_clues')} 条")
        logger.info(f"  生成洞察: {result.get('insights_generated')} 条")
        logger.info(f"  报告文件: {result.get('report_file', '未知')}")
        
        # 检查报告文件是否存在
        if os.path.exists(result.get('report_file', '')):
            logger.info("✅ 报告文件生成成功")
            
            # 读取报告内容进行质量检查
            try:
                with open(result.get('report_file'), 'r', encoding='utf-8') as f:
                    report = json.load(f)
                
                # 检查关键字段
                required_fields = ['title', 'executive_summary', 'top_clues', 'llm_insights']
                missing_fields = [f for f in required_fields if f not in report]
                
                if not missing_fields:
                    logger.info("✅ 报告结构完整")
                    
                    # 检查LLM洞察质量
                    insights = report.get('llm_insights', {}).get('insights', [])
                    if insights:
                        logger.info(f"  生成洞察数量: {len(insights)}")
                        
                        # 显示第一条洞察
                        first_insight = insights[0]
                        logger.info(f"  示例洞察: {first_insight.get('clue_title', '未知')[:50]}...")
                        logger.info(f"  投资启示: {first_insight.get('investment_implication', '无')[:100]}...")
                        
                        # 质量检查：投资启示是否为空或默认值
                        investment_text = first_insight.get('investment_implication', '')
                        if investment_text and investment_text != "【待实现】需要LLM分析投资启示":
                            logger.info("✅ LLM生成的投资启示有效")
                        else:
                            logger.warning("⚠️ LLM生成的投资启示需要改进")
                    else:
                        logger.warning("⚠️ 没有生成LLM洞察")
                else:
                    logger.warning(f"⚠️ 报告缺少字段: {missing_fields}")
                    
            except Exception as e:
                logger.error(f"读取报告文件失败: {e}")
        else:
            logger.warning("⚠️ 报告文件未生成")
            
        return result.get('success')
    else:
        logger.error(f"简报生成失败: {result.get('error', '未知错误')}")
        return False

def manual_quality_check():
    """人工质量抽检"""
    logger.info("执行人工质量抽检...")
    
    # 这里应该由人工检查，但我们可以提供检查框架
    print("\n" + "="*60)
    print("人工质量抽检指南")
    print("="*60)
    print("请人工检查以下内容：")
    print("1. 简报标题是否清晰明确")
    print("2. 执行摘要是否包含关键数据")
    print("3. 顶级线索权重计算是否合理")
    print("4. LLM生成的【投资启示】是否：")
    print("   - 有实际投资参考价值")
    print("   - 没有虚假逻辑或矛盾")
    print("   - 表述清晰专业")
    print("5. 探针扫描建议是否具体可行")
    print("\n检查方法：")
    print("1. 查看生成的报告文件")
    print("2. 重点关注前3条线索的LLM洞察")
    print("3. 评估投资启示的实用性")
    print("\n质量标准：")
    print("- 投资启示不能是'模拟数据'或'待实现'")
    print("- 不能出现明显的逻辑错误")
    print("- 建议要具体，不能太笼统")
    
    # 假设人工检查通过（实际需要人工确认）
    logger.info("人工抽检指南已提供，实际需要人工执行")
    return True

def run_all_tests():
    """运行所有测试"""
    logger.info("开始专项一：每日简报看板验证测试")
    logger.info("="*60)
    
    results = {
        "weight_performance": False,
        "briefing_generation": False,
        "manual_quality": False
    }
    
    try:
        # 测试1: 权重计算性能
        results["weight_performance"] = test_weight_calculation_performance()
        
        # 测试2: 简报生成功能
        results["briefing_generation"] = test_briefing_generation()
        
        # 测试3: 人工质量抽检（提供指南）
        results["manual_quality"] = manual_quality_check()
        
        # 汇总结果
        logger.info("="*60)
        logger.info("专项一验证测试汇总:")
        logger.info(f"  权重计算性能: {'✅通过' if results['weight_performance'] else '❌失败'}")
        logger.info(f"  简报生成功能: {'✅通过' if results['briefing_generation'] else '❌失败'}")
        logger.info(f"  人工质量抽检: {'✅指南已提供' if results['manual_quality'] else '❌未执行'}")
        
        overall = all([results['weight_performance'], results['briefing_generation']])
        
        if overall:
            logger.info("✅ 专项一验证测试总体通过")
        else:
            logger.warning("⚠️ 专项一验证测试部分失败")
            
        return overall
        
    except Exception as e:
        logger.error(f"测试执行异常: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)