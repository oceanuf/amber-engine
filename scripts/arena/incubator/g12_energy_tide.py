#!/usr/bin/env python3
"""
G12 能量潮汐评委 (Energy Tide Judge)
影子算法 - 板块级资金流共振检测

核心逻辑: 监控全市场5000只标的的资金流共振强度，识别板块级别的"海啸"信号
解决痛点: 单只股票无法反映板块集体异动
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
import datetime
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.storer.data_contract import get_feature, FeatureResponse

logger = logging.getLogger(__name__)

@dataclass
class EnergyTideConfig:
    """能量潮汐算法配置"""
    # 板块定义
    sectors = {
        "technology": ["计算机", "电子", "通信", "传媒"],
        "finance": ["银行", "非银金融", "房地产"],
        "consumption": ["食品饮料", "家用电器", "商贸零售", "医药生物"],
        "industry": ["机械设备", "化工", "有色金属", "建筑材料"],
        "energy": ["煤炭", "石油石化", "公用事业"],
        "defense": ["国防军工"]
    }
    
    # 资金流参数
    capital_flow_threshold = 0.02  # 资金流变化阈值 (2%)
    resonance_threshold = 0.15  # 共振强度阈值 (15%)
    lookback_days = 20  # 回看天数
    min_sector_coverage = 0.3  # 最小板块覆盖率 (30%)
    
    # 评分参数
    base_score = 50  # 基础评分
    max_sector_bonus = 30  # 最大板块加成
    max_resonance_bonus = 20  # 最大共振加成

@dataclass
class SectorCapitalFlow:
    """板块资金流数据"""
    sector_name: str
    sector_stocks: List[str]
    total_capital_inflow: float  # 总资金流入 (亿元)
    capital_inflow_change: float  # 资金流入变化 (%)
    leading_stocks: List[Dict]  # 领涨股票
    resonance_strength: float  # 共振强度 (0-1)
    sector_score: float  # 板块评分 (0-100)

@dataclass
class EnergyTideAnalysis:
    """能量潮汐分析结果"""
    timestamp: str
    analyzed_sectors: int
    total_capital_flow: float
    strongest_sector: str
    weakest_sector: str
    market_resonance_score: float  # 市场共振评分 (0-100)
    sector_analysis: Dict[str, SectorCapitalFlow]
    signals: List[str]
    confidence: float

class EnergyTideJudge:
    """能量潮汐评委"""
    
    def __init__(self, config: Optional[EnergyTideConfig] = None):
        self.config = config or EnergyTideConfig()
        self.data_contract = None
        self.initialized = False
        
    def initialize(self):
        """初始化算法"""
        try:
            # 初始化数据契约
            from scripts.storer.data_contract import get_data_contract
            self.data_contract = get_data_contract()
            
            logger.info("✅ G12 能量潮汐评委初始化完成")
            logger.info(f"   监控板块: {len(self.config.sectors)}个")
            logger.info(f"   回看天数: {self.config.lookback_days}天")
            
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"❌ G12 初始化失败: {e}")
            return False
    
    def analyze_sector(self, sector_name: str, sector_stocks: List[str]) -> Optional[SectorCapitalFlow]:
        """分析单个板块资金流"""
        if not self.initialized:
            logger.error("G12 未初始化")
            return None
        
        try:
            sector_capital_flows = []
            leading_stocks = []
            
            # 分析板块内每只股票
            for stock in sector_stocks[:10]:  # 限制分析前10只，防止性能问题
                try:
                    # 获取资金流数据
                    response = get_feature(
                        ticker=stock,
                        factor_name="capital_flow",
                        frequency="daily"
                    )
                    
                    if response.success and response.data is not None:
                        # 计算资金流变化
                        if len(response.data) >= 2:
                            current_flow = response.data[-1]
                            previous_flow = response.data[-2] if len(response.data) > 1 else current_flow
                            flow_change = (current_flow - previous_flow) / abs(previous_flow) if previous_flow != 0 else 0
                            
                            sector_capital_flows.append(current_flow)
                            
                            # 识别领涨股
                            if flow_change > self.config.capital_flow_threshold:
                                leading_stocks.append({
                                    "ticker": stock,
                                    "capital_flow": current_flow,
                                    "flow_change": flow_change
                                })
                except Exception as e:
                    logger.warning(f"股票 {stock} 分析失败: {e}")
                    continue
            
            if not sector_capital_flows:
                return None
            
            # 计算板块资金流统计
            total_capital_inflow = sum(sector_capital_flows)
            avg_capital_flow = np.mean(sector_capital_flows)
            std_capital_flow = np.std(sector_capital_flows) if len(sector_capital_flows) > 1 else 0
            
            # 计算资金流变化 (与历史平均比较)
            capital_inflow_change = 0
            if len(sector_capital_flows) > 5:
                recent_avg = np.mean(sector_capital_flows[-5:])
                historical_avg = np.mean(sector_capital_flows[:-5])
                if historical_avg != 0:
                    capital_inflow_change = (recent_avg - historical_avg) / abs(historical_avg)
            
            # 计算共振强度 (板块内股票同步性)
            resonance_strength = 0
            if std_capital_flow > 0:
                # 标准差越小，共振越强
                resonance_strength = 1.0 / (1.0 + std_capital_flow)
            
            # 计算板块评分
            sector_score = self._calculate_sector_score(
                total_capital_inflow=total_capital_inflow,
                capital_inflow_change=capital_inflow_change,
                resonance_strength=resonance_strength,
                leading_stocks_count=len(leading_stocks)
            )
            
            return SectorCapitalFlow(
                sector_name=sector_name,
                sector_stocks=sector_stocks,
                total_capital_inflow=total_capital_inflow,
                capital_inflow_change=capital_inflow_change,
                leading_stocks=leading_stocks[:5],  # 只保留前5只
                resonance_strength=resonance_strength,
                sector_score=sector_score
            )
            
        except Exception as e:
            logger.error(f"板块 {sector_name} 分析失败: {e}")
            return None
    
    def _calculate_sector_score(self, 
                               total_capital_inflow: float,
                               capital_inflow_change: float,
                               resonance_strength: float,
                               leading_stocks_count: int) -> float:
        """计算板块评分"""
        score = self.config.base_score
        
        # 资金流入加成
        inflow_bonus = min(total_capital_inflow / 10.0, 10)  # 每10亿加1分，最多10分
        score += inflow_bonus
        
        # 资金流变化加成
        if capital_inflow_change > 0:
            change_bonus = min(capital_inflow_change * 100, 10)  # 每1%加1分，最多10分
            score += change_bonus
        
        # 共振强度加成
        resonance_bonus = resonance_strength * 15  # 共振强度最高加15分
        score += resonance_bonus
        
        # 领涨股数量加成
        leading_bonus = min(leading_stocks_count * 3, 15)  # 每只领涨股加3分，最多15分
        score += leading_bonus
        
        return min(100, max(0, score))
    
    def analyze_market(self) -> EnergyTideAnalysis:
        """分析全市场能量潮汐"""
        if not self.initialized:
            if not self.initialize():
                raise RuntimeError("G12 初始化失败")
        
        timestamp = datetime.datetime.now().isoformat()
        sector_analysis = {}
        signals = []
        
        logger.info(f"🔍 G12 开始分析全市场能量潮汐...")
        
        # 分析所有板块
        for sector_name, sector_keywords in self.config.sectors.items():
            # 实际实现中，这里需要根据关键词获取板块内股票列表
            # 目前使用模拟数据
            sector_stocks = [f"00000{i}" for i in range(1, 11)]  # 模拟10只股票
            
            sector_result = self.analyze_sector(sector_name, sector_stocks)
            if sector_result:
                sector_analysis[sector_name] = sector_result
                
                # 生成信号
                if sector_result.sector_score >= 70:
                    signals.append(f"板块共振: {sector_name} 评分{sector_result.sector_score:.1f}")
                if sector_result.resonance_strength >= 0.8:
                    signals.append(f"强共振: {sector_name} 共振强度{sector_result.resonance_strength:.2f}")
        
        # 计算市场共振评分
        market_resonance_score = 50
        if sector_analysis:
            sector_scores = [s.sector_score for s in sector_analysis.values()]
            market_resonance_score = np.mean(sector_scores)
        
        # 识别最强和最弱板块
        strongest_sector = ""
        weakest_sector = ""
        if sector_analysis:
            sorted_sectors = sorted(sector_analysis.items(), key=lambda x: x[1].sector_score, reverse=True)
            strongest_sector = sorted_sectors[0][0] if sorted_sectors else ""
            weakest_sector = sorted_sectors[-1][0] if sorted_sectors else ""
        
        # 计算总资金流
        total_capital_flow = sum(s.total_capital_inflow for s in sector_analysis.values())
        
        # 计算置信度
        confidence = min(0.9, 0.5 + len(sector_analysis) / len(self.config.sectors) * 0.4)
        
        analysis = EnergyTideAnalysis(
            timestamp=timestamp,
            analyzed_sectors=len(sector_analysis),
            total_capital_flow=total_capital_flow,
            strongest_sector=strongest_sector,
            weakest_sector=weakest_sector,
            market_resonance_score=market_resonance_score,
            sector_analysis=sector_analysis,
            signals=signals,
            confidence=confidence
        )
        
        logger.info(f"✅ G12 市场分析完成")
        logger.info(f"   分析板块: {len(sector_analysis)}/{len(self.config.sectors)}")
        logger.info(f"   市场共振评分: {market_resonance_score:.1f}")
        logger.info(f"   最强板块: {strongest_sector}")
        logger.info(f"   信号数量: {len(signals)}")
        
        return analysis
    
    def score_ticker(self, ticker: str, sector: str = None) -> Dict:
        """
        为单个标的评分
        
        参数:
            ticker: 标的代码
            sector: 所属板块 (如果为None则自动判断)
            
        返回:
            {
                "score": 评分 (0-100),
                "confidence": 置信度 (0-1),
                "signals": 信号列表,
                "sector_alignment": 板块对齐度 (0-1),
                "capital_flow_strength": 资金流强度
            }
        """
        if not self.initialized:
            if not self.initialize():
                return {"score": 0, "confidence": 0, "signals": ["算法未初始化"]}
        
        try:
            # 获取板块信息
            if sector is None:
                sector = self._identify_sector(ticker)
            
            # 分析市场获取当前板块状态
            market_analysis = self.analyze_market()
            
            # 获取该板块分析
            sector_analysis = market_analysis.sector_analysis.get(sector)
            
            # 基础评分
            score = 50
            signals = []
            confidence = 0.5
            
            if sector_analysis:
                # 基于板块状态调整评分
                score = sector_analysis.sector_score
                
                # 板块共振信号
                if sector_analysis.resonance_strength >= 0.7:
                    score += 10
                    signals.append(f"板块共振强度: {sector_analysis.resonance_strength:.2f}")
                
                if sector_analysis.capital_inflow_change > 0.05:
                    score += 15
                    signals.append(f"板块资金流入增长: {sector_analysis.capital_inflow_change:.1%}")
                
                # 检查是否为领涨股
                is_leading = any(ls["ticker"] == ticker for ls in sector_analysis.leading_stocks)
                if is_leading:
                    score += 20
                    signals.append("板块领涨股")
                
                confidence = 0.7 + sector_analysis.resonance_strength * 0.3
            
            # 限制评分范围
            score = min(100, max(0, score))
            
            return {
                "score": score,
                "confidence": confidence,
                "signals": signals,
                "sector": sector,
                "sector_score": sector_analysis.sector_score if sector_analysis else 0,
                "resonance_strength": sector_analysis.resonance_strength if sector_analysis else 0,
                "is_leading": is_leading if 'is_leading' in locals() else False
            }
            
        except Exception as e:
            logger.error(f"标的 {ticker} 评分失败: {e}")
            return {
                "score": 0,
                "confidence": 0.1,
                "signals": [f"评分失败: {str(e)}"],
                "sector": sector or "unknown",
                "error": str(e)
            }
    
    def _identify_sector(self, ticker: str) -> str:
        """识别标的所属板块"""
        # 实际实现中需要根据标的特征识别板块
        # 目前使用简单映射
        sector_mapping = {
            "000001": "finance",
            "000002": "finance", 
            "000063": "technology",
            "000066": "technology",
            "000858": "consumption",
            "000568": "consumption",
            "000725": "industry",
            "000792": "energy",
            "000768": "defense"
        }
        
        return sector_mapping.get(ticker, "unknown")
    
    def get_algorithm_info(self) -> Dict:
        """获取算法信息"""
        return {
            "algorithm_id": "G12",
            "algorithm_name": "能量潮汐评委",
            "version": "1.0.0",
            "description": "监控全市场资金流共振强度，识别板块级别'海啸'信号",
            "solved_pain_point": "单只股票无法反映板块集体异动",
            "status": "incubator",
            "initialized": self.initialized,
            "config": asdict(self.config) if hasattr(self.config, '__dict__') else {}
        }

# 测试函数
def test_energy_tide():
    """测试能量潮汐算法"""
    print("🧪 测试 G12 能量潮汐评委...")
    
    judge = EnergyTideJudge()
    
    # 初始化
    if not judge.initialize():
        print("❌ 初始化失败")
        return False
    
    # 获取算法信息
    info = judge.get_algorithm_info()
    print(f"   算法ID: {info['algorithm_id']}")
    print(f"   算法名称: {info['algorithm_name']}")
    print(f"   状态: {info['status']}")
    
    # 分析市场
    print("\n🔍 分析全市场能量潮汐...")
    market_analysis = judge.analyze_market()
    
    print(f"   分析板块: {market_analysis.analyzed_sectors}")
    print(f"   市场共振评分: {market_analysis.market_resonance_score:.1f}")
    print(f"   最强板块: {market_analysis.strongest_sector}")
    print(f"   总资金流: {market_analysis.total_capital_flow:.1f}亿")
    print(f"   信号数量: {len(market_analysis.signals)}")
    
    # 测试单个标的评分
    print("\n🎯 测试标的评分...")
    test_tickers = ["000001", "000063", "000858"]
    
    for ticker in test_tickers:
        result = judge.score_ticker(ticker)
        print(f"   {ticker}: {result['score']:.1f}分 (置信度: {result['confidence']:.2f})")
        if result['signals']:
            print(f"     信号: {', '.join(result['signals'][:2])}")
    
    return True

if __name__ == "__main__":
    success = test_energy_tide()
    if success:
        print("\n✅ G12 能量潮汐评委测试通过")
    else:
        print("\n❌ G12 能量潮汐评委测试失败")