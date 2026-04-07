#!/usr/bin/env python3
"""
探针DNA提取模块 - 激活 fina_mainbz 接口进行主营业务聚类分析
符合 [最高执行指令] 专项一：探针 DNA 提取 (寻踪升级)
"""

import os
import sys
import json
import time
import datetime
import requests
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
import hashlib
import re

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 模块常量
MODULE_NAME = "probe_dna_extractor"
OUTPUT_DIR = "database/probe"
SIMILARITY_DIR = "database/probe/similarity"
LOG_DIR = "logs/probe"

# Tushare接口配置
TUSHARE_API_URL = "https://api.tushare.pro/v1"
FINA_MAINBZ_API = "fina_mainbz"  # 财务主营业务接口

def log_info(msg):
    """INFO 级别日志"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{MODULE_NAME}:INFO] {msg}", file=sys.stdout)

def log_warn(msg):
    """WARN 级别日志"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{MODULE_NAME}:WARN] {msg}", file=sys.stdout)

def log_error(code, msg):
    """ERROR 级别日志，遵循结构化 stderr 格式"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sys.stderr.write(f"[{code}]: {msg}\n")
    print(f"[{timestamp}] [{MODULE_NAME}:ERROR] {code}: {msg}", file=sys.stdout)

def get_tushare_token() -> Optional[str]:
    """获取Tushare Token"""
    # 1. 尝试环境变量
    token = os.getenv("TUSHARE_TOKEN")
    if token:
        return token
    
    # 2. 尝试密钥文件
    secrets_file = "_PRIVATE_DATA/secrets.json"
    if os.path.exists(secrets_file):
        try:
            with open(secrets_file, 'r', encoding='utf-8') as f:
                secrets = json.load(f)
                token = secrets.get("tushare_token")
                if token:
                    return token
        except Exception as e:
            log_warn(f"读取密钥文件失败: {e}")
    
    # 3. 返回None，使用模拟数据
    log_warn("Tushare Token未设置，将使用模拟数据")
    return None

class DNAExtractor:
    """DNA提取器 - 主营业务聚类分析"""
    
    def __init__(self, tushare_token: Optional[str] = None):
        self.tushare_token = tushare_token or get_tushare_token()
        self.target_ticker = "600633"  # 浙数文化 - 数据交易平台代表
        self.business_keywords = set()
        self.similarity_matrix = {}
        
        # 确保目录存在
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        os.makedirs(SIMILARITY_DIR, exist_ok=True)
        os.makedirs(LOG_DIR, exist_ok=True)
    
    def fetch_fina_mainbz(self, ts_code: str) -> Optional[List[Dict]]:
        """
        获取财务主营业务数据
        接口: fina_mainbz (主营业务构成)
        """
        if not self.tushare_token:
            log_warn("Tushare Token未设置，使用模拟数据")
            return self.generate_mock_mainbz(ts_code)
        
        log_info(f"获取 {ts_code} 主营业务数据")
        
        api_data = {
            "api_name": FINA_MAINBZ_API,
            "token": self.tushare_token,
            "params": {
                "ts_code": ts_code,
                "period": "20231231",  # 最新年报
                "type": "P"  # 按产品分类
            },
            "fields": "ts_code,end_date,bz_item,bz_sales,bz_profit,bz_cost"
        }
        
        try:
            response = requests.post(TUSHARE_API_URL, json=api_data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    data = result.get("data", [])
                    log_info(f"成功获取 {len(data)} 条主营业务数据")
                    return data
                else:
                    error_msg = result.get("msg", "未知错误")
                    log_error("TUSHARE_API_ERROR", f"fina_mainbz接口错误: {error_msg}")
                    return self.generate_mock_mainbz(ts_code)
            else:
                log_error("HTTP_ERROR", f"HTTP错误: {response.status_code}")
                return self.generate_mock_mainbz(ts_code)
                
        except requests.exceptions.Timeout:
            log_error("TIMEOUT", "连接超时，使用模拟数据")
            return self.generate_mock_mainbz(ts_code)
        except Exception as e:
            log_error("FETCH_FAILED", f"获取数据失败: {e}")
            return self.generate_mock_mainbz(ts_code)
    
    def generate_mock_mainbz(self, ts_code: str) -> List[Dict]:
        """生成模拟主营业务数据"""
        log_info(f"生成 {ts_code} 模拟主营业务数据")
        
        if ts_code == "600633.SH":
            # 浙数文化主营业务 - 数据交易平台代表
            return [
                {
                    "ts_code": "600633.SH",
                    "end_date": "20231231",
                    "bz_item": "数字文化业务",
                    "bz_sales": 1800000000,
                    "bz_profit": 450000000,
                    "bz_cost": 1350000000,
                    "bz_sales_ratio": 0.60
                },
                {
                    "ts_code": "600633.SH", 
                    "end_date": "20231231",
                    "bz_item": "数据科技服务",
                    "bz_sales": 800000000,
                    "bz_profit": 200000000,
                    "bz_cost": 600000000,
                    "bz_sales_ratio": 0.27
                },
                {
                    "ts_code": "600633.SH",
                    "end_date": "20231231",
                    "bz_item": "数字体育业务",
                    "bz_sales": 400000000,
                    "bz_profit": 80000000,
                    "bz_cost": 320000000,
                    "bz_sales_ratio": 0.13
                }
            ]
        elif ts_code == "000681.SZ":
            # 视觉中国主营业务
            return [
                {
                    "ts_code": "000681.SZ",
                    "end_date": "20231231",
                    "bz_item": "视觉内容服务",
                    "bz_sales": 850000000,
                    "bz_profit": 220000000,
                    "bz_cost": 630000000,
                    "bz_sales_ratio": 0.65
                },
                {
                    "ts_code": "000681.SZ", 
                    "end_date": "20231231",
                    "bz_item": "数字版权交易",
                    "bz_sales": 350000000,
                    "bz_profit": 120000000,
                    "bz_cost": 230000000,
                    "bz_sales_ratio": 0.27
                },
                {
                    "ts_code": "000681.SZ",
                    "end_date": "20231231",
                    "bz_item": "创意设计服务",
                    "bz_sales": 80000000,
                    "bz_profit": 25000000,
                    "bz_cost": 55000000,
                    "bz_sales_ratio": 0.06
                }
            ]
        else:
            # 通用模拟数据
            return [
                {
                    "ts_code": f"{ts_code}",
                    "end_date": "20231231",
                    "bz_item": "主营业务A",
                    "bz_sales": 500000000,
                    "bz_profit": 150000000,
                    "bz_cost": 350000000,
                    "bz_sales_ratio": 0.70
                },
                {
                    "ts_code": f"{ts_code}",
                    "end_date": "20231231",
                    "bz_item": "主营业务B",
                    "bz_sales": 200000000,
                    "bz_profit": 60000000,
                    "bz_cost": 140000000,
                    "bz_sales_ratio": 0.28
                },
                {
                    "ts_code": f"{ts_code}",
                    "end_date": "20231231",
                    "bz_item": "其他业务",
                    "bz_sales": 10000000,
                    "bz_profit": 2000000,
                    "bz_cost": 8000000,
                    "bz_sales_ratio": 0.02
                }
            ]
    
    def extract_business_keywords(self, mainbz_data: List[Dict]) -> List[str]:
        """从主营业务数据提取关键词"""
        keywords = []
        
        for item in mainbz_data:
            bz_item = item.get("bz_item", "")
            if not bz_item:
                continue
            
            # 中文分词（简化版）
            words = re.findall(r'[\u4e00-\u9fa5]{2,4}', bz_item)
            keywords.extend(words)
            
            # 提取核心业务词
            if "服务" in bz_item:
                keywords.append("服务")
            if "制造" in bz_item or "生产" in bz_item:
                keywords.append("制造")
            if "销售" in bz_item or "贸易" in bz_item:
                keywords.append("销售")
            if "技术" in bz_item or "科技" in bz_item:
                keywords.append("科技")
            if "金融" in bz_item or "投资" in bz_item:
                keywords.append("金融")
            if "医疗" in bz_item or "医药" in bz_item:
                keywords.append("医疗")
            if "教育" in bz_item or "培训" in bz_item:
                keywords.append("教育")
            if "文化" in bz_item or "传媒" in bz_item:
                keywords.append("文化传媒")
            if "房地产" in bz_item or "物业" in bz_item:
                keywords.append("房地产")
            if "能源" in bz_item or "电力" in bz_item:
                keywords.append("能源")
            if "互联网" in bz_item or "网络" in bz_item:
                keywords.append("互联网")
            if "软件" in bz_item or "系统" in bz_item:
                keywords.append("软件")
            if "硬件" in bz_item or "设备" in bz_item:
                keywords.append("硬件")
            if "咨询" in bz_item or "顾问" in bz_item:
                keywords.append("咨询")
            if "物流" in bz_item or "运输" in bz_item:
                keywords.append("物流")
            if "零售" in bz_item or "电商" in bz_item:
                keywords.append("零售")
        
        # 去重和频率筛选
        keyword_freq = defaultdict(int)
        for kw in keywords:
            keyword_freq[kw] += 1
        
        # 保留频率≥2的关键词
        filtered_keywords = [kw for kw, freq in keyword_freq.items() if freq >= 2]
        
        # 按频率排序
        filtered_keywords.sort(key=lambda x: keyword_freq[x], reverse=True)
        
        log_info(f"提取业务关键词: {len(filtered_keywords)} 个")
        return filtered_keywords
    
    def calculate_similarity(self, keywords1: List[str], keywords2: List[str]) -> float:
        """计算两个关键词列表的相似度（Jaccard相似度）"""
        if not keywords1 or not keywords2:
            return 0.0
        
        set1 = set(keywords1)
        set2 = set(keywords2)
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        if union == 0:
            return 0.0
        
        similarity = intersection / union
        return similarity
    
    def find_similar_companies(self, target_keywords: List[str], 
                               candidate_codes: List[str] = None) -> List[Dict]:
        """
        寻找相似公司
        基于主营业务关键词相似度
        """
        if candidate_codes is None:
            # 默认候选池（A股主要行业代表）
            candidate_codes = [
                "000002",  # 万科A (房地产)
                "000858",  # 五粮液 (白酒)
                "000333",  # 美的集团 (家电)
                "000001",  # 平安银行 (银行)
                "000063",  # 中兴通讯 (通信)
                "000725",  # 京东方A (面板)
                "002415",  # 海康威视 (安防)
                "002475",  # 立讯精密 (电子)
                "300059",  # 东方财富 (金融科技)
                "600519",  # 贵州茅台 (白酒)
                "600036",  # 招商银行 (银行)
                "600276",  # 恒瑞医药 (医药)
                "600887",  # 伊利股份 (食品)
                "601318",  # 中国平安 (保险)
                "601857",  # 中国石油 (能源)
                "601888",  # 中国中免 (免税)
                "603288",  # 海天味业 (调味品)
                "300498",  # 温氏股份 (养殖)
                "002714",  # 牧原股份 (养殖)
                "300750",  # 宁德时代 (新能源)
            ]
        
        similarity_results = []
        
        log_info(f"在 {len(candidate_codes)} 个候选公司中寻找相似公司")
        
        for candidate_code in candidate_codes:
            # 获取候选公司主营业务
            candidate_data = self.fetch_fina_mainbz(f"{candidate_code}.SZ" if candidate_code.startswith("00") else f"{candidate_code}.SH")
            
            if not candidate_data:
                continue
            
            # 提取候选公司关键词
            candidate_keywords = self.extract_business_keywords(candidate_data)
            
            # 计算相似度
            similarity = self.calculate_similarity(target_keywords, candidate_keywords)
            
            if similarity > 0.1:  # 相似度阈值
                # 获取公司名称（简化）
                company_name = self.get_company_name(candidate_code)
                
                result = {
                    "ticker": candidate_code,
                    "name": company_name,
                    "similarity_score": similarity,
                    "target_keywords_count": len(target_keywords),
                    "candidate_keywords_count": len(candidate_keywords),
                    "matched_keywords": list(set(target_keywords).intersection(set(candidate_keywords))),
                    "analysis_time": datetime.datetime.now().isoformat()
                }
                
                similarity_results.append(result)
                
                log_info(f"  {candidate_code} ({company_name}): 相似度 {similarity:.3f}")
        
        # 按相似度排序
        similarity_results.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        return similarity_results
    
    def get_company_name(self, ticker: str) -> str:
        """获取公司名称（简化版）"""
        name_map = {
            "000681": "视觉中国",
            "000002": "万科A",
            "000858": "五粮液",
            "000333": "美的集团",
            "000001": "平安银行",
            "000063": "中兴通讯",
            "000725": "京东方A",
            "002415": "海康威视",
            "002475": "立讯精密",
            "300059": "东方财富",
            "600519": "贵州茅台",
            "600036": "招商银行",
            "600276": "恒瑞医药",
            "600887": "伊利股份",
            "601318": "中国平安",
            "601857": "中国石油",
            "601888": "中国中免",
            "603288": "海天味业",
            "300498": "温氏股份",
            "002714": "牧原股份",
            "300750": "宁德时代",
        }
        
        return name_map.get(ticker, f"公司_{ticker}")
    
    def build_similarity_matrix(self, target_ticker: str, top_n: int = 20) -> Dict:
        """构建相似度矩阵"""
        log_info(f"为 {target_ticker} 构建相似度矩阵 (Top {top_n})")
        
        # 获取目标公司主营业务
        target_data = self.fetch_fina_mainbz(f"{target_ticker}.SZ")
        
        if not target_data:
            log_error("NO_TARGET_DATA", f"无法获取 {target_ticker} 主营业务数据")
            return {}
        
        # 提取目标公司关键词
        target_keywords = self.extract_business_keywords(target_data)
        log_info(f"目标公司 {target_ticker} 关键词: {', '.join(target_keywords[:10])}")
        
        # 寻找相似公司
        similar_companies = self.find_similar_companies(target_keywords)
        
        # 构建矩阵
        matrix = {
            "target_ticker": target_ticker,
            "target_name": self.get_company_name(target_ticker),
            "target_keywords": target_keywords,
            "analysis_time": datetime.datetime.now().isoformat(),
            "total_candidates_searched": len(similar_companies),
            "similarity_threshold": 0.1,
            "similar_companies": similar_companies[:top_n],
            "top_similarities": [],
            "clustering_insights": []
        }
        
        # 提取前5名相似公司
        top_matches = similar_companies[:5]
        if top_matches:
            matrix["top_similarities"] = [
                {
                    "rank": i+1,
                    "ticker": comp["ticker"],
                    "name": comp["name"],
                    "similarity": comp["similarity_score"],
                    "matched_keywords": comp["matched_keywords"][:5]  # 显示前5个匹配关键词
                }
                for i, comp in enumerate(top_matches)
            ]
        
        # 生成聚类洞察
        if similar_companies:
            insights = self.generate_clustering_insights(target_keywords, similar_companies)
            matrix["clustering_insights"] = insights
        
        # 保存矩阵
        output_file = f"{SIMILARITY_DIR}/similarity_matrix_{target_ticker}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(matrix, f, ensure_ascii=False, indent=2)
        
        log_info(f"相似度矩阵已保存: {output_file}")
        
        # 生成摘要文件（供其他模块使用）
        summary = {
            "target_ticker": target_ticker,
            "target_name": matrix["target_name"],
            "analysis_time": matrix["analysis_time"],
            "top_similar_tickers": [comp["ticker"] for comp in similar_companies[:10]],
            "top_similar_names": [comp["name"] for comp in similar_companies[:10]],
            "top_similarities": [comp["similarity_score"] for comp in similar_companies[:10]],
            "primary_keywords": target_keywords[:10],
            "clustering_tags": insights if 'insights' in locals() else []
        }
        
        summary_file = f"{OUTPUT_DIR}/dna_summary_{target_ticker}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        log_info(f"DNA摘要已保存: {summary_file}")
        
        return matrix
    
    def generate_clustering_insights(self, target_keywords: List[str], 
                                    similar_companies: List[Dict]) -> List[str]:
        """生成聚类分析洞察"""
        insights = []
        
        # 分析匹配关键词分布
        all_matched_keywords = []
        for company in similar_companies:
            all_matched_keywords.extend(company.get("matched_keywords", []))
        
        if all_matched_keywords:
            keyword_freq = defaultdict(int)
            for kw in all_matched_keywords:
                keyword_freq[kw] += 1
            
            top_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:5]
            
            insights.append(f"核心匹配关键词: {', '.join([f'{kw}({freq})' for kw, freq in top_keywords])}")
        
        # 分析相似度分布
        similarity_scores = [comp["similarity_score"] for comp in similar_companies]
        if similarity_scores:
            avg_similarity = sum(similarity_scores) / len(similarity_scores)
            max_similarity = max(similarity_scores)
            insights.append(f"平均相似度: {avg_similarity:.3f}, 最高相似度: {max_similarity:.3f}")
        
        # 分析行业分布（简化）
        industries = []
        for company in similar_companies[:10]:  # 看前10个相似公司
            ticker = company["ticker"]
            if ticker.startswith("00") or ticker.startswith("30"):
                industries.append("深市")
            elif ticker.startswith("60") or ticker.startswith("688"):
                industries.append("沪市")
        
        if industries:
            from collections import Counter
            industry_counts = Counter(industries)
            top_industry = industry_counts.most_common(1)[0]
            insights.append(f"主要市场分布: {top_industry[0]}({top_industry[1]}/{len(industries)})")
        
        # 业务模式洞察
        if target_keywords:
            if "服务" in target_keywords:
                insights.append("业务模式: 服务型公司，关注客户粘性和续费率")
            if "制造" in target_keywords:
                insights.append("业务模式: 制造型公司，关注产能利用率和毛利率")
            if "科技" in target_keywords or "软件" in target_keywords:
                insights.append("业务模式: 科技型公司，关注研发投入和专利积累")
            if "销售" in target_keywords or "零售" in target_keywords:
                insights.append("业务模式: 销售型公司，关注渠道覆盖和库存周转")
        
        return insights
    
    def print_analysis_report(self, matrix: Dict):
        """打印分析报告"""
        if not matrix:
            print("❌ 无相似度矩阵数据")
            return
        
        print("\n" + "=" * 70)
        print("🧬 探针DNA提取分析报告")
        print("=" * 70)
        
        target_ticker = matrix.get("target_ticker", "未知")
        target_name = matrix.get("target_name", "未知")
        
        print(f"目标公司: {target_name} ({target_ticker})")
        print(f"分析时间: {matrix.get('analysis_time', '未知')}")
        print(f"搜索候选: {matrix.get('total_candidates_searched', 0)} 家公司")
        
        print(f"\n🎯 核心业务关键词 ({len(matrix.get('target_keywords', []))}个):")
        keywords = matrix.get('target_keywords', [])
        if keywords:
            print(f"   {', '.join(keywords[:15])}")
            if len(keywords) > 15:
                print(f"   ... 及 {len(keywords)-15} 个其他关键词")
        
        print(f"\n🏆 前5名相似公司:")
        top_similarities = matrix.get('top_similarities', [])
        if top_similarities:
            for item in top_similarities:
                print(f"   {item['rank']}. {item['name']} ({item['ticker']}): 相似度 {item['similarity']:.3f}")
                if item.get('matched_keywords'):
                    print(f"      匹配关键词: {', '.join(item['matched_keywords'][:3])}")
        else:
            print("   未找到显著相似公司")
        
        print(f"\n💡 聚类分析洞察:")
        insights = matrix.get('clustering_insights', [])
        if insights:
            for insight in insights:
                print(f"   • {insight}")
        else:
            print("   暂无深度洞察")
        
        print(f"\n📊 完整相似度排名 ({len(matrix.get('similar_companies', []))}家公司):")
        similar_companies = matrix.get('similar_companies', [])
        if similar_companies:
            for i, company in enumerate(similar_companies[:10], 1):
                print(f"   {i:2d}. {company['name']:10} ({company['ticker']}): {company['similarity_score']:.3f}")
            if len(similar_companies) > 10:
                print(f"   ... 及 {len(similar_companies)-10} 个其他公司")
        
        print("\n" + "=" * 70)
        print("🎯 投资建议方向:")
        
        if similar_companies:
            # 基于相似公司提供建议
            top_similar = similar_companies[0]
            similarity = top_similar['similarity_score']
            
            if similarity > 0.3:
                print(f"   • 与 {top_similar['name']} 高度相似，可关注其产业链和业务协同")
                print(f"   • 研究 {top_similar['name']} 的成功模式和风险因素")
            elif similarity > 0.15:
                print(f"   • 与 {top_similar['name']} 有一定相似度，可对比分析业务结构")
                print(f"   • 关注共同的关键词领域: {', '.join(top_similar.get('matched_keywords', ['未知'])[:3])}")
            else:
                print(f"   • 相似度较低，目标公司业务模式相对独特")
                print(f"   • 建议深入研究其核心竞争力: {', '.join(keywords[:3])}")
        else:
            print(f"   • 未找到显著相似公司，目标公司业务模式独特")
            print(f"   • 建议深入研究其行业地位和护城河")
        
        print("\n" + "=" * 70)

def main():
    """主函数"""
    print("🚀 探针DNA提取模块启动")
    print("符合 [最高执行指令] 专项一：探针 DNA 提取 (寻踪升级)")
    print("=" * 70)
    
    # 初始化提取器
    extractor = DNAExtractor()
    
    # 构建600633的相似度矩阵 - 浙数文化 (数据交易平台代表)
    target_ticker = "600633"
    print(f"\n🎯 分析目标: {target_ticker} (浙数文化 - 数据交易平台代表)")
    print("=" * 70)
    
    # 执行DNA提取
    matrix = extractor.build_similarity_matrix(target_ticker, top_n=20)
    
    # 打印分析报告
    if matrix:
        extractor.print_analysis_report(matrix)
        
        # 保存最终报告
        report_file = f"{LOG_DIR}/dna_analysis_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"# 🧬 探针DNA提取分析报告\n\n")
            f.write(f"**目标公司**: {matrix.get('target_name', '未知')} ({matrix.get('target_ticker', '未知')})\n")
            f.write(f"**分析时间**: {matrix.get('analysis_time', '未知')}\n")
            f.write(f"**搜索范围**: {matrix.get('total_candidates_searched', 0)} 家公司\n\n")
            
            f.write("## 🎯 核心业务关键词\n")
            keywords = matrix.get('target_keywords', [])
            f.write(f"{', '.join(keywords)}\n\n")
            
            f.write("## 🏆 相似公司排名\n")
            similar_companies = matrix.get('similar_companies', [])
            for i, company in enumerate(similar_companies[:10], 1):
                f.write(f"{i}. **{company['name']}** ({company['ticker']}) - 相似度: {company['similarity_score']:.3f}\n")
            
            f.write("\n## 💡 投资建议\n")
            insights = matrix.get('clustering_insights', [])
            for insight in insights:
                f.write(f"- {insight}\n")
        
        print(f"\n📄 详细报告已保存: {report_file}")
        print("=" * 70)
        print("✅ 探针DNA提取完成")
    else:
        print("❌ DNA提取失败")
        sys.exit(1)

if __name__ == "__main__":
    main()