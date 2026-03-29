#!/usr/bin/env python3
"""
测试G1-G4算法
"""

import sys
import json
import os

# 添加策略目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/scripts/synthesizer/strategies')

# 导入算法
from gravity_dip import GravityDipStrategy
from dual_momentum import DualMomentumStrategy
from vol_squeeze import VolSqueezeStrategy
from dividend_alpha import DividendAlphaStrategy

def load_history_data(ticker="518880"):
    """加载历史数据"""
    history_file = f"database/history_{ticker}.json"
    if not os.path.exists(history_file):
        print(f"历史文件不存在: {history_file}")
        return None
    
    with open(history_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def test_algorithm(strategy, ticker, history_data):
    """测试单个算法"""
    print(f"\n=== 测试 {strategy.name} ===")
    print(f"描述: {strategy.description}")
    
    result = strategy.analyze(ticker, history_data)
    
    print(f"命中: {result['hit']}")
    print(f"得分: {result['score']}")
    print(f"置信度: {result['confidence']}")
    print(f"信号: {', '.join(result['signals'])}")
    
    # 打印关键元数据
    metadata = result.get('metadata', {})
    if 'signal_type' in metadata:
        print(f"信号类型: {metadata['signal_type']}")
    
    return result

def main():
    """主测试函数"""
    print("开始测试G1-G4算法")
    
    # 加载历史数据
    ticker = "518880"
    history_data = load_history_data(ticker)
    if not history_data:
        print("无法加载历史数据")
        return
    
    print(f"加载历史数据: {ticker}, 共 {len(history_data.get('history', []))} 条记录")
    
    # 创建策略实例
    strategies = [
        GravityDipStrategy(),
        DualMomentumStrategy(),
        VolSqueezeStrategy(),
        DividendAlphaStrategy()
    ]
    
    # 测试每个策略
    all_results = {}
    for strategy in strategies:
        result = test_algorithm(strategy, ticker, history_data)
        all_results[strategy.name] = result
    
    # 汇总结果
    print("\n=== 算法测试汇总 ===")
    total_score = 0
    hit_count = 0
    for name, result in all_results.items():
        print(f"{name}: 得分={result['score']}, 命中={result['hit']}")
        if result['hit']:
            hit_count += 1
        total_score += result['score']
    
    avg_score = total_score / len(strategies) if strategies else 0
    print(f"\n平均得分: {avg_score:.2f}")
    print(f"命中算法数: {hit_count}/{len(strategies)}")

if __name__ == "__main__":
    main()