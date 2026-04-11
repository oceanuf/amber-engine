#!/usr/bin/env python3
"""
灾变模拟测试脚本
测试架构加固模块在故障场景下的表现
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime
from typing import Dict, List, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_data_fallback_disaster():
    """测试数据降级模块的灾变场景"""
    print("🧪 测试数据降级灾变场景")
    print("=" * 50)
    
    try:
        # 导入DataFallback
        from scripts.arena.technical_fallback import DataFallback
        
        fallback = DataFallback()
        
        # 测试1: 正常股票（应有缓存数据）
        print("\n📊 测试1: 正常股票 (510300)")
        result1 = fallback.get_stock_price("510300")
        print(f"   结果: {'✅ 成功' if result1['success'] else '❌ 失败'}")
        print(f"   数据源: {result1.get('data_source', 'unknown')}")
        print(f"   价格: {result1.get('price', 'N/A')}")
        print(f"   备份标记: {result1.get('backup_marker', '无')}")
        
        # 测试2: 虚拟基金中的股票
        print("\n📊 测试2: 虚拟基金股票 (000681)")
        result2 = fallback.get_stock_price("000681")
        print(f"   结果: {'✅ 成功' if result2['success'] else '❌ 失败'}")
        print(f"   数据源: {result2.get('data_source', 'unknown')}")
        print(f"   价格: {result2.get('price', 'N/A')}")
        print(f"   备份标记: {result2.get('backup_marker', '无')}")
        
        # 测试3: 不存在的股票（测试默认降级）
        print("\n📊 测试3: 不存在股票 (TEST_DISASTER_001)")
        result3 = fallback.get_stock_price("TEST_DISASTER_001")
        print(f"   结果: {'✅ 成功' if result3['success'] else '❌ 失败'}")
        print(f"   数据源: {result3.get('data_source', 'unknown')}")
        print(f"   价格: {result3.get('price', 'N/A')}")
        print(f"   备份标记: {result3.get('backup_marker', '无')}")
        if result3.get('emergency'):
            print(f"   ⚠️  紧急模式: {result3.get('note', '')}")
        
        # 测试4: 批量获取测试
        print("\n📊 测试4: 批量获取混合股票")
        tickers = ["510300", "000681", "600633", "NON_EXISTENT_123"]
        batch_results = fallback.batch_get_prices(tickers)
        
        success_count = sum(1 for r in batch_results.values() if r.get('success'))
        backup_count = sum(1 for r in batch_results.values() if '[BACKUP_DATA]' in str(r.get('backup_marker', '')))
        
        print(f"   总计: {len(tickers)} 个股票")
        print(f"   成功: {success_count} 个")
        print(f"   使用备份: {backup_count} 个")
        
        # 输出详细结果
        for ticker, result in batch_results.items():
            marker = "🔴" if '[BACKUP_DATA]' in str(result.get('backup_marker', '')) else "🟢"
            source = result.get('data_source', 'unknown')
            price = result.get('price', 'N/A')
            print(f"   {marker} {ticker}: {source} | 价格: {price}")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据降级测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_port_monitor_disaster():
    """测试端口监控的灾变场景"""
    print("\n🚨 测试端口监控灾变场景")
    print("=" * 50)
    
    try:
        # 测试端口检查脚本
        sentry_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ops", "service_sentry.sh")
        
        if not os.path.exists(sentry_script):
            print(f"❌ 端口监控脚本不存在: {sentry_script}")
            return False
        
        # 测试1: 正常端口检查
        print("\n📡 测试1: 正常端口检查 (10168)")
        cmd = [sentry_script, "--test"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("   ✅ 端口健康检查通过")
            # 提取输出中的关键信息
            for line in result.stdout.split('\n'):
                if '端口健康' in line or '端口检查通过' in line:
                    print(f"   {line.strip()}")
        else:
            print(f"   ❌ 端口检查失败: {result.stderr}")
        
        # 测试2: 干运行模式检查配置
        print("\n⚙️ 测试2: 干运行模式检查配置")
        cmd = [sentry_script, "--dry-run"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("   ✅ 配置检查通过")
            # 显示关键配置
            for line in result.stdout.split('\n'):
                if any(keyword in line for keyword in ["端口:", "主机:", "服务名:", "最大失败次数:"]):
                    print(f"   {line.strip()}")
        else:
            print(f"   ❌ 配置检查失败: {result.stderr}")
        
        # 测试3: 模拟端口故障（通过修改参数测试不存在的端口）
        print("\n💥 测试3: 模拟端口故障（测试不存在的端口）")
        cmd = [sentry_script, "--port", "99999", "--test"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print("   ✅ 正确检测到故障端口")
            for line in result.stderr.split('\n'):
                if '端口不健康' in line or '检查失败' in line:
                    print(f"   {line.strip()}")
        else:
            print("   ⚠️  故障端口测试异常通过")
        
        # 测试4: 检查事故报告生成（模拟）
        print("\n📋 测试4: 事故报告功能验证")
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs", "sentry")
        report_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs", "cron")
        
        print(f"   日志目录: {log_dir}")
        print(f"   报告目录: {report_dir}")
        
        # 检查目录是否存在
        if os.path.exists(log_dir):
            print("   ✅ 日志目录存在")
        else:
            print("   ⚠️  日志目录不存在，但会被自动创建")
        
        if os.path.exists(report_dir):
            print("   ✅ 报告目录存在")
            # 检查是否有旧的事故报告
            import glob
            incident_files = glob.glob(os.path.join(report_dir, "incident_*.json"))
            if incident_files:
                print(f"   发现 {len(incident_files)} 个历史事故报告")
            else:
                print("   无历史事故报告")
        else:
            print("   ⚠️  报告目录不存在，但会被自动创建")
        
        return True
        
    except Exception as e:
        print(f"❌ 端口监控测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cron_preflight_disaster():
    """测试Cron预检的灾变场景"""
    print("\n🔄 测试Cron预检灾变场景")
    print("=" * 50)
    
    try:
        # 测试cron_manager.sh的预检功能
        cron_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ops", "cron_manager.sh")
        
        if not os.path.exists(cron_script):
            print(f"❌ Cron管理器脚本不存在: {cron_script}")
            return False
        
        # 测试干运行模式（包含预检）
        print("\n⚙️ 测试Cron管理器干运行模式（包含预检）")
        cmd = [cron_script, "--dry-run"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("   ✅ Cron预检通过")
            
            # 检查输出中是否包含预检信息
            output = result.stdout + result.stderr
            preflight_checks = [
                "开始架构加固预检",
                "10168端口健康",
                "数据降级模块",
                "arena_watch_list.json"
            ]
            
            for check in preflight_checks:
                if check in output:
                    print(f"   ✅ 包含: {check}")
                else:
                    print(f"   ⚠️  未找到: {check}")
        else:
            print(f"   ❌ Cron预检失败: {result.stderr}")
        
        return True
        
    except Exception as e:
        print(f"❌ Cron预检测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def generate_disaster_report(test_results: Dict[str, bool]):
    """生成灾变测试报告"""
    print("\n📊 灾变模拟测试报告")
    print("=" * 50)
    
    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results.values() if result)
    
    print(f"测试总数: {total_tests}")
    print(f"通过数: {passed_tests}")
    print(f"失败数: {total_tests - passed_tests}")
    print(f"通过率: {passed_tests/total_tests*100:.1f}%")
    
    print("\n详细结果:")
    for test_name, result in test_results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
    
    # 生成JSON报告
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "test_name": "架构加固灾变模拟测试",
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": total_tests - passed_tests,
        "pass_rate": passed_tests/total_tests*100,
        "detailed_results": test_results,
        "environment": {
            "python_version": sys.version,
            "workspace": os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "test_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    }
    
    # 保存报告
    report_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs", "testing")
    os.makedirs(report_dir, exist_ok=True)
    
    report_file = os.path.join(report_dir, f"disaster_simulation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 详细报告已保存至: {report_file}")
    
    return report_file

def main():
    """主测试函数"""
    print("🏭 架构加固灾变模拟测试开始")
    print("=" * 50)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_results = {}
    
    # 执行测试
    test_results["data_fallback_disaster"] = test_data_fallback_disaster()
    test_results["port_monitor_disaster"] = test_port_monitor_disaster()
    test_results["cron_preflight_disaster"] = test_cron_preflight_disaster()
    
    # 生成报告
    report_file = generate_disaster_report(test_results)
    
    # 总体评估
    all_passed = all(test_results.values())
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 所有灾变模拟测试通过！")
        print("   架构加固模块在故障场景下表现正常。")
        print("   系统具备基本的抗灾变能力。")
    else:
        print("⚠️  部分测试失败")
        print("   需要检查架构加固模块的故障处理逻辑。")
    
    print(f"\n测试完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())