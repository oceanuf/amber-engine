#!/usr/bin/env python3
"""
宏观脉冲分发器 (Macro Pulse Dispatcher)
版本: 1.0.0
描述: 生成T日宏观脉冲简报，为琥珀引擎提供宏观感知输入。
功能:
  1. 调用新闻哨兵获取新闻数据
  2. 分析宏观影响新闻
  3. 生成宏观脉冲简报
  4. 集成到cron_manager.sh的Step 0
"""

import os
import sys
import json
import datetime
import argparse
from typing import Dict, List, Any, Optional
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入新闻哨兵
try:
    from scripts.pipeline.news_sentinel import NewsSentinel
except ImportError:
    # 尝试相对导入
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from pipeline.news_sentinel import NewsSentinel

class MacroPulseDispatcher:
    """宏观脉冲分发器"""
    
    def __init__(self, output_dir: Optional[str] = None):
        """初始化分发器"""
        if output_dir:
            self.output_dir = output_dir
        else:
            self.output_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "reports", "macro"
            )
        
        # 确保目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 初始化新闻哨兵
        self.sentinel = NewsSentinel()
        
        logger.info(f"宏观脉冲分发器初始化完成，输出目录: {self.output_dir}")
    
    def load_today_news(self) -> List[Dict]:
        """加载今日新闻数据"""
        today_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "database", "news", "news_today.json"
        )
        
        if not os.path.exists(today_file):
            logger.warning(f"今日新闻文件不存在: {today_file}")
            return []
        
        try:
            with open(today_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            news_items = data.get("news", [])
            logger.info(f"✅ 从 {today_file} 加载 {len(news_items)} 条新闻")
            return news_items
        except Exception as e:
            logger.error(f"❌ 加载今日新闻失败: {e}")
            return []
    
    def fetch_fresh_news(self) -> List[Dict]:
        """获取新鲜新闻数据"""
        logger.info("🔄 获取新鲜新闻数据...")
        
        try:
            news_items, output_file = self.sentinel.run(limit_per_source=15)
            
            if not news_items:
                logger.warning("⚠️  未获取到新鲜新闻")
                return []
            
            # 转换为字典列表
            news_dicts = [item.__dict__ for item in news_items]
            logger.info(f"✅ 获取到 {len(news_dicts)} 条新鲜新闻")
            return news_dicts
        except Exception as e:
            logger.error(f"❌ 获取新鲜新闻失败: {e}")
            return []
    
    def analyze_macro_pulse(self, news_items: List[Dict]) -> Dict:
        """分析宏观脉冲"""
        logger.info("🔍 分析宏观脉冲...")
        
        # 过滤有宏观影响的新闻
        macro_news = [item for item in news_items if item.get("has_macro_impact", False)]
        
        # 统计各类别数量
        category_stats = {}
        for item in macro_news:
            category = item.get("category", "其他")
            category_stats[category] = category_stats.get(category, 0) + 1
        
        # 提取关键标签
        all_tags = []
        for item in macro_news:
            tags = item.get("macro_pulse_tags", [])
            all_tags.extend(tags)
        
        tag_stats = {}
        for tag in all_tags:
            tag_stats[tag] = tag_stats.get(tag, 0) + 1
        
        # 计算宏观强度指数
        macro_intensity = self._calculate_macro_intensity(macro_news)
        
        # 生成宏观态势评估
        macro_assessment = self._generate_macro_assessment(macro_news, category_stats, macro_intensity)
        
        # 提取关键新闻摘要
        key_news = self._extract_key_news(macro_news)
        
        analysis_result = {
            "total_news": len(news_items),
            "macro_news_count": len(macro_news),
            "macro_intensity": macro_intensity,
            "category_distribution": category_stats,
            "tag_distribution": tag_stats,
            "macro_assessment": macro_assessment,
            "key_news": key_news,
            "analysis_time": datetime.datetime.now().isoformat()
        }
        
        logger.info(f"📊 宏观分析完成: {len(macro_news)}/{len(news_items)} 条有宏观影响")
        return analysis_result
    
    def _calculate_macro_intensity(self, macro_news: List[Dict]) -> float:
        """计算宏观强度指数"""
        if not macro_news:
            return 0.0
        
        total_score = 0.0
        for item in macro_news:
            # 基于置信度得分和关键词数量
            confidence = item.get("confidence_score", 0.0)
            keywords_count = len(item.get("keywords", []))
            
            # 新闻源权重
            source_name = item.get("source", "")
            source_weight = 0.5
            for source in self.sentinel.news_sources:
                if source.name == source_name:
                    source_weight = source.weight
                    break
            
            item_score = confidence * source_weight * (1 + min(keywords_count * 0.1, 0.5))
            total_score += item_score
        
        # 归一化到0-1范围
        max_possible = len(macro_news) * 1.0 * 1.0 * 1.5  # 最大可能得分
        if max_possible > 0:
            intensity = total_score / max_possible
        else:
            intensity = 0.0
        
        return min(max(intensity, 0.0), 1.0)
    
    def _generate_macro_assessment(self, macro_news: List[Dict], 
                                  category_stats: Dict, macro_intensity: float) -> Dict:
        """生成宏观态势评估"""
        assessment = {
            "overall_tone": "中性",
            "risk_level": "低",
            "investment_implication": "无明显影响",
            "key_themes": [],
            "watch_items": []
        }
        
        if not macro_news:
            assessment["overall_tone"] = "平静"
            assessment["notes"] = "今日无显著宏观事件"
            return assessment
        
        # 根据宏观强度确定整体基调
        if macro_intensity >= 0.7:
            assessment["overall_tone"] = "强烈"
            assessment["risk_level"] = "高"
        elif macro_intensity >= 0.4:
            assessment["overall_tone"] = "活跃"
            assessment["risk_level"] = "中"
        elif macro_intensity >= 0.1:
            assessment["overall_tone"] = "温和"
            assessment["risk_level"] = "低"
        else:
            assessment["overall_tone"] = "平静"
            assessment["risk_level"] = "很低"
        
        # 确定关键主题（出现最多的类别）
        if category_stats:
            top_categories = sorted(category_stats.items(), key=lambda x: x[1], reverse=True)[:3]
            assessment["key_themes"] = [cat for cat, count in top_categories]
        
        # 生成投资影响
        if macro_intensity >= 0.7:
            assessment["investment_implication"] = "可能对市场产生显著影响，建议密切关注"
        elif macro_intensity >= 0.4:
            assessment["investment_implication"] = "对特定板块可能有影响，建议关注相关标的"
        elif macro_intensity >= 0.1:
            assessment["investment_implication"] = "影响有限，可保持现有策略"
        else:
            assessment["investment_implication"] = "无明显影响，正常操作"
        
        # 提取需要关注的项目
        watch_items = []
        for item in macro_news:
            if item.get("confidence_score", 0) >= 0.7:
                watch_items.append({
                    "title": item.get("title", "")[:50],
                    "category": item.get("category", ""),
                    "confidence": item.get("confidence_score", 0),
                    "keywords": item.get("keywords", [])[:3]
                })
        
        assessment["watch_items"] = watch_items[:5]  # 最多5个
        
        return assessment
    
    def _extract_key_news(self, macro_news: List[Dict]) -> List[Dict]:
        """提取关键新闻摘要"""
        if not macro_news:
            return []
        
        # 按置信度排序
        sorted_news = sorted(macro_news, key=lambda x: x.get("confidence_score", 0), reverse=True)
        
        key_news = []
        for item in sorted_news[:5]:  # 最多5条
            key_news.append({
                "title": item.get("title", ""),
                "source": item.get("source", ""),
                "category": item.get("category", ""),
                "confidence": item.get("confidence_score", 0),
                "keywords": item.get("keywords", [])[:5],
                "has_macro_impact": item.get("has_macro_impact", False),
                "summary": self._generate_news_summary(item)
            })
        
        return key_news
    
    def _generate_news_summary(self, news_item: Dict) -> str:
        """生成新闻摘要"""
        title = news_item.get("title", "")
        content = news_item.get("content", "")
        
        # 如果内容较短，直接使用
        if len(content) <= 200:
            return content
        
        # 否则提取前200字符
        return content[:200] + "..."
    
    def generate_pulse_report(self, analysis_result: Dict) -> str:
        """生成宏观脉冲报告"""
        logger.info("📝 生成宏观脉冲报告...")
        
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        report_data = {
            "metadata": {
                "report_type": "宏观脉冲简报",
                "date": today,
                "generated_by": "MacroPulseDispatcher",
                "version": "1.0.0",
                "generation_time": datetime.datetime.now().isoformat()
            },
            "executive_summary": {
                "total_news_analyzed": analysis_result["total_news"],
                "macro_news_count": analysis_result["macro_news_count"],
                "macro_intensity_index": analysis_result["macro_intensity"],
                "overall_tone": analysis_result["macro_assessment"]["overall_tone"],
                "risk_level": analysis_result["macro_assessment"]["risk_level"],
                "investment_implication": analysis_result["macro_assessment"]["investment_implication"]
            },
            "detailed_analysis": {
                "category_distribution": analysis_result["category_distribution"],
                "tag_distribution": analysis_result["tag_distribution"],
                "key_themes": analysis_result["macro_assessment"]["key_themes"],
                "watch_items": analysis_result["macro_assessment"]["watch_items"]
            },
            "key_news_highlights": analysis_result["key_news"],
            "technical_details": {
                "analysis_methodology": "基于新闻哨兵的关键词矩阵与置信度算法",
                "intensity_calculation": "综合考虑新闻源权重、置信度得分、关键词数量",
                "thresholds": {
                    "macro_impact": "confidence_score >= 0.5",
                    "high_intensity": ">= 0.7",
                    "medium_intensity": "0.4-0.7",
                    "low_intensity": "0.1-0.4"
                }
            }
        }
        
        # 保存报告
        filename = f"macro_pulse_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 宏观脉冲报告已保存: {filepath}")
            
            # 同时保存今日最新文件
            today_file = os.path.join(self.output_dir, "macro_pulse_today.json")
            with open(today_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 今日宏观脉冲报告已更新: {today_file}")
            
            return filepath
        except Exception as e:
            logger.error(f"❌ 保存报告失败: {e}")
            return ""
    
    def generate_human_readable_summary(self, analysis_result: Dict) -> str:
        """生成人类可读的摘要"""
        assessment = analysis_result["macro_assessment"]
        
        summary_lines = []
        summary_lines.append("=" * 60)
        summary_lines.append("📈 宏观脉冲简报")
        summary_lines.append(f"📅 日期: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
        summary_lines.append("=" * 60)
        summary_lines.append("")
        summary_lines.append("📊 执行摘要:")
        summary_lines.append(f"   分析新闻总数: {analysis_result['total_news']} 条")
        summary_lines.append(f"   宏观影响新闻: {analysis_result['macro_news_count']} 条")
        summary_lines.append(f"   宏观强度指数: {analysis_result['macro_intensity']:.2f}/1.0")
        summary_lines.append(f"   整体基调: {assessment['overall_tone']}")
        summary_lines.append(f"   风险等级: {assessment['risk_level']}")
        summary_lines.append(f"   投资影响: {assessment['investment_implication']}")
        summary_lines.append("")
        
        if assessment["key_themes"]:
            summary_lines.append("🎯 关键主题:")
            for theme in assessment["key_themes"]:
                summary_lines.append(f"   • {theme}")
            summary_lines.append("")
        
        if analysis_result["key_news"]:
            summary_lines.append("📰 关键新闻摘要:")
            for i, news in enumerate(analysis_result["key_news"][:3], 1):
                title = news.get("title", "")[:60]
                if len(title) < len(news.get("title", "")):
                    title += "..."
                summary_lines.append(f"   {i}. [{news.get('category')}] {title}")
                summary_lines.append(f"      置信度: {news.get('confidence'):.2f}")
            summary_lines.append("")
        
        summary_lines.append("=" * 60)
        
        return "\n".join(summary_lines)
    
    def run(self, use_cached_news: bool = True) -> Dict:
        """运行宏观脉冲分发器"""
        logger.info("🚀 启动宏观脉冲分发器...")
        
        # 获取新闻数据
        if use_cached_news:
            news_items = self.load_today_news()
            if not news_items:
                logger.info("📰 缓存无数据，获取新鲜新闻...")
                news_items = self.fetch_fresh_news()
        else:
            news_items = self.fetch_fresh_news()
        
        if not news_items:
            logger.warning("⚠️  无新闻数据可用，生成空报告")
            # 生成空报告
            empty_analysis = {
                "total_news": 0,
                "macro_news_count": 0,
                "macro_intensity": 0.0,
                "category_distribution": {},
                "tag_distribution": {},
                "macro_assessment": {
                    "overall_tone": "平静",
                    "risk_level": "很低",
                    "investment_implication": "无明显宏观事件",
                    "key_themes": [],
                    "watch_items": []
                },
                "key_news": []
            }
            
            report_file = self.generate_pulse_report(empty_analysis)
            summary = self.generate_human_readable_summary(empty_analysis)
            
            return {
                "success": False,
                "message": "无新闻数据可用",
                "report_file": report_file,
                "summary": summary
            }
        
        # 分析宏观脉冲
        analysis_result = self.analyze_macro_pulse(news_items)
        
        # 生成报告
        report_file = self.generate_pulse_report(analysis_result)
        
        # 生成人类可读摘要
        summary = self.generate_human_readable_summary(analysis_result)
        
        logger.info("✅ 宏观脉冲分发器执行完成")
        
        return {
            "success": True,
            "total_news": analysis_result["total_news"],
            "macro_news_count": analysis_result["macro_news_count"],
            "macro_intensity": analysis_result["macro_intensity"],
            "report_file": report_file,
            "summary": summary
        }

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="宏观脉冲分发器")
    parser.add_argument("--fresh", action="store_true", help="获取新鲜新闻（不使用缓存）")
    parser.add_argument("--output-dir", type=str, help="输出目录路径")
    parser.add_argument("--quiet", action="store_true", help="静默模式，仅输出关键信息")
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    print("=" * 60)
    print("📈 宏观脉冲分发器")
    print("=" * 60)
    
    try:
        # 初始化分发器
        dispatcher = MacroPulseDispatcher(output_dir=args.output_dir)
        
        # 运行分发器
        result = dispatcher.run(use_cached_news=not args.fresh)
        
        # 输出结果
        if result["success"]:
            print(f"\n✅ 宏观脉冲分析完成!")
            print(f"   分析新闻: {result['total_news']} 条")
            print(f"   宏观新闻: {result['macro_news_count']} 条")
            print(f"   宏观强度: {result['macro_intensity']:.2f}/1.0")
            print(f"   报告文件: {result['report_file']}")
            
            print(f"\n{result['summary']}")
        else:
            print(f"\n⚠️  {result['message']}")
            print(f"   报告文件: {result.get('report_file', '无')}")
        
        print("\n" + "=" * 60)
        print("🎉 宏观脉冲分发器执行完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 宏观脉冲分发器执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()