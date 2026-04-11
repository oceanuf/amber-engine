#!/usr/bin/env python3
"""
琥珀引擎 - 净值记录模块 (NAV Recorder)
版本: V1.0.0
功能: 自动计算虚拟基金每日资产净值(NAV)，记录到时间序列CSV中
法典依据: 任务指令[2616-0411-P0E] - 虚拟基金清算自动化与实战复盘闭环
作者: Engineer Cheese 🧀
创建日期: 2026-04-11
"""

import os
import sys
import json
import csv
import datetime
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
import tushare as ts

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NAVRecorder:
    """
    净值记录器 - 负责每日资产净值的计算与记录
    """
    
    def __init__(self, workspace_root: Optional[str] = None):
        """
        初始化净值记录器
        
        Args:
            workspace_root: 工作空间根目录，如果为None则从环境变量或默认路径获取
        """
        self.workspace_root = workspace_root or self._get_workspace_root()
        self.virtual_fund_path = os.path.join(self.workspace_root, "database", "arena", "virtual_fund.json")
        self.nav_history_path = os.path.join(self.workspace_root, "database", "arena", "nav_history.csv")
        
        # Tushare Pro API配置
        self.tushare_token = os.environ.get("TUSHARE_TOKEN")
        
        # 如果环境变量没有，尝试从secrets.json读取
        if not self.tushare_token:
            secrets_path = os.path.join(self.workspace_root, "_PRIVATE_DATA", "secrets.json")
            try:
                if os.path.exists(secrets_path):
                    import json
                    with open(secrets_path, 'r', encoding='utf-8') as f:
                        secrets = json.load(f)
                        self.tushare_token = secrets.get("TUSHARE_TOKEN")
                        logger.info("从secrets.json读取TUSHARE_TOKEN")
            except Exception as e:
                logger.warning(f"读取secrets.json失败: {e}")
        
        self.tushare_pro = None
        self.last_api_call_time = 0
        self.api_call_interval = 0.5  # 每次调用间隔0.5秒，避免频率限制
        
        # 价格缓存（用于回退和性能优化）
        self.price_cache: Dict[str, float] = {}
        
        # 初始化Tushare
        self._init_tushare()
        
        logger.info(f"净值记录器初始化完成，工作空间: {self.workspace_root}")
        logger.info(f"净值历史文件: {self.nav_history_path}")
    
    def _get_workspace_root(self) -> str:
        """获取工作空间根目录"""
        # 优先从环境变量获取
        workspace = os.environ.get("GITHUB_WORKSPACE")
        if workspace and os.path.exists(workspace):
            return workspace
        
        # 默认路径（amber-engine目录）
        default_path = "/home/luckyelite/.openclaw/workspace/amber-engine"
        if os.path.exists(default_path):
            return default_path
        
        # 当前脚本的祖父目录
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return script_dir
    
    def _init_tushare(self):
        """初始化Tushare Pro API"""
        if self.tushare_token:
            try:
                ts.set_token(self.tushare_token)
                self.tushare_pro = ts.pro_api()
                logger.info("Tushare Pro API初始化成功")
            except Exception as e:
                logger.warning(f"Tushare Pro API初始化失败: {e}，将使用回退逻辑")
        else:
            logger.warning("未找到TUSHARE_TOKEN环境变量，将使用回退逻辑")
    
    def _get_current_price(self, ticker: str) -> Tuple[float, str]:
        """
        获取股票当前价格，支持多级降级
        
        Args:
            ticker: 股票代码
            
        Returns:
            (价格, 来源描述)
        """
        # 1. 优先使用Tushare实时API
        if self.tushare_pro:
            try:
                # 频率控制
                current_time = time.time()
                if current_time - self.last_api_call_time < self.api_call_interval:
                    time.sleep(self.api_call_interval - (current_time - self.last_api_call_time))
                
                # 转换股票代码格式
                ts_code = f"{ticker}.SZ" if ticker.startswith('0') or ticker.startswith('3') else f"{ticker}.SH"
                
                # 查询实时行情
                df = self.tushare_pro.daily(ts_code=ts_code, trade_date=datetime.datetime.now().strftime('%Y%m%d'))
                self.last_api_call_time = time.time()
                
                if df is not None and not df.empty:
                    close_price = float(df.iloc[0]['close'])
                    self.price_cache[ticker] = close_price
                    return close_price, "Tushare实时API"
                else:
                    logger.warning(f"Tushare返回空数据: {ticker}")
                    
            except Exception as e:
                logger.warning(f"Tushare API调用失败: {ticker}, 错误: {e}")
                # 继续尝试其他来源
        
        # 2. 尝试从virtual_fund.json中获取current_price字段
        try:
            with open(self.virtual_fund_path, 'r', encoding='utf-8') as f:
                fund_data = json.load(f)
            
            for position in fund_data.get('positions', []):
                if position.get('ticker') == ticker:
                    current_price = position.get('current_price')
                    if current_price and current_price > 0:
                        return float(current_price), "virtual_fund.json缓存"
        except Exception as e:
            logger.warning(f"读取virtual_fund.json失败: {e}")
        
        # 3. 尝试从价格缓存中获取
        if ticker in self.price_cache:
            return self.price_cache[ticker], "内存缓存"
        
        # 4. 如果都失败，返回0.0并记录警告
        logger.error(f"无法获取股票价格: {ticker}，返回0.0")
        return 0.0, "DATA_MISSING"
    
    def _load_virtual_fund(self) -> Dict:
        """加载虚拟基金数据"""
        try:
            with open(self.virtual_fund_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载virtual_fund.json失败: {e}")
            raise
    
    def calculate_nav(self) -> Dict[str, Any]:
        """
        计算当前资产净值
        
        Returns:
            包含详细NAV数据的字典
        """
        fund_data = self._load_virtual_fund()
        
        # 获取现金
        cash = fund_data.get('current_capital', 0.0)
        
        # 计算持仓市值
        total_market_value = 0.0
        position_details = []
        
        for position in fund_data.get('positions', []):
            ticker = position.get('ticker')
            quantity = position.get('quantity', 0)
            
            if not ticker or quantity <= 0:
                continue
            
            # 获取当前价格
            current_price, price_source = self._get_current_price(ticker)
            
            # 计算市值
            market_value = current_price * quantity
            
            total_market_value += market_value
            
            position_details.append({
                'ticker': ticker,
                'name': position.get('name', ''),
                'quantity': quantity,
                'avg_cost': position.get('average_cost', 0),
                'current_price': current_price,
                'market_value': market_value,
                'price_source': price_source
            })
        
        # 总资产 = 现金 + 持仓市值
        total_assets = cash + total_market_value
        
        # 初始资本
        initial_capital = fund_data.get('initial_capital', 1000000.0)
        
        # 计算累计收益率
        total_return_pct = ((total_assets - initial_capital) / initial_capital * 100) if initial_capital > 0 else 0
        
        # 当前日期
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        nav_data = {
            'date': current_date,
            'timestamp': current_timestamp,
            'total_assets': round(total_assets, 2),
            'cash': round(cash, 2),
            'positions_market_value': round(total_market_value, 2),
            'initial_capital': round(initial_capital, 2),
            'total_return_pct': round(total_return_pct, 4),
            'position_count': len(position_details),
            'positions': position_details
        }
        
        logger.info(f"NAV计算完成: 总资产={total_assets:.2f}, 现金={cash:.2f}, 持仓市值={total_market_value:.2f}, 收益率={total_return_pct:.2f}%")
        
        return nav_data
    
    def record_nav(self, nav_data: Optional[Dict] = None) -> bool:
        """
        记录NAV到历史CSV文件
        
        Args:
            nav_data: 可选的NAV数据，如果为None则重新计算
            
        Returns:
            是否成功
        """
        if nav_data is None:
            nav_data = self.calculate_nav()
        
        try:
            # 检查文件是否存在，不存在则创建并写入表头
            file_exists = os.path.exists(self.nav_history_path)
            
            with open(self.nav_history_path, 'a', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'date', 'timestamp', 'total_assets', 'cash', 
                    'positions_market_value', 'initial_capital', 
                    'total_return_pct', 'position_count'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                if not file_exists:
                    writer.writeheader()
                    logger.info(f"创建新的NAV历史文件: {self.nav_history_path}")
                
                # 写入数据行
                row_data = {k: nav_data.get(k) for k in fieldnames}
                writer.writerow(row_data)
                
                logger.info(f"NAV记录已写入: {nav_data['date']} {nav_data['timestamp']}")
                return True
                
        except Exception as e:
            logger.error(f"写入NAV历史文件失败: {e}")
            return False
    
    def run(self) -> bool:
        """
        执行完整的NAV记录流程
        
        Returns:
            是否成功
        """
        try:
            logger.info("开始执行NAV记录流程...")
            
            # 计算NAV
            nav_data = self.calculate_nav()
            
            # 记录到CSV
            success = self.record_nav(nav_data)
            
            if success:
                logger.info("NAV记录流程完成")
            else:
                logger.error("NAV记录流程失败")
            
            return success
            
        except Exception as e:
            logger.error(f"NAV记录流程异常: {e}")
            return False

def main():
    """主函数"""
    recorder = NAVRecorder()
    success = recorder.run()
    
    if success:
        print("✅ NAV记录成功")
        sys.exit(0)
    else:
        print("❌ NAV记录失败")
        sys.exit(1)

if __name__ == "__main__":
    main()