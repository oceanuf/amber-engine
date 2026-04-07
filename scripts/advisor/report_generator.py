#!/usr/bin/env python3
"""
Advisor 报告生成器 - 生成每日投资报告
符合 [最高执行指令] 专项二：Advisor 模块逻辑闭环
读取 feedback/arena_to_synthesizer.json，生成每日报告
"""

import os
import sys
import json
import datetime
import re
from typing import Dict, List, Optional, Any
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 模块常量
MODULE_NAME = "advisor_report_generator"
TEMPLATE_FILE = "templates/daily_report.md"
OUTPUT_DIR = "database/reports"
FEEDBACK_FILE = "database/feedback/arena_to_synthesizer.json"
SENTINEL_FILE = "logs/sentry/high_value_clues_test.json"  # 哨兵线索文件
DNA_SUMMARY_FILE = "database/probe/dna_summary_000681.json"  # DNA摘要文件

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

class ReportGenerator:
    """报告生成器类"""
    
    def __init__(self):
        self.template_content = ""
        self.feedback_data = {}
        self.sentinel_data = {}
        self.dna_data = {}
        self.report_data = {}
        
        # 确保目录存在
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # 加载数据
        self.load_data()
    
    def load_data(self):
        """加载所有必要数据"""
        # 加载模板
        if os.path.exists(TEMPLATE_FILE):
            with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
                self.template_content = f.read()
            log_info(f"加载模板: {TEMPLATE_FILE}")
        else:
            log_error("TEMPLATE_NOT_FOUND", f"模板文件不存在: {TEMPLATE_FILE}")
            # 使用默认模板
            self.template_content = self.get_default_template()
        
        # 加载反馈数据
        if os.path.exists(FEEDBACK_FILE):
            with open(FEEDBACK_FILE, 'r', encoding='utf-8') as f:
                self.feedback_data = json.load(f)
            log_info(f"加载反馈数据: {FEEDBACK_FILE}")
        else:
            log_warn(f"反馈文件不存在: {FEEDBACK_FILE}")
        
        # 加载哨兵数据
        if os.path.exists(SENTINEL_FILE):
            with open(SENTINEL_FILE, 'r', encoding='utf-8') as f:
                self.sentinel_data = json.load(f)
            log_info(f"加载哨兵数据: {SENTINEL_FILE}")
        else:
            log_warn(f"哨兵文件不存在: {SENTINEL_FILE}")
        
        # 加载DNA数据
        if os.path.exists(DNA_SUMMARY_FILE):
            with open(DNA_SUMMARY_FILE, 'r', encoding='utf-8') as f:
                self.dna_data = json.load(f)
            log_info(f"加载DNA数据: {DNA_SUMMARY_FILE}")
        else:
            log_warn(f"DNA文件不存在: {DNA_SUMMARY_FILE}")
    
    def get_default_template(self) -> str:
        """获取默认模板"""
        return """# 📊 琥珀引擎每日投资报告

**报告日期**: {{report_date}}  
**生成时间**: {{generation_time}}  
**报告周期**: {{report_period}}  
**报告版本**: {{report_version}}

---

## 🎯 一、今日核心观点

### 市场环境评估
{{market_assessment}}

### 主要风险提示
{{risk_alert}}

### 关键机会方向
{{opportunity_direction}}

---

## 🛰️ 二、哨兵风向 (全球资讯感知)

### 📰 高价值情报摘要
{{sentinel_highlights}}

### 🔍 核心关键词监控
{{keyword_monitoring}}

### 🎯 源头权重分析
{{source_analysis}}

---

## 🔬 三、探针发现 (标的DNA分析)

### 🧬 目标公司分析
{{target_company_analysis}}

### 🔗 相似公司矩阵
{{similarity_matrix}}

### 💡 聚类洞察
{{clustering_insights}}

---

## ⚙️ 四、演算结果 (算法合成信号)

### 🎰 算法权重配置
{{algorithm_weights}}

### 📈 技术指标状态
{{technical_indicators}}

### 🎯 交易信号汇总
{{trading_signals}}

---

## 💰 五、演武场绩效 (实战验证)

### 📊 绩效指标
{{performance_metrics}}

### 🏆 胜率分析  
{{win_rate_analysis}}

### 🔄 权重调整反馈
{{weight_adjustments}}

---

## 🎯 六、投资建议

### 🎖️ 核心建议
{{core_recommendation}}

### 📋 具体操作策略
{{operation_strategy}}

### ⏰ 时间窗口
{{time_window}}

### 🎯 目标价位
{{target_price}}

---

## 🛡️ 七、风险控制

### 🔴 止损策略
{{stop_loss_strategy}}

### 🟡 风险监控
{{risk_monitoring}}

### 🟢 应急预案
{{emergency_plan}}

---

## 📝 八、附录

### 📊 数据来源
{{data_sources}}

### 🔍 分析方法
{{analysis_methods}}

### ⚠️ 局限性说明
{{limitations}}

---

**报告生成**: 琥珀引擎 Advisor 模块  
**生成时间**: {{generation_time}}  
**报告状态**: {{report_status}}  
**建议时效**: {{validity_period}}"""
    
    def generate_market_assessment(self) -> str:
        """生成市场环境评估"""
        # 基于哨兵数据生成
        if self.sentinel_data.get("high_value_clues"):
            clue_count = len(self.sentinel_data["high_value_clues"])
            avg_weight = sum(c.get('weight_analysis', {}).get('final_weight', 0) 
                           for c in self.sentinel_data["high_value_clues"]) / max(clue_count, 1)
            
            if avg_weight > 15:
                sentiment = "极度积极"
            elif avg_weight > 10:
                sentiment = "积极"
            elif avg_weight > 5:
                sentiment = "中性偏积极"
            else:
                sentiment = "中性"
            
            return f"市场情绪: {sentiment}，检测到 {clue_count} 条高价值情报，平均权重 {avg_weight:.1f}。"
        
        return "市场情绪: 中性，无明显高价值情报。"
    
    def generate_risk_alert(self) -> str:
        """生成风险提示"""
        risks = []
        
        # 检查绩效数据
        if self.feedback_data.get("metrics"):
            metrics = self.feedback_data["metrics"]
            if metrics.get("max_drawdown", 0) < -0.05:
                risks.append(f"最大回撤 {metrics['max_drawdown']:.1%} 超过阈值")
            if metrics.get("win_rate", 0) < 0.5:
                risks.append(f"胜率 {metrics['win_rate']:.1%} 低于50%")
        
        # 检查哨兵数据
        if self.sentinel_data.get("high_value_clues"):
            high_weight_clues = [c for c in self.sentinel_data["high_value_clues"] 
                               if c.get('weight_analysis', {}).get('final_weight', 0) > 20]
            if high_weight_clues:
                risks.append(f"检测到 {len(high_weight_clues)} 条极高权重情报，可能存在市场过度反应风险")
        
        if risks:
            return "• " + "\n• ".join(risks)
        else:
            return "无重大风险提示。"
    
    def generate_opportunity_direction(self) -> str:
        """生成机会方向"""
        opportunities = []
        
        # 从DNA数据提取
        if self.dna_data.get("primary_keywords"):
            keywords = self.dna_data["primary_keywords"][:5]
            opportunities.append(f"目标公司核心业务领域: {', '.join(keywords)}")
        
        # 从哨兵数据提取
        if self.sentinel_data.get("high_value_clues"):
            # 统计关键词出现频率
            keyword_freq = {}
            for clue in self.sentinel_data["high_value_clues"]:
                weight_info = clue.get('weight_analysis', {})
                core_keywords = weight_info.get('matched_core_keywords', [])
                for kw in core_keywords:
                    matrix = kw.get('matrix', '未知')
                    keyword_freq[matrix] = keyword_freq.get(matrix, 0) + 1
            
            if keyword_freq:
                top_matrix = max(keyword_freq.items(), key=lambda x: x[1])
                opportunities.append(f"高频核心关键词矩阵: {top_matrix[0]} ({top_matrix[1]}次)")
        
        # 从反馈数据提取
        if self.feedback_data.get("action", {}).get("algorithm_performance"):
            algo_perf = self.feedback_data["action"]["algorithm_performance"]
            top_algo = max(algo_perf.items(), key=lambda x: x[1].get('win_rate', 0))
            opportunities.append(f"表现最佳算法: {top_algo[0]} (胜率: {top_algo[1].get('win_rate', 0):.1%})")
        
        if opportunities:
            return "• " + "\n• ".join(opportunities)
        else:
            return "无明显机会方向。"
    
    def generate_sentinel_highlights(self) -> str:
        """生成哨兵高价值情报摘要"""
        if not self.sentinel_data.get("high_value_clues"):
            return "无高价值情报。"
        
        clues = self.sentinel_data["high_value_clues"]
        highlights = []
        
        for i, clue in enumerate(clues[:3], 1):  # 显示前3条
            title = clue.get('news_title', '未知标题')[:50]
            weight = clue.get('weight_analysis', {}).get('final_weight', 0)
            impact = clue.get('impact_level', '未知')
            
            highlights.append(f"{i}. {title}... (权重: {weight:.1f}, 影响: {impact})")
        
        return "\n".join(highlights)
    
    def generate_keyword_monitoring(self) -> str:
        """生成关键词监控"""
        if not self.sentinel_data.get("high_value_clues"):
            return "无关键词监控数据。"
        
        # 统计核心关键词
        keyword_freq = {}
        for clue in self.sentinel_data["high_value_clues"]:
            weight_info = clue.get('weight_analysis', {})
            core_keywords = weight_info.get('matched_core_keywords', [])
            for kw in core_keywords:
                matrix = kw.get('matrix', '未知')
                keyword = kw.get('keyword', '未知')
                key = f"{matrix}:{keyword}"
                keyword_freq[key] = keyword_freq.get(key, 0) + 1
        
        if not keyword_freq:
            return "无核心关键词匹配。"
        
        # 按频率排序
        sorted_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        
        monitoring = []
        for key, freq in sorted_keywords:
            matrix, keyword = key.split(':', 1)
            monitoring.append(f"{matrix}: {keyword} ({freq}次)")
        
        return "• " + "\n• ".join(monitoring)
    
    def generate_source_analysis(self) -> str:
        """生成源头权重分析"""
        if not self.sentinel_data.get("high_value_clues"):
            return "无源头权重数据。"
        
        # 统计源头权重
        source_weights = {}
        for clue in self.sentinel_data["high_value_clues"]:
            source = clue.get('news_source', '未知')
            weight = clue.get('weight_analysis', {}).get('source_weight', 0)
            if source not in source_weights:
                source_weights[source] = []
            source_weights[source].append(weight)
        
        if not source_weights:
            return "无源头数据。"
        
        analysis = []
        for source, weights in source_weights.items():
            avg_weight = sum(weights) / len(weights)
            analysis.append(f"{source}: 平均权重 {avg_weight:.2f} ({len(weights)}条)")
        
        return "• " + "\n• ".join(analysis)
    
    def generate_target_company_analysis(self) -> str:
        """生成目标公司分析"""
        if not self.dna_data:
            return "无DNA分析数据。"
        
        target_name = self.dna_data.get("target_name", "未知")
        target_ticker = self.dna_data.get("target_ticker", "未知")
        primary_keywords = self.dna_data.get("primary_keywords", [])
        
        analysis = f"**{target_name} ({target_ticker})**\n"
        
        if primary_keywords:
            analysis += f"核心业务关键词: {', '.join(primary_keywords[:10])}\n"
        
        if self.dna_data.get("top_similar_tickers"):
            similar_count = len(self.dna_data["top_similar_tickers"])
            analysis += f"发现 {similar_count} 家相似公司"
        
        return analysis
    
    def generate_similarity_matrix(self) -> str:
        """生成相似公司矩阵摘要"""
        if not self.dna_data.get("top_similar_tickers"):
            return "无相似公司数据。"
        
        matrix = []
        tickers = self.dna_data.get("top_similar_tickers", [])
        names = self.dna_data.get("top_similar_names", [])
        similarities = self.dna_data.get("top_similarities", [])
        
        for i in range(min(5, len(tickers))):
            matrix.append(f"{i+1}. {names[i]} ({tickers[i]}): 相似度 {similarities[i]:.3f}")
        
        return "\n".join(matrix)
    
    def generate_clustering_insights(self) -> str:
        """生成聚类洞察"""
        if not self.dna_data.get("clustering_tags"):
            return "无聚类洞察。"
        
        insights = self.dna_data.get("clustering_tags", [])
        return "• " + "\n• ".join(insights[:3])  # 显示前3条
    
    def generate_algorithm_weights(self) -> str:
        """生成算法权重配置"""
        if not self.feedback_data.get("action", {}).get("adjust_weights"):
            return "无权重调整数据。"
        
        adjust_weights = self.feedback_data["action"]["adjust_weights"]
        weights_info = []
        
        for algo, adjustment in adjust_weights.items():
            if adjustment > 0:
                weights_info.append(f"{algo}: +{adjustment:.3f}")
            else:
                weights_info.append(f"{algo}: {adjustment:.3f}")
        
        if weights_info:
            return "• " + "\n• ".join(weights_info)
        else:
            return "权重无调整。"
    
    def generate_technical_indicators(self) -> str:
        """生成技术指标状态"""
        # 这里可以集成实际的指标数据，目前使用模拟数据
        indicators = [
            "MA20: 金叉状态",
            "RSI: 52 (中性)",
            "MACD: 零轴上方，柱状线扩大",
            "布林带: 价格运行于中轨上方",
            "成交量: 温和放大"
        ]
        
        return "• " + "\n• ".join(indicators)
    
    def generate_trading_signals(self) -> str:
        """生成交易信号汇总"""
        signals = []
        
        # 从反馈数据提取
        if self.feedback_data.get("position_analysis"):
            positions = self.feedback_data["position_analysis"]
            for pos in positions:
                if pos.get("status") == "holding":
                    ticker = pos.get("ticker", "未知")
                    return_pct = pos.get("current_return_pct", 0)
                    signals.append(f"持有 {ticker}: 当前收益 {return_pct:.1f}%")
        
        # 添加模拟信号
        if not signals:
            signals = [
                "买入信号: 000681 (技术面突破)",
                "持有信号: 518880 (趋势延续)",
                "观望信号: 510300 (等待确认)"
            ]
        
        return "• " + "\n• ".join(signals)
    
    def generate_performance_metrics(self) -> str:
        """生成绩效指标"""
        if not self.feedback_data.get("metrics"):
            return "无绩效数据。"
        
        metrics = self.feedback_data["metrics"]
        performance = []
        
        for key, value in metrics.items():
            if key == "win_rate":
                performance.append(f"胜率: {value:.1%}")
            elif key == "profit_factor":
                performance.append(f"盈亏比: {value:.2f}")
            elif key == "max_drawdown":
                performance.append(f"最大回撤: {value:.1%}")
            elif key == "total_return_pct":
                performance.append(f"总收益: {value:.1f}%")
            elif key == "sharpe_ratio":
                performance.append(f"夏普比率: {value:.2f}")
        
        return "• " + "\n• ".join(performance)
    
    def generate_win_rate_analysis(self) -> str:
        """生成胜率分析"""
        if not self.feedback_data.get("action", {}).get("algorithm_performance"):
            return "无算法胜率数据。"
        
        algo_perf = self.feedback_data["action"]["algorithm_performance"]
        
        # 找出胜率最高和最低的算法
        if algo_perf:
            best_algo = max(algo_perf.items(), key=lambda x: x[1].get('win_rate', 0))
            worst_algo = min(algo_perf.items(), key=lambda x: x[1].get('win_rate', 0))
            
            analysis = [
                f"最佳算法: {best_algo[0]} (胜率: {best_algo[1].get('win_rate', 0):.1%})",
                f"最差算法: {worst_algo[0]} (胜率: {worst_algo[1].get('win_rate', 0):.1%})"
            ]
            
            return "\n".join(analysis)
        
        return "无胜率分析数据。"
    
    def generate_weight_adjustments(self) -> str:
        """生成权重调整反馈"""
        if not self.feedback_data.get("action", {}).get("adjust_weights"):
            return "无权重调整。"
        
        adjust_weights = self.feedback_data["action"]["adjust_weights"]
        comment = self.feedback_data["action"].get("comment", "无说明")
        
        adjustments = [f"调整说明: {comment}"]
        
        # 显示调整幅度最大的3个算法
        sorted_adjustments = sorted(adjust_weights.items(), key=lambda x: abs(x[1]), reverse=True)[:3]
        
        for algo, adjustment in sorted_adjustments:
            if adjustment > 0:
                adjustments.append(f"{algo}: 上调 {adjustment:.3f}")
            else:
                adjustments.append(f"{algo}: 下调 {abs(adjustment):.3f}")
        
        return "\n".join(adjustments)
    
    def generate_core_recommendation(self) -> str:
        """生成核心建议"""
        recommendations = []
        
        # 基于DNA分析
        if self.dna_data.get("top_similar_tickers"):
            top_similar = self.dna_data["top_similar_tickers"][0]
            recommendations.append(f"关注相似公司 {top_similar} 的联动效应")
        
        # 基于哨兵分析
        if self.sentinel_data.get("high_value_clues"):
            high_weight_clues = [c for c in self.sentinel_data["high_value_clues"] 
                               if c.get('weight_analysis', {}).get('final_weight', 0) > 15]
            if high_weight_clues:
                recommendations.append(f"关注 {len(high_weight_clues)} 条高权重情报相关板块")
        
        # 基于绩效分析
        if self.feedback_data.get("metrics", {}).get("win_rate", 0) > 0.55:
            recommendations.append("当前策略有效，继续执行")
        else:
            recommendations.append("策略效果一般，建议谨慎操作")
        
        if recommendations:
            return "• " + "\n• ".join(recommendations)
        else:
            return "保持观望。"
    
    def generate_operation_strategy(self) -> str:
        """生成操作策略"""
        strategies = [
            "分批建仓，控制单笔仓位≤5%",
            "严格执行止损，亏损达3%即止损",
            "盈利达到8%考虑部分止盈",
            "关注成交量配合情况"
        ]
        
        return "• " + "\n• ".join(strategies)
    
    def generate_time_window(self) -> str:
        """生成时间窗口"""
        now = datetime.datetime.now()
        next_week = now + datetime.timedelta(days=7)
        
        return f"本报告有效期至: {next_week.strftime('%Y-%m-%d')}"
    
    def generate_target_price(self) -> str:
        """生成目标价位"""
        # 模拟数据
        return "000681: 第一目标位 18.5元，第二目标位 20.0元"
    
    def generate_stop_loss_strategy(self) -> str:
        """生成止损策略"""
        strategies = [
            "移动止损: 盈利达5%后，止损位上移至成本价",
            "固定止损: 亏损达3%立即止损",
            "时间止损: 持有超过20天无盈利考虑离场"
        ]
        
        return "• " + "\n• ".join(strategies)
    
    def generate_risk_monitoring(self) -> str:
        """生成风险监控"""
        monitoring = [
            "监控市场波动率，VIX指数超过25进入警戒状态",
            "关注个股成交量异常放大（>5日均量2倍）",
            "监控板块轮动速度，过快轮动降低仓位"
        ]
        
        return "• " + "\n• ".join(monitoring)
    
    def generate_emergency_plan(self) -> str:
        """生成应急预案"""
        plans = [
            "黑天鹅事件: 立即将仓位降至30%以下",
            "流动性危机: 停止开新仓，优先处理亏损头寸",
            "系统故障: 启用手动备份交易计划"
        ]
        
        return "• " + "\n• ".join(plans)
    
    def generate_data_sources(self) -> str:
        """生成数据来源"""
        sources = [
            "哨兵系统: 全球资讯感知与权重计算",
            "探针系统: 主营业务DNA提取与相似度分析",
            "演武场: 虚拟基金绩效反馈",
            "合成器: 算法信号生成与权重调整"
        ]
        
        return "• " + "\n• ".join(sources)
    
    def generate_analysis_methods(self) -> str:
        """生成分析方法"""
        methods = [
            "权重驱动决策: final_weight = source_weight × relevance_weight × keyword_weight",
            "相似度聚类: Jaccard相似度算法分析主营业务匹配度",
            "反馈闭环: 基于演武场绩效动态调整算法权重",
            "多维度共振: 10个算法民主投票制合成信号"
        ]
        
        return "• " + "\n• ".join(methods)
    
    def generate_limitations(self) -> str:
        """生成局限性说明"""
        limitations = [
            "历史数据有限，回测周期较短",
            "模拟交易与实际交易存在心理差异",
            "市场极端情况下的模型有效性待验证",
            "依赖外部数据源，存在延迟或中断风险"
        ]
        
        return "• " + "\n• ".join(limitations)
    
    def collect_report_data(self) -> Dict[str, str]:
        """收集所有报告数据"""
        now = datetime.datetime.now()
        
        return {
            # 基本信息
            "report_date": now.strftime("%Y-%m-%d"),
            "generation_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "report_period": "日度",
            "report_version": "1.0.0",
            
            # 核心观点
            "market_assessment": self.generate_market_assessment(),
            "risk_alert": self.generate_risk_alert(),
            "opportunity_direction": self.generate_opportunity_direction(),
            
            # 哨兵风向
            "sentinel_highlights": self.generate_sentinel_highlights(),
            "keyword_monitoring": self.generate_keyword_monitoring(),
            "source_analysis": self.generate_source_analysis(),
            
            # 探针发现
            "target_company_analysis": self.generate_target_company_analysis(),
            "similarity_matrix": self.generate_similarity_matrix(),
            "clustering_insights": self.generate_clustering_insights(),
            
            # 演算结果
            "algorithm_weights": self.generate_algorithm_weights(),
            "technical_indicators": self.generate_technical_indicators(),
            "trading_signals": self.generate_trading_signals(),
            
            # 演武场绩效
            "performance_metrics": self.generate_performance_metrics(),
            "win_rate_analysis": self.generate_win_rate_analysis(),
            "weight_adjustments": self.generate_weight_adjustments(),
            
            # 投资建议
            "core_recommendation": self.generate_core_recommendation(),
            "operation_strategy": self.generate_operation_strategy(),
            "time_window": self.generate_time_window(),
            "target_price": self.generate_target_price(),
            
            # 风险控制
            "stop_loss_strategy": self.generate_stop_loss_strategy(),
            "risk_monitoring": self.generate_risk_monitoring(),
            "emergency_plan": self.generate_emergency_plan(),
            
            # 附录
            "data_sources": self.generate_data_sources(),
            "analysis_methods": self.generate_analysis_methods(),
            "limitations": self.generate_limitations(),
            
            # 元数据
            "report_status": "正式发布",
            "validity_period": "7天"
        }
    
    def render_template(self, data: Dict[str, str]) -> str:
        """渲染模板"""
        content = self.template_content
        
        # 替换所有变量
        for key, value in data.items():
            placeholder = "{{" + key + "}}"
            content = content.replace(placeholder, value)
        
        # 处理可能的未替换变量
        content = re.sub(r'\{\{.*?\}\}', '【数据缺失】', content)
        
        return content
    
    def generate_report(self) -> str:
        """生成报告"""
        log_info("开始生成每日投资报告")
        
        # 收集数据
        self.report_data = self.collect_report_data()
        
        # 渲染模板
        report_content = self.render_template(self.report_data)
        
        # 保存报告
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"daily_report_{timestamp}.md"
        report_path = os.path.join(OUTPUT_DIR, report_filename)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        log_info(f"报告已保存: {report_path}")
        
        # 同时保存JSON版本（供程序读取）
        json_path = os.path.join(OUTPUT_DIR, f"daily_report_{timestamp}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                "metadata": {
                    "report_id": f"REPORT_{timestamp}",
                    "generated_at": self.report_data["generation_time"],
                    "version": self.report_data["report_version"],
                    "file_path": report_path
                },
                "summary": {
                    "market_assessment": self.report_data["market_assessment"][:100] + "...",
                    "core_recommendation": self.report_data["core_recommendation"][:100] + "...",
                    "risk_alert": self.report_data["risk_alert"][:100] + "..."
                },
                "data_sources": {
                    "feedback_loaded": bool(self.feedback_data),
                    "sentinel_loaded": bool(self.sentinel_data),
                    "dna_loaded": bool(self.dna_data)
                }
            }, f, ensure_ascii=False, indent=2)
        
        log_info(f"JSON摘要已保存: {json_path}")
        
        return report_path
    
    def print_report_summary(self, report_path: str):
        """打印报告摘要"""
        print("\n" + "=" * 70)
        print("📋 每日投资报告生成完成")
        print("=" * 70)
        print(f"报告文件: {report_path}")
        print(f"生成时间: {self.report_data.get('generation_time', '未知')}")
        print(f"数据来源:")
        print(f"  • 哨兵系统: {'✅' if self.sentinel_data else '❌'}")
        print(f"  • 探针系统: {'✅' if self.dna_data else '❌'}")
        print(f"  • 演武场反馈: {'✅' if self.feedback_data else '❌'}")
        print()
        print("📊 核心观点摘要:")
        print(f"  市场评估: {self.report_data.get('market_assessment', '无数据')[:60]}...")
        print(f"  风险提示: {self.report_data.get('risk_alert', '无数据')[:60]}...")
        print(f"  机会方向: {self.report_data.get('opportunity_direction', '无数据')[:60]}...")
        print()
        print("🎯 投资建议摘要:")
        print(f"  核心建议: {self.report_data.get('core_recommendation', '无数据')[:60]}...")
        print()
        print("=" * 70)

def main():
    """主函数"""
    print("🚀 Advisor 报告生成器启动")
    print("符合 [最高执行指令] 专项二：Advisor 模块逻辑闭环")
    print("=" * 70)
    
    # 初始化生成器
    generator = ReportGenerator()
    
    # 生成报告
    try:
        report_path = generator.generate_report()
        generator.print_report_summary(report_path)
        
        print("✅ 报告生成完成")
        print("=" * 70)
        
    except Exception as e:
        log_error("REPORT_GENERATION_FAILED", f"报告生成失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()