#!/usr/bin/env python3
"""
[铁甲·繁星] 真实数据环境验证脚本
验证 Tushare Token 加载和基础数据获取能力
"""

import os
import sys
import json
from datetime import datetime

print("🔧 [铁甲·繁星] 真实数据环境验证")
print("=" * 60)

# 添加工作空间路径
workspace_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, workspace_root)

# 1. 检查环境变量加载
print("1. 环境变量检查:")
print("   - 当前工作目录:", workspace_root)
print("   - Python版本:", sys.version[:20])

# 检查 ~/.amber_env 是否存在
amber_env_path = os.path.expanduser("~/.amber_env")
if os.path.exists(amber_env_path):
    print(f"   ✅ ~/.amber_env 文件存在")
    # 尝试读取TUSHARE_TOKEN
    with open(amber_env_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if 'TUSHARE_TOKEN' in content:
            print("   ✅ ~/.amber_env 中包含 TUSHARE_TOKEN 配置")
        else:
            print("   ⚠️  ~/.amber_env 中未找到 TUSHARE_TOKEN")
else:
    print("   ⚠️  ~/.amber_env 文件不存在")

# 2. 检查 Tushare Token
print("\n2. Tushare Token 检查:")
token_from_env = os.getenv('TUSHARE_TOKEN')
if token_from_env:
    print(f"   ✅ 环境变量 TUSHARE_TOKEN 已设置: {token_from_env[:10]}...")
else:
    print("   ⚠️  环境变量 TUSHARE_TOKEN 未设置")

# 检查 secrets.json
secrets_path = os.path.join(workspace_root, '_PRIVATE_DATA', 'secrets.json')
if os.path.exists(secrets_path):
    try:
        with open(secrets_path, 'r', encoding='utf-8') as f:
            secrets = json.load(f)
            token_from_secrets = secrets.get('TUSHARE_TOKEN', '')
            if token_from_secrets:
                print(f"   ✅ secrets.json 中包含 Token: {token_from_secrets[:10]}...")
            else:
                print("   ⚠️  secrets.json 中未找到 TUSHARE_TOKEN")
    except Exception as e:
        print(f"   ❌ 读取 secrets.json 失败: {e}")
else:
    print("   ⚠️  secrets.json 文件不存在")

# 3. 测试 Tushare 初始化
print("\n3. Tushare 初始化测试:")
try:
    import tushare as ts
    
    # 尝试从多个来源获取token
    token = token_from_env
    if not token and 'token_from_secrets' in locals():
        token = token_from_secrets
    
    if token:
        ts.set_token(token)
        print(f"   ✅ Tushare Token 设置成功: {token[:10]}...")
        
        # 测试简单API调用
        try:
            pro = ts.pro_api()
            print("   ✅ Tushare pro_api() 初始化成功")
            
            # 测试基础数据获取 (不实际调用API)
            print("   ⏳ Tushare 基础功能就绪")
        except Exception as e:
            print(f"   ❌ Tushare API 初始化失败: {e}")
    else:
        print("   ⚠️  未找到有效的 Tushare Token")
except ImportError as e:
    print(f"   ❌ Tushare 模块未安装: {e}")
except Exception as e:
    print(f"   ❌ Tushare 测试失败: {e}")

# 4. 测试 AkShare
print("\n4. AkShare 测试:")
try:
    import akshare as ak
    version = ak.__version__
    print(f"   ✅ AkShare 版本: {version}")
    
    # 测试简单数据获取（不依赖网络）
    print("   ⏳ AkShare 模块加载成功")
except ImportError as e:
    print(f"   ❌ AkShare 模块未安装: {e}")
except Exception as e:
    print(f"   ❌ AkShare 测试失败: {e}")

# 5. 测试数据获取模块
print("\n5. 数据获取模块测试:")
try:
    from scripts.data_fetcher import fetcher
    
    print(f"   ✅ DataFetcher 导入成功")
    print(f"   ✅ Tushare Token 状态: {'已设置' if fetcher.ts_token else '未设置'}")
    
    # 测试模拟数据获取（不依赖网络）
    test_ticker = "000001"
    print(f"   ⏳ 测试数据获取: {test_ticker}")
    
    # 测试获取模拟数据
    mock_data = fetcher.get_mock_history(test_ticker, days=10)
    if mock_data:
        print(f"   ✅ 模拟数据获取成功，{len(mock_data['prices'])} 天数据")
    else:
        print("   ❌ 模拟数据获取失败")
        
except ImportError as e:
    print(f"   ❌ DataFetcher 导入失败: {e}")
except Exception as e:
    print(f"   ❌ 数据获取测试失败: {e}")

# 6. 环境变量加载建议
print("\n6. 环境变量加载建议:")
print("""
   如果环境变量未加载，请执行:
   
   # 方法1: 手动加载
   source ~/.amber_env
   
   # 方法2: 直接设置环境变量
   export TUSHARE_TOKEN="9e32ef28eac05c5fbb11e6f02a50da903def70f94b3018e93340568b"
   
   # 方法3: 修改Python代码直接加载
   # 在脚本开头添加:
   import os
   os.environ['TUSHARE_TOKEN'] = "your_token_here"
""")

# 7. 总结
print("\n7. 验证总结:")
print("=" * 60)
print(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 检查关键条件
critical_issues = []
if not token_from_env:
    critical_issues.append("环境变量 TUSHARE_TOKEN 未设置")
if not os.path.exists(secrets_path):
    critical_issues.append("secrets.json 文件不存在")

if critical_issues:
    print("❌ 关键问题:")
    for issue in critical_issues:
        print(f"   - {issue}")
    print("\n💡 建议: 请先修复以上问题再运行[铁甲·繁星]模型")
else:
    print("✅ 基础环境检查通过")
    print("💡 建议: 可以尝试运行真实数据版[铁甲·繁星]模型")

print("=" * 60)
print("执行命令测试真实数据:")
print(f"cd {workspace_root}")
print("source ~/.amber_env")
print("python3 scripts/synthesizer/models/iron_star_v1.py")