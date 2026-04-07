#!/usr/bin/env python3
"""
AkShare连接诊断工具
测试各种数据获取方法，找出可用的数据源
"""

import akshare as ak
import pandas as pd
import time
from datetime import datetime, timedelta
import requests

print("🔧 AkShare 连接诊断工具")
print("=" * 60)
print(f"AkShare版本: {ak.__version__}")
print(f"诊断时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

# 测试股票列表
test_stocks = [
    "000681",  # 视觉中国
    "600741",  # 华域汽车
    "000338",  # 潍柴动力
    "601238",  # 广汽集团
]

def test_method(method_name, func, *args, **kwargs):
    """测试一个数据获取方法"""
    print(f"\n📊 测试方法: {method_name}")
    print(f"参数: {args} {kwargs}")
    
    try:
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time
        
        if result is not None:
            if isinstance(result, pd.DataFrame):
                print(f"✅ 成功! 耗时: {elapsed:.2f}s")
                print(f"   返回数据: {len(result)} 行 x {len(result.columns)} 列")
                if not result.empty:
                    print(f"   最新日期: {result.iloc[0]['日期'] if '日期' in result.columns else 'N/A'}")
                    print(f"   最新价格: {result.iloc[0]['收盘'] if '收盘' in result.columns else 'N/A'}")
            else:
                print(f"✅ 成功! 耗时: {elapsed:.2f}s")
                print(f"   返回类型: {type(result)}")
        else:
            print(f"❌ 失败: 返回None")
            
    except Exception as e:
        print(f"❌ 失败: {type(e).__name__}: {str(e)[:100]}")

def test_website_connectivity():
    """测试AkShare依赖的网站连通性"""
    print("\n🌐 测试网站连通性:")
    
    websites = [
        ("东方财富", "http://quote.eastmoney.com/"),
        ("新浪财经", "https://finance.sina.com.cn/"),
        ("网易财经", "http://quotes.money.163.com/"),
        ("腾讯财经", "http://qt.gtimg.cn/"),
    ]
    
    for name, url in websites:
        try:
            response = requests.head(url, timeout=10, allow_redirects=True)
            print(f"   {name} ({url}): ✅ HTTP {response.status_code}")
        except Exception as e:
            print(f"   {name} ({url}): ❌ {type(e).__name__}")

# 执行诊断
print("\n1. 网站连通性测试")
test_website_connectivity()

print("\n2. 测试各种数据获取方法")
print("-" * 40)

# 测试方法1: 股票历史数据 (主要方法)
test_method("stock_zh_a_hist - 日线", ak.stock_zh_a_hist, symbol="000681", period="daily", adjust="qfq")

# 测试方法2: 股票历史数据 (周线)
test_method("stock_zh_a_hist - 周线", ak.stock_zh_a_hist, symbol="000681", period="weekly", adjust="qfq")

# 测试方法3: 新浪财经数据源
test_method("stock_zh_a_daily", ak.stock_zh_a_daily, symbol="sz000681")

# 测试方法4: 腾讯财经数据源
test_method("stock_zh_a_spot", ak.stock_zh_a_spot)

# 测试方法5: 网易财经数据源
test_method("stock_zh_a_hist_163", ak.stock_zh_a_hist_163, symbol="000681")

# 测试方法6: 复权因子
test_method("stock_zh_a_adjust", ak.stock_zh_a_adjust, symbol="000681")

# 测试方法7: 获取所有A股列表
test_method("stock_info_a_code_name", ak.stock_info_a_code_name)

print("\n3. 测试多个股票")
print("-" * 40)

for stock in test_stocks:
    print(f"\n📈 测试股票 {stock}:")
    try:
        # 快速测试，只获取最近5天数据
        df = ak.stock_zh_a_hist(symbol=stock, period="daily", adjust="qfq", start_date="20260401", end_date="20260401")
        if df is not None and not df.empty:
            print(f"   ✅ 成功获取数据，最新收盘价: {df.iloc[0]['收盘']:.2f}")
        else:
            print(f"   ❌ 未获取到数据")
    except Exception as e:
        print(f"   ❌ 失败: {type(e).__name__}: {str(e)[:80]}")

print("\n4. 请求参数优化测试")
print("-" * 40)

# 测试不同的timeout设置
for timeout in [10, 30, 60]:
    print(f"\n⏱️  Timeout={timeout}s:")
    try:
        import requests
        original_timeout = requests.utils.DEFAULT_TIMEOUT
        requests.utils.DEFAULT_TIMEOUT = (timeout, timeout)
        
        df = ak.stock_zh_a_hist(symbol="000681", period="daily", adjust="qfq")
        if df is not None and not df.empty:
            print(f"   ✅ 成功 (timeout={timeout}s)")
        else:
            print(f"   ❌ 失败 (timeout={timeout}s)")
            
        requests.utils.DEFAULT_TIMEOUT = original_timeout
    except Exception as e:
        print(f"   ❌ 异常: {type(e).__name__}")

print("\n5. 诊断总结")
print("=" * 60)

print("🎯 建议:")
print("1. 如果主要数据源失败，尝试备用数据源方法")
print("2. 增加timeout时间到30-60秒")
print("3. 添加重试机制 (最多3次)")
print("4. 优先使用Tushare (已验证可用)")
print("5. 考虑配置HTTP代理 (如果需要)")

print("\n🛠️ 快速修复命令:")
print("""# 修改data_fetcher.py，优先使用Tushare
cd /home/luckyelite/.openclaw/workspace/amber-engine
# 备份原文件
cp scripts/data_fetcher.py scripts/data_fetcher.py.backup
# 编辑文件，修改get_stock_history方法优先使用Tushare""")

print("\n📞 如果需要进一步帮助:")
print("1. 查看完整错误日志")
print("2. 检查服务器防火墙/出站规则")
print("3. 测试代理配置")

print("=" * 60)
print("诊断完成时间:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))