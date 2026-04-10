#!/usr/bin/env python3
"""
G13 政策语义向量家 (Policy Semantic Vector Analyst)
影子算法 - LLM政策文档语义分析

核心逻辑: 利用LLM对政策文档进行全量向量化对比，量化政策支持的"含金量"
解决痛点: 人工解读政策的片面性和滞后性
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
import datetime
import hashlib
import logging
import re

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = logging.getLogger(__name__)

@dataclass
class PolicySemanticConfig:
    """政策语义算法配置"""
    
    # 政策关键词库
    policy_keywords = {
        "data_elements": ["数据要素", "数据交易", "数据交易所", "数据资产", "数据确权"],
        "ai_tech": ["人工智能", "AI", "大模型", "算法", "机器学习", "深度学习"],
        "chip": ["芯片", "半导体", "集成电路", "国产替代", "自主可控"],
        "green_energy": ["新能源", "碳中和", "碳达峰", "光伏", "风电", "储能"],
        "digital_economy": ["数字经济", "数字化转型", "数字中国", "产业数字化"],
        "finance_reform": ["金融改革", "资本市场", "注册制", "直接融资"],
        "healthcare": ["医药", "医疗", "健康中国", "生物医药", "创新药"],
        "infrastructure": ["基础设施", "新基建", "5G", "物联网", "工业互联网"]
    }
    
    # 政策文档源
    policy_sources = [
        "国务院文件",
        "发改委通知", 
        "证监会公告",
        "央行货币政策报告",
        "工信部产业政策",
        "科技部科技规划",
        "地方政府规划"
    ]
    
    # 语义分析参数
    semantic_similarity_threshold = 0.7  # 语义相似度阈值
    policy_recency_weight = 0.3  # 政策新鲜度权重
    policy_authority_weight = 0.4  # 政策权威性权重
    policy_specificity_weight = 0.3  # 政策具体性权重
    
    # LLM参数 (实际实现时需要配置)
    llm_model = "gpt-4"  # 使用的LLM模型
    embedding_model = "text-embedding-ada-002"  # 嵌入模型
    max_tokens = 4000  # 最大token数
    
    # 评分参数
    base_score = 50
    max_keyword_match_bonus = 30
    max_semantic_similarity_bonus = 20
    max_policy_strength_bonus = 20

@dataclass
class PolicyDocument:
    """政策文档"""
    source: str  # 来源
    title: str  # 标题
    content: str  # 内容 (摘要)
    publish_date: str  # 发布日期
    authority_level: int  # 权威级别 (1-5)
    keywords: List[str]  # 关键词
    embedding: Optional[np.ndarray] = None  # 语义向量
    hash_id: str = ""  # 文档哈希ID

@dataclass
class CompanyPolicyAnalysis:
    """公司政策分析结果"""
    ticker: str
    company_name: str
    policy_match_score: float  # 政策匹配度 (0-100)
    matched_keywords: List[Dict]  # 匹配的关键词
    relevant_policies: List[PolicyDocument]  # 相关政策
    semantic_similarities: List[float]  # 语义相似度
    policy_strength: float  # 政策强度
    signals: List[str]
    confidence: float

@dataclass
class PolicySemanticAnalysis:
    """政策语义分析结果"""
    timestamp: str
    analyzed_companies: int
    policy_database_size: int
    most_relevant_policy: str
    hottest_sector: str
    overall_policy_sentiment: float  # 整体政策情绪 (0-1)
    company_analyses: Dict[str, CompanyPolicyAnalysis]

class PolicySemanticAnalyst:
    """政策语义向量家"""
    
    def __init__(self, config: Optional[PolicySemanticConfig] = None):
        self.config = config or PolicySemanticConfig()
        self.policy_database = []  # 政策文档数据库
        self.embeddings_cache = {}  # 向量缓存
        self.initialized = False
        self.llm_available = False
        
    def initialize(self):
        """初始化算法"""
        try:
            # 检查LLM可用性
            self.llm_available = self._check_llm_availability()
            
            # 加载政策数据库
            self._load_policy_database()
            
            logger.info("✅ G13 政策语义向量家初始化完成")
            logger.info(f"   政策关键词库: {len(self.config.policy_keywords)}个类别")
            logger.info(f"   政策文档数: {len(self.policy_database)}个")
            logger.info(f"   LLM可用性: {'✅' if self.llm_available else '❌'}")
            
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"❌ G13 初始化失败: {e}")
            return False
    
    def _check_llm_availability(self) -> bool:
        """检查LLM可用性"""
        # 实际实现中需要检查API密钥和连接
        # 目前返回模拟结果
        return False  # 默认不可用，使用基于关键词的方法
    
    def _load_policy_database(self):
        """加载政策数据库"""
        # 实际实现中需要从数据库或API加载
        # 目前使用模拟数据
        
        mock_policies = [
            PolicyDocument(
                source="国务院",
                title="关于构建数据基础制度更好发挥数据要素作用的意见",
                content="提出构建数据产权、流通交易、收益分配、安全治理等制度，促进数据要素价值释放。",
                publish_date="2026-03-15",
                authority_level=5,
                keywords=["数据要素", "数据交易", "数据产权", "数字经济"],
                hash_id=hashlib.md5("policy_001".encode()).hexdigest()
            ),
            PolicyDocument(
                source="发改委",
                title=""新时代"人工智能发展规划",
                content="推动人工智能与实体经济深度融合，加强算力基础设施建设。",
                publish_date="2026-02-20",
                authority_level=4,
                keywords=["人工智能", "AI", "算力", "基础设施"],
                hash_id=hashlib.md5("policy_002".encode()).hexdigest()
            ),
            PolicyDocument(
                source="证监会",
                title="关于支持科技型企业利用资本市场发展的指导意见",
                content="支持符合条件的科技型企业在科创板、创业板上市，扩大直接融资规模。",
                publish_date="2026-01-10",
                authority_level=4,
                keywords=["资本市场", "科创板", "直接融资", "科技企业"],
                hash_id=hashlib.md5("policy_003".encode()).hexdigest()
            ),
            PolicyDocument(
                source="工信部",
                title=""十四五"数字经济发展规划",
                content="到2025年，数字经济核心产业增加值占GDP比重达到10%。",
                publish_date="2025-12-01",
                authority_level=4,
                keywords=["数字经济", "数字化转型", "产业数字化", "数字中国"],
                hash_id=hashlib.md5("policy_004".encode()).hexdigest()
            ),
            PolicyDocument(
                source="央行",
                title="2026年第一季度中国货币政策执行报告",
                content="保持流动性合理充裕，精准有力实施好稳健的货币政策。",
                publish_date="2026-03-31",
                authority_level=5,
                keywords=["货币政策", "流动性", "稳健", "金融支持"],
                hash_id=hashlib.md5("policy_005".encode()).hexdigest()
            )
        ]
        
        self.policy_database = mock_policies
    
    def _get_company_info(self, ticker: str) -> Dict:
        """获取公司信息"""
        # 实际实现中需要从数据库获取
        # 目前使用模拟数据
        
        company_mapping = {
            "000681": {"name": "视觉中国", "industry": "传媒", "business": "数字版权交易"},
            "600633": {"name": "浙数文化", "industry": "传媒", "business": "数据交易平台"},
            "000938": {"name": "紫光股份", "industry": "计算机", "business": "云计算基础设施"},
            "688256": {"name": "寒武纪", "industry": "电子", "business": "AI芯片设计"},
            "603881": {"name": "数据港", "industry": "计算机", "business": "数据中心服务"},
            "000032": {"name": "深桑达A", "industry": "计算机", "business": "国资云平台"},
            "002368": {"name": "太极股份", "industry": "计算机", "business": "基础软件"}
        }
        
        return company_mapping.get(ticker, {
            "name": f"公司{ticker}",
            "industry": "未知",
            "business": "未知"
        })
    
    def _extract_keywords_from_text(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        keywords_found = []
        
        for category, keyword_list in self.config.policy_keywords.items():
            for keyword in keyword_list:
                if keyword in text:
                    keywords_found.append({
                        "keyword": keyword,
                        "category": category,
                        "count": text.count(keyword)
                    })
        
        return keywords_found
    
    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """计算语义相似度"""
        if self.llm_available:
            # 实际实现中使用LLM计算嵌入向量相似度
            # 目前使用基于关键词的简单方法
            pass
        
        # 基于关键词重叠的简单相似度计算
        keywords1 = self._extract_keywords_from_text(text1)
        keywords2 = self._extract_keywords_from_text(text2)
        
        if not keywords1 or not keywords2:
            return 0.0
        
        # 计算Jaccard相似度
        set1 = set([kw["keyword"] for kw in keywords1])
        set2 = set([kw["keyword"] for kw in keywords2])
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_policy_strength(self, policy: PolicyDocument) -> float:
        """计算政策强度"""
        # 基于权威级别、新鲜度、具体性计算
        today = datetime.datetime.now()
        publish_date = datetime.datetime.strptime(policy.publish_date, "%Y-%m-%d")
        
        # 新鲜度 (越新权重越高)
        days_old = (today - publish_date).days
        recency_score = max(0, 1.0 - days_old / 365)  # 一年内有效
        
        # 权威性
        authority_score = policy.authority_level / 5.0
        
        # 具体性 (基于关键词数量)
        specificity_score = min(1.0, len(policy.keywords) / 10.0)
        
        # 加权综合
        strength = (
            recency_score * self.config.policy_recency_weight +
            authority_score * self.config.policy_authority_weight +
            specificity_score * self.config.policy_specificity_weight
        )
        
        return strength
    
    def analyze_company(self, ticker: str) -> CompanyPolicyAnalysis:
        """分析公司政策匹配度"""
        if not self.initialized:
            if not self.initialize():
                raise RuntimeError("G13 初始化失败")
        
        # 获取公司信息
        company_info = self._get_company_info(ticker)
        company_text = f"{company_info['name']} {company_info['industry']} {company_info['business']}"
        
        # 提取公司关键词
        company_keywords = self._extract_keywords_from_text(company_text)
        
        # 分析每个政策文档
        relevant_policies = []
        semantic_similarities = []
        matched_keywords = []
        
        for policy in self.policy_database:
            # 计算语义相似度
            similarity = self._calculate_semantic_similarity(company_text, policy.content)
            
            if similarity > self.config.semantic_similarity_threshold:
                relevant_policies.append(policy)
                semantic_similarities.append(similarity)
                
                # 找出匹配的关键词
                for kw in company_keywords:
                    if kw["keyword"] in policy.content:
                        matched_keywords.append({
                            **kw,
                            "policy_title": policy.title,
                            "similarity": similarity
                        })
        
        # 计算政策匹配度评分
        policy_match_score = self._calculate_policy_match_score(
            company_keywords=company_keywords,
            matched_keywords=matched_keywords,
            semantic_similarities=semantic_similarities,
            relevant_policies=relevant_policies
        )
        
        # 计算政策强度
        policy_strength = 0
        if relevant_policies:
            policy_strength = sum(self._calculate_policy_strength(p) for p in relevant_policies) / len(relevant_policies)
        
        # 生成信号
        signals = []
        if policy_match_score >= 70:
            signals.append(f"强政策匹配: {policy_match_score:.1f}分")
        
        if matched_keywords:
            top_keywords = sorted(matched_keywords, key=lambda x: x["count"], reverse=True)[:3]
            signals.append(f"政策关键词: {', '.join([k['keyword'] for k in top_keywords])}")
        
        if relevant_policies:
            signals.append(f"相关政策: {len(relevant_policies)}个")
        
        # 计算置信度
        confidence = 0.5
        if self.llm_available:
            confidence = 0.8
        elif matched_keywords:
            confidence = 0.6 + min(0.3, len(matched_keywords) / 20.0)
        
        analysis = CompanyPolicyAnalysis(
            ticker=ticker,
            company_name=company_info["name"],
            policy_match_score=policy_match_score,
            matched_keywords=matched_keywords,
            relevant_policies=relevant_policies,
            semantic_similarities=semantic_similarities,
            policy_strength=policy_strength,
            signals=signals,
            confidence=confidence
        )
        
        return analysis
    
    def _calculate_policy_match_score(self,
                                     company_keywords: List[Dict],
                                     matched_keywords: List[Dict],
                                     semantic_similarities: List[float],
                                     relevant_policies: List[PolicyDocument]) -> float:
        """计算政策匹配度评分"""
        score = self.config.base_score
        
        # 关键词匹配加成
        if matched_keywords:
            keyword_bonus = min(len(matched_keywords) * 5, self.config.max_keyword_match_bonus)
            score += keyword_bonus
        
        # 语义相似度加成
        if semantic_similarities:
            avg_similarity = np.mean(semantic_similarities)
            similarity_bonus = avg_similarity * self.config.max_semantic_similarity_bonus
            score += similarity_bonus
        
        # 政策强度加成
        if relevant_policies:
            policy_strengths = [self._calculate_policy_strength(p) for p in relevant_policies]
            avg_strength = np.mean(policy_strengths)
            strength_bonus = avg_strength * self.config.max_policy_strength_bonus
            score += strength_bonus
        
        return min(100, max(0, score))
    
    def analyze_market(self) -> PolicySemanticAnalysis:
        """分析全市场政策语义"""
        if not self.initialized:
            if not self.initialize():
                raise RuntimeError("G13 初始化失败")
        
        timestamp = datetime.datetime.now().isoformat()
        
        # 分析一组公司
        test_tickers = ["000681", "600633", "000938", "688256", "603881", "000032", "002368"]
        company_analyses = {}
        
        logger.info(f"🔍 G13 开始分析全市场政策语义...")
        
        for ticker in test_tickers:
            try:
                analysis = self.analyze_company(ticker)
                company_analyses[ticker] = analysis
                
                logger.debug(f"   {ticker}: {analysis.policy_match_score:.1f}分")
                
            except Exception as e:
                logger.warning(f"公司 {ticker} 分析失败: {e}")
        
        # 计算整体政策情绪
        overall_policy_sentiment = 0.5
        if company_analyses:
            scores = [a.policy_match_score for a in company_analyses.values()]
            overall_policy_sentiment = np.mean(scores) / 100.0
        
        # 找出最相关的政策和最热门的板块
        most_relevant_policy = ""
        hottest_sector = ""
        
        if company_analyses:
            # 找出评分最高的公司
            best_company = max(company_analyses.values(), key=lambda x: x.policy_match_score)
            if best_company.relevant_policies:
                most_relevant_policy = best_company.relevant_policies[0].title
            
            # 分析板块热度 (基于关键词类别)
            sector_counts = {}
            for analysis in company_analyses.values():
                for kw in analysis.matched_keywords:
                    sector = kw["category"]
                    sector_counts[sector] = sector_counts.get(sector, 0) + 1
            
            if sector_counts:
                hottest_sector = max(sector_counts.items(), key=lambda x: x[1])[0]
        
        analysis = PolicySemanticAnalysis(
            timestamp=timestamp,
            analyzed_companies=len(company_analyses),
            policy_database_size=len(self.policy_database),
            most_relevant_policy=most_relevant_policy,
            hottest_sector=hottest_sector,
            overall_policy_sentiment=overall_policy_sentiment,
            company_analyses=company_analyses
        )
        
        logger.info(f"✅ G13 市场分析完成")
        logger.info(f"   分析公司: {len(company_analyses)}个")
        logger.info(f"   政策数据库: {len(self.policy_database)}个文档")
        logger.info(f"   整体政策情绪: {overall_policy_sentiment:.2f}")
        logger.info(f"   最热门板块: {hottest_sector}")
        
        return analysis
    
    def score_ticker(self, ticker: str) -> Dict:
        """
        为单个标的评分
        
        返回:
            {
                "score": 政策匹配度评分 (0-100),
                "confidence": 置信度 (0-1),
                "signals": 信号列表,
                "matched_keywords": 匹配的关键词,
                "policy_strength": 相关政策强度,
                "relevant_policies_count": 相关政策数量
            }
        """
        if not self.initialized:
            if not self.initialize():
                return {"score": 0, "confidence": 0, "signals": ["算法未初始化"]}
        
        try:
            analysis = self.analyze_company(ticker)
            
            return {
                "score": analysis.policy_match_score,
                "confidence": analysis.confidence,
                "signals": analysis.signals,
                "matched_keywords": [{"keyword": kw["keyword"], "category": kw["category"]} for kw in analysis.matched_keywords[:5]],
                "policy_strength": analysis.policy_strength,
                "relevant_policies_count": len(analysis.relevant_policies),
                "company_name": analysis.company_name
            }
            
        except Exception as e:
            logger.error(f"标的 {ticker} 评分失败: {e}")
            return {
                "score": 0,
                "confidence": 0.1,
                "signals": [f"评分失败: {str(e)}"],
                "matched_keywords": [],
                "policy_strength": 0,
                "relevant_policies_count": 0,
                "error": str(e)
            }
    
    def get_algorithm_info(self) -> Dict:
        """获取算法信息"""
        return {
            "algorithm_id": "G13",
            "algorithm_name": "政策语义向量家",
            "version": "1.0.0",
            "description": "利用LLM对政策文档进行全量向量化对比，量化政策支持的'含金量'",
            "solved_pain_point": "人工解读政策的片面性和滞后性",
            "status": "incubator",
            "llm_available": self.llm_available,
            "initialized": self.initialized,
            "policy_database_size": len(self.policy_database),
            "config": asdict(self.config) if hasattr(self.config, '__dict__') else {}
        }

# 测试函数
def test_policy_semantic():
    """测试政策语义算法"""
    print("🧪 测试 G13 政策语义向量家...")
    
    analyst = PolicySemanticAnalyst()
    
    # 初始化
    if not analyst.initialize():
        print("❌ 初始化失败")
        return False
    
    # 获取算法信息
    info = analyst.get_algorithm_info()
    print(f"   算法ID: {info['algorithm_id']}")
    print(f"   算法名称: {info['algorithm_name']}")
    print(f"   状态: {info['status']}")
    print(f"   LLM可用: {'✅' if info['llm_available'] else '❌'}")
    print(f"   政策数据库: {info['policy_database_size']}个文档")
    
    # 分析市场
    print("\n🔍 分析全市场政策语义...")
    market_analysis = analyst.analyze_market()
    
    print(f"   分析公司: {market_analysis.analyzed_companies}")
    print(f"   整体政策情绪: {market_analysis.overall_policy_sentiment:.2f}")
    print(f"   最热门板块: {market_analysis.hottest_sector}")
    print(f"   最相关政策: {market_analysis.most_relevant_policy[:50]}...")
    
    # 测试单个标的评分
    print("\n🎯 测试标的评分...")
    test_tickers = ["000681", "600633", "000938"]
    
    for ticker in test_tickers:
        result = analyst.score_ticker(ticker)
        print(f"   {ticker} ({result.get('company_name', '')}): {result['score']:.1f}分")
        print(f"     置信度: {result['confidence']:.2f}")
        print(f"     信号: {', '.join(result['signals'][:2]) if result['signals'] else '无'}")
        if result['matched_keywords']:
            print(f"     匹配关键词: {', '.join([k['keyword'] for k in result['matched_keywords'][:3]])}")
    
    return True

if __name__ == "__main__":
    success = test_policy_semantic()
    if success:
        print("\n✅ G13 政策语义向量家测试通过")
    else:
        print("\n❌ G13 政策语义向量家测试失败")