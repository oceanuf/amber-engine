#!/usr/bin/env python3
"""
环境自检与异常熔断脚本 - 2614-032号系统加固
功能：在orchestrator.py运行前执行环境自检，异常时自动修复
"""

import os
import sys
import json
import time
import subprocess
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/environment_check.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EnvironmentChecker:
    """环境检查与自修复器"""
    
    def __init__(self):
        """初始化检查器"""
        self.check_results = {}
        self.repair_attempts = {}
        
    def check_secrets_file(self) -> Tuple[bool, str]:
        """
        检查secrets.json文件
        
        Returns:
            (检查结果, 详细信息)
        """
        secrets_path = "_PRIVATE_DATA/secrets.json"
        
        try:
            if not os.path.exists(secrets_path):
                return False, f"secrets.json文件不存在: {secrets_path}"
            
            # 检查文件权限
            stat_info = os.stat(secrets_path)
            if stat_info.st_mode & 0o777 != 0o600:
                return False, f"secrets.json权限不安全: {oct(stat_info.st_mode)}，应为600"
            
            # 检查文件内容
            with open(secrets_path, 'r', encoding='utf-8') as f:
                secrets = json.load(f)
            
            required_keys = ["tushare_token", "gold_api_key"]
            missing_keys = [key for key in required_keys if key not in secrets]
            
            if missing_keys:
                return False, f"secrets.json缺少必需密钥: {missing_keys}"
            
            # 检查密钥有效性（简单检查）
            for key in required_keys:
                if not secrets[key] or secrets[key] == "your_token_here":
                    return False, f"secrets.json中{key}无效或为默认值"
            
            return True, "secrets.json检查通过"
            
        except json.JSONDecodeError as e:
            return False, f"secrets.json JSON解析错误: {str(e)}"
        except Exception as e:
            return False, f"secrets.json检查异常: {str(e)}"
    
    def check_skillhub_availability(self) -> Tuple[bool, str]:
        """
        检查SkillHub CLI可用性
        
        Returns:
            (检查结果, 详细信息)
        """
        try:
            # 检查skillhub命令是否存在
            result = subprocess.run(
                ["which", "skillhub"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return False, "skillhub命令未找到，请检查PATH"
            
            skillhub_path = result.stdout.strip()
            
            # 检查skillhub版本
            version_result = subprocess.run(
                ["skillhub", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if version_result.returncode != 0:
                return False, f"skillhub版本检查失败: {version_result.stderr}"
            
            return True, f"SkillHub可用: {skillhub_path}, {version_result.stdout.strip()}"
            
        except subprocess.TimeoutExpired:
            return False, "skillhub命令检查超时"
        except Exception as e:
            return False, f"skillhub检查异常: {str(e)}"
    
    def check_critical_skills(self) -> Tuple[bool, str]:
        """
        检查关键技能是否安装
        
        Returns:
            (检查结果, 详细信息)
        """
        critical_skills = [
            "akshare-stock",
            "market-news-analyst", 
            "playwright-mcp",
            "summarize",
            "research-paper-writer"
        ]
        
        missing_skills = []
        available_skills = []
        
        for skill in critical_skills:
            skill_path = f"skills/{skill}"
            if os.path.exists(skill_path):
                available_skills.append(skill)
            else:
                missing_skills.append(skill)
        
        if missing_skills:
            return False, f"关键技能缺失: {missing_skills}"
        
        return True, f"关键技能就绪: {len(available_skills)}/{len(critical_skills)}"
    
    def check_database_permissions(self) -> Tuple[bool, str]:
        """
        检查数据库目录权限
        
        Returns:
            (检查结果, 详细信息)
        """
        database_dirs = ["database", "database/cleaned", "database/sentiment"]
        
        for dir_path in database_dirs:
            if not os.path.exists(dir_path):
                try:
                    os.makedirs(dir_path, exist_ok=True)
                    logger.info(f"创建目录: {dir_path}")
                except Exception as e:
                    return False, f"目录创建失败 {dir_path}: {str(e)}"
            
            # 检查目录权限
            try:
                stat_info = os.stat(dir_path)
                # 目录权限应至少为755
                if not (stat_info.st_mode & 0o755 == 0o755):
                    return False, f"目录权限异常 {dir_path}: {oct(stat_info.st_mode)}"
            except Exception as e:
                return False, f"目录权限检查失败 {dir_path}: {str(e)}"
        
        return True, "数据库目录权限检查通过"
    
    def check_web_server_connectivity(self) -> Tuple[bool, str]:
        """
        检查Web服务器连接性
        
        Returns:
            (检查结果, 详细信息)
        """
        web_urls = [
            "https://gemini.googlemanager.cn:10168/index.php",
            "https://gemini.googlemanager.cn:10168/verify_fix.php"
        ]
        
        for url in web_urls:
            try:
                # 使用curl检查连接
                result = subprocess.run(
                    ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", url],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode != 0:
                    return False, f"Web服务器连接失败 {url}: curl错误"
                
                http_code = result.stdout.strip()
                if http_code not in ["200", "301", "302"]:
                    return False, f"Web服务器响应异常 {url}: HTTP {http_code}"
                
            except subprocess.TimeoutExpired:
                return False, f"Web服务器连接超时 {url}"
            except Exception as e:
                return False, f"Web服务器检查异常 {url}: {str(e)}"
        
        return True, "Web服务器连接性检查通过"
    
    def repair_secrets_file(self) -> Tuple[bool, str]:
        """
        尝试修复secrets.json文件
        
        Returns:
            (修复结果, 详细信息)
        """
        secrets_path = "_PRIVATE_DATA/secrets.json"
        backup_path = f"{secrets_path}.backup_{int(time.time())}"
        
        try:
            # 1. 备份原文件
            if os.path.exists(secrets_path):
                import shutil
                shutil.copy2(secrets_path, backup_path)
                logger.info(f"已备份secrets.json: {backup_path}")
            
            # 2. 尝试通过Playwright模拟登录修复
            logger.info("尝试通过Playwright修复secrets.json...")
            
            # 这里可以调用playwright-mcp技能模拟登录相关网站获取token
            # 由于安全原因，这里仅演示流程
            
            # 3. 创建默认模板（实际应通过自动化获取）
            default_secrets = {
                "tushare_token": os.environ.get("TUSHARE_TOKEN", "your_token_here"),
                "gold_api_key": os.environ.get("GOLD_API_KEY", "your_api_key_here"),
                "last_repair_time": datetime.now().isoformat(),
                "repair_method": "environment_checker"
            }
            
            # 确保目录存在
            os.makedirs(os.path.dirname(secrets_path), exist_ok=True)
            
            # 写入新文件
            with open(secrets_path, 'w', encoding='utf-8') as f:
                json.dump(default_secrets, f, ensure_ascii=False, indent=2)
            
            # 设置安全权限
            os.chmod(secrets_path, 0o600)
            
            return True, f"secrets.json已修复（模板），原文件备份于: {backup_path}"
            
        except Exception as e:
            return False, f"secrets.json修复失败: {str(e)}"
    
    def run_checks(self) -> Dict[str, Dict]:
        """
        运行所有环境检查
        
        Returns:
            检查结果字典
        """
        checks = [
            ("secrets_file", self.check_secrets_file),
            ("skillhub_availability", self.check_skillhub_availability),
            ("critical_skills", self.check_critical_skills),
            ("database_permissions", self.check_database_permissions),
            ("web_server_connectivity", self.check_web_server_connectivity)
        ]
        
        results = {}
        
        for check_name, check_func in checks:
            logger.info(f"执行检查: {check_name}")
            start_time = time.time()
            
            try:
                success, message = check_func()
                elapsed = time.time() - start_time
                
                results[check_name] = {
                    "success": success,
                    "message": message,
                    "elapsed_seconds": round(elapsed, 3),
                    "timestamp": datetime.now().isoformat()
                }
                
                status = "✅" if success else "❌"
                logger.info(f"{status} {check_name}: {message} ({elapsed:.2f}s)")
                
            except Exception as e:
                elapsed = time.time() - start_time
                results[check_name] = {
                    "success": False,
                    "message": f"检查异常: {str(e)}",
                    "elapsed_seconds": round(elapsed, 3),
                    "timestamp": datetime.now().isoformat()
                }
                logger.error(f"❌ {check_name}异常: {str(e)}")
        
        return results
    
    def attempt_repairs(self, failed_checks: Dict) -> Dict[str, Dict]:
        """
        尝试修复失败的检查项
        
        Args:
            failed_checks: 失败的检查项
            
        Returns:
            修复结果字典
        """
        repair_strategies = {
            "secrets_file": self.repair_secrets_file,
            # 其他检查项的修复策略可以在这里添加
        }
        
        repair_results = {}
        
        for check_name in failed_checks:
            if check_name in repair_strategies:
                logger.info(f"尝试修复: {check_name}")
                start_time = time.time()
                
                try:
                    success, message = repair_strategies[check_name]()
                    elapsed = time.time() - start_time
                    
                    repair_results[check_name] = {
                        "success": success,
                        "message": message,
                        "elapsed_seconds": round(elapsed, 3),
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    status = "✅" if success else "❌"
                    logger.info(f"{status} 修复{check_name}: {message} ({elapsed:.2f}s)")
                    
                except Exception as e:
                    elapsed = time.time() - start_time
                    repair_results[check_name] = {
                        "success": False,
                        "message": f"修复异常: {str(e)}",
                        "elapsed_seconds": round(elapsed, 3),
                        "timestamp": datetime.now().isoformat()
                    }
                    logger.error(f"❌ 修复{check_name}异常: {str(e)}")
            else:
                logger.warning(f"无修复策略: {check_name}")
                repair_results[check_name] = {
                    "success": False,
                    "message": "无可用修复策略",
                    "timestamp": datetime.now().isoformat()
                }
        
        return repair_results
    
    def generate_report(self, check_results: Dict, repair_results: Dict = None) -> Dict:
        """
        生成环境检查报告
        
        Args:
            check_results: 检查结果
            repair_results: 修复结果
            
        Returns:
            完整报告
        """
        total_checks = len(check_results)
        passed_checks = sum(1 for r in check_results.values() if r["success"])
        failed_checks = total_checks - passed_checks
        
        # 计算总体状态
        overall_success = failed_checks == 0
        
        report = {
            "module": "environment_check",
            "timestamp": datetime.now().isoformat(),
            "overall_status": "PASS" if overall_success else "FAIL",
            "summary": {
                "total_checks": total_checks,
                "passed_checks": passed_checks,
                "failed_checks": failed_checks,
                "success_rate": round(passed_checks / total_checks * 100, 2) if total_checks > 0 else 0
            },
            "check_details": check_results,
            "environment_info": {
                "python_version": sys.version,
                "working_directory": os.getcwd(),
                "skillhub_path": subprocess.run(["which", "skillhub"], capture_output=True, text=True).stdout.strip()
            }
        }
        
        if repair_results:
            report["repair_details"] = repair_results
            repaired_count = sum(1 for r in repair_results.values() if r["success"])
            report["summary"]["repaired_checks"] = repaired_count
        
        return report
    
    def run(self, attempt_repair: bool = True) -> bool:
        """
        运行完整的环境检查流程
        
        Args:
            attempt_repair: 是否尝试修复
            
        Returns:
            总体检查结果
        """
        logger.info("=" * 60)
        logger.info("环境检查与自修复系统启动")
        logger.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"修复模式: {'启用' if attempt_repair else '禁用'}")
        logger.info("=" * 60)
        
        # 1. 运行所有检查
        check_results = self.run_checks()
        
        # 2. 识别失败的检查
        failed_checks = {name: result for name, result in check_results.items() if not result["success"]}
        
        # 3. 如果需要，尝试修复
        repair_results = None
        if attempt_repair and failed_checks:
            logger.info(f"发现{len(failed_checks)}个失败检查，尝试修复...")
            repair_results = self.attempt_repairs(failed_checks)
            
            # 重新检查修复后的项目
            for check_name in list(failed_checks.keys()):
                if check_name in repair_results and repair_results[check_name]["success"]:
                    logger.info(f"重新检查修复项: {check_name}")
                    success, message = getattr(self, f"check_{check_name}")()
                    check_results[check_name] = {
                        "success": success,
                        "message": f"修复后: {message}",
                        "timestamp": datetime.now().isoformat()
                    }
        
        # 4. 生成报告
        report = self.generate_report(check_results, repair_results)
        
        # 5. 保存报告
        report_dir = "logs/environment_reports"
        os.makedirs(report_dir, exist_ok=True)
        
        report_file = os.path.join(report_dir, f"environment_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info("=" * 60)
        logger.info(f"环境检查完成: {report['overall_status']}")
        logger.info(f"检查通过: {report['summary']['passed_checks']}/{report['summary']['total_checks']}")
        logger.info(f"详细报告: {report_file}")
        logger.info("=" * 60)
        
        # 6. 返回总体结果
        return report["overall_status"] == "PASS"

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="环境检查与自修复系统")
    parser.add_argument("--no-repair", action="store_true", help="禁用自动修复")
    parser.add_argument("--check-only", nargs="+", help="仅检查指定项目")
    
    args = parser.parse_args()
    
    try:
        checker = EnvironmentChecker()
        
        # 运行检查
        success = checker.run(attempt_repair=not args.no_repair)
        
        # 返回退出码
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"环境检查系统执行失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()