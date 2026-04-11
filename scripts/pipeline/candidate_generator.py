#!/usr/bin/env python3
"""
候选生成器 (Candidate Generator)
版本: 1.0.0
描述: 基于热点关联结果，对候选股票进行进一步筛选和评估，生成最终候选列表。
功能:
  1. 加载热点关联报告
  2. 对候选股票进行多维度评估（简化版）
  3. 生成最终候选列表
  4. 输出候选画像报告
"""

import os
import sys
import json
import datetime
import logging
from typing import Dict, List, Any, Optional, Tuple
import random  # 暂时使用随机数据，后续应接入真实数据源

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CandidateGenerator:
    """候选生成器"""
    
    def __init__(self, tushare_token: Optional[str] = None):
        """初始化候选生成器"""
        self.tushare_token = tushare_token or self._load_tushare_token()
        
        # 评估权重配置
        self.evaluation_weights = {
            "macro_correlation": 0.3,   # 宏观关联度
            "industry_trend": 0.2,      # 行业趋势
            "fundamental_score": 0.25,  # 基本面得分
            "technical_score": 0.15,    # 技术面得分
            "liquidity_score": 0.1      # 流动性得分
        }
        
        logger.info("候选生成器初始化完成")
    
    def _load_tushare_token(self) -> Optional[str]:
        """加载Tushare Token"""
        secrets_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "_PRIVATE_DATA", "secrets.json"
        )
        
        try:
            if os.path.exists(secrets_file):
                with open(secrets_file, 'r', encoding='utf-8') as f:
                    secrets = json.load(f)
                    token = secrets.get("TUSHARE_TOKEN")
                    if token and token != "your_tushare_token_here":
                        logger.info("✅ 从secrets.json加载Tushare Token")
                        return token
            
            # 尝试环境变量
            token = os.getenv("TUSHARE_TOKEN")
            if token:
                logger.info("✅ 从环境变量加载Tushare Token")
                return token
            
            logger.warning("⚠️  未找到Tushare Token，将使用模拟数据")
            return None
        except Exception as e:
            logger.error(f"❌ 加载Tushare Token失败: {e}")
            return None
    
    def load_hotspot_report(self, hotspot_file: Optional[str] = None) -> Dict:
        """加载热点关联报告"""
        if not hotspot_file:
            # 默认使用今日最新热点关联报告
            hotspot_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "reports", "hotspot", "hotspot_correlation_today.json"
            )
        
        if not os.path.exists(hotspot_file):
            logger.warning(f"热点关联报告不存在: {hotspot_file}")
            # 返回空报告用于测试
            return {
                "stock_candidates": {
                    "all_candidates": []
                }
            }
        
        try:
            with open(hotspot_file, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
            
            stock_candidates = report_data.get("stock_candidates", {}).get("all_candidates", [])
            logger.info(f"✅ 加载热点关联报告: {len(stock_candidates)} 个候选股票")
            
            return {
                "stock_candidates": stock_candidates,
                "raw_data": report_data
            }
        except Exception as e:
            logger.error(f"❌ 加载热点关联报告失败: {e}")
            return {
                "stock_candidates": []
            }
    
    def evaluate_candidate(self, candidate: Dict) -> Dict:
        """评估单个候选股票"""
        stock_code = candidate.get("stock_code", "")
        industry = candidate.get("industry", "")
        correlation_score = candidate.get("correlation_score", 0.0)
        
        # 1. 宏观关联度得分（来自热点关联）
        macro_correlation_score = correlation_score
        
        # 2. 行业趋势得分（模拟数据）
        # 这里应该调用行业分析API，暂时使用随机数据
        industry_trend_score = random.uniform(0.4, 0.9)
        
        # 3. 基本面得分（模拟数据）
        # 这里应该调用基本面分析API（PE、PB、ROE等）
        fundamental_score = self._simulate_fundamental_score(stock_code)
        
        # 4. 技术面得分（模拟数据）
        # 这里应该调用技术分析API（均线、RSI、MACD等）
        technical_score = self._simulate_technical_score(stock_code)
        
        # 5. 流动性得分（模拟数据）
        # 这里应该调用流动性指标（成交量、换手率等）
        liquidity_score = self._simulate_liquidity_score(stock_code)
        
        # 计算综合得分
        weighted_score = (
            macro_correlation_score * self.evaluation_weights["macro_correlation"] +
            industry_trend_score * self.evaluation_weights["industry_trend"] +
            fundamental_score * self.evaluation_weights["fundamental_score"] +
            technical_score * self.evaluation_weights["technical_score"] +
            liquidity_score * self.evaluation_weights["liquidity_score"]
        )
        
        # 生成评估报告
        evaluation_report = {
            "stock_code": stock_code,
            "stock_name": candidate.get("stock_name", f"股票{stock_code}"),
            "industry": industry,
            "theme": candidate.get("theme", ""),
            "macro_correlation": {
                "score": macro_correlation_score,
                "reason": candidate.get("selection_reason", "")
            },
            "industry_trend": {
                "score": industry_trend_score,
                "reason": f"{industry}行业趋势评估"
            },
            "fundamental": {
                "score": fundamental_score,
                "reason": self._get_fundamental_reason(fundamental_score)
            },
            "technical": {
                "score": technical_score,
                "reason": self._get_technical_reason(technical_score)
            },
            "liquidity": {
                "score": liquidity_score,
                "reason": self._get_liquidity_reason(liquidity_score)
            },
            "weighted_score": weighted_score,
            "evaluation_time": datetime.datetime.now().isoformat()
        }
        
        return evaluation_report
    
    def _simulate_fundamental_score(self, stock_code: str) -> float:
        """模拟基本面得分（后续应接入真实API）"""
        # 根据股票代码生成确定性但随机的得分
        random.seed(hash(stock_code) % 1000)
        return random.uniform(0.3, 0.95)
    
    def _simulate_technical_score(self, stock_code: str) -> float:
        """模拟技术面得分（后续应接入真实API）"""
        random.seed(hash(stock_code) % 1000 + 1000)
        return random.uniform(0.2, 0.9)
    
    def _simulate_liquidity_score(self, stock_code: str) -> float:
        """模拟流动性得分（后续应接入真实API）"""
        random.seed(hash(stock_code) % 1000 + 2000)
        return random.uniform(0.4, 0.98)
    
    def _get_fundamental_reason(self, score: float) -> str:
        """获取基本面评估理由"""
        if score >= 0.8:
            return "基本面优秀，估值合理"
        elif score >= 0.6:
            return "基本面良好，有一定投资价值"
        elif score >= 0.4:
            return "基本面一般，需谨慎评估"
        else:
            return "基本面较弱，风险较高"
    
    def _get_technical_reason(self, score: float) -> str:
        """获取技术面评估理由"""
        if score >= 0.8:
            return "技术形态良好，处于上升趋势"
        elif score >= 0.6:
            return "技术形态中性，震荡整理"
        elif score >= 0.4:
            return "技术形态偏弱，需观察"
        else:
            return "技术形态较差，下跌趋势"
    
    def _get_liquidity_reason(self, score: float) -> str:
        """获取流动性评估理由"""
        if score >= 0.8:
            return "流动性充沛，成交活跃"
        elif score >= 0.6:
            return "流动性良好，成交正常"
        elif score >= 0.4:
            return "流动性一般，成交偏淡"
        else:
            return "流动性较差，成交稀疏"
    
    def evaluate_all_candidates(self, hotspot_report: Dict, 
                               max_candidates: int = 30) -> List[Dict]:
        """评估所有候选股票"""
        candidates = hotspot_report.get("stock_candidates", [])
        
        if not candidates:
            logger.warning("⚠️  无候选股票需要评估")
            return []
        
        # 限制评估数量
        candidates = candidates[:max_candidates]
        
        evaluated_candidates = []
        for candidate in candidates:
            evaluation = self.evaluate_candidate(candidate)
            evaluated_candidates.append(evaluation)
        
        # 按综合得分排序
        evaluated_candidates.sort(key=lambda x: x["weighted_score"], reverse=True)
        
        logger.info(f"📊 评估完成: {len(evaluated_candidates)} 个候选股票")
        return evaluated_candidates
    
    def filter_candidates(self, evaluated_candidates: List[Dict],
                         min_score: float = 0.5,
                         max_candidates: int = 15) -> List[Dict]:
        """过滤评估后的候选股票"""
        filtered = []
        
        for candidate in evaluated_candidates:
            if candidate["weighted_score"] >= min_score:
                filtered.append(candidate)
        
        # 限制数量
        filtered = filtered[:max_candidates]
        
        logger.info(f"🎯 过滤后剩余 {len(filtered)} 个候选股票 (阈值: {min_score})")
        return filtered
    
    def generate_candidate_profiles(self, filtered_candidates: List[Dict]) -> List[Dict]:
        """生成候选股票画像"""
        profiles = []
        
        for candidate in filtered_candidates:
            # 计算各项得分的等级
            profile = {
                "stock_code": candidate["stock_code"],
                "stock_name": candidate["stock_name"],
                "industry": candidate["industry"],
                "theme": candidate["theme"],
                "overall_score": candidate["weighted_score"],
                "score_breakdown": {
                    "macro_correlation": candidate["macro_correlation"]["score"],
                    "industry_trend": candidate["industry_trend"]["score"],
                    "fundamental": candidate["fundamental"]["score"],
                    "technical": candidate["technical"]["score"],
                    "liquidity": candidate["liquidity"]["score"]
                },
                "assessment_summary": self._generate_assessment_summary(candidate),
                "investment_suggestion": self._generate_investment_suggestion(candidate),
                "risk_level": self._determine_risk_level(candidate),
                "priority": len(profiles) + 1,  # 基于排序的优先级
                "profile_time": datetime.datetime.now().isoformat()
            }
            
            profiles.append(profile)
        
        return profiles
    
    def _generate_assessment_summary(self, candidate: Dict) -> str:
        """生成评估摘要"""
        scores = [
            f"宏观关联度: {candidate['macro_correlation']['score']:.2f}",
            f"行业趋势: {candidate['industry_trend']['score']:.2f}",
            f"基本面: {candidate['fundamental']['score']:.2f}",
            f"技术面: {candidate['technical']['score']:.2f}",
            f"流动性: {candidate['liquidity']['score']:.2f}"
        ]
        
        return f"综合得分: {candidate['weighted_score']:.3f} (" + ", ".join(scores) + ")"
    
    def _generate_investment_suggestion(self, candidate: Dict) -> str:
        """生成投资建议"""
        score = candidate["weighted_score"]
        
        if score >= 0.7:
            return "建议重点关注，具备较好的投资价值"
        elif score >= 0.6:
            return "建议观察，具备一定的投资潜力"
        elif score >= 0.5:
            return "建议谨慎关注，需要进一步分析"
        else:
            return "建议暂不关注，风险收益比较低"
    
    def _determine_risk_level(self, candidate: Dict) -> str:
        """确定风险等级"""
        score = candidate["weighted_score"]
        
        if score >= 0.7:
            return "低风险"
        elif score >= 0.6:
            return "中低风险"
        elif score >= 0.5:
            return "中等风险"
        elif score >= 0.4:
            return "中高风险"
        else:
            return "高风险"
    
    def generate_final_report(self, hotspot_report: Dict,
                             evaluated_candidates: List[Dict],
                             filtered_candidates: List[Dict],
                             candidate_profiles: List[Dict]) -> Dict:
        """生成最终报告"""
        report = {
            "metadata": {
                "report_type": "候选股票生成报告",
                "generated_by": "CandidateGenerator",
                "version": "1.0.0",
                "generation_time": datetime.datetime.now().isoformat(),
                "hotspot_source": "hotspot_correlation_today.json"
            },
            "executive_summary": {
                "total_candidates_evaluated": len(evaluated_candidates),
                "candidates_after_filtering": len(filtered_candidates),
                "top_candidate_score": filtered_candidates[0]["weighted_score"] if filtered_candidates else 0,
                "average_score": sum(c["weighted_score"] for c in filtered_candidates) / len(filtered_candidates) if filtered_candidates else 0,
                "risk_distribution": {
                    "low_risk": sum(1 for c in candidate_profiles if c["risk_level"] == "低风险"),
                    "medium_low_risk": sum(1 for c in candidate_profiles if c["risk_level"] == "中低风险"),
                    "medium_risk": sum(1 for c in candidate_profiles if c["risk_level"] == "中等风险"),
                    "medium_high_risk": sum(1 for c in candidate_profiles if c["risk_level"] == "中高风险"),
                    "high_risk": sum(1 for c in candidate_profiles if c["risk_level"] == "高风险")
                }
            },
            "candidate_evaluation": {
                "evaluation_weights": self.evaluation_weights,
                "filtering_threshold": 0.5,
                "max_candidates": 15
            },
            "candidate_profiles": candidate_profiles,
            "detailed_evaluations": filtered_candidates[:10],  # 只保留前10个详细评估
            "analysis_notes": [
                "注：当前版本使用模拟数据，后续需接入真实基本面、技术面、流动性数据",
                "评估权重可基于历史表现进行动态优化",
                "建议结合人工审核进行最终投资决策"
            ]
        }
        
        return report
    
    def save_report(self, report: Dict, output_dir: Optional[str] = None) -> str:
        """保存报告"""
        if not output_dir:
            output_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "reports", "candidates"
            )
        
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"candidate_generation_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 候选生成报告已保存: {filepath}")
            
            # 同时保存今日最新文件
            today_file = os.path.join(output_dir, "candidate_generation_today.json")
            with open(today_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 今日候选生成报告已更新: {today_file}")
            
            return filepath
        except Exception as e:
            logger.error(f"❌ 保存报告失败: {e}")
            return ""
    
    def run(self, hotspot_file: Optional[str] = None) -> Dict:
        """运行候选生成器"""
        logger.info("🚀 启动候选生成器...")
        
        # 1. 加载热点关联报告
        hotspot_report = self.load_hotspot_report(hotspot_file)
        
        candidates = hotspot_report.get("stock_candidates", [])
        if not candidates:
            logger.warning("⚠️  热点关联报告无候选股票，生成空报告")
            # 生成空报告
            empty_report = {
                "metadata": {
                    "report_type": "候选股票生成报告",
                    "generated_by": "CandidateGenerator",
                    "version": "1.0.0",
                    "generation_time": datetime.datetime.now().isoformat(),
                    "note": "热点关联报告无候选股票"
                },
                "executive_summary": {
                    "total_candidates_evaluated": 0,
                    "candidates_after_filtering": 0,
                    "top_candidate_score": 0,
                    "average_score": 0
                },
                "candidate_profiles": []
            }
            
            report_file = self.save_report(empty_report)
            return {
                "success": False,
                "message": "热点关联报告无候选股票",
                "report_file": report_file
            }
        
        # 2. 评估所有候选股票
        evaluated_candidates = self.evaluate_all_candidates(hotspot_report)
        
        if not evaluated_candidates:
            logger.warning("⚠️  候选股票评估失败")
            return {"success": False, "message": "候选股票评估失败"}
        
        # 3. 过滤候选股票
        filtered_candidates = self.filter_candidates(evaluated_candidates)
        
        if not filtered_candidates:
            logger.warning("⚠️  无候选股票通过过滤")
            return {"success": False, "message": "无候选股票通过过滤"}
        
        # 4. 生成候选画像
        candidate_profiles = self.generate_candidate_profiles(filtered_candidates)
        
        # 5. 生成最终报告
        report = self.generate_final_report(hotspot_report, evaluated_candidates, 
                                           filtered_candidates, candidate_profiles)
        
        # 6. 保存报告
        report_file = self.save_report(report)
        
        logger.info("✅ 候选生成器执行完成")
        
        return {
            "success": True,
            "total_evaluated": len(evaluated_candidates),
            "filtered_count": len(filtered_candidates),
            "top_score": filtered_candidates[0]["weighted_score"] if filtered_candidates else 0,
            "report_file": report_file,
            "top_candidates": candidate_profiles[:3]
        }

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="候选生成器")
    parser.add_argument("--hotspot-file", type=str, help="热点关联报告文件路径")
    parser.add_argument("--output-dir", type=str, help="输出目录路径")
    parser.add_argument("--quiet", action="store_true", help="静默模式")
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    print("=" * 60)
    print("🎯 候选生成器 - 标的画像初筛")
    print("=" * 60)
    
    try:
        # 初始化生成器
        generator = CandidateGenerator()
        
        # 运行生成器
        result = generator.run(args.hotspot_file)
        
        # 输出结果
        if result["success"]:
            print(f"\n✅ 候选生成完成!")
            print(f"   评估股票: {result['total_evaluated']} 个")
            print(f"   通过过滤: {result['filtered_count']} 个")
            print(f"   最高得分: {result['top_score']:.3f}")
            print(f"   报告文件: {result['report_file']}")
            
            if result.get("top_candidates"):
                print(f"\n🏆 前3名候选股票:")
                for i, candidate in enumerate(result["top_candidates"], 1):
                    print(f"   {i}. {candidate['stock_code']} - {candidate['stock_name']}")
                    print(f"      行业: {candidate['industry']}")
                    print(f"      主题: {candidate['theme']}")
                    print(f"      综合得分: {candidate['overall_score']:.3f}")
                    print(f"      风险等级: {candidate['risk_level']}")
                    print(f"      投资建议: {candidate['investment_suggestion']}")
        else:
            print(f"\n⚠️  {result['message']}")
            print(f"   报告文件: {result.get('report_file', '无')}")
        
        print("\n" + "=" * 60)
        print("🎉 候选生成器执行完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 候选生成器执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()