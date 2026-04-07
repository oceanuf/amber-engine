#!/usr/bin/env python3
import sys
import os

# 添加路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from scripts.synthesizer.strategies.gravity_dip import GravityDipStrategy
    print("✅ GravityDipStrategy导入成功")
except ImportError as e:
    print(f"❌ GravityDipStrategy导入失败: {e}")

try:
    from scripts.synthesizer.strategies.z_score_bias import ZScoreBiasStrategy
    print("✅ ZScoreBiasStrategy导入成功")
except ImportError as e:
    print(f"❌ ZScoreBiasStrategy导入失败: {e}")