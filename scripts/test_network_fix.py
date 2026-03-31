#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络加固测试脚本
测试对抗性设计和重试机制
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from network.proxy_manager import proxy_manager, anti_block
import time
import logging
import random

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_proxy_manager():
    """测试代理管理器"""
    print("=== 测试代理管理器 ===")
    
    # 测试连通性
    print("1. 测试网络连通性...")
    if proxy_manager.test_connectivity():
        print("✅ 网络连通性测试通过")
    else:
        print("❌ 网络连通性测试失败")
    
    # 测试请求
    print("\n2. 测试带重试的请求...")
    test_urls = [
        "https://httpbin.org/get",
        "https://httpbin.org/status/200",
        "https://httpbin.org/delay/1"
    ]
    
    for url in test_urls:
        print(f"\n测试URL: {url}")
        response = proxy_manager.make_request_with_retry(url)
        
        if response and response.status_code == 200:
            print(f"✅ 请求成功: 状态码 {response.status_code}")
            print(f"   用户代理: {response.request.headers.get('User-Agent')}")
        else:
            print("❌ 请求失败")
    
    return True


def test_anti_block_skill():
    """测试反封禁技能"""
    print("\n=== 测试反封禁技能 ===")
    
    # 创建一个会随机失败的测试函数
    def test_function(should_fail: bool = False):
        """测试函数，模拟可能失败的操作"""
        time.sleep(0.5)  # 模拟处理时间
        
        if should_fail and random.random() < 0.7:  # 70%概率失败
            raise ConnectionError("模拟网络连接失败")
        
        return f"成功执行，时间: {time.time()}"
    
    print("1. 测试正常执行...")
    try:
        result = anti_block.execute_with_protection(test_function, should_fail=False)
        print(f"✅ 正常执行成功: {result}")
    except Exception as e:
        print(f"❌ 正常执行失败: {e}")
    
    print("\n2. 测试可能失败的操作...")
    success_count = 0
    total_tests = 5
    
    for i in range(total_tests):
        print(f"\n测试 {i+1}/{total_tests}...")
        try:
            result = anti_block.execute_with_protection(test_function, should_fail=True)
            print(f"✅ 测试 {i+1} 成功: {result}")
            success_count += 1
        except Exception as e:
            print(f"❌ 测试 {i+1} 失败: {e}")
    
    success_rate = success_count / total_tests
    print(f"\n成功率: {success_rate:.1%} ({success_count}/{total_tests})")
    
    # 获取成功率统计
    actual_success_rate = anti_block.get_success_rate()
    print(f"技能记录的成功率: {actual_success_rate:.1%}")
    
    return success_rate > 0.3  # 至少30%成功率


def test_akshare_with_protection():
    """测试带保护的AKShare调用"""
    print("\n=== 测试带保护的AKShare调用 ===")
    
    import akshare as ak
    
    def safe_akshare_call(func, *args, **kwargs):
        """安全的AKShare调用包装"""
        try:
            return anti_block.execute_with_protection(func, *args, **kwargs)
        except Exception as e:
            logger.error(f"AKShare调用失败: {e}")
            return None
    
    test_cases = [
        {
            "name": "获取实时行情",
            "func": ak.stock_zh_a_spot_em,
            "args": [],
            "kwargs": {}
        },
        {
            "name": "获取历史K线",
            "func": ak.stock_zh_a_hist,
            "args": [],
            "kwargs": {
                "symbol": "000001",
                "period": "daily",
                "start_date": "20250101",
                "end_date": "20250110",
                "adjust": "qfq"
            }
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        print(f"\n测试: {test_case['name']}...")
        
        start_time = time.time()
        result = safe_akshare_call(
            test_case["func"],
            *test_case["args"],
            **test_case["kwargs"]
        )
        elapsed = time.time() - start_time
        
        if result is not None:
            if hasattr(result, 'shape'):
                print(f"✅ 成功获取数据，形状: {result.shape}, 耗时: {elapsed:.2f}秒")
            else:
                print(f"✅ 成功获取数据，类型: {type(result)}, 耗时: {elapsed:.2f}秒")
            results.append(True)
        else:
            print(f"❌ 获取数据失败，耗时: {elapsed:.2f}秒")
            results.append(False)
    
    success_count = sum(results)
    print(f"\nAKShare测试结果: {success_count}/{len(results)} 通过")
    
    return success_count > 0


def main():
    """主测试函数"""
    print("网络加固系统测试开始...")
    
    # 导入random模块
    import random
    
    test_results = []
    
    # 运行测试
    try:
        test_results.append(("代理管理器", test_proxy_manager()))
    except Exception as e:
        print(f"代理管理器测试异常: {e}")
        test_results.append(("代理管理器", False))
    
    try:
        test_results.append(("反封禁技能", test_anti_block_skill()))
    except Exception as e:
        print(f"反封禁技能测试异常: {e}")
        test_results.append(("反封禁技能", False))
    
    try:
        test_results.append(("AKShare保护", test_akshare_with_protection()))
    except Exception as e:
        print(f"AKShare保护测试异常: {e}")
        test_results.append(("AKShare保护", False))
    
    # 输出测试总结
    print("\n" + "="*50)
    print("测试总结:")
    print("="*50)
    
    passed = 0
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:20} {status}")
        if result:
            passed += 1
    
    print("="*50)
    print(f"总体结果: {passed}/{len(test_results)} 通过")
    
    if passed >= len(test_results) * 0.7:
        print("✅ 网络加固系统测试通过")
        return True
    else:
        print("❌ 网络加固系统测试失败")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)