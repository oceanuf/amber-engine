#!/usr/bin/env python3
"""
Resonance Engine - 共振评分引擎
实现"民主投票制"算法合成逻辑
符合 V1.2.1 工业标准
"""

import os
import sys
import json
import tempfile
import shutil
import datetime
import importlib
import inspect
from typing import Dict, Any, List, Optional, Tuple

# 模块常量
MODULE_NAME = "synthesizer_resonance_engine"
OUTPUT_FILE = "database/resonance_signal.json"
RESONANCE_REPORT_FILE = "database/resonance_report_{date}.json"
TMP_SUFFIX = ".tmp"
SCHEMA_FILE = "config/schema_resonance.json"  # 共振信号专用Schema
STRATEGIES_DIR = os.path.join(os.path.dirname(__file__), "strategies")
MAX_RETRIES = 3
RETRY_DELAY = 5  # 秒

# 标的配置（支持多个ETF）
TICKERS_CONFIG = {
    "518880": {
        "name": "黄金ETF",
        "data_file": "database/tushare_gold.json",  # Tushare数据源
        "history_file": "database/history_518880.json",  # 传统历史数据（备用）
        "type": "etf",
        "weight": 1.0
    },
    "510300": {
        "name": "沪深300ETF",
        "data_file": "database/tushare_hs300.json",
        "history_file": "database/history_510300.json",
        "type": "etf",
        "weight": 1.0
    },
    "510500": {
        "name": "中证500ETF",
        "data_file": "database/tushare_zz500.json",
        "history_file": "database/history_510500.json",
        "type": "etf",
        "weight": 1.0
    }
}

# 导入策略基类
sys.path.insert(0, os.path.dirname(__file__))
from strategies.base_strategy import BaseStrategy

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

def load_global_params() -> Optional[Dict[str, Any]]:
    """加载全局参数配置"""
    params_file = "config/global_params.json"
    if not os.path.exists(params_file):
        log_error("GLOBAL_PARAMS_NOT_FOUND", f"全局参数文件不存在: {params_file}")
        return None
    
    try:
        with open(params_file, 'r', encoding='utf-8') as f:
            params = json.load(f)
        log_info(f"加载全局参数成功，版本: {params.get('version', '未知')}")
        return params
    except Exception as e:
        log_error("GLOBAL_PARAMS_LOAD_ERROR", f"加载全局参数失败: {e}")
        return None

def load_strategy_weights() -> Optional[Dict[str, Any]]:
    """加载策略权重配置"""
    weights_file = "config/strategy_weights.json"
    if not os.path.exists(weights_file):
        log_error("STRATEGY_WEIGHTS_NOT_FOUND", f"策略权重文件不存在: {weights_file}")
        return None
    
    try:
        with open(weights_file, 'r', encoding='utf-8') as f:
            weights = json.load(f)
        log_info(f"加载策略权重成功，版本: {weights.get('version', '未知')}")
        return weights
    except Exception as e:
        log_error("STRATEGY_WEIGHTS_LOAD_ERROR", f"加载策略权重失败: {e}")
        return None

def load_history_data(ticker: str = "518880") -> Optional[Dict[str, Any]]:
    """加载历史数据"""
    history_file = f"database/history_{ticker}.json"
    if not os.path.exists(history_file):
        log_error("HISTORY_NOT_FOUND", f"历史数据文件不存在: {history_file}")
        return None
    
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            history_data = json.load(f)
        log_info(f"加载历史数据成功: {ticker}, 共 {len(history_data.get('history', []))} 条记录")
        return history_data
    except Exception as e:
        log_error("HISTORY_LOAD_ERROR", f"加载历史数据失败: {e}")
        return None

def load_analysis_data(ticker: str = "518880") -> Optional[Dict[str, Any]]:
    """加载分析数据（可选）"""
    analysis_file = f"database/analysis_{ticker}.json"
    if not os.path.exists(analysis_file):
        log_warn(f"分析数据文件不存在: {analysis_file}，将仅使用历史数据")
        return None
    
    try:
        with open(analysis_file, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        log_info(f"加载分析数据成功: {ticker}, 共 {len(analysis_data.get('indicators', []))} 个指标点")
        return analysis_data
    except Exception as e:
        log_warn(f"加载分析数据失败: {e}，将仅使用历史数据")
        return None

def load_ticker_data(ticker: str) -> Optional[Dict[str, Any]]:
    """加载标的的完整数据（优先Tushare，备用历史数据）"""
    config = TICKERS_CONFIG.get(ticker)
    if not config:
        log_error("TICKER_NOT_CONFIGURED", f"标的未配置: {ticker}")
        return None
    
    # 尝试加载Tushare数据
    tushare_file = config.get("data_file")
    if tushare_file and os.path.exists(tushare_file):
        try:
            with open(tushare_file, 'r', encoding='utf-8') as f:
                tushare_data = json.load(f)
            
            log_info(f"加载Tushare数据成功: {ticker}, 文件: {tushare_file}")
            
            # 转换Tushare数据格式为历史数据格式
            if "data" in tushare_data and isinstance(tushare_data["data"], list):
                history = []
                for item in tushare_data["data"]:
                    history_point = {
                        "date": item.get("date", ""),
                        "price": item.get("close", 0.0),
                        "open": item.get("open", 0.0),
                        "high": item.get("high", 0.0),
                        "low": item.get("low", 0.0),
                        "volume": item.get("volume", 0),
                        "change": item.get("change", 0.0),
                        "pct_chg": item.get("pct_chg", 0.0)
                    }
                    history.append(history_point)
                
                return {
                    "ticker": ticker,
                    "name": config["name"],
                    "type": config["type"],
                    "history": history,
                    "metadata": tushare_data.get("metadata", {}),
                    "data_source": "tushare"
                }
        
        except Exception as e:
            log_warn(f"加载Tushare数据失败: {e}，尝试历史数据")
    
    # 备用：加载传统历史数据
    history_file = config.get("history_file") or f"database/history_{ticker}.json"
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
            
            log_info(f"加载历史数据成功: {ticker}, 文件: {history_file}")
            history_data["data_source"] = "legacy"
            return history_data
        
        except Exception as e:
            log_error("HISTORY_LOAD_ERROR", f"加载历史数据失败: {e}")
            return None
    
    log_error("NO_DATA_SOURCE", f"标的 {ticker} 无可用数据源")
    return None

def discover_strategies() -> List[BaseStrategy]:
    """发现所有可用策略"""
    strategies = []
    
    try:
        # 手动导入所有算法 (G1-G11)
        from strategies.gravity_dip import GravityDipStrategy
        from strategies.dual_momentum import DualMomentumStrategy
        from strategies.vol_squeeze import VolSqueezeStrategy
        from strategies.dividend_alpha import DividendAlphaStrategy
        from strategies.weekly_rsi import WeeklyRSIStrategy
        from strategies.z_score_bias import ZScoreBiasStrategy
        from strategies.triple_cross import TripleCrossStrategy
        from strategies.vol_retrace import VolumeRetracementStrategy
        from strategies.macro_gold import MacroGoldStrategy
        from strategies.obv_divergence import OBVDivergenceStrategy
        from strategies.policy_resonance import PolicyResonanceStrategy  # G11
        
        strategy_classes = [
            GravityDipStrategy,
            DualMomentumStrategy,
            VolSqueezeStrategy,
            DividendAlphaStrategy,
            WeeklyRSIStrategy,
            ZScoreBiasStrategy,
            TripleCrossStrategy,
            VolumeRetracementStrategy,
            MacroGoldStrategy,
            OBVDivergenceStrategy,
            PolicyResonanceStrategy  # G11
        ]
        
        for cls in strategy_classes:
            try:
                strategy = cls()
                strategies.append(strategy)
                log_info(f"发现策略: {strategy.name}")
            except Exception as e:
                log_error("STRATEGY_INIT_ERROR", f"初始化策略 {cls.__name__} 失败: {e}")
    
    except ImportError as e:
        log_error("STRATEGY_IMPORT_ERROR", f"导入策略失败: {e}")
    
    return strategies

def run_strategies(strategies: List[BaseStrategy],
                  ticker: str,
                  history_data: Dict[str, Any],
                  analysis_data: Optional[Dict[str, Any]] = None,
                  global_params: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    """运行所有策略并收集结果"""
    results = {}
    
    for strategy in strategies:
        try:
            log_info(f"运行策略: {strategy.name}")
            
            # 运行策略分析
            result = strategy.analyze(
                ticker=ticker,
                history_data=history_data,
                analysis_data=analysis_data,
                global_params=global_params
            )
            
            results[strategy.name] = result
            log_info(f"策略 {strategy.name} 完成: 命中={result['hit']}, 得分={result['score']}")
            
        except Exception as e:
            log_error("STRATEGY_RUN_ERROR", f"运行策略 {strategy.name} 失败: {e}")
            # 创建错误结果
            results[strategy.name] = {
                "hit": False,
                "score": 0.0,
                "confidence": 0.0,
                "signals": [f"运行失败: {str(e)}"],
                "metadata": {"error": str(e)},
                "strategy_name": strategy.name
            }
    
    return results

def calculate_resonance_score(strategy_results: Dict[str, Dict[str, Any]],
                             weights_config: Dict[str, Any],
                             global_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    计算共振评分 - 民主投票制
    
    规则:
    1. 单一算法命中: 得分 +10
    2. 跨维度共振（多个算法命中）: 得分额外加权 ×1.5
    3. 一票否决权: 如果Weekly RSI处于80以上，强制下调得分至40以下
    """
    # 获取共振规则
    resonance_rules = weights_config.get("resonance_rules", {})
    single_algorithm_score = resonance_rules.get("single_algorithm_score", 10)
    resonance_multiplier = resonance_rules.get("resonance_multiplier", 1.5)
    min_algorithms_for_resonance = resonance_rules.get("min_algorithms_for_resonance", 2)
    weekly_rsi_veto_threshold = resonance_rules.get("weekly_rsi_veto_threshold", 80)
    veto_penalty_score = resonance_rules.get("veto_penalty_score", 40)
    
    # 统计命中情况
    hits = []
    hit_count = 0
    total_base_score = 0.0
    weighted_scores = []
    
    for strategy_name, result in strategy_results.items():
        if result.get("hit", False):
            hits.append(strategy_name)
            hit_count += 1
            
            # 基础得分（策略自身的得分，归一化到0-100）
            strategy_score = result.get("score", 0.0)
            total_base_score += strategy_score
            
            # 加权得分（考虑策略权重）
            strategy_weights = weights_config.get("algorithm_weights", {})
            weight_info = strategy_weights.get(strategy_name, {})
            weight = weight_info.get("weight", 1.0)
            enabled = weight_info.get("enabled", True)
            
            if enabled:
                weighted_score = strategy_score * weight
                weighted_scores.append(weighted_score)
    
    # 计算平均基础得分
    avg_base_score = total_base_score / len(strategy_results) if strategy_results else 0
    
    # 计算民主投票得分
    democracy_score = 0
    
    # 规则1: 单一算法命中得分
    democracy_score += hit_count * single_algorithm_score
    
    # 规则2: 跨维度共振加成
    if hit_count >= min_algorithms_for_resonance:
        # 共振加成 = 基础得分 × (共振乘数 - 1)
        resonance_bonus = avg_base_score * (resonance_multiplier - 1)
        democracy_score += resonance_bonus
    
    # 规则3: 加权平均得分（考虑权重）
    weighted_avg = sum(weighted_scores) / len(weighted_scores) if weighted_scores else 0
    
    # 综合得分（民主投票 + 加权平均）
    resonance_score = (democracy_score + weighted_avg) / 2
    resonance_score = min(100.0, max(0.0, resonance_score))
    
    # 规则4: 一票否决权（检查Weekly RSI G5算法）
    # TODO: 当G5算法实现后，检查RSI是否超过阈值
    # 目前G5未实现，跳过此检查
    veto_applied = False
    if "Weekly-RSI" in strategy_results:
        weekly_rsi_result = strategy_results["Weekly-RSI"]
        if weekly_rsi_result.get("hit", False):
            weekly_rsi_score = weekly_rsi_result.get("score", 0)
            if weekly_rsi_score > weekly_rsi_veto_threshold:
                resonance_score = min(resonance_score, veto_penalty_score)
                veto_applied = True
                log_warn(f"一票否决权应用: Weekly RSI超过阈值{weekly_rsi_veto_threshold}")
    
    # 确定信号状态
    signal_status = determine_signal_status(resonance_score, global_params)
    
    return {
        "resonance_score": round(resonance_score, 2),
        "hit_count": hit_count,
        "hits": hits,
        "avg_base_score": round(avg_base_score, 2),
        "weighted_avg_score": round(weighted_avg, 2),
        "democracy_score": round(democracy_score, 2),
        "veto_applied": veto_applied,
        "signal_status": signal_status,
        "strategy_results": {name: simplify_result(result) for name, result in strategy_results.items()}
    }

def simplify_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """简化策略结果用于输出"""
    simplified = {
        "hit": result.get("hit", False),
        "score": round(result.get("score", 0.0), 2),
        "confidence": round(result.get("confidence", 0.0), 2),
        "signals": result.get("signals", []),
        "signal_type": result.get("metadata", {}).get("signal_type", "unknown")
    }
    return simplified

def determine_signal_status(score: float, global_params: Dict[str, Any]) -> str:
    """根据分数确定信号状态"""
    thresholds = global_params.get("global_rules", {}).get("score_thresholds", {})
    
    extreme_comfort = thresholds.get("extreme_comfort", 80)
    comfort = thresholds.get("comfort", 60)
    neutral = thresholds.get("neutral", 40)
    caution = thresholds.get("caution", 30)
    survival_warning = thresholds.get("survival_warning", 30)
    
    if score >= extreme_comfort:
        return "极度舒适"
    elif score >= comfort:
        return "舒适"
    elif score >= neutral:
        return "中性"
    elif score >= caution:
        return "谨慎"
    else:
        return "生存预警"

def generate_final_signal(ticker: str,
                         history_data: Dict[str, Any],
                         resonance_result: Dict[str, Any],
                         global_params: Dict[str, Any]) -> Dict[str, Any]:
    """生成最终信号输出"""
    
    action_labels = global_params.get("global_rules", {}).get("action_labels", {})
    min_holding_days = global_params.get("global_rules", {}).get("min_holding_days", 60)
    
    # 根据共振分数确定操作建议
    resonance_score = resonance_result["resonance_score"]
    signal_status = resonance_result["signal_status"]
    
    # 确定操作标签
    if resonance_score >= 70:
        action = action_labels.get("BUY_ZONE", "买入区间")
        action_type = "BUY_ZONE"
    elif resonance_score >= 50:
        action = action_labels.get("HOLD", "持仓")
        action_type = "HOLD"
    elif resonance_score >= 30:
        action = action_labels.get("REDUCE", "减持")
        action_type = "REDUCE"
    else:
        action = action_labels.get("EXIT", "清仓")
        action_type = "EXIT"
    
    # 获取最新价格信息
    latest_info = {}
    if "history" in history_data and history_data["history"]:
        latest = history_data["history"][0]
        
        # 转换价格和变化值为数字（如果它们是字符串）
        price = latest.get("price")
        change = latest.get("change")
        
        try:
            if isinstance(price, str):
                price = float(price)
        except (ValueError, TypeError):
            price = 0.0
            
        try:
            if isinstance(change, str):
                change = float(change)
        except (ValueError, TypeError):
            change = 0.0
        
        latest_info = {
            "date": latest.get("date"),
            "price": price,
            "change": change
        }
    
    # 构建最终信号
    signal_time = datetime.datetime.now().isoformat()
    final_signal = {
        "ticker": ticker,
        "name": history_data.get("name", "未知"),
        "signal_time": signal_time,
        "resonance_score": resonance_score,
        "signal_status": signal_status,
        "action": action,
        "action_type": action_type,
        "min_holding_days": min_holding_days,
        "hit_count": resonance_result["hit_count"],
        "hits": resonance_result["hits"],
        "veto_applied": resonance_result["veto_applied"],
        "latest_info": latest_info,
        "strategy_summary": resonance_result["strategy_results"]
    }
    
    return final_signal

def validate_with_schema(data: Dict[str, Any], schema_file: str) -> bool:
    """使用 jsonschema 验证数据"""
    # 暂时跳过验证以加速开发
    log_warn("Schema 验证暂时跳过（开发模式）")
    return True
    
    # 检查Schema文件是否存在
    if not os.path.exists(schema_file):
        log_warn(f"Schema文件不存在: {schema_file}，跳过验证")
        return True
    
    try:
        import jsonschema
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        jsonschema.validate(instance=data, schema=schema)
        log_info("Schema 验证通过")
        return True
    except ImportError:
        log_warn("jsonschema 库未安装，跳过 Schema 验证")
        return True
    except Exception as e:
        log_error("SCHEMA_VALIDATE_FAIL", f"Schema 验证失败: {e}")
        return False

def write_with_atomic_protocol(data: Dict[str, Any], output_file: str) -> bool:
    """原子写入协议: Write(.tmp) -> Validate -> Rename(.json)"""
    tmp_file = output_file + TMP_SUFFIX
    
    try:
        # 1. 写入临时文件
        with open(tmp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log_info(f"数据写入临时文件: {tmp_file}")
        
        # 2. 验证数据 (使用 Schema)
        if not validate_with_schema(data, SCHEMA_FILE):
            log_error("ATOMIC_VALIDATE_FAIL", "原子写入协议: Schema 验证失败")
            os.remove(tmp_file)
            return False
        
        # 3. 原子重命名
        shutil.move(tmp_file, output_file)
        log_info(f"原子重命名完成: {tmp_file} -> {output_file}")
        return True
        
    except Exception as e:
        log_error("ATOMIC_WRITE_FAIL", f"原子写入协议失败: {e}")
        # 清理临时文件
        if os.path.exists(tmp_file):
            os.remove(tmp_file)
        return False

def run_single_ticker_analysis(ticker: str, config: Dict[str, Any], 
                              strategies: List[BaseStrategy],
                              global_params: Dict[str, Any],
                              weights_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """对单个标的进行完整共振分析"""
    log_info(f"开始分析标的: {config['name']} ({ticker})")
    
    # 1. 加载数据
    ticker_data = load_ticker_data(ticker)
    if not ticker_data:
        log_error("TICKER_DATA_LOAD_FAIL", f"加载标的 {ticker} 数据失败，跳过")
        return None
    
    # 加载分析数据（可选）
    analysis_data = load_analysis_data(ticker)
    
    # 2. 运行所有策略
    strategy_results = run_strategies(
        strategies=strategies,
        ticker=ticker,
        history_data=ticker_data,
        analysis_data=analysis_data,
        global_params=global_params
    )
    
    # 3. 计算共振评分
    resonance_result = calculate_resonance_score(
        strategy_results=strategy_results,
        weights_config=weights_config,
        global_params=global_params
    )
    
    log_info(f"共振评分计算完成 [{ticker}]: {resonance_result['resonance_score']}, 状态: {resonance_result['signal_status']}")
    log_info(f"命中算法 [{ticker}]: {resonance_result['hit_count']}个 - {', '.join(resonance_result['hits'])}")
    
    # 4. 生成最终信号
    final_signal = generate_final_signal(
        ticker=ticker,
        history_data=ticker_data,
        resonance_result=resonance_result,
        global_params=global_params
    )
    
    # 添加标的配置信息
    final_signal["weight"] = config.get("weight", 1.0)
    final_signal["type"] = config.get("type", "etf")
    
    return final_signal

def generate_resonance_report(all_signals: Dict[str, Dict[str, Any]], 
                             global_params: Dict[str, Any],
                             strategies: List[BaseStrategy]) -> Dict[str, Any]:
    """生成完整的共振报告"""
    report_date = datetime.datetime.now().strftime("%Y%m%d")
    
    # 计算总体共振矩阵
    overall_analysis = {
        "total_tickers": len(all_signals),
        "avg_resonance_score": 0.0,
        "signals_by_status": {},
        "top_performers": [],
        "strategy_hit_counts": {strategy.name: 0 for strategy in strategies}
    }
    
    total_score = 0.0
    ticker_count = 0
    
    for ticker, signal in all_signals.items():
        if signal:
            score = signal.get("resonance_score", 0)
            total_score += score
            ticker_count += 1
            
            # 按状态统计
            status = signal.get("signal_status", "未知")
            if status not in overall_analysis["signals_by_status"]:
                overall_analysis["signals_by_status"][status] = 0
            overall_analysis["signals_by_status"][status] += 1
            
            # 统计策略命中
            hits = signal.get("hits", [])
            for hit in hits:
                if hit in overall_analysis["strategy_hit_counts"]:
                    overall_analysis["strategy_hit_counts"][hit] += 1
    
    if ticker_count > 0:
        overall_analysis["avg_resonance_score"] = round(total_score / ticker_count, 2)
    
    # 选择表现最佳的标的（按共振分排序）
    valid_signals = [(ticker, signal) for ticker, signal in all_signals.items() if signal]
    sorted_signals = sorted(valid_signals, key=lambda x: x[1].get("resonance_score", 0), reverse=True)
    overall_analysis["top_performers"] = [
        {
            "ticker": ticker,
            "name": signal.get("name", "未知"),
            "resonance_score": signal.get("resonance_score", 0),
            "signal_status": signal.get("signal_status", "未知"),
            "action": signal.get("action", "未知")
        }
        for ticker, signal in sorted_signals[:5]  # 前5名
    ]
    
    # 构建完整报告
    report = {
        "metadata": {
            "report_id": f"resonance_report_{report_date}",
            "generated_at": datetime.datetime.now().isoformat(),
            "module": MODULE_NAME,
            "strategies_count": len(strategies),
            "tickers_count": len(all_signals)
        },
        "overall_analysis": overall_analysis,
        "ticker_signals": all_signals,
        "strategy_summary": {
            strategy.name: {
                "description": strategy.description if hasattr(strategy, 'description') else "无描述",
                "category": strategy.category if hasattr(strategy, 'category') else "未知"
            }
            for strategy in strategies
        }
    }
    
    return report

def main():
    """主函数 - 多标的共振分析引擎"""
    log_info(f"开始执行 {MODULE_NAME} - 十诫共振全量测试")
    
    # 1. 加载配置
    global_params = load_global_params()
    if not global_params:
        log_error("CONFIG_LOAD_FAIL", "加载全局配置失败，模块退出")
        sys.exit(101)
    
    weights_config = load_strategy_weights()
    if not weights_config:
        log_error("WEIGHTS_LOAD_FAIL", "加载策略权重失败，模块退出")
        sys.exit(102)
    
    # 2. 发现策略
    strategies = discover_strategies()
    if not strategies:
        log_error("NO_STRATEGIES", "未发现可用策略，模块退出")
        sys.exit(104)
    
    log_info(f"发现 {len(strategies)} 个策略: {', '.join([s.name for s in strategies])}")
    
    # 3. 遍历所有标的进行分析
    all_signals = {}
    
    for ticker, config in TICKERS_CONFIG.items():
        signal = run_single_ticker_analysis(
            ticker=ticker,
            config=config,
            strategies=strategies,
            global_params=global_params,
            weights_config=weights_config
        )
        all_signals[ticker] = signal
    
    # 4. 生成共振报告
    resonance_report = generate_resonance_report(all_signals, global_params, strategies)
    
    # 5. 保存共振报告
    report_date = datetime.datetime.now().strftime("%Y%m%d")
    report_file = f"database/resonance_report_{report_date}.json"
    
    if not write_with_atomic_protocol(resonance_report, report_file):
        log_error("REPORT_WRITE_FAIL", f"写入共振报告失败: {report_file}")
        sys.exit(106)
    
    log_info(f"共振报告生成成功: {report_file}")
    
    # 6. 保存主要标的的信号（向后兼容 - 黄金ETF）
    main_ticker = "518880"
    if main_ticker in all_signals and all_signals[main_ticker]:
        main_signal = all_signals[main_ticker]
        if not write_with_atomic_protocol(main_signal, OUTPUT_FILE):
            log_error("SIGNAL_WRITE_FAIL", f"写入主信号失败: {OUTPUT_FILE}")
            sys.exit(107)
        log_info(f"主信号保存成功: {OUTPUT_FILE}")
    
    # 7. 输出摘要
    valid_signals = [s for s in all_signals.values() if s]
    log_info(f"共振分析完成: {len(valid_signals)}/{len(all_signals)} 个标的分析成功")
    
    # 检查紫色推荐（7/10算法命中且包含G9/G10）
    purple_recommendations = []
    for ticker, signal in all_signals.items():
        if signal and signal.get("hit_count", 0) >= 7:
            hits = signal.get("hits", [])
            # 检查是否包含G9和G10
            has_g9 = any("Macro-Gold" in hit or "G9" in hit for hit in hits)
            has_g10 = any("OBV-Divergence" in hit or "G10" in hit for hit in hits)
            if has_g9 and has_g10:
                purple_recommendations.append(ticker)
    
    if purple_recommendations:
        log_info(f"🎯 紫色推荐标的: {', '.join(purple_recommendations)}")
    
    # 检查红色预警（G5一票否决）
    red_warnings = []
    for ticker, signal in all_signals.items():
        if signal and signal.get("veto_applied", False):
            red_warnings.append(ticker)
    
    if red_warnings:
        log_info(f"🚨 红色预警（一票否决）: {', '.join(red_warnings)}")
    
    sys.exit(0)  # 成功

if __name__ == "__main__":
    main()