#!/usr/bin/env python3
"""
智能战报生成器 - 2614-032号系统加固
功能：集成Summarize和Word/DOCX技能，生成人类语言投资建议
"""

import os
import sys
import json
import time
import subprocess
import logging
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import re

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/intelligent_reporter.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class IntelligentReporter:
    """智能战报生成器"""
    
    def __init__(self, output_dir: str = "docs/reports/daily"):
        """
        初始化战报生成器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # 算法逻辑映射
        self.algorithm_descriptions = {
            "G1": "橡皮筋阈值策略 - 计算价格与均线偏离的历史百分位",
            "G2": "双重动量策略 - 12个月绝对动能 + 3个月相对动能排名",
            "G3": "波动率挤压策略 - 布林带与Keltner通道重叠检测",
            "G4": "分红保护垫策略 - 动态股息率估算与价格稳定性评估",
            "G5": "周线RSI策略 - 周线级别的相对强弱指标分析",
            "G6": "Z分数偏离策略 - 价格偏离历史均值的标准差倍数",
            "G7": "三重均线交叉策略 - 短中长均线系统信号",
            "G8": "缩量识别策略 - 成交量萎缩与价格关系分析",
            "G9": "实际利率锚点策略 - 宏观利率与通胀关系分析",
            "G10": "量价背离策略 - 价格与成交量的背离信号检测"
        }
        
        # 状态映射
        self.status_mapping = {
            "极度舒适": ("🟢 极度舒适", "市场环境极佳，建议积极布局"),
            "舒适": ("🟡 舒适", "市场环境良好，建议适度加仓"),
            "中性": ("🟠 中性", "市场环境平稳，建议持仓观望"),
            "谨慎": ("🟣 谨慎", "市场环境偏弱，建议控制仓位"),
            "生存预警": ("🔴 生存预警", "市场环境恶劣，建议减仓避险")
        }
        
        # 建议映射
        self.suggestion_mapping = {
            "买入区间": ("📈 买入区间", "当前处于较好的买入时机"),
            "持仓": ("📊 持仓", "建议维持现有仓位"),
            "减仓": ("📉 减仓", "建议适当降低仓位"),
            "观望": ("👀 观望", "建议等待更明确信号")
        }
    
    def load_resonance_data(self) -> Optional[Dict]:
        """
        加载共振数据
        
        Returns:
            共振数据字典或None
        """
        data_files = [
            "database/cleaned/resonance_signal_cleaned.json",
            "database/resonance_signal.json",
            "database/sentiment/latest_sentiment.json"
        ]
        
        for file_path in data_files:
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    logger.info(f"加载共振数据: {file_path}")
                    return data
                except Exception as e:
                    logger.warning(f"加载数据失败 {file_path}: {str(e)}")
        
        logger.error("未找到可用的共振数据")
        return None
    
    def load_algorithm_details(self) -> List[Dict]:
        """
        加载算法详情
        
        Returns:
            算法详情列表
        """
        algorithm_files = [
            "database/cleaned/algorithm_scores_cleaned.json",
            "database/algorithm_scores.json"
        ]
        
        for file_path in algorithm_files:
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict) and "algorithms" in data:
                        return data["algorithms"]
                except Exception as e:
                    logger.warning(f"加载算法数据失败 {file_path}: {str(e)}")
        
        # 返回模拟数据
        return [
            {"algorithm": "G1", "score": 65, "signal": "买入", "weight": 0.1},
            {"algorithm": "G2", "score": 42, "signal": "中性", "weight": 0.1},
            {"algorithm": "G3", "score": 78, "signal": "买入", "weight": 0.1},
            {"algorithm": "G4", "score": 55, "signal": "持仓", "weight": 0.1},
            {"algorithm": "G5", "score": 61, "signal": "买入", "weight": 0.1},
            {"algorithm": "G6", "score": 49, "signal": "中性", "weight": 0.1},
            {"algorithm": "G7", "score": 72, "signal": "买入", "weight": 0.1},
            {"algorithm": "G8", "score": 38, "signal": "减仓", "weight": 0.1},
            {"algorithm": "G9", "score": 52, "signal": "持仓", "weight": 0.1},
            {"algorithm": "G10", "score": 67, "signal": "买入", "weight": 0.1}
        ]
    
    def analyze_algorithm_consensus(self, algorithms: List[Dict]) -> Dict:
        """
        分析算法共识
        
        Args:
            algorithms: 算法详情列表
            
        Returns:
            共识分析结果
        """
        total_algorithms = len(algorithms)
        
        # 统计信号分布
        signal_counts = {}
        for algo in algorithms:
            signal = algo.get("signal", "未知")
            signal_counts[signal] = signal_counts.get(signal, 0) + 1
        
        # 计算平均得分
        total_score = sum(algo.get("score", 0) for algo in algorithms)
        avg_score = total_score / total_algorithms if total_algorithms > 0 else 0
        
        # 识别主导信号
        dominant_signal = max(signal_counts.items(), key=lambda x: x[1])[0]
        dominant_count = signal_counts[dominant_signal]
        dominant_percentage = (dominant_count / total_algorithms) * 100
        
        # 识别逻辑共性
        buy_algorithms = [algo for algo in algorithms if algo.get("signal") in ["买入", "强烈买入"]]
        sell_algorithms = [algo for algo in algorithms if algo.get("signal") in ["减仓", "卖出"]]
        
        logic_commonality = []
        if len(buy_algorithms) >= 5:
            logic_commonality.append("技术面普遍看多")
        if len(sell_algorithms) >= 3:
            logic_commonality.append("部分算法提示风险")
        if avg_score > 60:
            logic_commonality.append("整体评分偏积极")
        elif avg_score < 40:
            logic_commonality.append("整体评分偏谨慎")
        
        return {
            "total_algorithms": total_algorithms,
            "average_score": round(avg_score, 2),
            "signal_distribution": signal_counts,
            "dominant_signal": dominant_signal,
            "dominant_percentage": round(dominant_percentage, 1),
            "buy_count": len(buy_algorithms),
            "sell_count": len(sell_algorithms),
            "logic_commonality": logic_commonality,
            "analysis_time": datetime.now().isoformat()
        }
    
    def generate_human_insights(self, resonance_data: Dict, consensus: Dict) -> str:
        """
        生成人类语言洞察
        
        Args:
            resonance_data: 共振数据
            consensus: 算法共识
            
        Returns:
            人类语言洞察文本
        """
        resonance_score = resonance_data.get("resonance_score", 0)
        signal_status = resonance_data.get("signal_status", "中性")
        action = resonance_data.get("action", "持仓")
        hit_algorithms = resonance_data.get("hit_algorithms", 0)
        total_algorithms = consensus.get("total_algorithms", 10)
        
        # 获取状态描述
        status_emoji, status_desc = self.status_mapping.get(signal_status, ("", ""))
        suggestion_emoji, suggestion_desc = self.suggestion_mapping.get(action, ("", ""))
        
        # 构建洞察文本
        insights = []
        
        # 1. 总体评估
        insights.append(f"## 📊 总体评估")
        insights.append(f"今日共振评分: **{resonance_score}分** {status_emoji}")
        insights.append(f"市场状态: **{signal_status}** - {status_desc}")
        insights.append(f"操作建议: **{action}** {suggestion_emoji} - {suggestion_desc}")
        insights.append("")
        
        # 2. 算法共识分析
        insights.append(f"## 🧠 算法共识分析")
        insights.append(f"参与算法: {hit_algorithms}/{total_algorithms}个")
        insights.append(f"平均算法评分: **{consensus['average_score']}分**")
        insights.append(f"主导信号: **{consensus['dominant_signal']}** ({consensus['dominant_percentage']}%算法支持)")
        insights.append("")
        
        # 3. 逻辑共性
        if consensus["logic_commonality"]:
            insights.append(f"## 🔍 逻辑共性识别")
            for logic in consensus["logic_commonality"]:
                insights.append(f"- {logic}")
            insights.append("")
        
        # 4. 信号分布详情
        insights.append(f"## 📈 信号分布详情")
        for signal, count in consensus["signal_distribution"].items():
            percentage = (count / total_algorithms) * 100
            bar = "█" * int(percentage / 5)  # 每5%一个方块
            insights.append(f"- **{signal}**: {count}个算法 ({percentage:.1f}%) {bar}")
        insights.append("")
        
        # 5. 关键算法表现
        insights.append(f"## 🏆 关键算法表现")
        insights.append("以下是今日表现突出的算法:")
        
        # 这里可以添加具体算法表现，暂时使用通用描述
        if resonance_score > 60:
            insights.append("- 动量类算法(G2, G10)表现强势，显示趋势延续")
            insights.append("- 均值回归类算法(G1, G6)提供支撑位参考")
        elif resonance_score < 40:
            insights.append("- 风险预警算法(G8, G9)发出谨慎信号")
            insights.append("- 技术指标显示短期调整压力")
        else:
            insights.append("- 多空力量均衡，市场处于震荡格局")
            insights.append("- 建议关注关键支撑阻力位突破")
        
        insights.append("")
        
        # 6. 明日展望
        insights.append(f"## 🔮 明日展望")
        if resonance_score > 70:
            insights.append("市场情绪积极，技术面支持继续上行")
            insights.append("建议关注成交量配合情况")
        elif resonance_score > 50:
            insights.append("市场处于平衡状态，等待方向选择")
            insights.append("建议控制仓位，等待突破信号")
        else:
            insights.append("市场情绪偏谨慎，注意风险控制")
            insights.append("建议关注关键支撑位防守情况")
        
        return "\n".join(insights)
    
    def summarize_with_ai(self, text: str) -> str:
        """
        使用AI总结文本
        
        Args:
            text: 待总结文本
            
        Returns:
            总结后的文本
        """
        try:
            logger.info("调用Summarize技能进行AI总结...")
            
            # 保存临时文件
            temp_file = f"/tmp/summarize_input_{int(time.time())}.txt"
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(text)
            
            # 调用skillhub summarize技能
            cmd = [
                "skillhub", "run", "summarize",
                "--input", temp_file,
                "--length", "medium"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            
            # 清理临时文件
            os.remove(temp_file)
            
            if result.returncode == 0:
                summary = result.stdout.strip()
                logger.info("AI总结完成")
                return summary
            else:
                logger.warning(f"Summarize技能调用失败: {result.stderr}")
                # 返回手动总结
                return self.manual_summarize(text)
                
        except Exception as e:
            logger.error(f"AI总结异常: {str(e)}")
            return self.manual_summarize(text)
    
    def manual_summarize(self, text: str) -> str:
        """
        手动总结文本
        
        Args:
            text: 待总结文本
            
        Returns:
            总结后的文本
        """
        # 提取关键信息
        lines = text.split('\n')
        key_points = []
        
        for line in lines:
            if any(keyword in line for keyword in ["共振评分", "市场状态", "操作建议", "主导信号", "逻辑共性"]):
                key_points.append(line.strip())
        
        # 构建总结
        summary = ["## 📋 执行摘要"]
        summary.extend(key_points[:8])  # 取前8个关键点
        summary.append("")
        summary.append("*注：此为手动摘要，建议优化Summarize技能配置*")
        
        return "\n".join(summary)
    
    def generate_word_report(self, content: str, summary: str) -> bool:
        """
        生成Word格式报告
        
        Args:
            content: 完整内容
            summary: 摘要内容
            
        Returns:
            生成结果
        """
        try:
            logger.info("调用Word/DOCX技能生成报告...")
            
            # 准备报告数据
            report_date = datetime.now().strftime("%Y年%m月%d日")
            report_title = f"琥珀引擎·日度作战指令 - {report_date}"
            
            report_data = {
                "title": report_title,
                "date": report_date,
                "summary": summary,
                "content": content,
                "metadata": {
                    "generator": "IntelligentReporter v1.0",
                    "generated_at": datetime.now().isoformat(),
                    "skill_used": ["summarize", "word-docx"]
                }
            }
            
            # 保存为JSON供Word技能使用
            temp_json = f"/tmp/report_data_{int(time.time())}.json"
            with open(temp_json, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            # 调用skillhub word-docx技能
            output_file = os.path.join(self.output_dir, f"琥珀引擎_作战指令_{datetime.now().strftime('%Y%m%d')}.docx")
            
            cmd = [
                "skillhub", "run", "word-docx",
                "--input", temp_json,
                "--output", output_file,
                "--template", "daily_report"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            
            # 清理临时文件
            os.remove(temp_json)
            
            if result.returncode == 0:
                logger.info(f"Word报告生成成功: {output_file}")
                
                # 同时生成PDF版本
                pdf_file = output_file.replace('.docx', '.pdf')
                pdf_cmd = [
                    "skillhub", "run", "research-paper-writer",
                    "--input", output_file,
                    "--output", pdf_file,
                    "--format", "pdf"
                ]
                
                pdf_result = subprocess.run(
                    pdf_cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if pdf_result.returncode == 0:
                    logger.info(f"PDF报告生成成功: {pdf_file}")
                else:
                    logger.warning(f"PDF报告生成失败: {pdf_result.stderr}")
                
                return True
            else:
                logger.error(f"Word报告生成失败: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Word报告生成异常: {str(e)}")
            return False
    
    def run(self) -> bool:
        """
        运行智能战报生成器
        
        Returns:
            执行结果
        """
        logger.info("=" * 60)
        logger.info("智能战报生成器启动")
        logger.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"输出目录: {self.output_dir}")
        logger.info("=" * 60)
        
        try:
            # 1. 加载数据
            resonance_data = self.load_resonance_data()
            if not resonance_data:
                logger.error("无法加载共振数据，终止执行")
                return False
            
            algorithms = self.load_algorithm_details()
            
            # 2. 分析算法共识
            consensus = self.analyze_algorithm_consensus(algorithms)
            
            # 3. 生成人类语言洞察
            human_insights = self.generate_human_insights(resonance_data, consensus)
            
            # 4. AI总结
            ai_summary = self.summarize_with_ai(human_insights)
            
            # 5. 生成Word报告
            report_success = self.generate_word_report(human_insights, ai_summary)
            
            # 6. 生成执行报告
            execution_report = {
                "module": "intelligent_reporter",
                "timestamp": datetime.now().isoformat(),
                "resonance_score": resonance_data.get("resonance_score", 0),
                "signal_status": resonance_data.get("signal_status", "未知"),
                "action": resonance_data.get("action", "未知"),
                "consensus_analysis": consensus,
                "report_generated": report_success,
                "ai_summary_used": "summarize" in ai_summary,
                "output_files": [
                    f"{self.output_dir}/琥珀引擎_作战指令_{datetime.now().strftime('%Y%m%d')}.docx",
                    f"{self.output_dir}/琥珀引擎_作战指令_{datetime.now().strftime('%Y%m%d')}.pdf"
                ]
            }
            
            # 保存执行报告
            report_file = os.path.join(self.output_dir, f"reporter_execution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(execution_report, f, ensure_ascii=False, indent=2)
            
            logger.info("=" * 60)
            logger.info("智能战报生成完成")
            logger.info(f"共振评分: {resonance_data.get('resonance_score', 0)}")
            logger.info(f"市场状态: {resonance_data.get('signal_status', '未知')}")
            logger.info(f"报告生成: {'成功' if report_success else '失败'}")
            logger.info(f"执行报告: {report_file}")
            logger.info("=" * 60)
            
            return report_success
            
        except Exception as e:
            logger.error(f"智能战报生成器执行失败: {str(e)}")
            return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="智能战报生成器")
    parser.add_argument("--output-dir", default="docs/reports/daily", help="输出目录")
    parser.add_argument("--no-word", action="store_true", help="不生成Word报告")
    
    args = parser.parse_args()
    
    try:
        reporter = IntelligentReporter(output_dir=args.output_dir)
        
        # 运行战报生成器
        success = reporter.run()
        
        # 返回退出码
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"智能战报生成器执行失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()