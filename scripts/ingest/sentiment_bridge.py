#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[2614-032号] 情感桥接器 - 琥珀引擎舆情对冲因子
功能：将非结构化新闻文本转化为结构化情感因子，对冲G9宏观权重
作者：Cheese 🧀 (工程师)
日期：2026-03-31
版本：v1.0.0
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/sentiment_bridge.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SentimentBridge:
    """舆情情感桥接器 - 将新闻文本转化为情感因子"""
    
    def __init__(self, timeout: int = 30):
        """
        初始化情感桥接器
        
        Args:
            timeout: 技能调用超时时间（秒）
        """
        self.timeout = timeout
        self.keyword_mapping = {
            # 黄金相关关键词映射
            "黄金": {
                "避险情绪": 0.8,
                "地缘风险": 0.7,
                "降息预期": 0.6,
                "央行购金": 0.9,
                "通胀担忧": 0.5,
                "美元走弱": 0.6,
                "战争风险": 0.8,
                "经济衰退": 0.7,
                "量化宽松": 0.4,
                "利率决议": 0.3
            },
            # 负面关键词映射
            "negative": {
                "加息": -0.3,
                "紧缩": -0.4,
                "抛售": -0.7,
                "恐慌": -0.6,
                "崩盘": -0.9,
                "下跌": -0.5,
                "风险": -0.4,
                "警告": -0.3,
                "担忧": -0.4,
                "危机": -0.8
            }
        }
        
    def fetch_news_sources(self) -> Dict[str, List[str]]:
        """
        多源新闻捕获：调用OpenClaw技能获取国内外新闻
        
        Returns:
            包含新闻源的字典
        """
        news_sources = {
            "cctv": [],
            "perplexity": [],
            "market_news": []
        }
        
        try:
            logger.info("开始多源新闻捕获...")
            
            # 1. 获取国内核心基调 (CCTV新闻)
            logger.info("调用 CCTV News Fetcher...")
            cctv_result = self.run_skill("cctv-news-fetcher", ["--limit", "10"])
            if cctv_result["success"]:
                news_sources["cctv"] = self.extract_headlines(cctv_result["output"])
                logger.info(f"获取CCTV新闻: {len(news_sources['cctv'])}条")
            
            # 2. 获取全球金融头条 (Perplexity)
            logger.info("调用 Perplexity 获取全球金融头条...")
            perplexity_result = self.run_skill("perplexity", [
                "--query", "黄金 避险 地缘风险 降息预期 央行购金 最新新闻",
                "--limit", "15"
            ])
            if perplexity_result["success"]:
                news_sources["perplexity"] = self.extract_headlines(perplexity_result["output"])
                logger.info(f"获取Perplexity新闻: {len(news_sources['perplexity'])}条")
            
            # 3. 获取市场新闻分析 (Market News Analyst)
            logger.info("调用 Market News Analyst...")
            market_result = self.run_skill("market-news-analyst", [
                "--symbol", "518880",
                "--period", "1d"
            ])
            if market_result["success"]:
                news_sources["market_news"] = self.extract_headlines(market_result["output"])
                logger.info(f"获取市场新闻: {len(news_sources['market_news'])}条")
            
            logger.info(f"新闻捕获完成: CCTV={len(news_sources['cctv'])}, "
                       f"Perplexity={len(news_sources['perplexity'])}, "
                       f"Market={len(news_sources['market_news'])}")
            
            return news_sources
            
        except Exception as e:
            logger.error(f"新闻捕获失败: {str(e)}")
            return news_sources
    
    def run_skill(self, skill_name: str, args: List[str] = None) -> Dict:
        """
        运行SkillHub技能
        
        Args:
            skill_name: 技能名称
            args: 参数列表
            
        Returns:
            执行结果字典
        """
        if args is None:
            args = []
        
        try:
            cmd = ["skillhub", "run", skill_name] + args
            logger.debug(f"执行命令: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "returncode": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            logger.warning(f"技能 {skill_name} 执行超时 ({self.timeout}秒)")
            return {
                "success": False,
                "output": "",
                "error": f"Timeout after {self.timeout} seconds",
                "returncode": -1
            }
        except Exception as e:
            logger.error(f"技能 {skill_name} 执行异常: {str(e)}")
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "returncode": -1
            }
    
    def extract_headlines(self, text: str) -> List[str]:
        """
        从技能输出中提取新闻标题
        
        Args:
            text: 技能输出文本
            
        Returns:
            新闻标题列表
        """
        headlines = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and len(line) > 10:  # 过滤短行
                # 提取可能的标题行
                if any(keyword in line.lower() for keyword in ["黄金", "金价", "避险", "降息", "央行"]):
                    headlines.append(line)
                elif line.endswith((".", "。", "!", "！", "?", "？")):
                    headlines.append(line)
        
        return headlines[:20]  # 限制数量
    
    def analyze_sentiment(self, headlines: List[str]) -> float:
        """
        分析新闻情感得分
        
        Args:
            headlines: 新闻标题列表
            
        Returns:
            情感得分 (-1 到 1)
        """
        if not headlines:
            logger.warning("无新闻数据，返回中性情感得分")
            return 0.0
        
        total_score = 0.0
        keyword_count = 0
        
        for headline in headlines:
            headline_lower = headline.lower()
            
            # 检查黄金相关关键词
            for keyword, weight in self.keyword_mapping["黄金"].items():
                if keyword in headline_lower:
                    total_score += weight
                    keyword_count += 1
                    logger.debug(f"发现黄金关键词: {keyword} -> +{weight}")
            
            # 检查负面关键词
            for keyword, weight in self.keyword_mapping["negative"].items():
                if keyword in headline_lower:
                    total_score += weight
                    keyword_count += 1
                    logger.debug(f"发现负面关键词: {keyword} -> {weight}")
        
        if keyword_count == 0:
            logger.info("未检测到相关关键词，返回中性情感")
            return 0.0
        
        # 计算平均情感得分，并归一化到[-1, 1]
        avg_score = total_score / keyword_count
        normalized_score = max(-1.0, min(1.0, avg_score))
        
        logger.info(f"情感分析完成: 检测到{keyword_count}个关键词，原始得分{avg_score:.3f}，归一化得分{normalized_score:.3f}")
        return normalized_score
    
    def calculate_final_score(self, base_score: float, sentiment_factor: float) -> float:
        """
        计算对冲后的最终评分
        
        公式: Final_Score = Base_Score × (1 + S_Factor × 0.2)
        
        Args:
            base_score: 基础共振评分 (0-100)
            sentiment_factor: 情感因子 (-1 到 1)
            
        Returns:
            对冲后的最终评分
        """
        final_score = base_score * (1 + sentiment_factor * 0.2)
        
        # 确保评分在合理范围内
        final_score = max(0.0, min(100.0, final_score))
        
        logger.info(f"情感对冲计算: 基础分{base_score:.2f} × (1 + {sentiment_factor:.3f}×0.2) = {final_score:.2f}")
        return final_score
    
    def generate_sentiment_report(self, sentiment_factor: float, news_count: Dict[str, int]) -> Dict:
        """
        生成情感分析报告
        
        Args:
            sentiment_factor: 情感因子
            news_count: 各来源新闻数量
            
        Returns:
            情感分析报告
        """
        sentiment_level = "中性"
        if sentiment_factor > 0.3:
            sentiment_level = "积极"
        elif sentiment_factor > 0.1:
            sentiment_level = "略积极"
        elif sentiment_factor < -0.3:
            sentiment_level = "消极"
        elif sentiment_factor < -0.1:
            sentiment_level = "略消极"
        
        report = {
            "fetch_time": datetime.now().isoformat(),
            "sentiment_factor": round(sentiment_factor, 4),
            "sentiment_level": sentiment_level,
            "news_sources": news_count,
            "description": f"舆情情感分析: {sentiment_level} ({sentiment_factor:.3f})",
            "impact": "将对G9宏观因子进行情感对冲修正"
        }
        
        return report
    
    def run(self, base_score: float = None) -> Dict:
        """
        运行情感桥接器主流程
        
        Args:
            base_score: 可选的基础共振评分
            
        Returns:
            完整的情感分析结果
        """
        logger.info("=" * 60)
        logger.info("琥珀引擎·情感桥接器启动")
        logger.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        try:
            # 1. 多源新闻捕获
            news_sources = self.fetch_news_sources()
            
            # 统计新闻数量
            news_count = {
                "cctv": len(news_sources["cctv"]),
                "perplexity": len(news_sources["perplexity"]),
                "market_news": len(news_sources["market_news"]),
                "total": sum(len(v) for v in news_sources.values())
            }
            
            # 2. 情感分析
            all_headlines = []
            for source in news_sources.values():
                all_headlines.extend(source)
            
            sentiment_factor = self.analyze_sentiment(all_headlines)
            
            # 3. 生成报告
            report = self.generate_sentiment_report(sentiment_factor, news_count)
            
            # 4. 如果提供了基础评分，计算对冲后评分
            if base_score is not None:
                final_score = self.calculate_final_score(base_score, sentiment_factor)
                report["base_score"] = base_score
                report["final_score"] = final_score
                report["score_adjustment"] = final_score - base_score
            
            # 5. 保存报告
            output_dir = "database/sentiment"
            os.makedirs(output_dir, exist_ok=True)
            
            output_file = os.path.join(output_dir, f"sentiment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"情感分析报告已保存: {output_file}")
            logger.info(f"情感因子: {sentiment_factor:.3f} ({report['sentiment_level']})")
            
            if base_score is not None:
                logger.info(f"评分对冲: {base_score:.2f} → {report.get('final_score', base_score):.2f} "
                          f"(调整: {report.get('score_adjustment', 0):+.2f})")
            
            logger.info("=" * 60)
            logger.info("情感桥接器执行完成")
            logger.info("=" * 60)
            
            return report
            
        except Exception as e:
            logger.error(f"情感桥接器执行失败: {str(e)}")
            raise

def main():
    """主函数"""
    try:
        # 创建情感桥接器实例
        bridge = SentimentBridge(timeout=30)
        
        # 检查是否提供了基础评分参数
        base_score = None
        if len(sys.argv) > 1:
            try:
                base_score = float(sys.argv[1])
                logger.info(f"使用提供的基础评分: {base_score}")
            except ValueError:
                logger.warning(f"无效的基础评分参数: {sys.argv[1]}")
        
        # 运行情感分析
        result = bridge.run(base_score)
        
        # 输出结果
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # 返回成功退出码
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"主程序执行失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()