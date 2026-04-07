#!/usr/bin/env python3
"""
G11 - Policy Resonance Strategy 政策感知因子策略
检测政策与标的业务匹配度，赋予动量乘数
符合 [2615-001号] "琥珀战车"试金石专项行动
"""

import json
import os
import re
from typing import Dict, Any, List, Optional, Tuple
from .base_strategy import BaseStrategy

class PolicyResonanceStrategy(BaseStrategy):
    """政策感知因子策略 (G11)"""
    
    def __init__(self):
        super().__init__(
            name="Policy-Resonance",
            description="政策感知因子策略，检测政策关键词与标的业务匹配度，赋予动量乘数"
        )
        
        # 政策关键词库 (基于哨兵抓取的数据)
        self.policy_keywords = self._load_policy_keywords()
        
        # 业务关键词映射表
        self.business_keyword_map = self._load_business_keyword_map()
    
    def get_required_history_days(self) -> int:
        """获取所需历史数据天数 - 政策因子不依赖历史数据"""
        return 0
    
    def _load_policy_keywords(self) -> Dict[str, float]:
        """加载政策关键词库"""
        # 从哨兵数据加载政策关键词
        # 这里使用静态关键词，实际应从哨兵模块动态获取
        keywords = {
            # 数据要素相关
            "数据要素": 1.0,
            "数据交易": 0.9,
            "数据交易所": 0.95,
            "中国数谷": 0.8,
            "杭州": 0.7,
            "深圳": 0.7,
            "三年行动计划": 0.85,
            "十亿基金": 0.75,
            "公共数据授权": 0.8,
            "数据跨境流动": 0.8,
            
            # 算力基础设施
            "算力": 0.85,
            "人工智能": 0.9,
            "AI": 0.9,
            "云计算": 0.8,
            "数据中心": 0.85,
            "IDC": 0.85,
            
            # 网络安全
            "网络安全": 0.9,
            "数据安全": 0.9,
            "信息安全": 0.9,
            
            # 芯片/半导体
            "芯片": 0.8,
            "半导体": 0.8,
            "国产替代": 0.75,
        }
        
        return keywords
    
    def _load_business_keyword_map(self) -> Dict[str, List[str]]:
        """加载业务关键词映射表"""
        # 将业务关键词映射到政策领域
        mapping = {
            "数据交易": ["数据交易", "数据流通", "数据服务", "大数据", "数据平台"],
            "算力基础设施": ["服务器", "云计算", "数据中心", "IDC", "算力", "高性能计算"],
            "网络安全": ["网络安全", "信息安全", "数据安全", "防护", "加密", "安全服务"],
            "芯片半导体": ["芯片", "半导体", "集成电路", "处理器", "GPU", "CPU"],
            "通信基础设施": ["5G", "通信", "网络", "光纤", "基站"],
            "基础软件": ["操作系统", "数据库", "中间件", "基础软件"],
        }
        return mapping
    
    def _extract_business_keywords(self, ticker: str, history_data: Dict[str, Any]) -> List[str]:
        """提取标的业务关键词"""
        # 从历史数据中提取业务信息
        # 这里简化处理，实际应从财务主营业务数据提取
        ticker_business_map = {
            "600633": ["数据交易", "数字文化", "大数据服务", "浙江"],  # 浙数文化
            "000938": ["云计算", "服务器", "网络设备", "紫光云"],  # 紫光股份
            "688256": ["AI芯片", "人工智能", "处理器", "寒武纪"],  # 寒武纪
            "603881": ["数据中心", "IDC", "云计算基础设施", "数据港"],  # 数据港
            "000032": ["云计算", "国资云", "深圳", "深桑达"],  # 深桑达A
            "002368": ["基础软件", "操作系统", "太极股份", "国产化"],  # 太极股份
            "000977": ["服务器", "云计算", "AI服务器", "浪潮"],  # 浪潮信息
            "603019": ["高性能计算", "服务器", "液冷", "中科曙光"],  # 中科曙光
            "002439": ["网络安全", "信息安全", "防护", "启明星辰"],  # 启明星辰
            "300369": ["网络安全", "绿盟科技", "安全服务", "防护"],  # 绿盟科技
        }
        
        ticker_code = ticker[:6]  # 提取基础代码
        return ticker_business_map.get(ticker_code, [])
    
    def _calculate_policy_match_score(self, business_keywords: List[str]) -> float:
        """计算政策匹配度分数 (0-1)"""
        if not business_keywords:
            return 0.0
        
        # 计算业务关键词与政策关键词的匹配度
        match_scores = []
        
        for business_keyword in business_keywords:
            # 查找匹配的政策关键词
            for policy_keyword, policy_weight in self.policy_keywords.items():
                # 简单的关键词匹配 (实际应使用更复杂的语义匹配)
                if business_keyword in policy_keyword or policy_keyword in business_keyword:
                    match_scores.append(policy_weight)
                    break
            
            # 检查业务关键词映射
            for policy_domain, domain_keywords in self.business_keyword_map.items():
                if business_keyword in domain_keywords:
                    # 找到对应的政策关键词
                    domain_policy_keywords = [k for k in self.policy_keywords.keys() 
                                            if any(dk in k for dk in domain_keywords)]
                    if domain_policy_keywords:
                        # 取最高权重
                        max_weight = max([self.policy_keywords[k] for k in domain_policy_keywords])
                        match_scores.append(max_weight)
                        break
        
        if not match_scores:
            return 0.0
        
        # 返回平均匹配分数
        return sum(match_scores) / len(match_scores)
    
    def _load_sentry_policy_data(self) -> Dict[str, Any]:
        """加载哨兵政策数据 (模拟)"""
        # 实际应从哨兵模块获取
        # 这里使用静态数据模拟
        sentry_data = {
            "policy_keywords": {
                "数据要素": {"weight": 0.95, "source": "国家数据局"},
                "杭州数据交易所": {"weight": 0.85, "source": "杭州政策"},
                "三年行动计划": {"weight": 0.90, "source": "国家政策"},
            },
            "hot_policies": [
                {"policy": "数据要素×三年行动计划", "weight": 0.92, "date": "2026-04-07"},
                {"policy": "杭州中国数谷建设", "weight": 0.88, "date": "2026-04-07"},
                {"policy": "算力基础设施投资", "weight": 0.85, "date": "2026-04-06"},
            ],
            "matched_companies": [
                {"ticker": "600633", "name": "浙数文化", "match_score": 0.89},
                {"ticker": "000938", "name": "紫光股份", "match_score": 0.76},
                {"ticker": "688256", "name": "寒武纪", "match_score": 0.71},
            ]
        }
        
        return sentry_data
    
    def analyze(self, 
                ticker: str,
                history_data: Dict[str, Any],
                analysis_data: Optional[Dict[str, Any]] = None,
                global_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        政策感知分析
        
        逻辑:
        1. 提取标的业务关键词
        2. 计算与政策关键词的匹配度
        3. 匹配度 > 85% 时，赋予 1.2x 动量乘数
        4. 输出政策共振信号
        """
        # 验证数据充足性
        valid, message = self.validate_data_sufficiency(history_data)
        if not valid:
            return self.create_result(
                hit=False,
                score=0.0,
                confidence=0.0,
                signals=[f"数据不足: {message}"],
                metadata={"error": message}
            )
        
        try:
            # 1. 提取业务关键词
            business_keywords = self._extract_business_keywords(ticker, history_data)
            
            # 2. 计算政策匹配度
            policy_match_score = self._calculate_policy_match_score(business_keywords)
            
            # 3. 加载哨兵政策数据
            sentry_data = self._load_sentry_policy_data()
            
            # 4. 判断是否命中
            hit = policy_match_score > 0.85  # 匹配度阈值
            
            # 5. 计算得分 (0-100)
            # 基础得分 = 匹配度 * 100
            base_score = policy_match_score * 100
            
            # 应用动量乘数
            momentum_multiplier = 1.2 if hit else 1.0
            final_score = min(100.0, base_score * momentum_multiplier)
            
            # 6. 计算置信度
            confidence = min(1.0, policy_match_score * 1.2)  # 匹配度越高，置信度越高
            
            # 7. 生成信号
            signals = []
            if hit:
                signals.append(f"强政策共振: 匹配度{policy_match_score:.1%} > 85%")
                signals.append(f"动量乘数: {momentum_multiplier:.1f}x")
            else:
                signals.append(f"政策匹配度: {policy_match_score:.1%} (未达阈值)")
            
            # 添加具体匹配信息
            if business_keywords:
                signals.append(f"业务关键词: {', '.join(business_keywords[:3])}")
            
            # 添加热点政策信息
            hot_policies = sentry_data.get("hot_policies", [])[:2]
            for policy in hot_policies:
                signals.append(f"热点政策: {policy['policy']} (权重: {policy['weight']})")
            
            # 8. 元数据
            metadata = {
                "policy_match_score": policy_match_score,
                "business_keywords": business_keywords,
                "momentum_multiplier": momentum_multiplier,
                "hit_threshold": 0.85,
                "policy_source": "哨兵数据模拟",
                "matched_keywords": list(self.policy_keywords.keys())[:5],
                "sentry_data_available": True,
            }
            
            # 9. 创建结果
            result = self.create_result(
                hit=hit,
                score=final_score,
                confidence=confidence,
                signals=signals,
                metadata=metadata
            )
            
            return result
            
        except Exception as e:
            error_msg = f"政策感知分析失败: {str(e)}"
            return self.create_result(
                hit=False,
                score=0.0,
                confidence=0.0,
                signals=[error_msg],
                metadata={"error": str(e)}
            )


# 策略工厂函数
def create_strategy():
    """创建策略实例 - 供共振引擎调用"""
    return PolicyResonanceStrategy()