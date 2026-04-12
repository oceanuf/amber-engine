#!/usr/bin/env python3
"""
流动性约束器 (Liquidity Checker)
版本: 1.0.0
描述: 检查交易规模相对于市场成交量的比例，防止流动性冲击。
功能:
  1. 检查交易规模与市场成交量的比例
  2. 触发流动性折价或部分成交
  3. 提供流动性风险评估
  4. 生成流动性检查报告
法典依据: 任务指令[2616-0412-P4] 交易审判维度完善与滑点仿真
"""

import os
import sys
import json
import datetime
import logging
import math
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, asdict
from enum import Enum

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LiquidityStatus(Enum):
    """流动性状态枚举"""
    NORMAL = "normal"           # 正常流动性
    WARNING = "warning"         # 流动性警告
    CRITICAL = "critical"       # 流动性危急
    FAILED = "failed"           # 流动性失败（无法成交）

class ExecutionResult(Enum):
    """执行结果枚举"""
    FULL_EXECUTION = "full_execution"      # 完全成交
    PARTIAL_EXECUTION = "partial_execution" # 部分成交
    EXECUTION_FAILED = "execution_failed"  # 成交失败
    PRICE_DISCOUNT = "price_discount"      # 价格折价

@dataclass
class MarketData:
    """市场数据容器"""
    ticker: str
    date: str
    volume: float           # 成交量（股数）
    amount: float           # 成交额（金额）
    turnover_rate: float    # 换手率
    avg_price: float        # 平均价格（成交额/成交量）
    
    def validate(self) -> bool:
        """验证市场数据有效性"""
        if self.volume < 0 or self.amount < 0:
            return False
        if self.turnover_rate < 0:
            return False
        if self.avg_price < 0:
            return False
        return True

@dataclass
class TradeRequest:
    """交易请求"""
    ticker: str
    direction: str          # "buy" 或 "sell"
    quantity: int           # 请求数量（股数）
    price: float            # 请求价格
    request_time: str       # 请求时间
    
    def validate(self) -> bool:
        """验证交易请求有效性"""
        if self.quantity <= 0:
            return False
        if self.price <= 0:
            return False
        if self.direction not in ["buy", "sell"]:
            return False
        return True

@dataclass
class LiquidityCheckResult:
    """流动性检查结果"""
    trade_request: TradeRequest
    market_data: MarketData
    status: LiquidityStatus
    execution_result: ExecutionResult
    execution_ratio: float          # 执行比例 (0-1)
    execution_quantity: int         # 实际执行数量
    liquidity_discount: float       # 流动性折价率 (0-1)
    adjusted_price: float          # 调整后价格
    liquidity_ratio: float          # 流动性比例 (交易量/市场成交量)
    risk_level: str                # 风险等级: low, medium, high
    recommendation: str            # 执行建议
    timestamp: str                 # 检查时间戳
    
    def to_dict(self):
        result_dict = asdict(self)
        # 将枚举转换为字符串
        result_dict["status"] = self.status.value
        result_dict["execution_result"] = self.execution_result.value
        return result_dict

class LiquidityChecker:
    """流动性约束器核心类"""
    
    def __init__(self, threshold_ratio: float = 0.001):
        """
        初始化流动性检查器
        
        Args:
            threshold_ratio: 流动性阈值比例（默认0.1%）
                            交易量超过市场成交量的该比例时触发检查
        """
        self.threshold_ratio = threshold_ratio
        
        # 配置参数
        self.config = {
            "warning_threshold": 0.0005,      # 警告阈值 0.05%
            "critical_threshold": 0.001,      # 危急阈值 0.1% (默认)
            "failed_threshold": 0.005,        # 失败阈值 0.5%
            "max_execution_ratio": 0.8,       # 最大执行比例 80%
            "min_execution_ratio": 0.1,       # 最小执行比例 10%
            "price_discount_factor": 0.02,    # 价格折价因子 2%
            "partial_execution_factor": 0.5,  # 部分成交因子 50%
            "turnover_sensitivity": 0.3,      # 换手率敏感度
            "time_sensitivity": 0.2           # 时间敏感度（早盘/尾盘）
        }
        
        logger.info(f"流动性检查器初始化完成，阈值比例: {threshold_ratio*100:.2f}%")
    
    def calculate_liquidity_ratio(self, trade_quantity: int, market_volume: float) -> float:
        """
        计算流动性比例
        
        公式: liquidity_ratio = trade_quantity / market_volume
        
        Args:
            trade_quantity: 交易数量
            market_volume: 市场成交量
            
        Returns:
            流动性比例 (小数形式)
        """
        if market_volume <= 0:
            logger.warning(f"市场成交量为0，无法计算流动性比例")
            return float('inf')  # 表示无限大
        
        ratio = trade_quantity / market_volume
        
        logger.debug(f"计算流动性比例: {ratio:.6f} (交易量: {trade_quantity}, 市场成交量: {market_volume:.0f})")
        return ratio
    
    def determine_liquidity_status(self, liquidity_ratio: float) -> LiquidityStatus:
        """
        确定流动性状态
        
        Args:
            liquidity_ratio: 流动性比例
            
        Returns:
            流动性状态
        """
        if liquidity_ratio >= self.config["failed_threshold"]:
            return LiquidityStatus.FAILED
        elif liquidity_ratio >= self.config["critical_threshold"]:
            return LiquidityStatus.CRITICAL
        elif liquidity_ratio >= self.config["warning_threshold"]:
            return LiquidityStatus.WARNING
        else:
            return LiquidityStatus.NORMAL
    
    def calculate_execution_ratio(self, status: LiquidityStatus, 
                                 liquidity_ratio: float,
                                 turnover_rate: float) -> float:
        """
        计算执行比例
        
        基于流动性状态、流动性比例和换手率
        
        Args:
            status: 流动性状态
            liquidity_ratio: 流动性比例
            turnover_rate: 换手率
            
        Returns:
            执行比例 (0-1)
        """
        if status == LiquidityStatus.FAILED:
            return 0.0
        
        if status == LiquidityStatus.NORMAL:
            return 1.0  # 完全执行
        
        # 警告和危急状态需要计算部分执行
        base_ratio = 1.0 - liquidity_ratio * 10  # 基础衰减
        
        # 考虑换手率影响：换手率越高，执行比例越高
        turnover_factor = min(1.0, turnover_rate * self.config["turnover_sensitivity"])
        base_ratio *= (0.7 + 0.3 * turnover_factor)  # 换手率贡献30%
        
        # 考虑时间因素（简化版：假设早盘流动性更好）
        current_hour = datetime.datetime.now().hour
        time_factor = 1.0
        if 9 <= current_hour <= 10:  # 早盘
            time_factor = 1.1
        elif 14 <= current_hour <= 15:  # 尾盘
            time_factor = 0.9
        
        base_ratio *= time_factor
        
        # 应用部分成交因子
        if status == LiquidityStatus.CRITICAL:
            base_ratio *= self.config["partial_execution_factor"]
        
        # 确保在合理范围内
        min_ratio = self.config["min_execution_ratio"]
        max_ratio = self.config["max_execution_ratio"]
        execution_ratio = max(min_ratio, min(base_ratio, max_ratio))
        
        logger.debug(f"计算执行比例: {execution_ratio:.2f} (状态: {status.value}, "
                   f"流动性比例: {liquidity_ratio:.6f}, 换手率: {turnover_rate:.2f}%)")
        
        return execution_ratio
    
    def calculate_price_discount(self, status: LiquidityStatus,
                                liquidity_ratio: float,
                                direction: str) -> float:
        """
        计算价格折价率
        
        流动性不足时需要价格折价才能成交
        
        Args:
            status: 流动性状态
            liquidity_ratio: 流动性比例
            direction: 交易方向
            
        Returns:
            价格折价率 (小数形式，正值表示折价)
        """
        if status == LiquidityStatus.NORMAL:
            return 0.0
        
        # 基础折价率
        base_discount = self.config["price_discount_factor"]
        
        # 根据流动性比例调整
        discount_multiplier = liquidity_ratio * 100  # 放大比例
        adjusted_discount = base_discount * discount_multiplier
        
        # 方向调整：卖出折价（价格更低），买入溢价（价格更高）
        if direction == "buy":
            adjusted_discount = abs(adjusted_discount)  # 买入需要溢价
        else:  # sell
            adjusted_discount = -abs(adjusted_discount)  # 卖出需要折价
        
        # 状态调整
        if status == LiquidityStatus.CRITICAL:
            adjusted_discount *= 2.0
        elif status == LiquidityStatus.FAILED:
            adjusted_discount *= 3.0
        
        # 限制折价范围
        max_discount = 0.1  # 最大10%折价/溢价
        adjusted_discount = max(-max_discount, min(adjusted_discount, max_discount))
        
        logger.debug(f"计算价格折价率: {adjusted_discount*100:.2f}% "
                   f"(状态: {status.value}, 方向: {direction})")
        
        return adjusted_discount
    
    def determine_execution_result(self, status: LiquidityStatus,
                                  execution_ratio: float) -> ExecutionResult:
        """
        确定执行结果
        
        Args:
            status: 流动性状态
            execution_ratio: 执行比例
            
        Returns:
            执行结果
        """
        if status == LiquidityStatus.FAILED:
            return ExecutionResult.EXECUTION_FAILED
        
        if execution_ratio >= 0.95:
            return ExecutionResult.FULL_EXECUTION
        elif execution_ratio >= 0.1:
            return ExecutionResult.PARTIAL_EXECUTION
        else:
            return ExecutionResult.PRICE_DISCOUNT
    
    def determine_risk_level(self, liquidity_ratio: float, 
                           execution_ratio: float) -> str:
        """
        确定风险等级
        
        Args:
            liquidity_ratio: 流动性比例
            execution_ratio: 执行比例
            
        Returns:
            风险等级: "low", "medium", "high"
        """
        if liquidity_ratio < self.config["warning_threshold"]:
            return "low"
        elif liquidity_ratio < self.config["critical_threshold"]:
            return "medium"
        else:
            return "high"
    
    def generate_recommendation(self, status: LiquidityStatus,
                              execution_result: ExecutionResult,
                              risk_level: str) -> str:
        """
        生成执行建议
        
        Args:
            status: 流动性状态
            execution_result: 执行结果
            risk_level: 风险等级
            
        Returns:
            执行建议
        """
        recommendations = {
            (LiquidityStatus.NORMAL, ExecutionResult.FULL_EXECUTION, "low"): 
                "流动性充足，建议正常执行",
            
            (LiquidityStatus.WARNING, ExecutionResult.FULL_EXECUTION, "medium"):
                "流动性一般，建议分批执行或使用限价单",
            
            (LiquidityStatus.WARNING, ExecutionResult.PARTIAL_EXECUTION, "medium"):
                "流动性一般，建议分批执行，剩余部分等待更好时机",
            
            (LiquidityStatus.CRITICAL, ExecutionResult.PARTIAL_EXECUTION, "high"):
                "流动性紧张，建议大幅减少交易规模或使用算法交易",
            
            (LiquidityStatus.CRITICAL, ExecutionResult.PRICE_DISCOUNT, "high"):
                "流动性紧张，需要价格折价才能成交，建议重新评估",
            
            (LiquidityStatus.FAILED, ExecutionResult.EXECUTION_FAILED, "high"):
                "流动性严重不足，建议取消交易或寻找替代标的"
        }
        
        # 查找匹配的建议
        key = (status, execution_result, risk_level)
        if key in recommendations:
            return recommendations[key]
        
        # 默认建议
        if status == LiquidityStatus.FAILED:
            return "交易无法执行，建议取消"
        elif risk_level == "high":
            return "高风险交易，建议谨慎执行"
        else:
            return "建议正常执行"
    
    def check_liquidity(self, trade_request: TradeRequest, 
                       market_data: MarketData) -> LiquidityCheckResult:
        """
        执行流动性检查
        
        核心逻辑: 检查交易规模是否超过市场成交额的0.1%
        
        Args:
            trade_request: 交易请求
            market_data: 市场数据
            
        Returns:
            流动性检查结果
        """
        # 验证输入数据
        if not trade_request.validate():
            logger.error("交易请求无效")
            raise ValueError("无效的交易请求")
        
        if not market_data.validate():
            logger.error("市场数据无效")
            raise ValueError("无效的市场数据")
        
        # 1. 计算流动性比例
        liquidity_ratio = self.calculate_liquidity_ratio(
            trade_request.quantity, 
            market_data.volume
        )
        
        # 2. 确定流动性状态
        status = self.determine_liquidity_status(liquidity_ratio)
        
        # 3. 计算执行比例
        execution_ratio = self.calculate_execution_ratio(
            status, liquidity_ratio, market_data.turnover_rate
        )
        
        # 4. 计算价格折价率
        price_discount = self.calculate_price_discount(
            status, liquidity_ratio, trade_request.direction
        )
        
        # 5. 确定执行结果
        execution_result = self.determine_execution_result(status, execution_ratio)
        
        # 6. 计算实际执行数量
        execution_quantity = int(trade_request.quantity * execution_ratio)
        
        # 7. 计算调整后价格
        adjusted_price = trade_request.price * (1 + price_discount)
        
        # 8. 确定风险等级
        risk_level = self.determine_risk_level(liquidity_ratio, execution_ratio)
        
        # 9. 生成执行建议
        recommendation = self.generate_recommendation(status, execution_result, risk_level)
        
        # 10. 创建检查结果
        result = LiquidityCheckResult(
            trade_request=trade_request,
            market_data=market_data,
            status=status,
            execution_result=execution_result,
            execution_ratio=execution_ratio,
            execution_quantity=execution_quantity,
            liquidity_discount=price_discount,
            adjusted_price=adjusted_price,
            liquidity_ratio=liquidity_ratio,
            risk_level=risk_level,
            recommendation=recommendation,
            timestamp=datetime.datetime.now().isoformat()
        )
        
        # 记录检查结果
        self._log_check_result(result)
        
        logger.info(f"流动性检查完成: {trade_request.ticker} {trade_request.direction} "
                   f"{trade_request.quantity}股 -> {execution_quantity}股 "
                   f"(状态: {status.value}, 执行: {execution_result.value})")
        
        return result
    
    def _log_check_result(self, result: LiquidityCheckResult):
        """记录检查结果到日志文件"""
        log_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "logs", "liquidity"
        )
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f"liquidity_check_{datetime.datetime.now().strftime('%Y%m%d')}.log")
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                log_entry = {
                    "timestamp": result.timestamp,
                    "ticker": result.trade_request.ticker,
                    "direction": result.trade_request.direction,
                    "request_quantity": result.trade_request.quantity,
                    "execution_quantity": result.execution_quantity,
                    "liquidity_ratio": result.liquidity_ratio,
                    "status": result.status.value,
                    "execution_result": result.execution_result.value,
                    "risk_level": result.risk_level
                }
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"记录流动性检查日志失败: {e}")
    
    def batch_check_liquidity(self, trade_requests: List[TradeRequest],
                             market_data_list: List[MarketData]) -> List[LiquidityCheckResult]:
        """
        批量检查流动性
        
        Args:
            trade_requests: 交易请求列表
            market_data_list: 市场数据列表
            
        Returns:
            流动性检查结果列表
        """
        if len(trade_requests) != len(market_data_list):
            logger.error(f"交易请求数量({len(trade_requests)})与市场数据数量({len(market_data_list)})不匹配")
            raise ValueError("交易请求与市场数据数量不匹配")
        
        results = []
        
        for i, (trade_request, market_data) in enumerate(zip(trade_requests, market_data_list)):
            try:
                result = self.check_liquidity(trade_request, market_data)
                results.append(result)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"批量检查进度: {i+1}/{len(trade_requests)}")
                    
            except Exception as e:
                logger.error(f"第{i+1}个交易流动性检查失败: {e}")
                # 创建默认失败结果
                failed_result = LiquidityCheckResult(
                    trade_request=trade_request,
                    market_data=market_data,
                    status=LiquidityStatus.FAILED,
                    execution_result=ExecutionResult.EXECUTION_FAILED,
                    execution_ratio=0.0,
                    execution_quantity=0,
                    liquidity_discount=0.0,
                    adjusted_price=trade_request.price,
                    liquidity_ratio=float('inf'),
                    risk_level="high",
                    recommendation="检查失败，建议人工审核",
                    timestamp=datetime.datetime.now().isoformat()
                )
                results.append(failed_result)
        
        logger.info(f"批量检查完成: {len(results)}/{len(trade_requests)} 个交易")
        return results
    
    def generate_liquidity_report(self, results: List[LiquidityCheckResult]) -> Dict:
        """
        生成流动性分析报告
        
        Args:
            results: 流动性检查结果列表
            
        Returns:
            流动性分析报告
        """
        if not results:
            return {"error": "无流动性检查结果"}
        
        total_checks = len(results)
        successful_checks = len([r for r in results if r.status != LiquidityStatus.FAILED])
        
        # 统计执行结果
        full_execution = len([r for r in results if r.execution_result == ExecutionResult.FULL_EXECUTION])
        partial_execution = len([r for r in results if r.execution_result == ExecutionResult.PARTIAL_EXECUTION])
        price_discount = len([r for r in results if r.execution_result == ExecutionResult.PRICE_DISCOUNT])
        execution_failed = len([r for r in results if r.execution_result == ExecutionResult.EXECUTION_FAILED])
        
        # 统计风险等级
        low_risk = len([r for r in results if r.risk_level == "low"])
        medium_risk = len([r for r in results if r.risk_level == "medium"])
        high_risk = len([r for r in results if r.risk_level == "high"])
        
        # 计算平均指标
        avg_liquidity_ratio = sum(r.liquidity_ratio for r in results if r.liquidity_ratio != float('inf')) / total_checks
        avg_execution_ratio = sum(r.execution_ratio for r in results) / total_checks
        avg_discount = sum(r.liquidity_discount for r in results) / total_checks
        
        # 生成报告
        report = {
            "metadata": {
                "report_type": "流动性检查分析报告",
                "generated_by": "LiquidityChecker",
                "threshold_ratio": self.threshold_ratio,
                "generation_time": datetime.datetime.now().isoformat(),
                "total_checks": total_checks
            },
            "summary_statistics": {
                "total_checks": total_checks,
                "successful_checks": successful_checks,
                "check_success_rate": f"{(successful_checks/total_checks)*100:.1f}%",
                "full_execution": full_execution,
                "partial_execution": partial_execution,
                "price_discount": price_discount,
                "execution_failed": execution_failed,
                "low_risk_trades": low_risk,
                "medium_risk_trades": medium_risk,
                "high_risk_trades": high_risk,
                "average_liquidity_ratio": avg_liquidity_ratio,
                "average_execution_ratio": avg_execution_ratio,
                "average_price_discount": f"{avg_discount*100:.2f}%"
            },
            "liquidity_status_distribution": {
                "normal": len([r for r in results if r.status == LiquidityStatus.NORMAL]),
                "warning": len([r for r in results if r.status == LiquidityStatus.WARNING]),
                "critical": len([r for r in results if r.status == LiquidityStatus.CRITICAL]),
                "failed": len([r for r in results if r.status == LiquidityStatus.FAILED])
            },
            "detailed_results": [result.to_dict() for result in results[:5]],  # 只保留前5个详细结果
            "risk_analysis": {
                "highest_risk_trades": self._identify_highest_risk_trades(results),
                "liquidity_bottlenecks": self._identify_liquidity_bottlenecks(results),
                "recommended_threshold_adjustment": self._recommend_threshold_adjustment(results)
            },
            "recommendations": [
                "高流动性比例交易建议分批执行",
                "流动性紧张标的建议使用限价单或算法交易",
                "定期调整流动性阈值以适应市场变化",
                "建立流动性预警机制，提前识别潜在风险"
            ]
        }
        
        return report
    
    def _identify_highest_risk_trades(self, results: List[LiquidityCheckResult]) -> List[Dict]:
        """识别最高风险交易"""
        high_risk_trades = []
        for result in results:
            if result.risk_level == "high" and result.liquidity_ratio != float('inf'):
                high_risk_trades.append({
                    "ticker": result.trade_request.ticker,
                    "direction": result.trade_request.direction,
                    "liquidity_ratio": result.liquidity_ratio,
                    "status": result.status.value,
                    "recommendation": result.recommendation
                })
        
        # 按流动性比例排序
        high_risk_trades.sort(key=lambda x: x["liquidity_ratio"], reverse=True)
        return high_risk_trades[:3]  # 返回前3个最高风险
    
    def _identify_liquidity_bottlenecks(self, results: List[LiquidityCheckResult]) -> List[str]:
        """识别流动性瓶颈"""
        bottlenecks = set()
        for result in results:
            if result.status in [LiquidityStatus.CRITICAL, LiquidityStatus.FAILED]:
                bottlenecks.add(result.trade_request.ticker)
        
        return list(bottlenecks)[:5]  # 返回前5个瓶颈标的
    
    def _recommend_threshold_adjustment(self, results: List[LiquidityCheckResult]) -> str:
        """推荐阈值调整建议"""
        failed_count = len([r for r in results if r.status == LiquidityStatus.FAILED])
        total_count = len(results)
        
        if total_count == 0:
            return "暂无足够数据推荐阈值调整"
        
        failure_rate = failed_count / total_count
        
        if failure_rate > 0.3:
            return f"失败率过高({failure_rate*100:.1f}%)，建议将失败阈值从{self.config['failed_threshold']*100:.2f}%提高到{self.config['failed_threshold']*1.5*100:.2f}%"
        elif failure_rate < 0.05:
            return f"失败率较低({failure_rate*100:.1f}%)，当前阈值设置合理"
        else:
            return f"失败率适中({failure_rate*100:.1f}%)，建议保持当前阈值设置"
    
    def save_report(self, report: Dict, output_path: Optional[str] = None) -> str:
        """保存流动性报告"""
        if output_path is None:
            output_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "reports", "liquidity"
            )
            os.makedirs(output_dir, exist_ok=True)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(output_dir, f"liquidity_report_{timestamp}.json")
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"流动性报告已保存: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"保存流动性报告失败: {e}")
            return ""

def main():
    """主函数 - 测试流动性检查器"""
    import argparse
    
    parser = argparse.ArgumentParser(description="流动性检查器测试")
    parser.add_argument("--threshold", type=float, default=0.001,
                       help="流动性阈值比例（默认0.1%）")
    parser.add_argument("--ticker", type=str, default="000001",
                       help="股票代码")
    parser.add_argument("--direction", choices=["buy", "sell"], default="buy",
                       help="交易方向")
    parser.add_argument("--quantity", type=int, default=10000,
                       help="交易数量（股）")
    parser.add_argument("--price", type=float, default=10.0,
                       help="交易价格")
    parser.add_argument("--market-volume", type=float, default=10000000,
                       help="市场成交量（股）")
    parser.add_argument("--market-amount", type=float, default=100000000,
                       help="市场成交额（元）")
    parser.add_argument("--turnover-rate", type=float, default=2.5,
                       help="换手率（%）")
    parser.add_argument("--batch", action="store_true",
                       help="批量测试模式")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("💧 流动性检查器测试")
    print("=" * 60)
    
    try:
        # 初始化检查器
        checker = LiquidityChecker(threshold_ratio=args.threshold)
        
        if args.batch:
            # 批量测试
            print(f"🧪 批量测试模式，阈值比例: {args.threshold*100:.2f}%")
            
            # 生成测试数据
            trade_requests = []
            market_data_list = []
            
            for i in range(5):
                trade_requests.append(TradeRequest(
                    ticker=f"{args.ticker}",
                    direction="buy" if i % 2 == 0 else "sell",
                    quantity=args.quantity * (2 ** i),  # 指数增长
                    price=args.price + i * 0.5,
                    request_time=datetime.datetime.now().isoformat()
                ))
                
                market_data_list.append(MarketData(
                    ticker=f"{args.ticker}",
                    date=datetime.datetime.now().strftime("%Y-%m-%d"),
                    volume=args.market_volume * (1 + i * 0.5),
                    amount=args.market_amount * (1 + i * 0.5),
                    turnover_rate=args.turnover_rate + i * 0.5,
                    avg_price=args.price + i * 0.5
                ))
            
            # 批量检查
            results = checker.batch_check_liquidity(trade_requests, market_data_list)
            
            # 生成报告
            report = checker.generate_liquidity_report(results)
            
            # 输出摘要
            summary = report["summary_statistics"]
            print(f"\n📊 批量测试结果摘要:")
            print(f"   总检查数: {summary['total_checks']}")
            print(f"   成功检查: {summary['successful_checks']}")
            print(f"   成功率: {summary['check_success_rate']}")
            print(f"   完全成交: {summary['full_execution']}")
            print(f"   部分成交: {summary['partial_execution']}")
            print(f"   价格折价: {summary['price_discount']}")
            print(f"   成交失败: {summary['execution_failed']}")
            print(f"   低风险交易: {summary['low_risk_trades']}")
            print(f"   中风险交易: {summary['medium_risk_trades']}")
            print(f"   高风险交易: {summary['high_risk_trades']}")
            print(f"   平均流动性比例: {summary['average_liquidity_ratio']:.6f}")
            print(f"   平均执行比例: {summary['average_execution_ratio']:.2f}")
            print(f"   平均价格折价: {summary['average_price_discount']}")
            
            # 保存报告
            report_file = checker.save_report(report)
            if report_file:
                print(f"   报告文件: {report_file}")
            
        else:
            # 单次测试
            print(f"🧪 单次测试，阈值比例: {args.threshold*100:.2f}%")
            print(f"   股票代码: {args.ticker}")
            print(f"   交易方向: {args.direction}")
            print(f"   交易数量: {args.quantity}股")
            print(f"   交易价格: {args.price}")
            print(f"   市场成交量: {args.market_volume:.0f}股")
            print(f"   市场成交额: {args.market_amount:.0f}元")
            print(f"   换手率: {args.turnover_rate}%")
            
            # 创建交易请求和市场数据
            trade_request = TradeRequest(
                ticker=args.ticker,
                direction=args.direction,
                quantity=args.quantity,
                price=args.price,
                request_time=datetime.datetime.now().isoformat()
            )
            
            market_data = MarketData(
                ticker=args.ticker,
                date=datetime.datetime.now().strftime("%Y-%m-%d"),
                volume=args.market_volume,
                amount=args.market_amount,
                turnover_rate=args.turnover_rate,
                avg_price=args.price
            )
            
            # 执行检查
            result = checker.check_liquidity(trade_request, market_data)
            
            # 输出结果
            print(f"\n📈 流动性检查结果:")
            print(f"   流动性状态: {result.status.value}")
            print(f"   执行结果: {result.execution_result.value}")
            print(f"   流动性比例: {result.liquidity_ratio:.6f}")
            print(f"   执行比例: {result.execution_ratio:.2f}")
            print(f"   请求数量: {result.trade_request.quantity}股")
            print(f"   执行数量: {result.execution_quantity}股")
            print(f"   价格折价率: {result.liquidity_discount*100:.2f}%")
            print(f"   原始价格: {result.trade_request.price:.4f}")
            print(f"   调整后价格: {result.adjusted_price:.4f}")
            print(f"   风险等级: {result.risk_level}")
            print(f"   执行建议: {result.recommendation}")
        
        print("\n" + "=" * 60)
        print("🎉 流动性检查器测试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 流动性检查器测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()