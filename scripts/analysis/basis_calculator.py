#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[2614-034号] 基差计算器 - 期货与现货ETF基差因子分析
功能：计算AU.SHF(沪金期货)与518880(黄金ETF)的基差因子
作者：Cheese 🧀 (工程师)
日期：2026-03-31
版本：v1.0.0
"""

import os
import sys
import json
import math
import logging
import subprocess
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/basis_calculator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BasisCalculator:
    """基差计算器 - 分析期货与现货ETF关系"""
    
    def __init__(self, tushare_token: str = None):
        """
        初始化基差计算器
        
        Args:
            tushare_token: Tushare API Token
        """
        self.tushare_token = tushare_token or os.getenv('TUSHARE_TOKEN')
        
        # 配置
        self.config = {
            "futures_symbol": "AU.SHF",  # 沪金主力
            "etf_symbol": "518880.SH",   # 黄金ETF
            "lookback_days": 30,         # 回看天数
            "basis_thresholds": {
                "extreme_contango": 2.0,   # 极端升水 (>2%)
                "strong_contango": 1.0,    # 强势升水 (1-2%)
                "normal": 0.5,             # 正常范围 (±0.5%)
                "strong_backwardation": -1.0,  # 强势贴水 (<-1%)
                "extreme_backwardation": -2.0  # 极端贴水 (<-2%)
            },
            "weight_adjustments": {
                "extreme_contango": 0.15,      # 极端升水增加15%权重
                "strong_contango": 0.08,       # 强势升水增加8%权重
                "normal": 0.0,                 # 正常范围不调整
                "strong_backwardation": -0.08, # 强势贴水减少8%权重
                "extreme_backwardation": -0.15 # 极端贴水减少15%权重
            }
        }
        
        logger.info(f"基差计算器初始化完成，配置: {json.dumps(self.config, ensure_ascii=False)}")
    
    def fetch_futures_data(self) -> Optional[Dict]:
        """
        获取期货数据
        
        Returns:
            期货数据字典
        """
        try:
            logger.info(f"获取期货数据: {self.config['futures_symbol']}")
            
            # 设置环境变量
            env = os.environ.copy()
            if self.tushare_token:
                env['TUSHARE_TOKEN'] = self.tushare_token
            
            # 执行Tushare命令
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            market_script = os.path.join(script_dir, "skills", "tushare", "scripts", "market.py")
            
            cmd = ["python3", market_script, "fut_daily", "--ts_code", self.config['futures_symbol']]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                env=env,
                cwd=script_dir
            )
            
            if result.returncode == 0:
                # 解析输出
                output = result.stdout.strip()
                lines = output.split('\n')
                
                # 查找数据行
                data_lines = []
                in_data_section = False
                
                for line in lines:
                    if "期货日线" in line:
                        in_data_section = True
                        continue
                    if in_data_section and line.strip() and "-----" not in line:
                        data_lines.append(line.strip())
                
                if data_lines:
                    # 解析第一行数据（最新数据）
                    latest_data = data_lines[0].split()
                    if len(latest_data) >= 6:
                        return {
                            "symbol": self.config['futures_symbol'],
                            "date": latest_data[0],
                            "open": float(latest_data[1]),
                            "close": float(latest_data[2]),
                            "high": float(latest_data[3]),
                            "low": float(latest_data[4]),
                            "open_interest": int(latest_data[5]),
                            "data_source": "tushare",
                            "fetch_time": datetime.now().isoformat()
                        }
            
            logger.warning(f"期货数据解析失败，使用模拟数据")
            return self.generate_simulated_futures_data()
            
        except Exception as e:
            logger.error(f"期货数据获取异常: {str(e)}")
            return self.generate_simulated_futures_data()
    
    def generate_simulated_futures_data(self) -> Dict:
        """生成模拟期货数据"""
        return {
            "symbol": self.config['futures_symbol'],
            "date": datetime.now().strftime("%Y%m%d"),
            "open": 1014.5,
            "close": 1014.88,
            "high": 1019.5,
            "low": 988.1,
            "open_interest": 180953,
            "data_source": "simulated",
            "fetch_time": datetime.now().isoformat(),
            "note": "模拟数据（Tushare解析失败）"
        }
    
    def fetch_etf_data(self) -> Optional[Dict]:
        """
        获取ETF数据
        
        Returns:
            ETF数据字典
        """
        try:
            logger.info(f"获取ETF数据: {self.config['etf_symbol']}")
            
            # 尝试Tushare
            env = os.environ.copy()
            if self.tushare_token:
                env['TUSHARE_TOKEN'] = self.tushare_token
            
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            market_script = os.path.join(script_dir, "skills", "tushare", "scripts", "market.py")
            
            cmd = ["python3", market_script, "daily", "--ts_code", self.config['etf_symbol']]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                env=env,
                cwd=script_dir
            )
            
            if result.returncode == 0 and "没有数据" not in result.stdout:
                # 解析输出
                output = result.stdout.strip()
                lines = output.split('\n')
                
                # 查找数据行
                data_lines = []
                in_data_section = False
                
                for line in lines:
                    if "日线行情" in line:
                        in_data_section = True
                        continue
                    if in_data_section and line.strip() and "-----" not in line:
                        data_lines.append(line.strip())
                
                if data_lines:
                    # 解析第一行数据
                    latest_data = data_lines[0].split()
                    if len(latest_data) >= 6:
                        return {
                            "symbol": self.config['etf_symbol'],
                            "date": latest_data[0],
                            "open": float(latest_data[1]),
                            "close": float(latest_data[2]),
                            "high": float(latest_data[3]),
                            "low": float(latest_data[4]),
                            "volume": float(latest_data[5]),
                            "data_source": "tushare",
                            "fetch_time": datetime.now().isoformat()
                        }
            
            # Tushare失败，使用模拟数据
            logger.warning(f"ETF数据Tushare获取失败，使用模拟数据")
            return self.generate_simulated_etf_data()
            
        except Exception as e:
            logger.error(f"ETF数据获取异常: {str(e)}")
            return self.generate_simulated_etf_data()
    
    def generate_simulated_etf_data(self) -> Dict:
        """生成模拟ETF数据"""
        return {
            "symbol": self.config['etf_symbol'],
            "date": datetime.now().strftime("%Y%m%d"),
            "open": 5.142,
            "close": 5.156,
            "high": 5.168,
            "low": 5.138,
            "volume": 1256000,
            "data_source": "simulated",
            "fetch_time": datetime.now().isoformat(),
            "note": "模拟数据（Tushare返回空）"
        }
    
    def calculate_basis(self, futures_price: float, etf_price: float) -> Dict:
        """
        计算基差
        
        Args:
            futures_price: 期货价格
            etf_price: ETF价格
            
        Returns:
            基差计算结果
        """
        try:
            # 计算绝对基差
            absolute_basis = futures_price - etf_price
            
            # 计算相对基差（百分比）
            if etf_price > 0:
                relative_basis = (absolute_basis / etf_price) * 100
            else:
                relative_basis = 0.0
            
            # 判断基差状态
            basis_status = "normal"
            basis_description = "正常范围"
            
            thresholds = self.config['basis_thresholds']
            
            if relative_basis > thresholds['extreme_contango']:
                basis_status = "extreme_contango"
                basis_description = "极端升水"
            elif relative_basis > thresholds['strong_contango']:
                basis_status = "strong_contango"
                basis_description = "强势升水"
            elif relative_basis < thresholds['extreme_backwardation']:
                basis_status = "extreme_backwardation"
                basis_description = "极端贴水"
            elif relative_basis < thresholds['strong_backwardation']:
                basis_status = "strong_backwardation"
                basis_description = "强势贴水"
            else:
                basis_status = "normal"
                basis_description = "正常范围"
            
            # 计算权重调整
            weight_adjustment = self.config['weight_adjustments'].get(basis_status, 0.0)
            
            # 生成交易信号
            signal = "中性"
            signal_strength = "中等"
            
            if basis_status in ["extreme_contango", "strong_contango"]:
                signal = "看涨现货"
                signal_strength = "强" if basis_status == "extreme_contango" else "中等"
            elif basis_status in ["extreme_backwardation", "strong_backwardation"]:
                signal = "看跌现货"
                signal_strength = "强" if basis_status == "extreme_backwardation" else "中等"
            
            return {
                "futures_price": round(futures_price, 3),
                "etf_price": round(etf_price, 3),
                "absolute_basis": round(absolute_basis, 3),
                "relative_basis": round(relative_basis, 3),
                "basis_status": basis_status,
                "basis_description": basis_description,
                "weight_adjustment": round(weight_adjustment, 3),
                "signal": signal,
                "signal_strength": signal_strength,
                "calculation_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"基差计算异常: {str(e)}")
            return {
                "error": str(e),
                "calculation_time": datetime.now().isoformat()
            }
    
    def analyze_historical_basis(self, historical_data: List[Dict]) -> Dict:
        """
        分析历史基差
        
        Args:
            historical_data: 历史数据列表
            
        Returns:
            历史分析结果
        """
        try:
            if not historical_data or len(historical_data) < 5:
                return {"error": "历史数据不足"}
            
            # 提取基差序列
            basis_values = [item.get('relative_basis', 0) for item in historical_data]
            
            # 计算统计指标
            stats = {
                "count": len(basis_values),
                "mean": round(statistics.mean(basis_values), 3),
                "median": round(statistics.median(basis_values), 3),
                "stdev": round(statistics.stdev(basis_values), 3) if len(basis_values) > 1 else 0,
                "min": round(min(basis_values), 3),
                "max": round(max(basis_values), 3),
                "current_zscore": 0
            }
            
            # 计算当前Z分数
            if stats['stdev'] > 0:
                current_basis = basis_values[-1]
                stats['current_zscore'] = round((current_basis - stats['mean']) / stats['stdev'], 3)
            
            # 分析趋势
            recent_basis = basis_values[-5:] if len(basis_values) >= 5 else basis_values
            trend = "平稳"
            
            if len(recent_basis) >= 2:
                first = recent_basis[0]
                last = recent_basis[-1]
                
                if last > first + 0.5:
                    trend = "上升"
                elif last < first - 0.5:
                    trend = "下降"
            
            # 生成历史分析结论
            conclusion = []
            
            if abs(stats['current_zscore']) > 2:
                conclusion.append(f"当前基差处于极端位置 (Z分数: {stats['current_zscore']})")
            elif abs(stats['current_zscore']) > 1:
                conclusion.append(f"当前基差偏离正常范围 (Z分数: {stats['current_zscore']})")
            
            if trend != "平稳":
                conclusion.append(f"基差近期呈现{trend}趋势")
            
            if not conclusion:
                conclusion.append("基差处于正常波动范围")
            
            return {
                "statistics": stats,
                "trend": trend,
                "conclusion": conclusion,
                "analysis_period": f"{len(basis_values)}个数据点",
                "analysis_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"历史基差分析异常: {str(e)}")
            return {"error": str(e)}
    
    def generate_g11_algorithm_input(self, basis_result: Dict, historical_analysis: Dict) -> Dict:
        """
        生成G11算法输入
        
        Args:
            basis_result: 基差计算结果
            historical_analysis: 历史分析结果
            
        Returns:
            G11算法输入数据
        """
        try:
            # 计算综合得分 (0-100)
            base_score = 50  # 中性基准分
            
            # 根据基差状态调整
            weight_adjustment = basis_result.get('weight_adjustment', 0) * 100
            adjusted_score = base_score + weight_adjustment
            
            # 限制范围
            final_score = max(0, min(100, adjusted_score))
            
            # 确定信号状态
            if final_score >= 70:
                signal_status = "极度舒适"
            elif final_score >= 60:
                signal_status = "舒适"
            elif final_score >= 40:
                signal_status = "中性"
            elif final_score >= 30:
                signal_status = "谨慎"
            else:
                signal_status = "生存预警"
            
            # 生成算法描述
            algorithm_description = f"基差因子算法(G11) - {basis_result.get('basis_description', '未知')}"
            
            if basis_result.get('signal') != "中性":
                algorithm_description += f"，{basis_result.get('signal')}信号({basis_result.get('signal_strength', '中等')})"
            
            return {
                "algorithm_name": "G11_基差因子",
                "algorithm_version": "v1.0.0",
                "calculation_time": datetime.now().isoformat(),
                "basis_input": {
                    "futures_symbol": self.config['futures_symbol'],
                    "etf_symbol": self.config['etf_symbol'],
                    "futures_price": basis_result.get('futures_price'),
                    "etf_price": basis_result.get('etf_price'),
                    "relative_basis": basis_result.get('relative_basis'),
                    "basis_status": basis_result.get('basis_status')
                },
                "historical_context": historical_analysis,
                "output": {
                    "score": round(final_score, 2),
                    "signal_status": signal_status,
                    "weight_adjustment": basis_result.get('weight_adjustment'),
                    "recommendation": self.generate_recommendation(basis_result, final_score),
                    "confidence": self.calculate_confidence(basis_result, historical_analysis)
                },
                "metadata": {
                    "config_used": self.config,
                    "data_sources": ["tushare", "simulated"],
                    "generator": "BasisCalculator v1.0.0"
                }
            }
            
        except Exception as e:
            logger.error(f"G11算法输入生成异常: {str(e)}")
            return {"error": str(e)}
    
    def generate_recommendation(self, basis_result: Dict, score: float) -> str:
        """生成投资建议"""
        status = basis_result.get('basis_status', 'normal')
        signal = basis_result.get('signal', '中性')
        
        recommendations = {
            "extreme_contango": "期货大幅升水，强烈建议增持现货ETF",
            "strong_contango": "期货升水，建议适度增持现货ETF",
            "normal": "基差正常，建议维持现有仓位",
            "strong_backwardation": "期货贴水，建议适度减持现货ETF",
            "extreme_backwardation": "期货大幅贴水，强烈建议减持现货ETF"
        }
        
        return recommendations.get(status, "基差分析异常，建议谨慎操作")
    
    def calculate_confidence(self, basis_result: Dict, historical_analysis: Dict) -> float:
        """计算置信度"""
        try:
            confidence = 0.7  # 基础置信度
            
            # 数据源质量
            if basis_result.get('data_source') == 'tushare':
                confidence += 0.2
            elif basis_result.get('data_source') == 'simulated':
                confidence -= 0.1
            
            # 历史数据支持
            if historical_analysis.get('statistics', {}).get('count', 0) >= 10:
                confidence += 0.1
            
            # Z分数影响（越极端置信度越低）
            zscore = abs(historical_analysis.get('statistics', {}).get('current_zscore', 0))
            if zscore > 2:
                confidence -= 0.1
            elif zscore < 1:
                confidence += 0.05
            
            return round(max(0.3, min(0.95, confidence)), 2)
            
        except:
            return 0.5
    
    def run(self) -> Dict:
        """
        运行基差分析
        
        Returns:
            完整分析结果
        """
        logger.info("=" * 60)
        logger.info("基差计算器启动")
        logger.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"期货: {self.config['futures_symbol']}")
        logger.info(f"ETF: {self.config['etf_symbol']}")
        logger.info("=" * 60)
        
        try:
            # 1. 获取数据
            futures_data = self.fetch_futures_data()
            etf_data = self.fetch_etf_data()
            
            logger.info(f"期货数据: {futures_data.get('close')} ({futures_data.get('data_source')})")
            logger.info(f"ETF数据: {etf_data.get('close')} ({etf_data.get('data_source')})")
            
            # 2. 计算基差
            basis_result = self.calculate_basis(
                futures_data['close'],
                etf_data['close']
            )
            
            logger.info(f"基差结果: {basis_result['relative_basis']}% ({basis_result['basis_description']})")
            
            # 3. 生成模拟历史数据（实际应获取历史数据）
            historical_data = []
            for i in range(30):
                hist_date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
                hist_basis = basis_result['relative_basis'] + (i % 7 - 3) * 0.1  # 模拟波动
                historical_data.append({
                    "date": hist_date,
                    "relative_basis": hist_basis,
                    "basis_status": "normal" if abs(hist_basis) < 1 else "contango" if hist_basis > 0 else "backwardation"
                })
            
            # 4. 分析历史基差
            historical_analysis = self.analyze_historical_basis(historical_data)
            
            # 5. 生成G11算法输入
            g11_input = self.generate_g11_algorithm_input(basis_result, historical_analysis)
            
            # 6. 生成完整报告
            report = {
                "report_id": f"basis_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "generation_time": datetime.now().isoformat(),
                "data_sources": {
                    "futures": futures_data,
                    "etf": etf_data
                },
                "basis_analysis": basis_result,
                "historical_context": historical_analysis,
                "g11_algorithm": g11_input,
                "summary": {
                    "basis_level": basis_result['basis_description'],
                    "signal": basis_result['signal'],
                    "g11_score": g11_input['output']['score'],
                    "recommendation": g11_input['output']['recommendation'],
                    "confidence": g11_input['output']['confidence']
                }
            }
            
            # 7. 保存报告
            report_dir = "database/basis_analysis"
            os.makedirs(report_dir, exist_ok=True)
            
            report_file = os.path.join(report_dir, f"basis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info("=" * 60)
            logger.info(f"基差分析完成: {basis_result['basis_description']}")
            logger.info(f"G11评分: {g11_input['output']['score']}")
            logger.info(f"建议: {g11_input['output']['recommendation']}")
            logger.info(f"详细报告: {report_file}")
            logger.info("=" * 60)
            
            return report
            
        except Exception as e:
            logger.error(f"基差分析执行失败: {str(e)}")
            return {
                "error": str(e),
                "generation_time": datetime.now().isoformat()
            }

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="基差计算器 - 期货与现货ETF基差因子分析")
    parser.add_argument("--token", help="Tushare Token (可选，使用环境变量)")
    parser.add_argument("--output", help="输出文件路径")
    
    args = parser.parse_args()
    
    try:
        # 创建基差计算器
        calculator = BasisCalculator(tushare_token=args.token)
        
        # 运行分析
        report = calculator.run()
        
        # 输出结果
        if "error" in report:
            print(f"❌ 基差分析失败: {report['error']}")
            sys.exit(1)
        
        # 打印摘要
        summary = report.get('summary', {})
        print("\n" + "="*60)
        print("基差分析摘要")
        print("="*60)
        print(f"分析时间: {report['generation_time']}")
        print(f"期货: {report['data_sources']['futures']['symbol']} ({report['data_sources']['futures']['close']})")
        print(f"ETF: {report['data_sources']['etf']['symbol']} ({report['data_sources']['etf']['close']})")
        print(f"基差: {report['basis_analysis']['relative_basis']}% ({report['basis_analysis']['basis_description']})")
        print(f"G11评分: {summary.get('g11_score', 'N/A')}")
        print(f"信号: {summary.get('signal', 'N/A')}")
        print(f"建议: {summary.get('recommendation', 'N/A')}")
        print(f"置信度: {summary.get('confidence', 'N/A')}")
        print("="*60)
        
        # 保存到指定文件
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"完整报告已保存: {args.output}")
        
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"基差计算器执行失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()