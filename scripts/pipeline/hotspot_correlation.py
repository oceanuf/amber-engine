#!/usr/bin/env python3
"""
热点关联引擎 (Hotspot Correlation Engine)
版本: 1.0.0
描述: 建立宏观脉冲信号与行业/股票的语义映射矩阵，实现SOP第二阶段：情报驱动的标的自动化挖掘。
功能:
  1. 解析宏观脉冲报告，提取关键主题和标签
  2. 建立语义映射矩阵：宏观主题 → 行业分类 → 候选股票池
  3. 计算关联强度得分
  4. 输出候选股票列表
"""

import os
import sys
import json
import datetime
import logging
from typing import Dict, List, Any, Optional, Tuple
import re

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HotspotCorrelation:
    """热点关联引擎"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化热点关联引擎"""
        self.mapping_matrix = self._load_mapping_matrix()
        self.industry_stock_map = self._load_industry_stock_map()
        
        logger.info(f"热点关联引擎初始化完成，加载 {len(self.mapping_matrix)} 个主题映射")
    
    def _load_mapping_matrix(self) -> Dict[str, Dict]:
        """加载语义映射矩阵"""
        # 宏观主题到行业的映射
        mapping_matrix = {
            "货币政策": {
                "description": "央行货币政策调整相关",
                "industries": ["银行", "证券", "保险", "房地产"],
                "keywords": ["降准", "降息", "MLF", "LPR", "逆回购", "货币政策", "央行"],
                "weight": 0.8
            },
            "财政政策": {
                "description": "政府财政政策相关",
                "industries": ["基建", "建筑", "水泥", "钢铁", "环保"],
                "keywords": ["财政政策", "减税", "增税", "赤字", "国债", "地方债"],
                "weight": 0.7
            },
            "经济数据": {
                "description": "宏观经济数据发布",
                "industries": ["消费", "零售", "物流", "旅游"],
                "keywords": ["GDP", "CPI", "PPI", "PMI", "出口", "进口", "贸易顺差", "失业率"],
                "weight": 0.6
            },
            "产业政策": {
                "description": "产业扶持与发展政策",
                "industries": ["半导体", "芯片", "人工智能", "新能源", "5G", "云计算", "生物医药"],
                "keywords": ["AI", "人工智能", "新能源", "半导体", "芯片", "集成电路", "5G", "云计算", "生物医药"],
                "weight": 0.9
            },
            "地缘政治": {
                "description": "国际关系与地缘政治事件",
                "industries": ["国防军工", "黄金", "石油", "农业", "稀土"],
                "keywords": ["中美", "中欧", "贸易战", "制裁", "关税", "地缘风险", "冲突"],
                "weight": 0.8
            },
            "监管政策": {
                "description": "行业监管与整顿",
                "industries": ["互联网", "教育", "医疗", "金融科技"],
                "keywords": ["监管", "整顿", "规范", "指导意见", "新规"],
                "weight": 0.7
            },
            "市场情绪": {
                "description": "市场情绪与资金流向",
                "industries": ["券商", "传媒", "游戏", "白酒"],
                "keywords": ["牛市", "熊市", "反弹", "回调", "震荡", "波动"],
                "weight": 0.5
            }
        }
        
        return mapping_matrix
    
    def _load_industry_stock_map(self) -> Dict[str, List[str]]:
        """加载行业-股票映射"""
        # 这里应该从数据库或配置文件加载实际的行业-股票映射
        # 暂时使用示例数据
        industry_stock_map = {
            "银行": ["601398", "601939", "601288", "601988", "601328"],
            "证券": ["600030", "600999", "601688", "000776", "002736"],
            "保险": ["601318", "601628", "601336", "601601"],
            "房地产": ["000002", "600048", "600383", "000671"],
            "基建": ["601668", "601186", "601390", "601800"],
            "建筑": ["601117", "601618", "601669"],
            "水泥": ["600585", "000401", "600801", "000672"],
            "钢铁": ["600019", "000898", "600022", "000932"],
            "环保": ["300070", "002672", "300137", "600874"],
            "消费": ["600519", "000858", "000568", "600887"],
            "零售": ["601888", "002024", "600859", "000759"],
            "物流": ["002352", "600233", "002120", "603128"],
            "旅游": ["600054", "000888", "002059", "603199"],
            "半导体": ["603986", "600703", "002049", "300661"],
            "芯片": ["600584", "002185", "002371", "300604"],
            "人工智能": ["002230", "002415", "300033", "300229"],
            "新能源": ["002594", "300750", "002460", "600438"],
            "5G": ["000063", "002463", "600498", "300136"],
            "云计算": ["000977", "002368", "600588", "600845"],
            "生物医药": ["600276", "000538", "600196", "002007"],
            "国防军工": ["600760", "000768", "600893", "600685"],
            "黄金": ["600547", "600489", "002155", "600988"],
            "石油": ["601857", "600028", "600688", "000554"],
            "农业": ["600598", "000998", "002041", "600354"],
            "稀土": ["600111", "000831", "600392", "600259"],
            "互联网": ["00700", "BABA", "JD", "PDD"],  # 港股/美股代码
            "教育": ["600661", "002607", "300010", "300359"],
            "医疗": ["300003", "002223", "300015", "600763"],
            "金融科技": ["300033", "002657", "300339", "300465"],
            "券商": ["600030", "600999", "601688", "000776"],
            "传媒": ["600037", "000917", "002624", "300027"],
            "游戏": ["002624", "300113", "002555", "600880"],
            "白酒": ["600519", "000858", "000568", "600809"]
        }
        
        logger.info(f"加载行业-股票映射，覆盖 {len(industry_stock_map)} 个行业")
        return industry_stock_map
    
    def load_macro_pulse(self, pulse_file: Optional[str] = None) -> Dict:
        """加载宏观脉冲报告"""
        if not pulse_file:
            # 默认使用今日最新宏观脉冲报告
            pulse_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "reports", "macro", "macro_pulse_today.json"
            )
        
        if not os.path.exists(pulse_file):
            logger.warning(f"宏观脉冲报告不存在: {pulse_file}")
            return {
                "key_themes": [],
                "tag_distribution": {},
                "watch_items": [],
                "macro_intensity": 0.0
            }
        
        try:
            with open(pulse_file, 'r', encoding='utf-8') as f:
                pulse_data = json.load(f)
            
            # 提取关键信息
            key_themes = pulse_data.get("detailed_analysis", {}).get("key_themes", [])
            tag_distribution = pulse_data.get("detailed_analysis", {}).get("tag_distribution", {})
            watch_items = pulse_data.get("detailed_analysis", {}).get("watch_items", [])
            macro_intensity = pulse_data.get("executive_summary", {}).get("macro_intensity_index", 0.0)
            
            logger.info(f"✅ 加载宏观脉冲报告: {len(key_themes)} 个关键主题")
            
            return {
                "key_themes": key_themes,
                "tag_distribution": tag_distribution,
                "watch_items": watch_items,
                "macro_intensity": macro_intensity,
                "raw_data": pulse_data
            }
        except Exception as e:
            logger.error(f"❌ 加载宏观脉冲报告失败: {e}")
            return {
                "key_themes": [],
                "tag_distribution": {},
                "watch_items": [],
                "macro_intensity": 0.0
            }
    
    def correlate_themes_to_industries(self, macro_pulse: Dict) -> List[Dict]:
        """关联宏观主题到行业"""
        key_themes = macro_pulse.get("key_themes", [])
        tag_distribution = macro_pulse.get("tag_distribution", {})
        macro_intensity = macro_pulse.get("macro_intensity", 0.0)
        
        correlated_industries = []
        
        # 1. 基于关键主题的直接映射
        for theme in key_themes:
            if theme in self.mapping_matrix:
                mapping = self.mapping_matrix[theme]
                industries = mapping.get("industries", [])
                
                for industry in industries:
                    # 计算关联得分
                    base_score = mapping.get("weight", 0.5)
                    intensity_factor = macro_intensity  # 宏观强度因子
                    
                    # 标签分布因子（如果该主题在标签中有分布）
                    tag_factor = tag_distribution.get(theme, 0) / 10.0 if tag_distribution.get(theme, 0) > 0 else 0.5
                    
                    correlation_score = base_score * 0.4 + intensity_factor * 0.3 + tag_factor * 0.3
                    
                    correlated_industries.append({
                        "theme": theme,
                        "industry": industry,
                        "description": mapping.get("description", ""),
                        "correlation_score": correlation_score,
                        "factors": {
                            "base_score": base_score,
                            "intensity_factor": intensity_factor,
                            "tag_factor": tag_factor
                        }
                    })
        
        # 2. 基于标签分布的补充映射
        for tag, count in tag_distribution.items():
            # 寻找与标签相关的主题
            for theme, mapping in self.mapping_matrix.items():
                keywords = mapping.get("keywords", [])
                if any(keyword in tag for keyword in keywords) and theme not in key_themes:
                    industries = mapping.get("industries", [])
                    
                    for industry in industries:
                        tag_weight = min(count / 5.0, 1.0)  # 归一化标签权重
                        correlation_score = mapping.get("weight", 0.5) * 0.6 + tag_weight * 0.4
                        
                        correlated_industries.append({
                            "theme": f"{tag}（标签衍生）",
                            "industry": industry,
                            "description": f"从标签'{tag}'衍生",
                            "correlation_score": correlation_score,
                            "factors": {
                                "base_score": mapping.get("weight", 0.5),
                                "tag_weight": tag_weight
                            }
                        })
        
        # 去重并排序
        seen = set()
        unique_industries = []
        for item in correlated_industries:
            key = (item["theme"], item["industry"])
            if key not in seen:
                seen.add(key)
                unique_industries.append(item)
        
        # 按关联得分排序
        unique_industries.sort(key=lambda x: x["correlation_score"], reverse=True)
        
        logger.info(f"🔗 关联完成: {len(unique_industries)} 个行业关联")
        return unique_industries
    
    def generate_stock_candidates(self, correlated_industries: List[Dict], 
                                 max_stocks_per_industry: int = 3) -> List[Dict]:
        """生成候选股票列表"""
        stock_candidates = []
        
        for industry_item in correlated_industries:
            industry = industry_item["industry"]
            correlation_score = industry_item["correlation_score"]
            
            if industry in self.industry_stock_map:
                stocks = self.industry_stock_map[industry][:max_stocks_per_industry]
                
                for stock_code in stocks:
                    # 计算股票得分（基于行业关联得分）
                    stock_score = correlation_score * 0.8  # 行业得分权重
                    
                    # 可以在这里添加股票特异性因子（如市值、流动性、基本面等）
                    # 暂时使用简化模型
                    
                    stock_candidates.append({
                        "stock_code": stock_code,
                        "stock_name": f"股票{stock_code}",  # 应该从数据库获取实际名称
                        "industry": industry,
                        "theme": industry_item["theme"],
                        "correlation_score": correlation_score,
                        "stock_score": stock_score,
                        "selection_reason": f"受{industry_item['theme']}主题影响，属于{industry}行业"
                    })
        
        # 按股票得分排序
        stock_candidates.sort(key=lambda x: x["stock_score"], reverse=True)
        
        logger.info(f"📊 生成 {len(stock_candidates)} 个候选股票")
        return stock_candidates
    
    def filter_candidates(self, stock_candidates: List[Dict], 
                         min_score: float = 0.3,
                         max_candidates: int = 20) -> List[Dict]:
        """过滤候选股票"""
        filtered = []
        
        for candidate in stock_candidates:
            if candidate["stock_score"] >= min_score:
                filtered.append(candidate)
        
        # 限制数量
        filtered = filtered[:max_candidates]
        
        logger.info(f"🎯 过滤后剩余 {len(filtered)} 个候选股票 (阈值: {min_score})")
        return filtered
    
    def generate_correlation_report(self, macro_pulse: Dict, 
                                   correlated_industries: List[Dict],
                                   stock_candidates: List[Dict]) -> Dict:
        """生成关联分析报告"""
        report = {
            "metadata": {
                "report_type": "热点关联分析报告",
                "generated_by": "HotspotCorrelation",
                "version": "1.0.0",
                "generation_time": datetime.datetime.now().isoformat(),
                "macro_pulse_source": "macro_pulse_today.json"
            },
            "macro_pulse_summary": {
                "key_themes": macro_pulse.get("key_themes", []),
                "tag_distribution": macro_pulse.get("tag_distribution", {}),
                "macro_intensity": macro_pulse.get("macro_intensity", 0.0),
                "watch_items_count": len(macro_pulse.get("watch_items", []))
            },
            "industry_correlation": {
                "total_industries": len(correlated_industries),
                "top_industries": correlated_industries[:5],
                "all_industries": correlated_industries
            },
            "stock_candidates": {
                "total_candidates": len(stock_candidates),
                "top_candidates": stock_candidates[:10],
                "all_candidates": stock_candidates
            },
            "analysis_parameters": {
                "mapping_matrix_size": len(self.mapping_matrix),
                "industry_stock_map_size": len(self.industry_stock_map),
                "filtering_threshold": 0.3,
                "max_candidates_per_industry": 3
            }
        }
        
        return report
    
    def save_report(self, report: Dict, output_dir: Optional[str] = None) -> str:
        """保存报告"""
        if not output_dir:
            output_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "reports", "hotspot"
            )
        
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"hotspot_correlation_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 热点关联报告已保存: {filepath}")
            
            # 同时保存今日最新文件
            today_file = os.path.join(output_dir, "hotspot_correlation_today.json")
            with open(today_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 今日热点关联报告已更新: {today_file}")
            
            return filepath
        except Exception as e:
            logger.error(f"❌ 保存报告失败: {e}")
            return ""
    
    def run(self, pulse_file: Optional[str] = None) -> Dict:
        """运行热点关联引擎"""
        logger.info("🚀 启动热点关联引擎...")
        
        # 1. 加载宏观脉冲
        macro_pulse = self.load_macro_pulse(pulse_file)
        
        if not macro_pulse.get("key_themes") and macro_pulse.get("macro_intensity", 0) < 0.1:
            logger.warning("⚠️  宏观脉冲信号较弱或无关键主题，跳过热点关联")
            return {"success": False, "message": "宏观脉冲信号不足"}
        
        # 2. 关联主题到行业
        correlated_industries = self.correlate_themes_to_industries(macro_pulse)
        
        if not correlated_industries:
            logger.warning("⚠️  未找到行业关联")
            return {"success": False, "message": "无行业关联结果"}
        
        # 3. 生成候选股票
        stock_candidates = self.generate_stock_candidates(correlated_industries)
        
        if not stock_candidates:
            logger.warning("⚠️  未生成候选股票")
            return {"success": False, "message": "无候选股票"}
        
        # 4. 过滤候选股票
        filtered_candidates = self.filter_candidates(stock_candidates)
        
        # 5. 生成报告
        report = self.generate_correlation_report(macro_pulse, correlated_industries, filtered_candidates)
        
        # 6. 保存报告
        report_file = self.save_report(report)
        
        logger.info("✅ 热点关联引擎执行完成")
        
        return {
            "success": True,
            "macro_themes_count": len(macro_pulse.get("key_themes", [])),
            "industries_count": len(correlated_industries),
            "candidates_count": len(filtered_candidates),
            "report_file": report_file,
            "top_candidates": filtered_candidates[:5]
        }

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="热点关联引擎")
    parser.add_argument("--pulse-file", type=str, help="宏观脉冲报告文件路径")
    parser.add_argument("--output-dir", type=str, help="输出目录路径")
    parser.add_argument("--quiet", action="store_true", help="静默模式")
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    print("=" * 60)
    print("🔗 热点关联引擎 - SOP第二阶段")
    print("=" * 60)
    
    try:
        # 初始化引擎
        engine = HotspotCorrelation()
        
        # 运行引擎
        result = engine.run(args.pulse_file)
        
        # 输出结果
        if result["success"]:
            print(f"\n✅ 热点关联分析完成!")
            print(f"   宏观主题: {result['macro_themes_count']} 个")
            print(f"   关联行业: {result['industries_count']} 个")
            print(f"   候选股票: {result['candidates_count']} 个")
            print(f"   报告文件: {result['report_file']}")
            
            if result.get("top_candidates"):
                print(f"\n🎯 前5名候选股票:")
                for i, candidate in enumerate(result["top_candidates"], 1):
                    print(f"   {i}. {candidate['stock_code']} - {candidate['industry']}")
                    print(f"      主题: {candidate['theme']}")
                    print(f"      得分: {candidate['stock_score']:.3f}")
                    print(f"      理由: {candidate['selection_reason']}")
        else:
            print(f"\n⚠️  {result['message']}")
        
        print("\n" + "=" * 60)
        print("🎉 热点关联引擎执行完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 热点关联引擎执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()