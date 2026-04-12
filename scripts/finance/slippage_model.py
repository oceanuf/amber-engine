#!/usr/bin/env python3
"""
滑点仿真模型 (Slippage Simulation Model)
版本: 1.0.0
描述: 为交易清算引入真实世界的执行摩擦，告别"实验室真空价格"。
功能:
  1. 基于价格波动率计算动态滑点系数
  2. 区分买入滑点(向上)与卖出滑点(向下)
  3. 支持多种滑点计算模型
  4. 提供滑点损失量化分析
法典依据: 任务指令[2616-0412-P4] 交易审判维度完善与滑点仿真
"""

import os
import sys
import json
import datetime
import logging
import random
import math
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, asdict

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class PriceData:
    """价格数据容器"""
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    amount: float  # 成交额
    
    def validate(self) -> bool:
        """验证价格数据有效性"""
        if self.high_price < self.low_price:
            return False
        if self.close_price < 0 or self.open_price < 0:
            return False
        if self.volume < 0 or self.amount < 0:
            return False
        return True

@dataclass
class SlippageResult:
    """滑点计算结果"""
    original_price: float  # 原始价格（收盘价）
    execution_price: float  # 执行价格（含滑点）
    slippage_rate: float   # 滑点率 (百分比)
    slippage_amount: float # 滑点金额 (单股)
    direction: str        # 交易方向: "buy" 或 "sell"
    model_used: str       # 使用的滑点模型
    volatility: float     # 日内波动率
    confidence: float     # 模型置信度 (0-1)
    timestamp: str        # 计算时间戳
    
    def to_dict(self):
        return asdict(self)

class SlippageModel:
    """滑点仿真模型核心类"""
    
    def __init__(self, model_type: str = "dynamic_volatility"):
        """
        初始化滑点模型
        
        Args:
            model_type: 滑点模型类型
                - "dynamic_volatility": 动态波动率模型 (默认)
                - "fixed_percentage": 固定百分比模型
                - "volume_weighted": 成交量加权模型
        """
        self.model_type = model_type
        self.model_config = self._load_model_config()
        
        logger.info(f"滑点模型初始化完成，模型类型: {model_type}")
    
    def _load_model_config(self) -> Dict:
        """加载模型配置"""
        config = {
            "dynamic_volatility": {
                "base_slippage": 0.001,  # 基础滑点率 0.1%
                "volatility_multiplier": 1.0,  # 波动率乘数
                "min_slippage": 0.0005,  # 最小滑点率 0.05%
                "max_slippage": 0.02,    # 最大滑点率 2.0%
                "volume_sensitivity": 0.3,  # 成交量敏感度
                "random_factor": 0.1     # 随机因子权重
            },
            "fixed_percentage": {
                "buy_slippage": 0.002,   # 买入滑点 0.2%
                "sell_slippage": 0.0015, # 卖出滑点 0.15%
                "apply_to_all": True     # 应用于所有交易
            },
            "volume_weighted": {
                "volume_threshold": 100000000,  # 成交量阈值 (1亿)
                "low_volume_penalty": 0.003,    # 低成交量惩罚 0.3%
                "high_volume_bonus": 0.0005,    # 高成交量奖励 0.05%
                "volume_exponent": 0.5          # 成交量指数
            }
        }
        
        return config.get(self.model_type, config["dynamic_volatility"])
    
    def calculate_volatility(self, price_data: PriceData) -> float:
        """
        计算日内波动率
        
        公式: volatility = (high - low) / low
        这是相对波动率，表示价格日内最大相对变化幅度
        
        Args:
            price_data: 价格数据
            
        Returns:
            波动率 (小数形式，如 0.05 表示 5%)
        """
        if price_data.low_price == 0:
            logger.warning("低价为0，无法计算波动率")
            return 0.0
        
        volatility = (price_data.high_price - price_data.low_price) / price_data.low_price
        
        # 防止极端波动率
        volatility = min(volatility, 0.2)  # 最大20%波动率
        volatility = max(volatility, 0.001)  # 最小0.1%波动率
        
        logger.debug(f"计算波动率: {volatility:.4f} (高: {price_data.high_price}, 低: {price_data.low_price})")
        return volatility
    
    def calculate_volume_factor(self, price_data: PriceData) -> float:
        """
        计算成交量影响因子
        
        成交量越大，滑点通常越小
        公式: volume_factor = 1 / (1 + sqrt(volume / volume_threshold))
        
        Args:
            price_data: 价格数据
            
        Returns:
            成交量因子 (0-1之间)
        """
        config = self.model_config
        volume_threshold = config.get("volume_threshold", 100000000)
        
        if price_data.volume <= 0:
            return 1.0
        
        # 使用平方根衰减函数
        normalized_volume = price_data.volume / volume_threshold
        if normalized_volume <= 0:
            return 1.0
        
        volume_factor = 1.0 / (1.0 + math.sqrt(normalized_volume))
        
        # 应用成交量敏感度
        volume_sensitivity = config.get("volume_sensitivity", 0.3)
        volume_factor = 1.0 - (1.0 - volume_factor) * volume_sensitivity
        
        logger.debug(f"计算成交量因子: {volume_factor:.4f} (成交量: {price_data.volume:.0f})")
        return volume_factor
    
    def calculate_base_slippage(self, direction: str, price_data: PriceData) -> float:
        """
        计算基础滑点率
        
        Args:
            direction: 交易方向 ("buy" 或 "sell")
            price_data: 价格数据
            
        Returns:
            基础滑点率 (小数形式)
        """
        config = self.model_config
        
        if self.model_type == "fixed_percentage":
            # 固定百分比模型
            if direction == "buy":
                return config.get("buy_slippage", 0.002)
            else:  # sell
                return config.get("sell_slippage", 0.0015)
        
        elif self.model_type == "dynamic_volatility":
            # 动态波动率模型
            volatility = self.calculate_volatility(price_data)
            volume_factor = self.calculate_volume_factor(price_data)
            
            # 基础滑点率 * 波动率乘数 * 成交量因子
            base_slippage = config.get("base_slippage", 0.001)
            volatility_multiplier = config.get("volatility_multiplier", 1.0)
            
            base_rate = base_slippage * (1.0 + volatility * volatility_multiplier) * volume_factor
            
            # 方向调整：买入通常滑点更高
            if direction == "buy":
                base_rate *= 1.2  # 买入滑点增加20%
            
            # 添加随机因子
            random_factor = config.get("random_factor", 0.1)
            random_adjustment = random.uniform(-random_factor, random_factor) * base_rate
            base_rate += random_adjustment
            
            # 应用上下限
            min_slippage = config.get("min_slippage", 0.0005)
            max_slippage = config.get("max_slippage", 0.02)
            base_rate = max(min_slippage, min(base_rate, max_slippage))
            
            return base_rate
        
        elif self.model_type == "volume_weighted":
            # 成交量加权模型
            volume_threshold = config.get("volume_threshold", 100000000)
            
            if price_data.volume < volume_threshold:
                # 低成交量惩罚
                low_volume_penalty = config.get("low_volume_penalty", 0.003)
                base_rate = low_volume_penalty
            else:
                # 高成交量奖励
                high_volume_bonus = config.get("high_volume_bonus", 0.0005)
                base_rate = high_volume_bonus
            
            # 方向调整
            if direction == "buy":
                base_rate *= 1.15
            
            return base_rate
        
        else:
            # 默认使用动态波动率模型
            return 0.001
    
    def calculate_slippage(self, direction: str, original_price: float, 
                          price_data: Optional[PriceData] = None) -> SlippageResult:
        """
        计算滑点价格
        
        核心公式: Price_real = Price_close × (1 ± α)
        其中 α 为滑点率，方向决定正负号
        
        Args:
            direction: 交易方向 ("buy" 或 "sell")
            original_price: 原始价格（通常为收盘价）
            price_data: 价格数据（可选，用于计算波动率）
            
        Returns:
            滑点计算结果
        """
        if price_data is None:
            # 如果没有提供价格数据，使用默认值
            price_data = PriceData(
                open_price=original_price,
                high_price=original_price * 1.05,  # 假设5%波动
                low_price=original_price * 0.95,
                close_price=original_price,
                volume=1000000,
                amount=original_price * 1000000
            )
        
        if not price_data.validate():
            logger.warning("价格数据无效，使用默认价格数据")
            price_data = PriceData(
                open_price=original_price,
                high_price=original_price,
                low_price=original_price,
                close_price=original_price,
                volume=1000000,
                amount=original_price * 1000000
            )
        
        # 计算基础滑点率
        base_slippage_rate = self.calculate_base_slippage(direction, price_data)
        
        # 计算波动率（用于结果报告）
        volatility = self.calculate_volatility(price_data)
        
        # 确定滑点方向
        # 买入：价格上涨 -> 执行价格更高
        # 卖出：价格下跌 -> 执行价格更低
        if direction == "buy":
            execution_price = original_price * (1 + base_slippage_rate)
        elif direction == "sell":
            execution_price = original_price * (1 - base_slippage_rate)
        else:
            logger.error(f"未知交易方向: {direction}，默认使用买入方向")
            direction = "buy"
            execution_price = original_price * (1 + base_slippage_rate)
        
        # 计算滑点金额（单股）
        slippage_amount = abs(execution_price - original_price)
        
        # 计算模型置信度
        confidence = self._calculate_confidence(price_data, base_slippage_rate)
        
        # 生成结果
        result = SlippageResult(
            original_price=original_price,
            execution_price=execution_price,
            slippage_rate=base_slippage_rate,
            slippage_amount=slippage_amount,
            direction=direction,
            model_used=self.model_type,
            volatility=volatility,
            confidence=confidence,
            timestamp=datetime.datetime.now().isoformat()
        )
        
        logger.info(f"滑点计算完成: {direction} {original_price:.4f} -> {execution_price:.4f} "
                   f"(滑点率: {base_slippage_rate*100:.2f}%, 波动率: {volatility*100:.2f}%)")
        
        return result
    
    def _calculate_confidence(self, price_data: PriceData, slippage_rate: float) -> float:
        """
        计算模型置信度
        
        基于数据完整性和滑点率合理性
        """
        confidence = 0.8  # 基础置信度
        
        # 1. 数据完整性检查
        if price_data.high_price == price_data.low_price:
            confidence *= 0.7  # 无波动数据，置信度降低
            logger.debug("高低价相同，置信度降低")
        
        if price_data.volume <= 0:
            confidence *= 0.6  # 无成交量数据
            logger.debug("无成交量数据，置信度降低")
        
        # 2. 滑点率合理性检查
        if slippage_rate > 0.02:  # 超过2%的滑点率可能不合理
            confidence *= 0.5
            logger.debug("滑点率过高，置信度降低")
        
        # 3. 波动率合理性检查
        volatility = self.calculate_volatility(price_data)
        if volatility > 0.1:  # 超过10%的日内波动率
            confidence *= 0.8  # 高波动率降低置信度
        
        # 确保置信度在合理范围内
        confidence = max(0.1, min(confidence, 1.0))
        
        return confidence
    
    def batch_calculate_slippage(self, trades: List[Dict]) -> List[SlippageResult]:
        """
        批量计算滑点
        
        Args:
            trades: 交易列表，每项包含:
                - direction: 交易方向
                - original_price: 原始价格
                - price_data: 价格数据（可选）
                
        Returns:
            滑点计算结果列表
        """
        results = []
        
        for i, trade in enumerate(trades):
            try:
                direction = trade.get("direction", "buy")
                original_price = trade.get("original_price", 0.0)
                price_data_dict = trade.get("price_data")
                
                if price_data_dict:
                    price_data = PriceData(**price_data_dict)
                else:
                    price_data = None
                
                result = self.calculate_slippage(direction, original_price, price_data)
                results.append(result)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"批量计算进度: {i+1}/{len(trades)}")
                    
            except Exception as e:
                logger.error(f"第{i+1}个交易滑点计算失败: {e}")
                # 添加默认结果
                default_result = SlippageResult(
                    original_price=trade.get("original_price", 0.0),
                    execution_price=trade.get("original_price", 0.0),
                    slippage_rate=0.0,
                    slippage_amount=0.0,
                    direction=trade.get("direction", "buy"),
                    model_used=self.model_type,
                    volatility=0.0,
                    confidence=0.1,
                    timestamp=datetime.datetime.now().isoformat()
                )
                results.append(default_result)
        
        logger.info(f"批量计算完成: {len(results)}/{len(trades)} 个交易")
        return results
    
    def generate_slippage_report(self, results: List[SlippageResult]) -> Dict:
        """
        生成滑点分析报告
        
        Args:
            results: 滑点计算结果列表
            
        Returns:
            滑点分析报告
        """
        if not results:
            return {"error": "无滑点计算结果"}
        
        total_trades = len(results)
        buy_trades = [r for r in results if r.direction == "buy"]
        sell_trades = [r for r in results if r.direction == "sell"]
        
        # 计算统计指标
        avg_slippage_rate = sum(r.slippage_rate for r in results) / total_trades
        avg_buy_slippage = sum(r.slippage_rate for r in buy_trades) / len(buy_trades) if buy_trades else 0
        avg_sell_slippage = sum(r.slippage_rate for r in sell_trades) / len(sell_trades) if sell_trades else 0
        
        total_slippage_amount = sum(r.slippage_amount for r in results)
        avg_confidence = sum(r.confidence for r in results) / total_trades
        
        # 生成报告
        report = {
            "metadata": {
                "report_type": "滑点仿真分析报告",
                "generated_by": "SlippageModel",
                "model_type": self.model_type,
                "generation_time": datetime.datetime.now().isoformat(),
                "total_trades_analyzed": total_trades
            },
            "summary_statistics": {
                "total_trades": total_trades,
                "buy_trades": len(buy_trades),
                "sell_trades": len(sell_trades),
                "average_slippage_rate": avg_slippage_rate,
                "average_buy_slippage_rate": avg_buy_slippage,
                "average_sell_slippage_rate": avg_sell_slippage,
                "total_slippage_amount": total_slippage_amount,
                "average_confidence": avg_confidence,
                "model_effectiveness": f"{(1 - avg_slippage_rate) * 100:.1f}%"
            },
            "distribution_analysis": {
                "slippage_rate_distribution": self._calculate_distribution([r.slippage_rate for r in results]),
                "volatility_distribution": self._calculate_distribution([r.volatility for r in results]),
                "confidence_distribution": self._calculate_distribution([r.confidence for r in results])
            },
            "detailed_results": [result.to_dict() for result in results[:10]],  # 只保留前10个详细结果
            "recommendations": [
                "买入交易平均滑点率较高，建议优化买入时机",
                "高波动率标的滑点风险较大，需谨慎交易",
                "低成交量标的执行价格不确定性较高",
                "建议使用限价单而非市价单以减少滑点损失"
            ]
        }
        
        return report
    
    def _calculate_distribution(self, values: List[float]) -> Dict:
        """计算数值分布"""
        if not values:
            return {}
        
        import statistics
        
        try:
            return {
                "min": min(values),
                "max": max(values),
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
                "count": len(values)
            }
        except:
            return {
                "min": min(values),
                "max": max(values),
                "mean": sum(values) / len(values),
                "count": len(values)
            }
    
    def save_report(self, report: Dict, output_path: Optional[str] = None) -> str:
        """保存滑点报告"""
        if output_path is None:
            output_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "reports", "slippage"
            )
            os.makedirs(output_dir, exist_ok=True)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(output_dir, f"slippage_report_{timestamp}.json")
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"滑点报告已保存: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"保存滑点报告失败: {e}")
            return ""

def main():
    """主函数 - 测试滑点模型"""
    import argparse
    
    parser = argparse.ArgumentParser(description="滑点仿真模型测试")
    parser.add_argument("--model", choices=["dynamic_volatility", "fixed_percentage", "volume_weighted"],
                       default="dynamic_volatility", help="滑点模型类型")
    parser.add_argument("--direction", choices=["buy", "sell"], default="buy",
                       help="交易方向")
    parser.add_argument("--price", type=float, default=10.0, help="原始价格")
    parser.add_argument("--high", type=float, default=10.5, help="最高价")
    parser.add_argument("--low", type=float, default=9.5, help="最低价")
    parser.add_argument("--volume", type=float, default=1000000, help="成交量")
    parser.add_argument("--batch", action="store_true", help="批量测试模式")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🎯 滑点仿真模型测试")
    print("=" * 60)
    
    try:
        # 初始化模型
        model = SlippageModel(model_type=args.model)
        
        if args.batch:
            # 批量测试
            print(f"🧪 批量测试模式，模型类型: {args.model}")
            
            # 生成测试数据
            test_trades = []
            for i in range(5):
                test_trades.append({
                    "direction": "buy" if i % 2 == 0 else "sell",
                    "original_price": args.price + i * 0.5,
                    "price_data": {
                        "open_price": args.price + i * 0.5,
                        "high_price": args.high + i * 0.5,
                        "low_price": args.low + i * 0.5,
                        "close_price": args.price + i * 0.5,
                        "volume": args.volume * (1 + i * 0.2),
                        "amount": (args.price + i * 0.5) * args.volume * (1 + i * 0.2)
                    }
                })
            
            # 批量计算
            results = model.batch_calculate_slippage(test_trades)
            
            # 生成报告
            report = model.generate_slippage_report(results)
            
            # 输出摘要
            summary = report["summary_statistics"]
            print(f"\n📊 批量测试结果摘要:")
            print(f"   总交易数: {summary['total_trades']}")
            print(f"   买入交易: {summary['buy_trades']}")
            print(f"   卖出交易: {summary['sell_trades']}")
            print(f"   平均滑点率: {summary['average_slippage_rate']*100:.2f}%")
            print(f"   买入平均滑点: {summary['average_buy_slippage_rate']*100:.2f}%")
            print(f"   卖出平均滑点: {summary['average_sell_slippage_rate']*100:.2f}%")
            print(f"   总滑点金额: {summary['total_slippage_amount']:.2f}")
            
            # 保存报告
            report_file = model.save_report(report)
            if report_file:
                print(f"   报告文件: {report_file}")
            
        else:
            # 单次测试
            print(f"🧪 单次测试，模型类型: {args.model}")
            print(f"   交易方向: {args.direction}")
            print(f"   原始价格: {args.price}")
            
            # 创建价格数据
            price_data = PriceData(
                open_price=args.price,
                high_price=args.high,
                low_price=args.low,
                close_price=args.price,
                volume=args.volume,
                amount=args.price * args.volume
            )
            
            # 计算滑点
            result = model.calculate_slippage(args.direction, args.price, price_data)
            
            # 输出结果
            print(f"\n📈 滑点计算结果:")
            print(f"   原始价格: {result.original_price:.4f}")
            print(f"   执行价格: {result.execution_price:.4f}")
            print(f"   滑点率: {result.slippage_rate*100:.2f}%")
            print(f"   滑点金额(单股): {result.slippage_amount:.4f}")
            print(f"   日内波动率: {result.volatility*100:.2f}%")
            print(f"   模型置信度: {result.confidence:.2f}")
            print(f"   使用模型: {result.model_used}")
        
        print("\n" + "=" * 60)
        print("🎉 滑点模型测试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 滑点模型测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()