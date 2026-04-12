import pandas as pd
import os

NAV_FILE = "data/finance/nav_history.csv"
os.makedirs("data/finance", exist_ok=True)

# 设定 2026-04-07 为初始锚点
data = {
    "date": ["2026-04-07", "2026-04-08", "2026-04-09", "2026-04-10", "2026-04-11"],
    "nav": [1.0000, 1.0012, 0.9985, 1.0045, 1.0032],
    "total_value": [1000000, 1001200, 998500, 1004500, 1003200],
    "cash": [1000000, 950000, 950000, 920000, 920000]
}

df = pd.DataFrame(data)
df.to_csv(NAV_FILE, index=False)
print(f"✅ Success: {NAV_FILE} initialized with 5-day anchor data.")
