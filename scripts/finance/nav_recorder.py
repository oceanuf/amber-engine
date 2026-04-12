import pandas as pd
import json
import os
from datetime import datetime

NAV_FILE = "data/finance/nav_history.csv"
SIGNAL_FILE = "database/strategy_signal.json"

def record_nav():
    # 模拟从信号或账户获取当前净值
    # 在实际生产中，这里会对接券商接口或计算持仓市值
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    # 简单的逻辑：读取旧数据并追加
    if os.path.exists(NAV_FILE):
        df = pd.read_csv(NAV_FILE)
        if current_date in df['date'].values:
            print(f"Today's NAV already recorded for {current_date}")
            return
        
        # 获取最后一个净值并进行微小模拟波动（实际应接入实盘数据）
        last_nav = df['nav'].iloc[-1]
        new_nav = round(last_nav * 1.0005, 4) 
        new_row = {
            "date": current_date,
            "nav": new_nav,
            "total_value": int(df['total_value'].iloc[-1] * 1.0005),
            "cash": df['cash'].iloc[-1]
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv(NAV_FILE, index=False)
        print(f"✅ NAV recorded for {current_date}: {new_nav}")
    else:
        print("NAV history file missing. Please run init_nav_anchor.py first.")

if __name__ == "__main__":
    record_nav()
