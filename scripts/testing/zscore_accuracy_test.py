#!/usr/bin/env python3
"""
Z-Score 精度校验测试 - 验证合成引擎计算精度
符合 V1.4.1 地基加固专项要求
误差要求: < 0.0001%
"""

import os
import sys
import json
import math
import statistics
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_test_data(ticker: str = "000681") -> Optional[Dict]:
    """加载测试数据"""
    history_file = f"database/history_{ticker}.json"
    if not os.path.exists(history_file):
        print(f"❌ 测试数据文件不存在: {history_file}")
        return None
    
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载测试数据失败: {e}")
        return None

def manual_zscore_calculation(prices: List[float], window: int = 20) -> List[Optional[float]]:
    """
    手动计算 Z-Score（基准值）
    Z-Score = (当前价格 - 移动平均) / 标准差
    
    使用 Excel 兼容的计算方法：
    1. 使用样本标准差（STDEV.S）
    2. 使用算术平均（AVERAGE）
    3. 数据不足时返回 None
    """
    n = len(prices)
    zscores = []
    
    for i in range(n):
        if i < window - 1:
            # 数据不足，无法计算
            zscores.append(None)
        else:
            # 获取窗口内数据
            window_prices = prices[i - window + 1:i + 1]
            
            # 计算移动平均（算术平均）
            ma = statistics.mean(window_prices)
            
            # 计算样本标准差 (Excel 的 STDEV.S)
            if len(window_prices) >= 2:
                # 样本标准差公式: sqrt(Σ(x - μ)² / (n-1))
                variance = sum((x - ma) ** 2 for x in window_prices) / (len(window_prices) - 1)
                std_dev = math.sqrt(variance)
                
                # 避免除以零
                if std_dev == 0:
                    zscore = 0.0
                else:
                    zscore = (prices[i] - ma) / std_dev
            else:
                zscore = 0.0
            
            zscores.append(zscore)
    
    return zscores

def extract_prices_from_history(history_data: Dict) -> Tuple[List[float], List[str]]:
    """从历史数据中提取价格和日期"""
    prices = []
    dates = []
    
    for item in history_data.get("history", []):
        try:
            price = float(item.get("price", 0))
            date = item.get("date", "")
            
            prices.append(price)
            dates.append(date)
        except (ValueError, TypeError):
            continue
    
    return prices, dates

def load_synthesizer_zscore(ticker: str = "000681") -> Optional[List[float]]:
    """加载合成引擎计算的 Z-Score"""
    # 尝试从不同位置加载合成结果
    possible_files = [
        f"database/analysis_{ticker}.json",  # Analyzer输出
        f"database/resonance_signal.json",   # 合成信号
        f"database/cleaned/resonance_signal_cleaned.json"
    ]
    
    for filepath in possible_files:
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 尝试从不同结构中提取 Z-Score
                zscores = []
                
                # 尝试结构1: indicators数组中的z_score字段
                if "indicators" in data and isinstance(data["indicators"], list):
                    for indicator in data["indicators"]:
                        if "z_score" in indicator:
                            zscores.append(float(indicator["z_score"]))
                        elif "zscore" in indicator:
                            zscores.append(float(indicator["zscore"]))
                
                # 尝试结构2: 直接包含z_score的数组
                if "z_scores" in data and isinstance(data["z_scores"], list):
                    zscores = [float(z) for z in data["z_scores"]]
                
                if zscores:
                    print(f"✅ 从 {filepath} 加载 {len(zscores)} 个 Z-Score 值")
                    return zscores
                    
            except Exception as e:
                print(f"⚠️  读取文件失败 {filepath}: {e}")
                continue
    
    print(f"❌ 未找到合成引擎的 Z-Score 输出")
    return None

def calculate_accuracy_metrics(manual_zscores: List[Optional[float]], 
                              synth_zscores: List[float]) -> Dict:
    """
    计算精度指标
    
    返回:
        - 绝对误差 (Absolute Error)
        - 相对误差百分比 (Relative Error %)
        - 最大误差 (Max Error)
        - 平均误差 (Mean Error)
        - 通过率 (Pass Rate, 误差 < 0.0001%)
    """
    # 对齐数据长度
    min_len = min(len(manual_zscores), len(synth_zscores))
    manual_zscores = manual_zscores[:min_len]
    synth_zscores = synth_zscores[:min_len]
    
    # 过滤掉 None 值
    valid_pairs = []
    for manual, synth in zip(manual_zscores, synth_zscores):
        if manual is not None:
            valid_pairs.append((manual, synth))
    
    if not valid_pairs:
        return {"error": "无有效数据对"}
    
    manual_vals, synth_vals = zip(*valid_pairs)
    
    # 计算误差
    absolute_errors = []
    relative_errors = []
    
    for manual, synth in valid_pairs:
        abs_error = abs(manual - synth)
        absolute_errors.append(abs_error)
        
        # 避免除以零
        if manual != 0:
            rel_error = abs(abs_error / manual) * 100  # 百分比
            relative_errors.append(rel_error)
    
    # 统计指标
    metrics = {
        "数据点总数": len(valid_pairs),
        "绝对误差统计": {
            "最大值": max(absolute_errors),
            "最小值": min(absolute_errors),
            "平均值": statistics.mean(absolute_errors),
            "中位数": statistics.median(absolute_errors),
            "标准差": statistics.stdev(absolute_errors) if len(absolute_errors) > 1 else 0
        }
    }
    
    if relative_errors:
        metrics["相对误差统计(%)"] = {
            "最大值": max(relative_errors),
            "最小值": min(relative_errors),
            "平均值": statistics.mean(relative_errors),
            "中位数": statistics.median(relative_errors)
        }
        
        # 计算通过率 (误差 < 0.0001%)
        threshold = 0.0001
        pass_count = sum(1 for err in relative_errors if err < threshold)
        pass_rate = (pass_count / len(relative_errors)) * 100
        
        metrics["精度要求"] = f"相对误差 < {threshold}%"
        metrics["通过率"] = f"{pass_rate:.4f}% ({pass_count}/{len(relative_errors)})"
        metrics["测试结果"] = "✅ 通过" if pass_rate == 100 else f"⚠️  部分失败 ({100 - pass_rate:.2f}% 未通过)"
    else:
        metrics["相对误差统计"] = "无法计算（所有基准值为0）"
        metrics["测试结果"] = "⚠️  无法验证精度"
    
    return metrics

def generate_excel_verification(prices: List[float], 
                               manual_zscores: List[Optional[float]],
                               synth_zscores: List[float],
                               dates: List[str],
                               output_file: str = "zscore_verification.csv"):
    """
    生成 Excel 验证文件（CSV格式）
    """
    # 准备数据
    data = []
    
    for i in range(len(prices)):
        date = dates[i] if i < len(dates) else f"Day_{i+1}"
        price = prices[i]
        manual_z = manual_zscores[i] if i < len(manual_zscores) else None
        synth_z = synth_zscores[i] if i < len(synth_zscores) else None
        
        if manual_z is None:
            continue
            
        # 计算误差
        abs_error = abs(manual_z - synth_z) if synth_z is not None else None
        rel_error = abs(abs_error / manual_z * 100) if manual_z != 0 and abs_error is not None else None
        
        data.append({
            "日期": date,
            "价格": price,
            "手动Z-Score": manual_z,
            "合成Z-Score": synth_z,
            "绝对误差": abs_error,
            "相对误差%": rel_error,
            "是否通过": "是" if rel_error is not None and rel_error < 0.0001 else "否"
        })
    
    # 创建 DataFrame 并保存
    df = pd.DataFrame(data)
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f"📊 验证文件已生成: {output_file}")
    print(f"   包含 {len(data)} 行数据")
    
    return output_file

def run_accuracy_test(ticker: str = "000681"):
    """执行精度校验测试"""
    print("=" * 60)
    print(f"📏 Z-Score 精度校验测试 - {ticker}")
    print("=" * 60)
    
    # 1. 加载测试数据
    print("\\n1️⃣ 加载测试数据...")
    history_data = load_test_data(ticker)
    if not history_data:
        return False
    
    prices, dates = extract_prices_from_history(history_data)
    print(f"   ✅ 加载 {len(prices)} 个价格数据点")
    print(f"   日期范围: {dates[0]} 到 {dates[-1]}")
    
    # 2. 手动计算 Z-Score（基准值）
    print("\\n2️⃣ 手动计算 Z-Score（Excel兼容算法）...")
    manual_zscores = manual_zscore_calculation(prices, window=20)
    
    # 统计有效值
    valid_manual = sum(1 for z in manual_zscores if z is not None)
    print(f"   ✅ 计算 {valid_manual} 个有效 Z-Score 值")
    print(f"   窗口大小: 20日")
    print(f"   计算方法: 样本标准差 (STDEV.S)")
    
    # 3. 加载合成引擎的 Z-Score
    print("\\n3️⃣ 加载合成引擎计算结果...")
    synth_zscores = load_synthesizer_zscore(ticker)
    
    if synth_zscores is None:
        print("   ⚠️  未找到合成引擎输出，尝试运行分析流程...")
        # 这里可以添加自动运行 Analyzer 的逻辑
        print("   ❌ 测试中止：需要先运行分析合成流程")
        return False
    
    print(f"   ✅ 加载 {len(synth_zscores)} 个合成 Z-Score 值")
    
    # 4. 计算精度指标
    print("\\n4️⃣ 计算精度指标...")
    metrics = calculate_accuracy_metrics(manual_zscores, synth_zscores)
    
    # 打印结果
    print("\\n📊 精度测试结果:")
    print("-" * 40)
    
    for key, value in metrics.items():
        if isinstance(value, dict):
            print(f"{key}:")
            for sub_key, sub_value in value.items():
                print(f"  {sub_key}: {sub_value}")
        else:
            print(f"{key}: {value}")
    
    # 5. 生成验证文件
    print("\\n5️⃣ 生成详细验证文件...")
    verification_file = generate_excel_verification(
        prices, manual_zscores, synth_zscores, dates,
        output_file=f"logs/zscore_verification_{ticker}.csv"
    )
    
    # 6. 最终评估
    print("\\n🎯 最终评估:")
    print("-" * 40)
    
    if "测试结果" in metrics:
        test_result = metrics["测试结果"]
        if "✅" in test_result:
            print("🎉 精度测试通过！")
            print(f"   所有数据点误差 < 0.0001%")
            success = True
        else:
            print("⚠️  精度测试未完全通过")
            print(f"   需要检查合成引擎计算逻辑")
            success = False
    else:
        print("❌ 无法完成精度测试")
        success = False
    
    # 7. 保存测试报告
    report = {
        "test_name": "Z-Score精度校验",
        "ticker": ticker,
        "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_points": len(prices),
        "window_size": 20,
        "accuracy_metrics": metrics,
        "verification_file": verification_file,
        "success": success
    }
    
    report_file = f"logs/zscore_accuracy_report_{ticker}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\\n📋 测试报告已保存: {report_file}")
    print("=" * 60)
    
    return success

def main():
    """主函数"""
    # 解析命令行参数
    ticker = "000681"
    if len(sys.argv) > 1:
        ticker = sys.argv[1]
    
    try:
        success = run_accuracy_test(ticker)
        return 0 if success else 1
    except Exception as e:
        print(f"❌ 测试执行异常: {e}")
        import traceback
        traceback.print_exc()
        return 2

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)