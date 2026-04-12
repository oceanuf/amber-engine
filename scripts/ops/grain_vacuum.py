import re
import os
from datetime import datetime
from typing import Tuple, Dict

GRAIN_FILE = "GRAIN.md"
ARCHIVE_FILE = "GRAIN_ARCHIVE.md"

def analyze_grain_status() -> Dict[str, int]:
    """分析GRAIN.md状态，返回任务统计"""
    if not os.path.exists(GRAIN_FILE):
        return {"total": 0, "completed": 0, "pending": 0, "running": 0, "blocked": 0, "cancelled": 0}
    
    try:
        with open(GRAIN_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 统计任务状态
        completed = content.count("✅")
        pending = content.count("🔲")
        running = content.count("⏳")
        blocked = content.count("❌")
        cancelled = content.count("🚫")
        
        total = completed + pending + running + blocked + cancelled
        
        return {
            "total": total,
            "completed": completed,
            "pending": pending,
            "running": running,
            "blocked": blocked,
            "cancelled": cancelled
        }
    except Exception:
        return {"total": 0, "completed": 0, "pending": 0, "running": 0, "blocked": 0, "cancelled": 0}

def vacuum() -> Tuple[int, int, Dict[str, int]]:
    """
    执行Grain Vacuum
    
    返回:
        Tuple[归档数量, 剩余任务数, 处理后状态]
    """
    if not os.path.exists(GRAIN_FILE):
        return 0, 0, {"total": 0, "completed": 0, "pending": 0, "running": 0, "blocked": 0, "cancelled": 0}

    # 执行前的状态
    before_status = analyze_grain_status()
    
    with open(GRAIN_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # 识别任务序列块的正则表达式
    pattern = r"(## 🎯 当前任务序列:.*?(?=\n## 🎯|\n---|\Z))"
    sections = re.findall(pattern, content, re.DOTALL)
    
    active_sections = []
    archived_sections = []

    for section in sections:
        if "🔲" not in section and "⏳" not in section and "✅" in section:
            archived_sections.append(section)
        else:
            active_sections.append(section)

    if not archived_sections:
        # 无已完成任务
        after_status = analyze_grain_status()
        remaining = after_status["pending"] + after_status["running"]
        return 0, remaining, after_status

    # 执行归档
    with open(ARCHIVE_FILE, 'a', encoding='utf-8') as f:
        f.write(f"\n\n### 📦 Archived at {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("\n".join(archived_sections))

    header = content.split("---")[0] + "---\n\n"
    new_content = header + "\n".join(active_sections)
    footer = "\n\n---\n\n## 📅 历史执行记录 (归档镜像)\n- [✅ 自动归档已执行 | " + datetime.now().strftime('%Y-%m-%d') + "]"
    
    with open(GRAIN_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content + footer)
    
    # 执行后的状态
    after_status = analyze_grain_status()
    
    # 计算归档数量和剩余任务
    archived_count = before_status["completed"] - after_status["completed"]
    remaining = after_status["pending"] + after_status["running"]
    
    return archived_count, remaining, after_status

def main():
    """命令行入口"""
    archived_count, remaining, status = vacuum()
    
    if archived_count == 0 and remaining == 0:
        print("Done: No tasks found in GRAIN.md")
    elif archived_count == 0:
        print(f"Done: No completed tasks found. {remaining} tasks remaining.")
    else:
        print(f"Success: {archived_count} tasks archived. {remaining} tasks remaining.")
        print(f"Status: 🔲{status['pending']} ⏳{status['running']} ✅{status['completed']} ❌{status['blocked']} 🚫{status['cancelled']}")

if __name__ == "__main__":
    main()
