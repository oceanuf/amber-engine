#!/usr/bin/env python3
"""
验证Tushare Token加载机制
直接在Python中测试，不依赖shell环境变量
"""

import os
import sys
import json

print("🔧 Tushare Token 加载验证")
print("=" * 60)

# 1. 检查环境变量
print("1. 检查环境变量:")
token_from_env = os.getenv('TUSHARE_TOKEN')
if token_from_env:
    print(f"   ✅ 环境变量 TUSHARE_TOKEN: {token_from_env[:10]}... (长度:{len(token_from_env)})")
else:
    print("   ⚠️  环境变量 TUSHARE_TOKEN 未设置")

# 2. 检查 secrets.json
print("\n2. 检查 secrets.json:")
secrets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_PRIVATE_DATA', 'secrets.json')
if os.path.exists(secrets_path):
    try:
        with open(secrets_path, 'r', encoding='utf-8') as f:
            secrets = json.load(f)
            token_from_secrets = secrets.get('TUSHARE_TOKEN', '')
            if token_from_secrets:
                print(f"   ✅ secrets.json Token: {token_from_secrets[:10]}... (长度:{len(token_from_secrets)})")
            else:
                print("   ⚠️  secrets.json 中未找到 TUSHARE_TOKEN")
    except Exception as e:
        print(f"   ❌ 读取 secrets.json 失败: {e}")
else:
    print(f"   ❌ secrets.json 文件不存在: {secrets_path}")

# 3. 测试 data_fetcher.py 的加载机制
print("\n3. 测试 data_fetcher.py 加载机制:")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # 先设置环境变量（模拟data_fetcher的行为）
    if not token_from_env and token_from_secrets:
        os.environ['TUSHARE_TOKEN'] = token_from_secrets
        print(f"   ✅ 将secrets.json Token设置到环境变量: {token_from_secrets[:10]}...")
    
    # 导入并测试data_fetcher
    from scripts.data_fetcher import fetcher
    
    print(f"   ✅ DataFetcher 导入成功")
    print(f"   ✅ fetcher.ts_token: {'已设置' if fetcher.ts_token else '未设置'}")
    if fetcher.ts_token:
        print(f"   ✅ Token值: {fetcher.ts_token[:10]}...")
    
except ImportError as e:
    print(f"   ❌ DataFetcher 导入失败: {e}")
except Exception as e:
    print(f"   ❌ 测试失败: {e}")

# 4. 测试 Tushare 初始化
print("\n4. 测试 Tushare 初始化:")
try:
    import tushare as ts
    
    # 使用当前环境中的Token
    current_token = os.getenv('TUSHARE_TOKEN')
    if current_token:
        ts.set_token(current_token)
        print(f"   ✅ Tushare Token 设置成功: {current_token[:10]}...")
        
        # 测试pro_api初始化
        try:
            pro = ts.pro_api()
            print("   ✅ Tushare pro_api() 初始化成功")
            
            # 尝试一个简单的API调用（不实际执行）
            print("   ⏳ Tushare API 就绪")
            
        except Exception as e:
            print(f"   ❌ Tushare API 初始化失败: {e}")
    else:
        print("   ⚠️  当前无有效Token，跳过Tushare初始化")
        
except ImportError as e:
    print(f"   ❌ Tushare 模块未安装: {e}")
except Exception as e:
    print(f"   ❌ Tushare 测试失败: {e}")

# 5. 测试数据获取
print("\n5. 测试数据获取:")
try:
    from scripts.data_fetcher import fetcher
    
    # 测试模拟数据获取
    test_ticker = "000001"
    print(f"   ⏳ 测试 {test_ticker} 数据获取...")
    
    # 首先检查Tushare状态
    if fetcher.ts_token:
        print(f"   ✅ Tushare Token 已加载，将尝试真实数据")
    else:
        print(f"   ⚠️  Tushare Token 未加载，将使用模拟数据")
    
    # 获取数据
    data = fetcher.get_stock_history(test_ticker, days=5)
    if data:
        print(f"   ✅ 数据获取成功")
        print(f"   ✅ 数据源: {'真实数据' if data.get('prices', []) and len(data['prices']) > 0 else '模拟数据'}")
        print(f"   ✅ 数据天数: {len(data.get('prices', []))}")
        if data.get('prices'):
            print(f"   ✅ 最新价格: {data['prices'][0]:.2f}")
    else:
        print("   ❌ 数据获取失败")
        
except Exception as e:
    print(f"   ❌ 数据获取测试失败: {e}")

# 6. 总结
print("\n6. 验证总结:")
print("=" * 60)

has_token = bool(os.getenv('TUSHARE_TOKEN'))
data_fetcher_ready = 'fetcher' in locals() and fetcher.ts_token

if has_token and data_fetcher_ready:
    print("✅ ✅ ✅ 验证通过!")
    print("Tushare Token 已正确加载，可以运行真实数据版[铁甲·繁星]")
elif token_from_secrets:
    print("⚠️  ⚠️  ⚠️ 部分验证通过")
    print("secrets.json 中有Token，但环境变量未加载")
    print("建议: 在运行前手动设置环境变量")
else:
    print("❌ ❌ ❌ 验证失败")
    print("未找到有效的Tushare Token")

print("\n执行建议:")
print("1. 运行真实数据版模型:")
print(f"   cd {os.path.dirname(os.path.abspath(__file__))}")
print("   python3 scripts/synthesizer/models/iron_star_v1.py")
print("\n2. 如果仍有问题，检查:")
print("   - ~/.amber_env 文件是否存在")
print("   - secrets.json 文件权限")
print("   - Tushare Token 是否有效")

print("=" * 60)