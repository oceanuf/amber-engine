#!/usr/bin/env python3
"""
检查Tushare API状态
"""

import os
import sys
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载密钥
secrets_path = "_PRIVATE_DATA/secrets.json"
if os.path.exists(secrets_path):
    with open(secrets_path, 'r', encoding='utf-8') as f:
        secrets = json.load(f)
    token = secrets.get("TUSHARE_TOKEN")
else:
    token = os.environ.get("TUSHARE_TOKEN")

if not token:
    print("❌ 未找到Tushare令牌")
    sys.exit(1)

print(f"✅ Tushare令牌存在: {token[:10]}...")

# 尝试导入tushare
try:
    import tushare as ts
    print("✅ tushare库已安装")
except ImportError:
    print("❌ tushare库未安装")
    sys.exit(1)

# 设置token
ts.set_token(token)
pro = ts.pro_api()

# 尝试简单的API调用
try:
    # 尝试获取交易日历
    df = pro.trade_cal(exchange='SSE', start_date='20260401', end_date='20260407')
    print(f"✅ Tushare API连接成功")
    print(f"   最近交易日: {df[df['is_open']==1]['cal_date'].iloc[-1] if not df.empty else '无数据'}")
    print(f"   积分状态: 可用 (成功获取交易日历)")
    
    # 检查用户信息（需要权限）
    try:
        user_info = pro.user_info()
        if 'points' in user_info:
            print(f"   用户积分: {user_info.get('points', '未知')}")
        else:
            print("   用户信息: 权限受限，无法获取积分详情")
    except Exception as e:
        print(f"   用户信息: 权限受限 ({str(e)[:50]})")
        
except Exception as e:
    print(f"❌ Tushare API调用失败: {e}")
    sys.exit(1)

print("✅ 环境保活检查完成 - Tushare API处于Active状态")