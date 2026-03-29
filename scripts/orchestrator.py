#!/usr/bin/env python3
"""
中央调度器原型 - 符合 V1.2.1 标准
负责调度模块执行，处理错误与熔断
"""

import os
import sys
import subprocess
import datetime
import json
import time
import signal

def load_secrets():
    """从 _PRIVATE_DATA/secrets.json 加载密钥到环境变量"""
    secrets_path = "_PRIVATE_DATA/secrets.json"
    if not os.path.exists(secrets_path):
        return False
    
    try:
        with open(secrets_path, 'r', encoding='utf-8') as f:
            secrets = json.load(f)
        
        # 将密钥加载到环境变量（如果尚未设置）
        for key, value in secrets.items():
            if not key.startswith('_') and value:  # 跳过注释字段和空值
                if key not in os.environ:
                    os.environ[key] = str(value)
        
        return True
    except Exception as e:
        print(f"[orchestrator:WARN] 加载密钥文件失败: {e}", file=sys.stderr)
        return False

# 配置
MODULES = [
    {
        "name": "ingest_etf_gold",
        "path": "scripts/ingest/etf_gold.py",
        "retry_on": ["NET_TIMEOUT"],  # 对这些错误码重试
        "circuit_break_on": ["SCHEMA_MISMATCH", "AUTH_FAIL"],  # 对这些错误码熔断
        "max_retries": 3,
        "timeout": 300,  # 秒
        "frequency": "daily",
        "dependencies": []  # 无依赖
    },
    {
        "name": "ingest_etf_index",
        "path": "scripts/ingest/etf_index.py",
        "retry_on": ["NET_TIMEOUT"],  # 对这些错误码重试
        "circuit_break_on": ["SCHEMA_MISMATCH", "AUTH_FAIL"],  # 对这些错误码熔断
        "max_retries": 3,
        "timeout": 300,  # 秒
        "frequency": "daily",
        "dependencies": []
    },
    {
        "name": "ingest_macro_logic",
        "path": "scripts/ingest/macro_logic.py",
        "retry_on": ["NET_TIMEOUT"],  # 对这些错误码重试
        "circuit_break_on": ["SCHEMA_MISMATCH", "AUTH_FAIL"],  # 对这些错误码熔断
        "max_retries": 3,
        "timeout": 300,  # 秒
        "frequency": "weekly",
        "dependencies": []
    },
    {
        "name": "ingest_sentiment_monitor",
        "path": "scripts/ingest/sentiment_monitor.py",
        "retry_on": ["NET_TIMEOUT"],  # 对这些错误码重试
        "circuit_break_on": ["SCHEMA_MISMATCH", "AUTH_FAIL"],  # 对这些错误码熔断
        "max_retries": 3,
        "timeout": 300,  # 秒
        "frequency": "daily",
        "dependencies": []
    },
    {
        "name": "cleaner_etf_purify",
        "path": "scripts/cleaner/etf_purify.py",
        "retry_on": ["NET_TIMEOUT", "FILE_WRITE_FAIL"],  # 对这些错误码重试
        "circuit_break_on": ["SCHEMA_MISMATCH", "VALIDATE_FAIL"],  # 对这些错误码熔断
        "max_retries": 2,
        "timeout": 600,  # 清洗可能需要更长时间
        "frequency": "daily",
        "dependencies": ["ingest_etf_gold", "ingest_etf_index"]  # 依赖这两个 ingest 模块
    },
    {
        "name": "storer_vault_storer",
        "path": "scripts/storer/vault_storer.py",
        "retry_on": ["FILE_WRITE_FAIL", "BACKUP_FAIL"],  # 对这些错误码重试
        "circuit_break_on": ["PERMISSION_FAIL", "MERGE_FAIL"],  # 对这些错误码熔断
        "max_retries": 2,
        "timeout": 900,  # 存储可能需要更长时间（包含备份操作）
        "frequency": "daily",
        "dependencies": ["cleaner_etf_purify"]  # 依赖 cleaner 模块
    },
    {
        "name": "analyzer_indicator_engine",
        "path": "scripts/analyzer/indicator_engine.py",
        "retry_on": ["DATA_LOAD_FAIL", "ANALYSIS_FAIL", "FILE_WRITE_FAIL"],
        "circuit_break_on": ["SCHEMA_VALIDATE_FAIL", "ATOMIC_VALIDATE_FAIL"],
        "max_retries": 2,
        "timeout": 600,
        "frequency": "daily",
        "dependencies": ["storer_vault_storer"]
    },
    {
        "name": "synthesizer_score_engine",
        "path": "scripts/synthesizer/score_engine.py",
        "retry_on": ["ANALYSIS_NOT_FOUND", "PARAMS_NOT_FOUND", "SYNTHESIS_FAIL", "FILE_WRITE_FAIL"],
        "circuit_break_on": ["SCHEMA_VALIDATE_FAIL", "ATOMIC_VALIDATE_FAIL"],
        "max_retries": 2,
        "timeout": 600,
        "frequency": "daily",
        "dependencies": ["analyzer_indicator_engine"]
    }
    # 可以添加更多模块：Synthesizer, Targeter 等
]

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "orchestrator.log")
CIRCUIT_BREAKER_FILE = os.path.join(LOG_DIR, "circuit_breaker.json")

def ensure_log_dir():
    """确保日志目录存在"""
    os.makedirs(LOG_DIR, exist_ok=True)

def log(level, module, message):
    """统一日志记录"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{module}:{level}] {message}\n"
    
    # 写入文件
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)
    
    # 同时输出到 stdout（便于调试）
    print(log_entry, end="")

def load_circuit_breaker_state():
    """加载熔断器状态"""
    if not os.path.exists(CIRCUIT_BREAKER_FILE):
        return {}
    
    try:
        with open(CIRCUIT_BREAKER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_circuit_breaker_state(state):
    """保存熔断器状态"""
    try:
        with open(CIRCUIT_BREAKER_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log("ERROR", "orchestrator", f"保存熔断器状态失败: {e}")

def is_circuit_broken(module_name, error_code):
    """检查是否应该触发熔断"""
    state = load_circuit_breaker_state()
    module_state = state.get(module_name, {})
    
    # 检查此错误码是否配置为触发熔断
    for module_config in MODULES:
        if module_config["name"] == module_name:
            if error_code in module_config["circuit_break_on"]:
                return True
    
    # 检查是否已在熔断状态（例如，最近5分钟内熔断过）
    last_break = module_state.get("last_break")
    if last_break:
        last_time = datetime.datetime.fromisoformat(last_break)
        if (datetime.datetime.now() - last_time).total_seconds() < 300:  # 5分钟
            return True
    
    return False

def record_circuit_break(module_name, error_code, message):
    """记录熔断事件"""
    state = load_circuit_breaker_state()
    if module_name not in state:
        state[module_name] = {}
    
    state[module_name].update({
        "last_break": datetime.datetime.now().isoformat(),
        "error_code": error_code,
        "message": message,
        "break_count": state[module_name].get("break_count", 0) + 1
    })
    
    save_circuit_breaker_state(state)
    
    # 发送警报（这里只是日志，实际可接入邮件/钉钉）
    alert_msg = f"🚨 模块 {module_name} 触发熔断！错误码: {error_code}, 原因: {message}"
    log("ALERT", "orchestrator", alert_msg)
    print(f"\n⚠️  {alert_msg}\n")

def parse_stderr(stderr_text):
    """解析 stderr，提取错误码和消息"""
    # 期望格式: "[ERR_CODE]: Message"
    lines = stderr_text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('[') and ']:' in line:
            # 提取错误码
            end_bracket = line.find(']')
            if end_bracket > 0:
                error_code = line[1:end_bracket]
                message = line[end_bracket+2:].strip()
                return error_code, message
    return None, stderr_text

def run_module(module_config):
    """执行单个模块"""
    module_name = module_config["name"]
    module_path = module_config["path"]
    max_retries = module_config["max_retries"]
    
    log("INFO", "orchestrator", f"开始执行模块: {module_name}")
    
    for attempt in range(max_retries):
        if attempt > 0:
            log("INFO", "orchestrator", f"重试 {attempt}/{max_retries} - {module_name}")
            time.sleep(5)  # 重试间隔
        
        try:
            # 检查熔断状态
            if is_circuit_broken(module_name, None):
                log("WARN", "orchestrator", f"模块 {module_name} 处于熔断状态，跳过执行")
                return False, "CIRCUIT_BROKEN"
            
            # 执行命令
            cmd = [sys.executable, module_path]
            log("DEBUG", "orchestrator", f"执行命令: {' '.join(cmd)}")
            
            # 设置超时
            start_time = time.time()
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            
            try:
                stdout, stderr = process.communicate(timeout=module_config["timeout"])
                exit_code = process.returncode
                duration = time.time() - start_time
                
                # 记录输出
                if stdout:
                    log("DEBUG", module_name, f"stdout: {stdout[:500]}")  # 只记录前500字符
                if stderr:
                    log("DEBUG", module_name, f"stderr: {stderr}")
                
                # 解析错误码
                error_code, error_msg = parse_stderr(stderr)
                
                # 处理结果
                if exit_code == 0:
                    log("INFO", "orchestrator", f"模块 {module_name} 执行成功 (耗时: {duration:.2f}s)")
                    return True, None
                else:
                    log("WARN", "orchestrator", f"模块 {module_name} 失败，退出码: {exit_code}")
                    
                    # 检查是否需要熔断
                    if error_code and is_circuit_broken(module_name, error_code):
                        record_circuit_break(module_name, error_code, error_msg)
                        return False, "CIRCUIT_BROKEN"
                    
                    # 检查是否应该重试
                    if error_code in module_config["retry_on"]:
                        log("INFO", "orchestrator", f"错误码 {error_code} 可重试，进行下一次尝试")
                        continue  # 重试
                    else:
                        # 不可重试的错误
                        log("ERROR", "orchestrator", f"模块 {module_name} 遇到不可重试错误: {error_code}")
                        return False, error_code or "UNKNOWN"
            
            except subprocess.TimeoutExpired:
                process.kill()
                log("ERROR", "orchestrator", f"模块 {module_name} 执行超时")
                # 超时视为网络错误，可重试
                if attempt < max_retries - 1:
                    continue
                else:
                    return False, "TIMEOUT"
                    
        except Exception as e:
            log("ERROR", "orchestrator", f"执行模块 {module_name} 时发生异常: {e}")
            import traceback
            traceback.print_exc()
            if attempt < max_retries - 1:
                continue
            else:
                return False, "EXECUTION_ERROR"
    
    # 所有重试都失败
    log("ERROR", "orchestrator", f"模块 {module_name} 达到最大重试次数仍失败")
    return False, "MAX_RETRIES_EXCEEDED"

def generate_execution_report(results):
    """生成执行报告"""
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "total_modules": len(results),
        "successful": sum(1 for r in results if r[0]),
        "failed": sum(1 for r in results if not r[0]),
        "details": []
    }
    
    for (success, module_name, error_info) in results:
        report["details"].append({
            "module": module_name,
            "success": success,
            "error": error_info if not success else None
        })
    
    # 保存报告
    reports_dir = "docs/reports"
    os.makedirs(reports_dir, exist_ok=True)
    
    report_file = os.path.join(reports_dir, f"orchestrator_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    log("INFO", "orchestrator", f"执行报告已保存: {report_file}")
    return report

def main():
    """主调度循环"""
    ensure_log_dir()
    
    # 加载密钥到环境变量
    if load_secrets():
        log("INFO", "orchestrator", "密钥文件加载成功")
    else:
        log("WARN", "orchestrator", "未找到密钥文件或加载失败，使用环境变量")
    
    log("INFO", "orchestrator", "中央调度器启动")
    log("INFO", "orchestrator", f"Python 版本: {sys.version}")
    log("INFO", "orchestrator", f"工作目录: {os.getcwd()}")
    
    # 检查环境变量（密钥等）
    if "GOLD_API_KEY" not in os.environ:
        log("WARN", "orchestrator", "GOLD_API_KEY 环境变量未设置，模块可能使用模拟数据")
    
    # 执行所有模块（支持依赖关系）
    results = []
    module_status = {}  # 记录模块执行状态: {name: (success, error_info)}
    
    for module_config in MODULES:
        module_name = module_config["name"]
        
        # 检查模块文件是否存在
        if not os.path.exists(module_config["path"]):
            log("ERROR", "orchestrator", f"模块文件不存在: {module_config['path']}")
            results.append((False, module_name, "MODULE_FILE_MISSING"))
            module_status[module_name] = (False, "MODULE_FILE_MISSING")
            continue
        
        # 检查依赖关系
        dependencies = module_config.get("dependencies", [])
        missing_deps = []
        failed_deps = []
        
        for dep in dependencies:
            if dep not in module_status:
                missing_deps.append(dep)
            elif not module_status[dep][0]:  # 依赖模块失败
                failed_deps.append(dep)
        
        if missing_deps:
            log("ERROR", "orchestrator", f"模块 {module_name} 依赖的模块尚未执行: {missing_deps}")
            results.append((False, module_name, f"DEPENDENCY_NOT_EXECUTED: {missing_deps}"))
            module_status[module_name] = (False, f"DEPENDENCY_NOT_EXECUTED: {missing_deps}")
            continue
        
        if failed_deps:
            log("WARN", "orchestrator", f"模块 {module_name} 依赖的模块失败: {failed_deps}，跳过执行")
            results.append((False, module_name, f"DEPENDENCY_FAILED: {failed_deps}"))
            module_status[module_name] = (False, f"DEPENDENCY_FAILED: {failed_deps}")
            continue
        
        # 执行模块
        success, error_info = run_module(module_config)
        results.append((success, module_name, error_info))
        module_status[module_name] = (success, error_info)
    
    # 生成报告
    report = generate_execution_report(results)
    
    # 总结
    if report["failed"] == 0:
        log("INFO", "orchestrator", f"所有模块执行成功 ({report['successful']}/{report['total_modules']})")
        return 0
    else:
        log("ERROR", "orchestrator", f"部分模块执行失败 ({report['failed']}/{report['total_modules']})")
        # 输出失败详情
        for detail in report["details"]:
            if not detail["success"]:
                log("ERROR", "orchestrator", f"  - {detail['module']}: {detail['error']}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)