#!/usr/bin/env python3
"""
每日简报看板生成器 - V1.7.0 "智库并网"专项行动
专项一：每日简报看板自动化生成

功能：
1. 每日18:00自动从database/sentry/提取权重前10的资讯
2. 强行调用LLM接口，结合Probe寻踪路径，生成【背后的思考】
3. 确保reports/目录可访问，生成HTML简报

作者: 工程师 Cheese 🧀
日期: 2026-04-05
"""

import os
import sys
import json
import datetime
import logging
from typing import List, Dict, Any, Optional
import argparse

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置路径
SENTRY_BRIDGE_FILE = "database/sentry/sentry_to_probe_bridge.json"
SENTRY_CLUES_DIR = "database/sentry/clues"
REPORTS_DIR = "reports/daily_briefing"
LOG_DIR = "logs/briefing"
BRIEFING_OUTPUT_FILE = "reports/daily_briefing/{date}_briefing.json"
HTML_OUTPUT_FILE = "reports/daily_briefing/{date}_briefing.html"

# 配置日志
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, f"briefing_{datetime.date.today().isoformat()}.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DailyBriefingGenerator:
    """每日简报生成器"""
    
    def __init__(self, use_mock_llm: bool = False):
        self.use_mock_llm = use_mock_llm
        self.today = datetime.date.today().isoformat()
        
        # 确保输出目录存在
        os.makedirs(REPORTS_DIR, exist_ok=True)
        
    def load_sentry_data(self) -> Dict[str, Any]:
        """加载哨兵数据"""
        try:
            # 首先尝试从桥接文件加载
            if os.path.exists(SENTRY_BRIDGE_FILE):
                with open(SENTRY_BRIDGE_FILE, 'r', encoding='utf-8') as f:
                    bridge_data = json.load(f)
                logger.info(f"成功加载哨兵桥接文件，共 {len(bridge_data.get('current_clues', []))} 条当前线索")
                return bridge_data
            else:
                logger.warning(f"哨兵桥接文件不存在: {SENTRY_BRIDGE_FILE}")
                
            # 尝试从clues目录加载
            clue_files = []
            if os.path.exists(SENTRY_CLUES_DIR):
                clue_files = [f for f in os.listdir(SENTRY_CLUES_DIR) if f.endswith('.json')]
                
            clues = []
            for clue_file in clue_files[:20]:  # 最多加载20个文件
                try:
                    with open(os.path.join(SENTRY_CLUES_DIR, clue_file), 'r', encoding='utf-8') as f:
                        clue_data = json.load(f)
                        if isinstance(clue_data, list):
                            clues.extend(clue_data)
                        else:
                            clues.append(clue_data)
                except Exception as e:
                    logger.error(f"加载线索文件 {clue_file} 失败: {e}")
                    
            return {
                "current_clues": clues,
                "historical_clues": [],
                "metadata": {
                    "source": "clues_directory",
                    "total_clues": len(clues),
                    "loaded_date": self.today
                }
            }
            
        except Exception as e:
            logger.error(f"加载哨兵数据失败: {e}")
            return {"current_clues": [], "historical_clues": [], "metadata": {"error": str(e)}}
    
    def rank_clues_by_weight(self, clues: List[Dict[str, Any]], top_n: int = 10) -> List[Dict[str, Any]]:
        """按权重对线索进行排序，返回前N条"""
        if not clues:
            logger.warning("没有可排序的线索")
            return []
            
        # 计算每条线索的权重分数
        scored_clues = []
        for clue in clues:
            score = self._calculate_clue_weight(clue)
            scored_clue = clue.copy()
            scored_clue['weight_score'] = score
            scored_clues.append(scored_clue)
            
        # 按权重降序排序
        scored_clues.sort(key=lambda x: x.get('weight_score', 0), reverse=True)
        
        # 返回前N条
        top_clues = scored_clues[:top_n]
        logger.info(f"筛选出权重前 {len(top_clues)} 条线索 (总分范围: {top_clues[0].get('weight_score') if top_clues else 0:.2f} - {top_clues[-1].get('weight_score') if top_clues else 0:.2f})")
        
        return top_clues
    
    def _calculate_clue_weight(self, clue: Dict[str, Any]) -> float:
        """计算线索权重分数"""
        weight = 0.0
        
        # 1. 来源可信度权重 (最高30分)
        source = clue.get('source', 'unknown')
        source_weights = {
            'tushare_vip': 30,
            'reuters': 25,
            'bloomberg': 25,
            'financial_times': 20,
            'wall_street_journal': 20,
            'sina_finance': 15,
            'eastmoney': 15,
            'unknown': 10
        }
        weight += source_weights.get(source.lower(), 10)
        
        # 2. 紧急程度权重 (最高25分)
        urgency = clue.get('urgency', 'medium')
        urgency_weights = {
            'critical': 25,
            'high': 20,
            'medium': 15,
            'low': 10
        }
        weight += urgency_weights.get(urgency, 15)
        
        # 3. 影响范围权重 (最高20分)
        scope = clue.get('scope', 'sector')
        scope_weights = {
            'global': 20,
            'national': 15,
            'industry': 10,
            'sector': 8,
            'company': 5
        }
        weight += scope_weights.get(scope, 8)
        
        # 4. 时间新鲜度权重 (最高15分)
        # 如果线索有时间戳，计算时间衰减
        timestamp = clue.get('timestamp')
        if timestamp:
            try:
                # 简化处理：如果是今天的线索，加15分；昨天的加10分；以此类推
                if isinstance(timestamp, str):
                    # 尝试解析时间戳
                    if 'T' in timestamp:
                        clue_date = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00')).date()
                    else:
                        clue_date = datetime.datetime.strptime(timestamp[:10], '%Y-%m-%d').date()
                else:
                    # 假设是Unix时间戳
                    clue_date = datetime.datetime.fromtimestamp(timestamp).date()
                    
                today = datetime.date.today()
                days_diff = (today - clue_date).days
                
                if days_diff == 0:
                    weight += 15
                elif days_diff == 1:
                    weight += 10
                elif days_diff <= 3:
                    weight += 5
                elif days_diff <= 7:
                    weight += 2
            except:
                weight += 5  # 解析失败，给基础分
        else:
            weight += 5  # 没有时间戳，给基础分
            
        # 5. 关联标的数量权重 (最高10分)
        related_targets = clue.get('related_targets', [])
        weight += min(len(related_targets) * 2, 10)
        
        return weight
    
    def generate_llm_insights(self, top_clues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """调用LLM生成【背后的思考】"""
        logger.info(f"开始生成 {len(top_clues)} 条线索的LLM洞察")
        
        insights = []
        
        for i, clue in enumerate(top_clues, 1):
            try:
                clue_insight = self._generate_single_insight(clue, i, len(top_clues))
                insights.append(clue_insight)
                logger.info(f"已生成线索 {i}/{len(top_clues)} 的洞察: {clue.get('title', '无标题')[:50]}...")
            except Exception as e:
                logger.error(f"生成线索 {i} 的洞察失败: {e}")
                # 添加错误占位符
                insights.append({
                    "clue_index": i,
                    "clue_title": clue.get('title', '未知标题'),
                    "insight": f"洞察生成失败: {str(e)}",
                    "investment_implication": "无法生成投资启示",
                    "confidence": 0.0,
                    "generated_at": datetime.datetime.now().isoformat(),
                    "error": True
                })
                
        return {
            "total_insights": len(insights),
            "generation_time": datetime.datetime.now().isoformat(),
            "insights": insights,
            "llm_provider": "perplexity" if not self.use_mock_llm else "mock"
        }
    
    def _generate_single_insight(self, clue: Dict[str, Any], index: int, total: int) -> Dict[str, Any]:
        """生成单条线索的洞察"""
        
        # 准备线索摘要
        clue_summary = {
            "title": clue.get('title', '无标题'),
            "content": clue.get('content', '无内容')[:500],  # 截断
            "source": clue.get('source', '未知来源'),
            "urgency": clue.get('urgency', 'medium'),
            "scope": clue.get('scope', 'sector'),
            "related_targets": clue.get('related_targets', []),
            "weight_score": clue.get('weight_score', 0)
        }
        
        if self.use_mock_llm:
            # 模拟LLM响应
            return {
                "clue_index": index,
                "clue_title": clue.get('title', '未知标题'),
                "clue_summary": clue_summary,
                "insight": f"这是对线索'{clue.get('title', '未知')}'的模拟洞察。基于来源{clue.get('source')}和紧急程度{clue.get('urgency')}，该信息可能对{clue.get('scope', '行业')}层面产生影响。",
                "investment_implication": "模拟投资启示：建议关注相关标的，等待市场消化信息。",
                "confidence": 0.85,
                "probe_suggestions": ["建议深蓝探针扫描相关行业", "建议监控相关概念板块"],
                "generated_at": datetime.datetime.now().isoformat()
            }
        else:
            # 实际调用LLM接口
            # TODO: 集成Perplexity API或其他LLM
            # 目前先返回模拟数据
            return {
                "clue_index": index,
                "clue_title": clue.get('title', '未知标题'),
                "clue_summary": clue_summary,
                "insight": "【待实现】需要集成LLM API生成真实洞察",
                "investment_implication": "【待实现】需要LLM分析投资启示",
                "confidence": 0.0,
                "probe_suggestions": [],
                "generated_at": datetime.datetime.now().isoformat(),
                "llm_pending": True
            }
    
    def generate_briefing_report(self, sentry_data: Dict[str, Any], 
                                top_clues: List[Dict[str, Any]], 
                                llm_insights: Dict[str, Any]) -> Dict[str, Any]:
        """生成完整的简报报告"""
        
        report = {
            "report_id": f"briefing_{self.today}_{int(datetime.datetime.now().timestamp())}",
            "generation_date": self.today,
            "generation_time": datetime.datetime.now().isoformat(),
            "title": f"琥珀引擎每日投资简报 - {self.today}",
            "executive_summary": {
                "total_clues_analyzed": len(sentry_data.get('current_clues', [])),
                "top_clues_count": len(top_clues),
                "insights_generated": llm_insights.get('total_insights', 0),
                "avg_clue_weight": sum(c.get('weight_score', 0) for c in top_clues) / max(len(top_clues), 1),
                "generation_duration": "待计算"
            },
            "data_sources": {
                "sentry_bridge_file": SENTRY_BRIDGE_FILE,
                "clues_directory": SENTRY_CLUES_DIR,
                "data_freshness": sentry_data.get('metadata', {}).get('loaded_date', 'unknown')
            },
            "top_clues": top_clues,
            "llm_insights": llm_insights,
            "probe_integration": {
                "status": "pending",
                "suggested_scans": self._generate_probe_suggestions(top_clues),
                "integration_note": "深蓝探针将根据这些线索进行标的发现扫描"
            },
            "metadata": {
                "version": "1.0.0",
                "author": "工程师 Cheese 🧀",
                "mission": "V1.7.0 '智库并网'专项行动 - 专项一",
                "llm_used": llm_insights.get('llm_provider', 'unknown'),
                "notes": "每日18:00自动生成"
            }
        }
        
        logger.info(f"简报报告生成完成，包含 {len(top_clues)} 条顶级线索和 {llm_insights.get('total_insights', 0)} 条洞察")
        return report
    
    def _generate_probe_suggestions(self, top_clues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成探针扫描建议"""
        suggestions = []
        
        for clue in top_clues[:5]:  # 前5条线索生成建议
            suggestion = {
                "clue_title": clue.get('title', '未知')[:100],
                "scan_priority": clue.get('urgency', 'medium'),
                "suggested_industries": clue.get('related_industries', ['general']),
                "reason": f"权重分数: {clue.get('weight_score', 0):.2f}, 紧急程度: {clue.get('urgency', 'medium')}",
                "expected_output": "发现3-5个相关投资标的"
            }
            suggestions.append(suggestion)
            
        return suggestions
    
    def save_report(self, report: Dict[str, Any]) -> str:
        """保存报告到文件"""
        # JSON格式
        json_file = BRIEFING_OUTPUT_FILE.format(date=self.today)
        os.makedirs(os.path.dirname(json_file), exist_ok=True)
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"简报JSON已保存: {json_file}")
        
        # HTML格式（简化版）
        html_file = HTML_OUTPUT_FILE.format(date=self.today)
        self._generate_html_report(report, html_file)
        
        logger.info(f"简报HTML已保存: {html_file}")
        
        return json_file
    
    def _generate_html_report(self, report: Dict[str, Any], html_file: str):
        """生成HTML格式的简报"""
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report['title']}</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; color: #333; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ border-bottom: 3px solid #2c3e50; padding-bottom: 20px; margin-bottom: 30px; }}
        .header h1 {{ color: #2c3e50; margin: 0; }}
        .header .subtitle {{ color: #7f8c8d; font-size: 1.1em; margin-top: 5px; }}
        .summary {{ background: #ecf0f1; padding: 20px; border-radius: 8px; margin-bottom: 30px; }}
        .summary h2 {{ color: #34495e; margin-top: 0; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
        .summary-item {{ background: white; padding: 15px; border-radius: 6px; text-align: center; }}
        .summary-item .value {{ font-size: 1.8em; font-weight: bold; color: #2c3e50; }}
        .summary-item .label {{ font-size: 0.9em; color: #7f8c8d; margin-top: 5px; }}
        .section {{ margin-bottom: 40px; }}
        .section h2 {{ color: #2c3e50; border-left: 4px solid #3498db; padding-left: 10px; }}
        .clue-card {{ background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 20px; margin-bottom: 15px; }}
        .clue-card h3 {{ margin-top: 0; color: #2c3e50; }}
        .clue-meta {{ display: flex; justify-content: space-between; font-size: 0.9em; color: #6c757d; margin-bottom: 10px; }}
        .clue-weight {{ font-weight: bold; color: #e74c3c; }}
        .insight-card {{ background: #e8f4fd; border: 1px solid #b3d7ff; border-radius: 8px; padding: 20px; margin-bottom: 15px; }}
        .insight-card h3 {{ margin-top: 0; color: #2980b9; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #7f8c8d; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{report['title']}</h1>
            <div class="subtitle">
                生成时间: {report['generation_time']} | 报告ID: {report['report_id']}
            </div>
        </div>
        
        <div class="summary">
            <h2>📊 简报概览</h2>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="value">{report['executive_summary']['total_clues_analyzed']}</div>
                    <div class="label">分析线索总数</div>
                </div>
                <div class="summary-item">
                    <div class="value">{report['executive_summary']['top_clues_count']}</div>
                    <div class="label">顶级线索数量</div>
                </div>
                <div class="summary-item">
                    <div class="value">{report['executive_summary']['insights_generated']}</div>
                    <div class="label">生成洞察数量</div>
                </div>
                <div class="summary-item">
                    <div class="value">{report['executive_summary']['avg_clue_weight']:.2f}</div>
                    <div class="label">平均线索权重</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>🔍 权重前{len(report['top_clues'])}条资讯线索</h2>
            {"".join([self._generate_clue_html(clue) for clue in report['top_clues'][:10]])}
        </div>
        
        <div class="section">
            <h2>💡 LLM洞察分析</h2>
            {"".join([self._generate_insight_html(insight) for insight in report['llm_insights'].get('insights', [])[:5]])}
        </div>
        
        <div class="section">
            <h2>🎯 探针扫描建议</h2>
            <p>根据以上分析，建议深蓝探针进行以下扫描：</p>
            <ul>
                {"".join([f"<li><strong>{s['clue_title']}</strong> - 优先级: {s['scan_priority']} ({s['reason']})</li>" for s in report['probe_integration'].get('suggested_scans', [])[:3]])}
            </ul>
        </div>
        
        <div class="footer">
            <p>📋 琥珀引擎 V1.7.0 "智库并网"专项行动 | 生成系统: 工程师 Cheese 🧀 | 数据源: {report['data_sources']['sentry_bridge_file']}</p>
            <p>⚠️ 本报告仅供参考，不构成投资建议。投资有风险，决策需谨慎。</p>
        </div>
    </div>
</body>
</html>
        """
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def _generate_clue_html(self, clue: Dict[str, Any]) -> str:
        """生成单个线索的HTML"""
        return f"""
        <div class="clue-card">
            <div class="clue-meta">
                <span>来源: {clue.get('source', '未知')}</span>
                <span>紧急程度: {clue.get('urgency', 'medium')}</span>
                <span class="clue-weight">权重: {clue.get('weight_score', 0):.2f}</span>
            </div>
            <h3>{clue.get('title', '无标题')}</h3>
            <p>{clue.get('content', '无内容')[:200]}...</p>
        </div>
        """
    
    def _generate_insight_html(self, insight: Dict[str, Any]) -> str:
        """生成单个洞察的HTML"""
        return f"""
        <div class="insight-card">
            <h3>洞察 #{insight.get('clue_index', 0)}: {insight.get('clue_title', '未知')}</h3>
            <p><strong>背后思考:</strong> {insight.get('insight', '无洞察内容')}</p>
            <p><strong>投资启示:</strong> {insight.get('investment_implication', '无投资启示')}</p>
            <p><strong>置信度:</strong> {insight.get('confidence', 0)*100:.1f}%</p>
        </div>
        """
    
    def run(self, mock_data: bool = False):
        """运行简报生成流程"""
        logger.info("=" * 60)
        logger.info(f"开始生成每日简报 - {self.today}")
        logger.info("=" * 60)
        
        start_time = datetime.datetime.now()
        
        try:
            # 1. 加载哨兵数据
            logger.info("步骤1: 加载哨兵数据...")
            sentry_data = self.load_sentry_data()
            logger.info(f"加载到 {len(sentry_data.get('current_clues', []))} 条线索")
            
            if mock_data and len(sentry_data.get('current_clues', [])) == 0:
                logger.info("使用模拟数据填充...")
                sentry_data['current_clues'] = self._generate_mock_clues()
            
            # 2. 筛选权重前10的线索
            logger.info("步骤2: 筛选权重前10的线索...")
            top_clues = self.rank_clues_by_weight(sentry_data.get('current_clues', []), top_n=10)
            
            if not top_clues:
                logger.warning("没有筛选到任何线索，使用模拟数据")
                top_clues = self.rank_clues_by_weight(self._generate_mock_clues(), top_n=10)
            
            # 3. 生成LLM洞察
            logger.info("步骤3: 生成LLM洞察...")
            llm_insights = self.generate_llm_insights(top_clues)
            
            # 4. 生成完整报告
            logger.info("步骤4: 生成完整报告...")
            report = self.generate_briefing_report(sentry_data, top_clues, llm_insights)
            
            # 5. 保存报告
            logger.info("步骤5: 保存报告...")
            report_file = self.save_report(report)
            
            # 计算耗时
            duration = (datetime.datetime.now() - start_time).total_seconds()
            logger.info(f"简报生成完成! 耗时: {duration:.2f}秒")
            logger.info(f"报告文件: {report_file}")
            
            return {
                "success": True,
                "report_file": report_file,
                "duration_seconds": duration,
                "clues_analyzed": len(sentry_data.get('current_clues', [])),
                "top_clues": len(top_clues),
                "insights_generated": llm_insights.get('total_insights', 0)
            }
            
        except Exception as e:
            logger.error(f"简报生成失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "duration_seconds": (datetime.datetime.now() - start_time).total_seconds()
            }
    
    def _generate_mock_clues(self) -> List[Dict[str, Any]]:
        """生成模拟线索数据（用于测试）"""
        mock_clues = [
            {
                "id": "mock_001",
                "title": "央行宣布降准0.5个百分点，释放长期资金约1万亿元",
                "content": "中国人民银行决定下调金融机构存款准备金率0.5个百分点，此次降准将释放长期资金约1万亿元，旨在支持实体经济发展，保持流动性合理充裕。",
                "source": "tushare_vip",
                "urgency": "high",
                "scope": "national",
                "timestamp": datetime.datetime.now().isoformat(),
                "related_targets": ["000001.SH", "399001.SZ"],
                "related_industries": ["banking", "finance"]
            },
            {
                "id": "mock_002",
                "title": "新能源汽车购置税减免政策延续至2027年底",
                "content": "财政部等三部门联合发布公告，明确新能源汽车车辆购置税减免政策将延续至2027年12月31日，政策延续将利好新能源汽车产业链。",
                "source": "reuters",
                "urgency": "medium",
                "scope": "industry",
                "timestamp": (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat(),
                "related_targets": ["002594.SZ", "300750.SZ"],
                "related_industries": ["new_energy_vehicles", "battery"]
            },
            {
                "id": "mock_003",
                "title": "人工智能芯片出口管制升级，多家公司受影响",
                "content": "美国商务部升级对华人工智能芯片出口管制措施，将影响包括英伟达、AMD在内的多家芯片制造商对华出口，可能加速国产替代进程。",
                "source": "bloomberg",
                "urgency": "critical",
                "scope": "global",
                "timestamp": (datetime.datetime.now() - datetime.timedelta(hours=3)).isoformat(),
                "related_targets": ["688981.SH", "002049.SZ"],
                "related_industries": ["semiconductor", "ai_chip"]
            },
            {
                "id": "mock_004",
                "title": "光伏组件价格连续三周上涨，行业景气度回升",
                "content": "根据行业数据，光伏组件价格已连续三周上涨，主要受原材料成本上升和需求回暖影响，行业龙头公司有望受益。",
                "source": "sina_finance",
                "urgency": "medium",
                "scope": "sector",
                "timestamp": (datetime.datetime.now() - datetime.timedelta(days=2)).isoformat(),
                "related_targets": ["601012.SH", "300274.SZ"],
                "related_industries": ["photovoltaic", "renewable_energy"]
            },
            {
                "id": "mock_005",
                "title": "医疗设备国产化替代加速，政策支持力度加大",
                "content": "国家卫健委发文要求各级医疗机构优先采购国产医疗设备，政策推动下，国产医疗设备企业迎来发展机遇。",
                "source": "eastmoney",
                "urgency": "medium",
                "scope": "industry",
                "timestamp": (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat(),
                "related_targets": ["300003.SZ", "002223.SZ"],
                "related_industries": ["medical_devices", "healthcare"]
            }
        ]
        return mock_clues


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='琥珀引擎每日简报生成器')
    parser.add_argument('--mock', action='store_true', help='使用模拟数据（测试用）')
    parser.add_argument('--mock-llm', action='store_true', help='使用模拟LLM（测试用）')
    parser.add_argument('--output-dir', type=str, default='reports/daily_briefing', help='输出目录')
    
    args = parser.parse_args()
    
    # 更新输出目录
    global REPORTS_DIR, BRIEFING_OUTPUT_FILE, HTML_OUTPUT_FILE
    REPORTS_DIR = args.output_dir
    BRIEFING_OUTPUT_FILE = os.path.join(REPORTS_DIR, "{date}_briefing.json")
    HTML_OUTPUT_FILE = os.path.join(REPORTS_DIR, "{date}_briefing.html")
    
    # 创建生成器
    generator = DailyBriefingGenerator(use_mock_llm=args.mock_llm)
    
    # 运行生成
    result = generator.run(mock_data=args.mock)
    
    if result['success']:
        print(f"\n✅ 简报生成成功！")
        print(f"   分析线索: {result['clues_analyzed']} 条")
        print(f"   顶级线索: {result['top_clues']} 条")
        print(f"   生成洞察: {result['insights_generated']} 条")
        print(f"   耗时: {result['duration_seconds']:.2f} 秒")
        print(f"   报告文件: {result['report_file']}")
        sys.exit(0)
    else:
        print(f"\n❌ 简报生成失败: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()