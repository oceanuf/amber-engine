#!/usr/bin/env python3
"""
测试共振引擎导入
"""

import sys
import os

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from scripts.synthesizer.resonance_engine import main
    
    print("共振引擎导入成功")
    
    # 测试策略发现
    from scripts.synthesizer.resonance_engine import discover_strategies
    
    strategies = discover_strategies()
    print(f"发现策略数量: {len(strategies)}")
    for s in strategies:
        print(f"  - {s.name}: {s.description}")
    
    print("\n测试通过!")
    
except Exception as e:
    print(f"测试失败: {e}")
    import traceback
    traceback.print_exc()