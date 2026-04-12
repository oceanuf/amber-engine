import json
import os
from datetime import datetime

def generate_daily_report():
    today = datetime.now().strftime('%Y-%m-%d')
    json_path = f"reports/macro/macro_pulse_today.json"
    output_path = f"daily-news/{today}.md"
    
    # 确保目录存在
    os.makedirs("daily-news", exist_ok=True)

    content = f"# 📰 琥珀每日资讯全档 - {today}\n\n"
    
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        content += f"## 🌐 宏观综述\n> {data.get('summary', '今日无摘要')}\n\n"
        content += f"**情绪得分**: {data.get('sentiment_score', 'N/A')} (范围: 0-1)\n\n"
        
        content += "## 🚀 核心资讯\n"
        for news in data.get('top_news', []):
            content += f"### 📌 {news.get('title')}\n"
            content += f"- {news.get('content')}\n"
            content += f"- **情绪权重**: {news.get('sentiment')}\n\n"
    else:
        content += "> ⚠️ 今日未采集到有效结构化新闻数据。\n"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Daily report generated: {output_path}")

if __name__ == "__main__":
    generate_daily_report()
