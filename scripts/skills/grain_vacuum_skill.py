#!/usr/bin/env python3
"""
Grain Vacuum Skill - 文档治理技能
版本: 1.0.0
描述: 语义触发GRAIN.md自动归档，实现"所说即所得"的文档治理
功能:
  1. 语义识别: 支持"打扫grain"、"整理任务"、"清理GRAIN"等指令
  2. 快照备份: 执行前对GRAIN.md进行备份
  3. 物理执行: 调用grain_vacuum.py核心逻辑
  4. 智能反馈: 统计归档任务数，提供专业反馈
  5. 异常处理: 处理死锁、无任务等边界情况
"""

import os
import sys
import re
import shutil
import datetime
from typing import Dict, List, Optional, Tuple

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class GrainVacuumSkill:
    """Grain文档治理技能"""
    
    def __init__(self):
        """初始化技能"""
        self.trigger_patterns = [
            r"(?i)(打扫|清理|整理)\s*(grain|任务|GRAIN)",
            r"(?i)vacuum\s*grain",
            r"(?i)clean\s*tasks",
            r"(?i)归档\s*任务"
        ]
        
        # 文件路径
        self.grain_file = "GRAIN.md"
        self.archive_file = "GRAIN_ARCHIVE.md"
        self.backup_dir = "backups/grain"
        
        # 创建备份目录
        os.makedirs(self.backup_dir, exist_ok=True)
        
    def should_trigger(self, text: str) -> bool:
        """检查是否应该触发技能"""
        text = text.strip().lower()
        
        for pattern in self.trigger_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def create_backup(self) -> str:
        """创建GRAIN.md备份"""
        if not os.path.exists(self.grain_file):
            return None
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(self.backup_dir, f"GRAIN_{timestamp}.md")
        
        try:
            shutil.copy2(self.grain_file, backup_file)
            return backup_file
        except Exception as e:
            print(f"备份失败: {e}")
            return None
    
    def analyze_grain_status(self) -> Dict[str, int]:
        """分析GRAIN.md状态"""
        if not os.path.exists(self.grain_file):
            return {"total": 0, "completed": 0, "pending": 0, "running": 0, "blocked": 0, "cancelled": 0}
        
        try:
            with open(self.grain_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 只统计任务部分，排除状态说明部分
            # 找到第一个"---"之后的内容（跳过状态说明）
            parts = content.split("---", 2)
            if len(parts) >= 3:
                # 第一部分是状态说明，第二部分是任务内容，第三部分是历史记录
                task_content = parts[1]
            else:
                task_content = content
            
            # 统计任务状态（只统计任务部分）
            completed = task_content.count("✅")
            pending = task_content.count("🔲")
            running = task_content.count("⏳")
            blocked = task_content.count("❌")
            cancelled = task_content.count("🚫")
            
            total = completed + pending + running + blocked + cancelled
            
            return {
                "total": total,
                "completed": completed,
                "pending": pending,
                "running": running,
                "blocked": blocked,
                "cancelled": cancelled
            }
        except Exception as e:
            print(f"分析GRAIN状态失败: {e}")
            return {"total": 0, "completed": 0, "pending": 0, "running": 0, "blocked": 0, "cancelled": 0}
    
    def execute_vacuum(self) -> Tuple[int, int, Dict[str, int]]:
        """执行Grain Vacuum"""
        # 导入grain_vacuum模块
        try:
            from scripts.ops.grain_vacuum import vacuum
            
            # 直接调用vacuum，它现在返回(归档数量, 剩余任务数, 状态)
            archived_count, remaining_tasks, status = vacuum()
            
            return archived_count, remaining_tasks, status
            
        except ImportError as e:
            print(f"导入grain_vacuum模块失败: {e}")
            return 0, 0, {"total": 0, "completed": 0, "pending": 0, "running": 0, "blocked": 0, "cancelled": 0}
        except Exception as e:
            print(f"执行vacuum失败: {e}")
            return 0, 0, {"total": 0, "completed": 0, "pending": 0, "running": 0, "blocked": 0, "cancelled": 0}
    
    def generate_response(self, archived_count: int, remaining_tasks: int, status: Dict[str, int]) -> str:
        """生成响应消息"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        if archived_count == 0 and remaining_tasks == 0:
            return f"""🧹 **Grain文档治理报告** ({timestamp})

📊 **执行结果**: 无任务可归档
📋 **当前状态**: GRAIN.md为空或不存在
💡 **建议**: 请先创建任务或检查文件路径

> *"整洁的文档是高效协作的基础。"*"""
        
        elif archived_count == 0 and remaining_tasks > 0:
            return f"""🧹 **Grain文档治理报告** ({timestamp})

📊 **执行结果**: 无已完成任务可归档
📋 **当前状态**: 
  - 待处理任务: {status['pending']} 个
  - 执行中任务: {status['running']} 个
  - 阻塞任务: {status['blocked']} 个
💡 **建议**: 请先完成任务或标记为✅状态

> *"专注当下，未来自会井然有序。"*"""
        
        elif archived_count > 0:
            return f"""🧹 **Grain文档治理报告** ({timestamp})

✅ **整理完毕!**
📊 **归档统计**: 
  - 已归档任务: {archived_count} 个
  - 剩余任务: {remaining_tasks} 个
📋 **详细状态**:
  - 🔲 待处理: {status['pending']} 个
  - ⏳ 执行中: {status['running']} 个  
  - ❌ 阻塞: {status['blocked']} 个
  - 🚫 已取消: {status['cancelled']} 个
📁 **文件位置**:
  - 当前任务: `GRAIN.md`
  - 历史归档: `GRAIN_ARCHIVE.md`

> *"归档不是结束，而是新篇章的开始。"*"""
        
        else:
            return f"""🧹 **Grain文档治理报告** ({timestamp})

⚠️ **执行异常**
📊 **状态分析**: 系统检测到异常情况
💡 **建议操作**: 
  1. 检查 `GRAIN.md` 文件格式
  2. 验证 `scripts/ops/grain_vacuum.py` 脚本
  3. 查看系统日志获取详细信息

> *"异常是系统进化的契机。"*"""
    
    def process(self, text: str) -> str:
        """处理用户输入"""
        if not self.should_trigger(text):
            return None
        
        print(f"🧹 收到Grain治理指令: {text}")
        
        # 1. 创建备份
        backup_file = self.create_backup()
        if backup_file:
            print(f"  备份已创建: {backup_file}")
        
        # 2. 执行vacuum
        archived_count, remaining_tasks, status = self.execute_vacuum()
        
        # 3. 生成响应
        response = self.generate_response(archived_count, remaining_tasks, status)
        
        return response

def main():
    """主函数 - 测试用"""
    skill = GrainVacuumSkill()
    
    test_cases = [
        "打扫grain",
        "清理GRAIN",
        "整理任务",
        "vacuum grain",
        "归档任务"
    ]
    
    print("🧹 Grain Vacuum Skill 测试")
    print("=" * 60)
    
    for text in test_cases:
        print(f"\n测试指令: '{text}'")
        
        if skill.should_trigger(text):
            print("  ✅ 触发成功")
            
            # 执行处理
            response = skill.process(text)
            if response:
                print("  📋 响应生成:")
                print(response[:200] + "..." if len(response) > 200 else response)
        else:
            print("  ❌ 未触发")

if __name__ == "__main__":
    main()