import re
import os
from datetime import datetime

GRAIN_FILE = "GRAIN.md"
ARCHIVE_FILE = "GRAIN_ARCHIVE.md"

def vacuum():
    if not os.path.exists(GRAIN_FILE):
        return

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
        print("Done: No completed tasks found for vacuuming.")
        return

    with open(ARCHIVE_FILE, 'a', encoding='utf-8') as f:
        f.write(f"\n\n### 📦 Archived at {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("\n".join(archived_sections))

    header = content.split("---")[0] + "---\n\n"
    new_content = header + "\n".join(active_sections)
    footer = "\n\n---\n\n## 📅 历史执行记录 (归档镜像)\n- [✅ 自动归档已执行 | " + datetime.now().strftime('%Y-%m-%d') + "]"
    
    with open(GRAIN_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content + footer)
    print(f"Success: {len(archived_sections)} sequences moved to archive.")

if __name__ == "__main__":
    vacuum()
