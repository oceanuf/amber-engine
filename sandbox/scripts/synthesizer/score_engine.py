#!/usr/bin/env python3
"""
Synthesizer module for strategy signal generation - 符合 V1.2.1 标准
标准输出: database/strategy_signal.json
算法合成: 多维度加权评分，生成操作倾向信号
"""

import os
import sys
import json
import tempfile
import shutil
import datetime
from typing import Dict, Any, Optional, Tuple

# 模块常量
MODULE_NAME = "synthesizer_score_engine"
OUTPUT_FILE = "database/strategy_signal.json"
TMP_SUFFIX = ".tmp"
ANALYSIS_FILE = "database/analysis_518880.json"
PARAMS_FILE = "config/strategy_params.json"
SCHEMA_FILE = "config/schema_signal.json"  # 验证用
MAX_RETRIES = 3
RETRY_DELAY = 5  # 秒

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
    # 同时打印到 stdout 便于调试
    print(f"[{timestamp}] [{MODULE_NAME}:ERROR] {code}: {msg}", file=sys.stdout)

def load_analysis_data() -> Optional[Dict[str, Any]]:
    """
    加载分析数据文件
    """
    if not os.path.exists(ANALYSIS_FILE):
        log_error("ANALYSIS_NOT_FOUND", f"分析数据文件不存在: {ANALYSIS_FILE}")
        return None
    
    try:
        with open(ANALYSIS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 验证基本结构
        if "indicators" not in data or not isinstance(data["indicators"], list):
            log_error("INVALID_ANALYSIS_FORMAT", "分析数据格式无效: 缺少 'indicators' 数组")
            return None
        
        if len(data["indicators"]) == 0:
            log_error("EMPTY_ANALYSIS", "分析数据为空")
            return None
        
        return data
    except json.JSONDecodeError as e:
        log_error("JSON_PARSE_ERROR", f"解析分析数据 JSON 失败: {e}")
        return None
    except Exception as e:
        log_error("ANALYSIS_LOAD_ERROR", f"加载分析数据失败: {e}")
        return None

def load_strategy_params() -> Optional[Dict[str, Any]]:
    """
    加载策略参数配置
    """
    if not os.path.exists(PARAMS_FILE):
        log_error("PARAMS_NOT_FOUND", f"策略参数文件不存在: {PARAMS_FILE}")
        return None
    
    try:
        with open(PARAMS_FILE, 'r', encoding='utf-8') as f:
            params = json.load(f)
        
        # 验证必需字段
        required_fields = ["version", "last_updated", "dimensions", "score_thresholds"]
        for field in required_fields:
            if field not in params:
                log_error("INVALID_PARAMS_FORMAT", f"策略参数缺少必需字段: {field}")
                return None
        
        return params
    except json.JSONDecodeError as e:
        log_error("PARAMS_JSON_ERROR", f"解析策略参数 JSON 失败: {e}")
        return None
    except Exception as e:
        log_error("PARAMS_LOAD_ERROR", f"加载策略参数失败: {e}")
        return None

def get_latest_indicators(analysis_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    获取最新的指标数据（数组第一个元素为最新）
    """
    try:
        indicators = analysis_data["indicators"]
        if not indicators:
            log_error("NO_INDICATORS", "指标数组为空")
            return None
        
        # 最新数据在数组第一个位置（按日期降序排列）
        latest = indicators[0]
        
        # 验证必需字段
        required_fields = ["date", "price", "change", "ma5", "ma20", "ma60", "bias_20", "roc_5"]
        for field in required_fields:
            if field not in latest:
                log_error("MISSING_INDICATOR_FIELD", f"最新指标缺少字段: {field}")
                return None
        
        return latest
    except Exception as e:
        log_error("LATEST_INDICATORS_ERROR", f"获取最新指标失败: {e}")
        return None

def calculate_safety_score(latest_indicators: Dict[str, Any], params: Dict[str, Any]) -> float:
    """
    计算安全维度得分
    """
    safety_params = params["dimensions"]["safety"]
    bias_20 = latest_indicators.get("bias_20")
    
    # 如果bias_20为null，返回0分
    if bias_20 is None:
        log_warn("BIAS20_NULL: 乖离率(Bias20)为null，安全维度得分为0")
        return 0.0
    
    bias_threshold = safety_params.get("bias_threshold", -2.0)
    score_if_oversold = safety_params.get("score_if_oversold", 30)
    
    # 超卖安全区: bias_20 < bias_threshold
    if bias_20 < bias_threshold:
        return float(score_if_oversold)
    
    return 0.0

def calculate_trend_score(latest_indicators: Dict[str, Any], params: Dict[str, Any]) -> float:
    """
    计算趋势维度得分
    """
    trend_params = params["dimensions"]["trend"]
    price = latest_indicators.get("price")
    ma20 = latest_indicators.get("ma20")
    
    # 如果price或ma20为null，返回0分
    if price is None or ma20 is None:
        log_warn("PRICE_OR_MA20_NULL: 价格或MA20为null，趋势维度得分为0")
        return 0.0
    
    price_above_ma_score = trend_params.get("price_above_ma_score", 40)
    
    # 价格高于MA20
    if price > ma20:
        return float(price_above_ma_score)
    
    return 0.0

def calculate_momentum_score(latest_indicators: Dict[str, Any], params: Dict[str, Any]) -> float:
    """
    计算动能维度得分
    """
    momentum_params = params["dimensions"]["momentum"]
    roc_5 = latest_indicators.get("roc_5")
    
    # 如果roc_5为null，返回0分
    if roc_5 is None:
        log_warn("ROC5_NULL: ROC5为null，动能维度得分为0")
        return 0.0
    
    roc_positive_score = momentum_params.get("roc_positive_score", 30)
    
    # ROC5为正
    if roc_5 > 0:
        return float(roc_positive_score)
    
    return 0.0

def calculate_total_score(latest_indicators: Dict[str, Any], params: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
    """
    计算总分及各维度得分
    """
    # 计算各维度得分
    safety_score = calculate_safety_score(latest_indicators, params)
    trend_score = calculate_trend_score(latest_indicators, params)
    momentum_score = calculate_momentum_score(latest_indicators, params)
    
    # 计算加权总分（根据权重比例调整）
    safety_weight = params["dimensions"]["safety"]["weight"]
    trend_weight = params["dimensions"]["trend"]["weight"]
    momentum_weight = params["dimensions"]["momentum"]["weight"]
    total_weight = safety_weight + trend_weight + momentum_weight
    
    if total_weight == 0:
        total_weight = 1  # 避免除零错误
    
    # 计算加权总分（0-100分）
    weighted_safety = safety_score * (safety_weight / 100.0)
    weighted_trend = trend_score * (trend_weight / 100.0)
    weighted_momentum = momentum_score * (momentum_weight / 100.0)
    
    total_score = weighted_safety + weighted_trend + weighted_momentum
    
    # 确保总分在0-100范围内
    total_score = max(0.0, min(100.0, total_score))
    
    dimension_scores = {
        "safety": round(safety_score, 2),
        "trend": round(trend_score, 2),
        "momentum": round(momentum_score, 2),
        "weighted_safety": round(weighted_safety, 2),
        "weighted_trend": round(weighted_trend, 2),
        "weighted_momentum": round(weighted_momentum, 2)
    }
    
    return round(total_score, 2), dimension_scores

def determine_signal_status(total_score: float, params: Dict[str, Any]) -> str:
    """
    根据总分确定信号状态
    """
    thresholds = params["score_thresholds"]
    
    if total_score >= thresholds["extreme_comfort"]:
        return "极度舒适"
    elif total_score >= thresholds["comfort"]:
        return "舒适"
    elif total_score >= thresholds["neutral"]:
        return "中性"
    elif total_score >= thresholds["caution"]:
        return "谨慎"
    elif total_score < thresholds["survival_warning"]:
        return "生存预警"
    else:
        return "未知"

def synthesize_strategy_signal(analysis_data: Dict[str, Any], params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    合成策略信号
    """
    try:
        # 获取最新指标
        latest_indicators = get_latest_indicators(analysis_data)
        if not latest_indicators:
            log_error("NO_LATEST_INDICATORS", "无法获取最新指标")
            return None
        
        # 计算总分和各维度得分
        total_score, dimension_scores = calculate_total_score(latest_indicators, params)
        
        # 确定信号状态
        signal_status = determine_signal_status(total_score, params)
        
        # 获取分析元数据
        ticker = analysis_data.get("ticker", "518880")
        name = analysis_data.get("name", "未知ETF")
        analysis_time = analysis_data.get("analysis_time", datetime.datetime.now().isoformat())
        
        # 构建输出数据结构
        synthesis_time = datetime.datetime.now().isoformat()
        result = {
            "ticker": ticker,
            "name": name,
            "analysis_time": analysis_time,
            "synthesis_time": synthesis_time,
            "latest_date": latest_indicators["date"],
            "latest_price": latest_indicators["price"],
            "latest_change": latest_indicators["change"],
            "latest_ma20": latest_indicators["ma20"],
            "latest_bias_20": latest_indicators["bias_20"],
            "latest_roc_5": latest_indicators["roc_5"],
            "total_score": total_score,
            "signal_status": signal_status,
            "dimension_scores": dimension_scores,
            "strategy_params_version": params["version"],
            "source_module": MODULE_NAME
        }
        
        return result
        
    except Exception as e:
        log_error("SYNTHESIS_ERROR", f"合成策略信号时发生错误: {e}")
        return None

def validate_with_schema(data: Dict[str, Any], schema_file: str) -> bool:
    """
    使用 jsonschema 验证数据
    """
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
    except jsonschema.ValidationError as e:
        log_error("SCHEMA_VALIDATE_FAIL", f"Schema 验证失败: {e.message}")
        return False
    except Exception as e:
        log_error("VALIDATE_ERROR", f"验证过程出错: {e}")
        return False

def write_with_atomic_protocol(data: Dict[str, Any], output_file: str) -> bool:
    """
    原子写入协议: Write(.tmp) -> Validate -> Rename(.json)
    """
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
    log_info(f"开始执行 {MODULE_NAME}")
    
    # 1. 加载分析数据
    analysis_data = load_analysis_data()
    if not analysis_data:
        log_error("ANALYSIS_LOAD_FAIL", "加载分析数据失败，模块退出")
        sys.exit(101)  # 数据加载失败
    
    log_info(f"加载分析数据成功，共 {len(analysis_data['indicators'])} 个指标点")
    
    # 2. 加载策略参数
    strategy_params = load_strategy_params()
    if not strategy_params:
        log_error("PARAMS_LOAD_FAIL", "加载策略参数失败，模块退出")
        sys.exit(102)  # 参数加载失败
    
    log_info(f"加载策略参数成功，版本: {strategy_params['version']}")
    
    # 3. 合成策略信号
    strategy_signal = synthesize_strategy_signal(analysis_data, strategy_params)
    if not strategy_signal:
        log_error("SYNTHESIS_FAIL", "合成策略信号失败，模块退出")
        sys.exit(103)  # 合成失败
    
    log_info(f"策略信号合成完成，总分: {strategy_signal['total_score']}, 状态: {strategy_signal['signal_status']}")
    
    # 4. 原子写入输出文件
    if not write_with_atomic_protocol(strategy_signal, OUTPUT_FILE):
        log_error("WRITE_FAIL", "写入输出文件失败，模块退出")
        sys.exit(104)  # 写入失败
    
    log_info(f"成功生成策略信号文件: {OUTPUT_FILE}")
    sys.exit(0)  # 成功

if __name__ == "__main__":
    main()