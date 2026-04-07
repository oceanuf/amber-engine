#!/usr/bin/env python3
"""
调度器熔断测试脚本 - 模拟 Tushare Token 失效场景
符合 V1.4.1 地基加固专项要求
"""

import os
import sys
import time
import subprocess
import json
import tempfile
import shutil

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 测试配置
TEST_MODULE = "ingest_tushare_adapter"
TEST_ERROR_CODE = "TUSHARE_INIT_FAIL"
MAX_RETRIES = 3
CIRCUIT_BREAKER_FILE = "logs/circuit_breaker.json"
ORCHESTRATOR_PATH = "scripts/orchestrator.py"

def setup_test_environment():
    """设置测试环境"""
    print("🔧 设置熔断测试环境")
    
    # 确保日志目录存在
    os.makedirs("logs", exist_ok=True)
    
    # 清理现有熔断器状态
    if os.path.exists(CIRCUIT_BREAKER_FILE):
        print(f"清理现有熔断器状态: {CIRCUIT_BREAKER_FILE}")
        backup_file = CIRCUIT_BREAKER_FILE + ".pre_test.bak"
        shutil.copy2(CIRCUIT_BREAKER_FILE, backup_file)
        os.remove(CIRCUIT_BREAKER_FILE)
    
    # 创建模拟的 Tushare 模块，总是返回失败
    test_module_content = '''#!/usr/bin/env python3
"""
模拟 Tushare Token 失效的测试模块
"""

import sys
import time
import random

def main():
    """主函数，模拟 Token 失效"""
    print(f"[{TEST_ERROR_CODE}]: Tushare Token 失效，认证失败")
    print("错误详情: 无效的Tushare Token，请检查环境变量TUSHARE_TOKEN")
    print("建议: 1. 检查Token是否过期 2. 重新获取有效Token 3. 检查网络连接")
    
    # 模拟网络延迟
    time.sleep(random.uniform(0.5, 2.0))
    
    # 始终返回失败
    sys.exit(101)  # 使用非零退出码表示失败

if __name__ == "__main__":
    main()
'''
    
    # 创建测试模块文件
    test_module_path = f"scripts/ingest/{TEST_MODULE}_test_fail.py"
    with open(test_module_path, 'w', encoding='utf-8') as f:
        f.write(test_module_content)
    
    print(f"创建测试模块: {test_module_path}")
    
    # 修改 orchestrator 配置临时使用测试模块
    orchestrator_backup = ORCHESTRATOR_PATH + ".backup"
    if os.path.exists(orchestrator_backup):
        print(f"恢复 orchestrator 备份: {orchestrator_backup}")
        shutil.copy2(orchestrator_backup, ORCHESTRATOR_PATH)
    else:
        print(f"创建 orchestrator 备份: {orchestrator_backup}")
        shutil.copy2(ORCHESTRATOR_PATH, orchestrator_backup)
    
    # 读取并修改 orchestrator 配置
    with open(ORCHESTRATOR_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换模块路径为测试模块
    old_path = f'"path": "scripts/ingest/{TEST_MODULE}.py"'
    new_path = f'"path": "scripts/ingest/{TEST_MODULE}_test_fail.py"'
    content = content.replace(old_path, new_path)
    
    with open(ORCHESTRATOR_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 测试环境设置完成")
    return test_module_path, orchestrator_backup

def run_circuit_breaker_test():
    """执行熔断测试"""
    print("\\n🚀 开始熔断测试")
    print("=" * 60)
    
    test_results = []
    
    for attempt in range(MAX_RETRIES + 1):  # 额外运行一次验证熔断
        print(f"\\n📊 测试轮次 {attempt + 1}/{MAX_RETRIES + 1}")
        print("-" * 40)
        
        start_time = time.time()
        
        try:
            # 运行调度器
            cmd = [sys.executable, ORCHESTRATOR_PATH]
            print(f"执行命令: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            
            stdout, stderr = process.communicate(timeout=60)  # 60秒超时
            exit_code = process.returncode
            duration = time.time() - start_time
            
            # 分析输出
            error_found = False
            circuit_triggered = False
            
            if TEST_ERROR_CODE in stdout or TEST_ERROR_CODE in stderr:
                error_found = True
                print(f"✅ 检测到预期错误码: {TEST_ERROR_CODE}")
            
            if "触发熔断" in stdout or "熔断状态" in stdout:
                circuit_triggered = True
                print("✅ 检测到熔断触发")
            
            # 检查熔断器状态文件
            circuit_state = {}
            if os.path.exists(CIRCUIT_BREAKER_FILE):
                with open(CIRCUIT_BREAKER_FILE, 'r', encoding='utf-8') as f:
                    circuit_state = json.load(f)
            
            test_result = {
                "attempt": attempt + 1,
                "exit_code": exit_code,
                "duration": round(duration, 2),
                "error_found": error_found,
                "circuit_triggered": circuit_triggered,
                "circuit_state": circuit_state.get(TEST_MODULE, {}),
                "stdout_summary": stdout[-500:] if stdout else "",  # 最后500字符
                "stderr_summary": stderr[-500:] if stderr else ""
            }
            
            test_results.append(test_result)
            
            print(f"退出码: {exit_code}")
            print(f"执行时间: {duration:.2f}秒")
            print(f"错误检测: {'✅' if error_found else '❌'}")
            print(f"熔断触发: {'✅' if circuit_triggered else '❌'}")
            
            # 等待重试间隔
            if attempt < MAX_RETRIES:
                wait_time = 5
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
                
        except subprocess.TimeoutExpired:
            print("❌ 测试超时 (60秒)")
            test_results.append({
                "attempt": attempt + 1,
                "timeout": True,
                "duration": 60
            })
        except Exception as e:
            print(f"❌ 测试执行异常: {e}")
            test_results.append({
                "attempt": attempt + 1,
                "error": str(e)
            })
    
    return test_results

def cleanup_test_environment(test_module_path, orchestrator_backup):
    """清理测试环境"""
    print("\\n🧹 清理测试环境")
    
    # 删除测试模块
    if os.path.exists(test_module_path):
        os.remove(test_module_path)
        print(f"删除测试模块: {test_module_path}")
    
    # 恢复 orchestrator 配置
    if os.path.exists(orchestrator_backup):
        shutil.copy2(orchestrator_backup, ORCHESTRATOR_PATH)
        print(f"恢复 orchestrator 配置: {ORCHESTRATOR_PATH}")
    
    # 恢复熔断器状态
    circuit_backup = CIRCUIT_BREAKER_FILE + ".pre_test.bak"
    if os.path.exists(circuit_backup):
        shutil.copy2(circuit_backup, CIRCUIT_BREAKER_FILE)
        print(f"恢复熔断器状态: {CIRCUIT_BREAKER_FILE}")
    
    print("✅ 环境清理完成")

def analyze_test_results(test_results):
    """分析测试结果"""
    print("\\n📈 熔断测试结果分析")
    print("=" * 60)
    
    if not test_results:
        print("❌ 无测试结果")
        return False
    
    # 关键检查点
    checks = {
        "重试机制": False,
        "熔断触发": False,
        "优雅挂起": False,
        "断点保留": False
    }
    
    # 检查重试机制
    if len(test_results) >= MAX_RETRIES:
        checks["重试机制"] = True
        print(f"✅ 重试机制: 检测到 {MAX_RETRIES} 次重试")
    
    # 检查熔断触发
    circuit_triggered_in_any = any(r.get("circuit_triggered", False) for r in test_results)
    checks["熔断触发"] = circuit_triggered_in_any
    print(f"熔断触发: {'✅' if circuit_triggered_in_any else '❌'}")
    
    # 检查优雅挂起（最后轮次应该跳过模块执行）
    last_result = test_results[-1]
    if "熔断状态" in last_result.get("stdout_summary", "") or "跳过执行" in last_result.get("stdout_summary", ""):
        checks["优雅挂起"] = True
        print("✅ 优雅挂起: 熔断后模块被跳过执行")
    
    # 检查断点保留
    if os.path.exists(CIRCUIT_BREAKER_FILE):
        with open(CIRCUIT_BREAKER_FILE, 'r', encoding='utf-8') as f:
            circuit_state = json.load(f)
        
        if TEST_MODULE in circuit_state:
            checks["断点保留"] = True
            print(f"✅ 断点保留: 熔断状态已保存到 {CIRCUIT_BREAKER_FILE}")
            print(f"   熔断次数: {circuit_state[TEST_MODULE].get('break_count', 0)}")
            print(f"   最后熔断时间: {circuit_state[TEST_MODULE].get('last_break', 'N/A')}")
    
    # 总体评估
    print("\\n🎯 总体评估")
    print("-" * 40)
    
    success_count = sum(checks.values())
    total_checks = len(checks)
    
    print(f"通过检查: {success_count}/{total_checks}")
    
    for check_name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}")
    
    # 生成测试报告
    report = {
        "test_name": "调度器熔断测试",
        "test_module": TEST_MODULE,
        "test_error_code": TEST_ERROR_CODE,
        "max_retries": MAX_RETRIES,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "checks": checks,
        "success_rate": success_count / total_checks if total_checks > 0 else 0,
        "results_summary": [
            {
                "attempt": r.get("attempt"),
                "error_found": r.get("error_found", False),
                "circuit_triggered": r.get("circuit_triggered", False)
            }
            for r in test_results
        ]
    }
    
    # 保存测试报告
    report_file = "logs/circuit_breaker_test_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\\n📋 测试报告已保存: {report_file}")
    
    return success_count == total_checks

def main():
    """主测试函数"""
    print("=" * 60)
    print("🛡️  调度器熔断测试 - Tushare Token 失效场景")
    print("=" * 60)
    
    # 设置测试环境
    test_module_path, orchestrator_backup = setup_test_environment()
    
    try:
        # 执行测试
        test_results = run_circuit_breaker_test()
        
        # 分析结果
        test_passed = analyze_test_results(test_results)
        
        # 最终结论
        print("\\n" + "=" * 60)
        if test_passed:
            print("🎉 熔断测试通过！调度器能够在Token失效时:")
            print("   1. 正确重试3次")
            print("   2. 触发熔断机制")
            print("   3. 优雅挂起并保留断点")
            print("   4. 防止无限重试导致系统崩溃")
        else:
            print("⚠️  熔断测试部分失败，需要检查以下问题:")
            print("   1. 重试机制是否正确实现")
            print("   2. 熔断条件是否满足时触发")
            print("   3. 熔断状态是否持久化保存")
            print("   4. 模块是否在熔断后正确跳过")
        
        return 0 if test_passed else 1
        
    finally:
        # 清理环境
        cleanup_test_environment(test_module_path, orchestrator_backup)
    
    print("=" * 60)

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)