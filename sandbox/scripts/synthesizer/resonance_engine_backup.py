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
TMP_SUFFIX = ".tmp"
SCHEMA_FILE = "config/schema_resonance.json"  # 共振信号专用Schema
STRATEGIES_DIR = os.path.join(os.path.dirname(__file__), "strategies")
MAX_RETRIES = 3
RETRY_DELAY = 5  # 秒

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

def discover_strategies() -> List[BaseStrategy]:
    """发现所有可用策略"""
    strategies = []
    
    try:
        # 手动导入所有算法 (G1-G10)
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
            OBVDivergenceStrategy
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

def main():
    """主函数"""
    log_info(f"开始执行 {MODULE_NAME} - 共振评分引擎")
    
    # 1. 加载配置
    global_params = load_global_params()
    if not global_params:
        log_error("CONFIG_LOAD_FAIL", "加载全局配置失败，模块退出")
        sys.exit(101)
    
    weights_config = load_strategy_weights()
    if not weights_config:
        log_error("WEIGHTS_LOAD_FAIL", "加载策略权重失败，模块退出")
        sys.exit(102)
    
    # 2. 加载数据
    ticker = "518880"  # 默认黄金ETF
    history_data = load_history_data(ticker)
    if not history_data:
        log_error("DATA_LOAD_FAIL", "加载历史数据失败，模块退出")
        sys.exit(103)
    
    analysis_data = load_analysis_data(ticker)  # 可选
    
    # 3. 发现并运行策略
    strategies = discover_strategies()
    if not strategies:
        log_error("NO_STRATEGIES", "未发现可用策略，模块退出")
        sys.exit(104)
    
    log_info(f"发现 {len(strategies)} 个策略")
    
    # 4. 运行所有策略
    strategy_results = run_strategies(
        strategies=strategies,
        ticker=ticker,
        history_data=history_data,
        analysis_data=analysis_data,
        global_params=global_params
    )
    
    # 5. 计算共振评分
    resonance_result = calculate_resonance_score(
        strategy_results=strategy_results,
        weights_config=weights_config,
        global_params=global_params
    )
    
    log_info(f"共振评分计算完成: {resonance_result['resonance_score']}, 状态: {resonance_result['signal_status']}")
    log_info(f"命中算法: {resonance_result['hit_count']}个 - {', '.join(resonance_result['hits'])}")
    
    # 6. 生成最终信号
    final_signal = generate_final_signal(
        ticker=ticker,
        history_data=history_data,
        resonance_result=resonance_result,
        global_params=global_params
    )
    
    # 7. 原子写入输出文件
    if not write_with_atomic_protocol(final_signal, OUTPUT_FILE):
        log_error("WRITE_FAIL", "写入输出文件失败，模块退出")
        sys.exit(105)
    
    log_info(f"成功生成共振信号文件: {OUTPUT_FILE}")
    log_info(f"最终信号: 共振分={final_signal['resonance_score']}, 操作={final_signal['action']}")
    
    sys.exit(0)  # 成功

if __name__ == "__main__":
    main()