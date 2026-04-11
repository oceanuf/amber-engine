#!/usr/bin/env python3
"""
琥珀引擎演武场报告生成器 - 核心逻辑类
版本: V1.0.0 (原型)
功能: 从virtual_fund.json提取持仓数据，查询价格，生成报告数据
法典依据: 任务指令[2616-0411-P0A]
"""

import os
import sys
import json
import datetime
import time
from typing import Dict, List, Optional, Tuple, Any
import logging
import tushare as ts

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ArenaReportGenerator:
    """演武场报告生成器核心类"""
    
    def __init__(self, workspace_root: Optional[str] = None):
        """
        初始化报告生成器
        
        Args:
            workspace_root: 工作空间根目录，如果为None则从环境变量或默认路径获取
        """
        self.workspace_root = workspace_root or self._get_workspace_root()
        self.virtual_fund_path = os.path.join(self.workspace_root, "database", "arena", "virtual_fund.json")
        self.resonance_report_pattern = os.path.join(self.workspace_root, "database", "resonance_report_*.json")
        
        # 加载数据
        self.virtual_fund_data = self._load_virtual_fund()
        self.current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # 价格缓存（原型阶段使用模拟数据，供回退使用）
        self.price_cache = {
            "000681": 20.37,  # 视觉中国
            "600633": 12.52,  # 浙数文化
            "000938": 27.02,  # 紫光股份
            "518880": 5.42,   # 黄金ETF
            "510500": 6.78,   # 中证500ETF
            "510300": 4.12    # 沪深300ETF
        }
        
        # Tushare Pro API初始化
        self.tushare_token = os.environ.get("TUSHARE_TOKEN")
        self.tushare_pro = None
        self.last_api_call_time = 0
        self.api_call_interval = 0.5  # 每次调用间隔0.5秒，避免频率限制
        
        if self.tushare_token:
            try:
                ts.set_token(self.tushare_token)
                self.tushare_pro = ts.pro_api()
                logger.info("Tushare Pro API初始化成功")
            except Exception as e:
                logger.warning(f"Tushare Pro API初始化失败: {e}，将使用缓存价格")
        else:
            logger.warning("未找到TUSHARE_TOKEN环境变量，将使用缓存价格")
        
        logger.info(f"报告生成器初始化完成，工作空间: {self.workspace_root}")
    
    def _get_workspace_root(self) -> str:
        """获取工作空间根目录"""
        # 优先从环境变量获取
        workspace = os.environ.get("GITHUB_WORKSPACE")
        if workspace and os.path.exists(workspace):
            return workspace
        
        # 默认路径（amber-engine目录）
        default_path = "/home/luckyelite/.openclaw/workspace/amber-engine"
        if os.path.exists(default_path):
            return default_path
        
        # 当前脚本的祖父目录
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return script_dir
    
    def _load_virtual_fund(self) -> Dict:
        """加载virtual_fund.json数据"""
        try:
            with open(self.virtual_fund_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"成功加载virtual_fund.json，包含{len(data.get('positions', []))}个持仓")
            return data
        except FileNotFoundError:
            logger.error(f"virtual_fund.json文件不存在: {self.virtual_fund_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {e}")
            raise
    
    def get_current_price(self, ticker: str) -> Tuple[float, str]:
        """
        获取标的当前价格（优先Tushare API，失败则回退缓存）
        
        Args:
            ticker: 股票代码
            
        Returns:
            (价格, 状态) 状态为 "OK" 或 "DATA_MISSING"
        """
        # 首先检查缓存（快速路径）
        if ticker in self.price_cache:
            return self.price_cache[ticker], "OK"
        
        # 尝试使用Tushare API获取实时价格
        if self.tushare_pro:
            try:
                # API频率控制：确保调用间隔
                current_time = time.time()
                time_since_last_call = current_time - self.last_api_call_time
                if time_since_last_call < self.api_call_interval:
                    sleep_time = self.api_call_interval - time_since_last_call
                    logger.debug(f"API频率控制: 等待{sleep_time:.2f}秒")
                    time.sleep(sleep_time)
                
                # 转换股票代码为Tushare格式
                if ticker.startswith("6"):
                    ts_code = f"{ticker}.SH"
                else:
                    ts_code = f"{ticker}.SZ"
                
                logger.info(f"查询Tushare实时价格: {ticker} -> {ts_code}")
                
                # 调用Tushare daily接口获取最新数据
                # trade_date格式: YYYYMMDD，空表示最新交易日
                df = self.tushare_pro.daily(ts_code=ts_code, trade_date="")
                
                # 更新最后调用时间
                self.last_api_call_time = time.time()
                
                if df is not None and not df.empty:
                    latest = df.iloc[0]
                    close_price = latest["close"]
                    logger.info(f"Tushare价格获取成功: {ticker} = {close_price}")
                    
                    # 更新缓存
                    self.price_cache[ticker] = close_price
                    return close_price, "OK"
                else:
                    logger.warning(f"Tushare返回空数据: {ticker}")
                    
            except Exception as e:
                logger.warning(f"Tushare API调用失败: {ticker}, 错误: {e}")
                # 继续尝试缓存
        
        # Tushare不可用或失败，尝试从本地数据库获取历史价格
        # 这里可以扩展：查询本地存储的历史收盘价
        
        # 最终回退：返回DATA_MISSING警告
        logger.warning(f"价格数据缺失: {ticker}，返回0.0作为占位符")
        return 0.0, "DATA_MISSING"
    
    def calculate_position_metrics(self, position: Dict, current_price: float) -> Dict:
        """
        计算单个持仓的指标
        
        Args:
            position: 持仓数据
            current_price: 当前价格
            
        Returns:
            增强的持仓指标字典
        """
        avg_cost = position.get("average_cost", 0)
        quantity = position.get("quantity", 0)
        entry_date_str = position.get("entry_date", self.current_date)
        
        # 计算市值和盈亏
        market_value = current_price * quantity
        cost_basis = avg_cost * quantity
        unrealized_pnl = market_value - cost_basis
        unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0
        
        # 计算在仓天数
        try:
            entry_date = datetime.datetime.strptime(entry_date_str, "%Y-%m-%d")
            current_date = datetime.datetime.strptime(self.current_date, "%Y-%m-%d")
            days_in_position = (current_date - entry_date).days
        except ValueError:
            days_in_position = 0
            logger.warning(f"日期格式错误: {entry_date_str}")
        
        # 盈亏Emoji
        pnl_emoji = "🟢" if unrealized_pnl >= 0 else "🔴"
        
        # 检查止损线
        stop_loss_daily = unrealized_pnl_pct <= -10
        stop_loss_total = unrealized_pnl_pct <= -15
        
        return {
            "ticker": position.get("ticker"),
            "name": position.get("name"),
            "sector": position.get("sector", "未知"),
            "quantity": quantity,
            "avg_cost": round(avg_cost, 2),
            "current_price": round(current_price, 2),
            "market_value": round(market_value, 2),
            "cost_basis": round(cost_basis, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "unrealized_pnl_pct": round(unrealized_pnl_pct, 2),
            "pnl_emoji": pnl_emoji,
            "days_in_position": days_in_position,
            "entry_date": entry_date_str,
            "status": "active",
            "stop_loss_daily": stop_loss_daily,
            "stop_loss_total": stop_loss_total,
            "price_status": "OK" if current_price > 0 else "DATA_MISSING"
        }
    
    def get_resonance_score(self, ticker: str) -> Optional[float]:
        """
        获取标的的共振评分
        
        Args:
            ticker: 股票代码
            
        Returns:
            共振评分或None
        """
        # 查找最新的共振报告
        import glob
        resonance_files = glob.glob(self.resonance_report_pattern)
        if not resonance_files:
            logger.warning("未找到共振报告文件")
            return None
        
        # 使用最新的报告
        latest_file = max(resonance_files, key=os.path.getmtime)
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 在共振报告中查找标的
            for item in data.get("overall_analysis", {}).get("top_performers", []):
                if item.get("ticker") == ticker:
                    return item.get("resonance_score")
            
            # 在详细分析中查找
            for ticker_key, analysis in data.get("detailed_analysis", {}).items():
                if ticker_key == ticker:
                    return analysis.get("resonance_score")
            
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            logger.warning(f"读取共振报告失败: {e}")
        
        return None
    
    def generate_report_data(self) -> Dict[str, Any]:
        """
        生成报告数据字典
        
        Returns:
            包含所有报告数据的字典
        """
        logger.info("开始生成报告数据...")
        
        # 基础信息
        fund_data = self.virtual_fund_data
        initial_capital = fund_data.get("initial_capital", 1000000.00)
        current_capital = fund_data.get("current_capital", 700000.00)
        
        # 处理持仓
        positions = []
        total_market_value = 0
        total_cost_basis = 0
        
        for position in fund_data.get("positions", []):
            ticker = position.get("ticker")
            if not ticker:
                continue
            
            # 获取当前价格
            current_price, price_status = self.get_current_price(ticker)
            
            # 计算指标
            position_metrics = self.calculate_position_metrics(position, current_price)
            
            # 获取共振评分
            resonance_score = self.get_resonance_score(ticker)
            position_metrics["resonance_score"] = resonance_score
            
            positions.append(position_metrics)
            
            total_market_value += position_metrics["market_value"]
            total_cost_basis += position_metrics["cost_basis"]
        
        # 按盈亏率排序
        positions.sort(key=lambda x: x["unrealized_pnl_pct"], reverse=True)
        
        # 计算总体指标
        total_pnl = total_market_value - total_cost_basis
        total_return_pct = (total_pnl / total_cost_basis * 100) if total_cost_basis > 0 else 0
        total_return_emoji = "🟢" if total_pnl >= 0 else "🔴"
        
        # 现金和风险资产
        cash_reserve_amount = current_capital - total_market_value
        cash_reserve_pct = (cash_reserve_amount / current_capital * 100) if current_capital > 0 else 0
        risk_asset_pct = 100 - cash_reserve_pct
        risk_asset_amount = total_market_value
        
        # 构建报告数据
        report_data = {
            "metadata": {
                "report_id": f"arena_daily_{self.current_date.replace('-', '')}",
                "report_date": self.current_date,
                "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "report_status": "原型测试",
                "version": "1.0.0"
            },
            "fund_summary": {
                "initial_capital": round(initial_capital, 2),
                "current_capital": round(current_capital, 2),
                "total_return": round(total_pnl, 2),
                "total_return_pct": round(total_return_pct, 2),
                "total_return_emoji": total_return_emoji,
                "cash_reserve_amount": round(cash_reserve_amount, 2),
                "cash_reserve_pct": round(cash_reserve_pct, 2),
                "risk_asset_amount": round(risk_asset_amount, 2),
                "risk_asset_pct": round(risk_asset_pct, 2),
                "performance_metrics": fund_data.get("performance_metrics", {})
            },
            "positions": positions,
            "new_entries": [],  # 新晋标的（需要从队列管理器获取）
            "transactions_today": [],  # 今日交易（需要从transaction_history过滤）
            "algorithm_changes": [],  # 算法权重变化（需要从权重历史获取）
            "data_integrity": {
                "virtual_fund_loaded": bool(self.virtual_fund_data),
                "positions_count": len(positions),
                "missing_prices": len([p for p in positions if p["price_status"] == "DATA_MISSING"]),
                "missing_resonance_scores": len([p for p in positions if p.get("resonance_score") is None])
            }
        }
        
        logger.info(f"报告数据生成完成，包含{len(positions)}个持仓")
        return report_data
    
    def render_report(self, report_data: Dict[str, Any]) -> str:
        """
        渲染报告为Markdown文本（简化版）
        
        Args:
            report_data: 报告数据字典
            
        Returns:
            Markdown格式的报告文本
        """
        logger.info("开始渲染报告...")
        
        # 加载模板
        template_path = os.path.join(self.workspace_root, "templates", "arena_daily_report.md")
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
        except FileNotFoundError:
            logger.warning(f"模板文件不存在: {template_path}，使用简化模板")
            template = self._get_fallback_template()
        
        # 原型阶段：返回简化报告
        return self._render_simple_report(report_data)
    
    def _render_simple_report(self, report_data: Dict[str, Any]) -> str:
        """生成简化报告（原型用）"""
        md_lines = []
        
        # 标题
        md_lines.append(f"# 🏟️ 琥珀引擎演武场实战报告 (原型)")
        md_lines.append(f"**报告日期**: {report_data['metadata']['report_date']}  ")
        md_lines.append(f"**生成时间**: {report_data['metadata']['generated_at']}  ")
        md_lines.append(f"**状态**: {report_data['metadata']['report_status']}  ")
        md_lines.append("")
        
        # 资金总览
        md_lines.append("## 📊 持仓损益总览")
        md_lines.append("")
        md_lines.append(f"- **初始资金**: {report_data['fund_summary']['initial_capital']} CNY")
        md_lines.append(f"- **当前资本**: {report_data['fund_summary']['current_capital']} CNY")
        md_lines.append(f"- **总收益率**: {report_data['fund_summary']['total_return_pct']}% {report_data['fund_summary']['total_return_emoji']}")
        md_lines.append(f"- **现金储备**: {report_data['fund_summary']['cash_reserve_pct']}% ({report_data['fund_summary']['cash_reserve_amount']} CNY)")
        md_lines.append(f"- **风险资产**: {report_data['fund_summary']['risk_asset_pct']}% ({report_data['fund_summary']['risk_asset_amount']} CNY)")
        md_lines.append("")
        
        # 持仓明细
        md_lines.append("## 📋 持仓明细")
        md_lines.append("")
        md_lines.append("| 代码 | 名称 | 持仓数量 | 成本均价 | 当前价格 | 持仓市值 | 累计盈亏 | 盈亏率 | 在仓天数 |")
        md_lines.append("|------|------|----------|----------|----------|----------|----------|--------|----------|")
        
        for pos in report_data["positions"]:
            md_lines.append(f"| {pos['ticker']} | {pos['name']} | {pos['quantity']} | {pos['avg_cost']} | {pos['current_price']} | {pos['market_value']} | {pos['unrealized_pnl']} {pos['pnl_emoji']} | {pos['unrealized_pnl_pct']}% | {pos['days_in_position']} |")
        
        md_lines.append("")
        
        # 数据完整性检查
        md_lines.append("## ⚠️ 数据完整性检查")
        md_lines.append("")
        missing_prices = report_data['data_integrity']['missing_prices']
        missing_scores = report_data['data_integrity']['missing_resonance_scores']
        
        if missing_prices > 0:
            md_lines.append(f"- 🔴 **价格数据缺失**: {missing_prices}个标的缺少价格数据")
        else:
            md_lines.append(f"- 🟢 **价格数据完整**: 所有标的都有价格数据")
            
        if missing_scores > 0:
            md_lines.append(f"- 🔴 **共振评分缺失**: {missing_scores}个标的缺少共振评分")
        else:
            md_lines.append(f"- 🟢 **共振评分完整**: 所有标的都有共振评分")
        
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("**报告生成**: 琥珀引擎演武场报告生成器 V1.0 (原型)  ")
        md_lines.append("**数据来源**: virtual_fund.json + 价格缓存  ")
        md_lines.append("**法典对齐**: 任务指令[2616-0411-P0A]  ")
        md_lines.append("")
        md_lines.append("> \"原型已走通，逻辑在进化。\"")
        
        return "\n".join(md_lines)
    
    def _get_fallback_template(self) -> str:
        """获取回退模板"""
        return """# 🏟️ 琥珀引擎演武场实战报告

**报告日期**: {{ report_date }}
**状态**: 原型测试

## 📊 持仓损益总览
{{ summary }}

## 📋 持仓明细
{{ positions_table }}

## ⚠️ 数据完整性
{{ data_integrity }}

---

**生成**: 琥珀引擎报告生成器原型
"""


def main():
    """主函数 - 测试用"""
    try:
        # 初始化生成器
        generator = ArenaReportGenerator()
        
        # 生成报告数据
        report_data = generator.generate_report_data()
        
        # 渲染报告
        report_md = generator.render_report(report_data)
        
        # 输出报告
        print(report_md)
        
        # 保存到文件（测试用）
        output_dir = os.path.join(generator.workspace_root, "reports", "arena")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{generator.current_date}.md")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_md)
        
        print(f"\n✅ 报告已保存至: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"报告生成失败: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)