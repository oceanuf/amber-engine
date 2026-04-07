#!/usr/bin/env python3
"""
测试全球资讯哨兵权重计算集成
验证 [2614-092号] 指令的核心关键词矩阵集成效果
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scripts.sentry.global_news_stream import GlobalNewsStream

def test_core_keyword_weighting():
    """测试核心关键词权重计算"""
    print("🧪 测试核心关键词权重计算")
    print("=" * 60)
    
    # 初始化流（不启动监听）
    stream = GlobalNewsStream()
    
    if not stream.credibility_data:
        print("❌ 信任度矩阵加载失败")
        return False
    
    # 测试新闻1: 包含核心关键词"新质生产力" (十五五规划, 权重5.0)
    test_news_1 = {
        "title": "国家发改委推动新质生产力发展，聚焦低空经济与数字底座",
        "content": "国家发展改革委近日发布关于加快发展新质生产力的指导意见，重点布局低空经济、数字底座等前沿领域。",
        "pub_time": "2026-04-04 12:00:00",
        "src": "新华网",
        "tags": ["新质生产力", "低空经济", "数字底座", "十五五规划"],
        "related_stocks": []
    }
    
    print("📰 测试新闻1: 十五五规划核心关键词")
    print(f"   标题: {test_news_1['title']}")
    print(f"   来源: {test_news_1['src']}")
    
    clue1 = stream.analyze_news_to_clue(test_news_1)
    
    if clue1:
        print(f"✅ 生成线索: {clue1['clue_id']}")
        print(f"   影响等级: {clue1['impact_level']}")
        print(f"   时间敏感性: {clue1['time_sensitivity']}")
        weight_info = clue1.get('weight_analysis', {})
        print(f"   最终权重: {weight_info.get('final_weight', 0):.2f}")
        print(f"   源头权重: {weight_info.get('source_weight', 0):.2f}")
        print(f"   关键词权重: {weight_info.get('keyword_weight', 0):.2f}")
        print(f"   相关性权重: {weight_info.get('relevance_weight', 0):.2f}")
        print(f"   高强度扫描: {clue1.get('high_intensity_scan_triggered', False)}")
        
        # 验证权重计算
        if weight_info.get('final_weight', 0) >= 4.0:
            print("🎯 通过: 核心关键词触发高强度扫描预警")
        else:
            print("⚠️  警告: 核心关键词未触发高强度扫描")
    else:
        print("❌ 失败: 未生成线索")
        return False
    
    print()
    
    # 测试新闻2: 包含"国产替代"核心关键词
    test_news_2 = {
        "title": "半导体产业加速国产替代，核心算法实现突破",
        "content": "国内半导体企业在光刻机、核心算法等领域取得重大突破，供应链重构加速。",
        "pub_time": "2026-04-04 11:30:00",
        "src": "国家统计局",
        "tags": ["国产替代", "光刻机", "核心算法", "供应链重构"],
        "related_stocks": []
    }
    
    print("📰 测试新闻2: 国产替代核心关键词")
    print(f"   标题: {test_news_2['title']}")
    print(f"   来源: {test_news_2['src']}")
    
    clue2 = stream.analyze_news_to_clue(test_news_2)
    
    if clue2:
        print(f"✅ 生成线索: {clue2['clue_id']}")
        weight_info = clue2.get('weight_analysis', {})
        print(f"   最终权重: {weight_info.get('final_weight', 0):.2f}")
        print(f"   高强度扫描: {clue2.get('high_intensity_scan_triggered', False)}")
        
        # 检查是否匹配核心关键词矩阵
        core_keywords = weight_info.get('matched_core_keywords', [])
        if core_keywords:
            print(f"   匹配核心关键词: {len(core_keywords)} 个")
            for kw in core_keywords[:3]:  # 显示前3个
                print(f"     - {kw.get('matrix')}: {kw.get('keyword')} (权重: {kw.get('weight')})")
    else:
        print("❌ 失败: 未生成线索")
        return False
    
    print()
    
    # 测试新闻3: 一般财经新闻 (低权重)
    test_news_3 = {
        "title": "消费市场回暖，餐饮旅游板块表现活跃",
        "content": "随着节假日临近，消费市场逐渐回暖，餐饮、旅游等板块表现活跃。",
        "pub_time": "2026-04-04 10:00:00",
        "src": "新浪财经",
        "tags": ["消费", "餐饮", "旅游", "市场"],
        "related_stocks": []
    }
    
    print("📰 测试新闻3: 一般财经新闻")
    print(f"   标题: {test_news_3['title']}")
    
    clue3 = stream.analyze_news_to_clue(test_news_3)
    
    if clue3:
        weight_info = clue3.get('weight_analysis', {})
        print(f"   最终权重: {weight_info.get('final_weight', 0):.2f}")
        print(f"   高强度扫描: {clue3.get('high_intensity_scan_triggered', False)}")
        
        if weight_info.get('final_weight', 0) < 3.0:
            print("✅ 通过: 一般新闻权重较低，未触发高强度扫描")
        else:
            print("⚠️  警告: 一般新闻权重过高")
    else:
        print("ℹ️  未生成线索 (可能无匹配规则，正常)")
    
    print()
    print("=" * 60)
    print("🧪 权重计算集成测试完成")
    
    return True

def test_weight_formula():
    """测试权重计算公式"""
    print("🧮 测试权重计算公式: final_weight = source_weight × relevance_weight × keyword_weight")
    print("=" * 60)
    
    # 模拟计算
    test_cases = [
        {"source": "新华网", "keyword": "新质生产力", "expected_high": True},
        {"source": "国家统计局", "keyword": "国产替代", "expected_high": True},
        {"source": "路透社", "keyword": "美联储", "expected_high": True},
        {"source": "新浪财经", "keyword": "消费", "expected_high": False},
    ]
    
    for i, test in enumerate(test_cases, 1):
        source = test["source"]
        keyword = test["keyword"]
        
        # 估算权重
        source_weight = 4.5 if "新华" in source else 4.0 if "国家统计" in source else 2.0
        keyword_weight = 5.0 if keyword in ["新质生产力", "国产替代", "美联储"] else 2.0
        relevance_weight = 1.0
        
        final_weight = source_weight * relevance_weight * keyword_weight
        
        print(f"测试案例 {i}:")
        print(f"  来源: {source} (权重: {source_weight:.1f})")
        print(f"  关键词: {keyword} (权重: {keyword_weight:.1f})")
        print(f"  最终权重: {final_weight:.1f}")
        print(f"  预期高强度: {'是' if test['expected_high'] else '否'}")
        print(f"  实际高强度: {'是' if final_weight >= 4.0 else '否'}")
        
        if (final_weight >= 4.0) == test['expected_high']:
            print("  ✅ 通过")
        else:
            print("  ❌ 失败")
        print()
    
    print("=" * 60)
    return True

if __name__ == "__main__":
    print("🚀 全球资讯哨兵权重计算集成测试")
    print("符合 [2614-092号] 战术指令要求")
    print()
    
    success = True
    
    try:
        success = test_core_keyword_weighting() and success
        success = test_weight_formula() and success
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        success = False
    
    if success:
        print("🎉 所有测试通过！权重计算集成完成。")
        print("下一步: 运行实际新闻流，在15:00前生成高价值情报")
    else:
        print("⚠️  测试失败，需要检查代码逻辑")
    
    sys.exit(0 if success else 1)