#!/usr/bin/env python3
"""
演武场监控列表同步钩子
功能：自动将入选1队/2队的标的同步到监控列表，从根源上消灭'情报断流'
法典依据：HEARTBEAT.md 紧急任务2 + 任务指令[2616-0411-P0B]
"""

import os
import sys
import json
import datetime
from typing import Dict, List, Optional, Set
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WatchListSyncer:
    """监控列表同步器"""
    
    def __init__(self, workspace_root: Optional[str] = None):
        """
        初始化同步器
        
        Args:
            workspace_root: 工作空间根目录
        """
        if workspace_root is None:
            workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.workspace_root = workspace_root
        
        # 路径定义
        self.watch_list_path = os.path.join(self.workspace_root, "config", "arena_watch_list.json")
        self.virtual_fund_path = os.path.join(self.workspace_root, "database", "arena", "virtual_fund.json")
        self.resonance_report_pattern = os.path.join(self.workspace_root, "database", "resonance_report_*.json")
        
        logger.info(f"监控列表同步器初始化完成，工作空间: {self.workspace_root}")
    
    def load_watch_list(self) -> Dict:
        """加载监控列表配置"""
        try:
            with open(self.watch_list_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"成功加载监控列表，包含{len(data.get('watch_list', []))}个标的")
            return data
        except FileNotFoundError:
            logger.error(f"监控列表文件不存在: {self.watch_list_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {e}")
            raise
    
    def load_virtual_fund_positions(self) -> List[Dict]:
        """加载虚拟基金持仓"""
        try:
            with open(self.virtual_fund_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            positions = data.get("positions", [])
            logger.info(f"成功加载虚拟基金持仓，包含{len(positions)}个标的")
            return positions
        except FileNotFoundError:
            logger.warning(f"虚拟基金文件不存在: {self.virtual_fund_path}")
            return []
        except json.JSONDecodeError as e:
            logger.warning(f"虚拟基金JSON解析错误: {e}")
            return []
    
    def get_resonance_scores(self) -> Dict[str, float]:
        """获取最新共振评分"""
        import glob
        scores = {}
        
        resonance_files = glob.glob(self.resonance_report_pattern)
        if not resonance_files:
            logger.warning("未找到共振报告文件")
            return scores
        
        # 使用最新的报告
        latest_file = max(resonance_files, key=os.path.getmtime)
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 从top_performers提取
            for item in data.get("overall_analysis", {}).get("top_performers", []):
                ticker = item.get("ticker")
                score = item.get("resonance_score")
                if ticker and score is not None:
                    scores[ticker] = score
            
            # 从detailed_analysis提取
            for ticker_key, analysis in data.get("detailed_analysis", {}).items():
                score = analysis.get("resonance_score")
                if score is not None:
                    scores[ticker_key] = score
                    
            logger.info(f"成功加载共振评分，包含{len(scores)}个标的")
            return scores
            
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            logger.warning(f"读取共振报告失败: {e}")
            return scores
    
    def determine_team(self, ticker: str, resonance_score: Optional[float]) -> str:
        """
        根据共振评分确定队伍
        
        Args:
            ticker: 股票代码
            resonance_score: 共振评分
            
        Returns:
            "1队" 或 "2队"
        """
        if resonance_score is None:
            # 无法确定评分，默认2队
            return "2队"
        
        if resonance_score >= 70:
            return "1队"
        elif resonance_score >= 60:
            return "2队"
        else:
            # 低于60分，不纳入监控（除非已在持仓中）
            return "观察队"
    
    def sync_from_positions(self, watch_list_data: Dict) -> Dict:
        """
        从持仓同步到监控列表
        
        Args:
            watch_list_data: 监控列表数据
            
        Returns:
            更新后的监控列表数据
        """
        positions = self.load_virtual_fund_positions()
        if not positions:
            logger.warning("无持仓数据，跳过持仓同步")
            return watch_list_data
        
        # 获取现有标的集合
        existing_tickers = {item["ticker"] for item in watch_list_data.get("watch_list", [])}
        
        # 获取共振评分
        resonance_scores = self.get_resonance_scores()
        
        updates_made = False
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        for position in positions:
            ticker = position.get("ticker")
            name = position.get("name", "未知")
            
            if not ticker:
                continue
            
            if ticker not in existing_tickers:
                # 新标的，添加到监控列表
                resonance_score = resonance_scores.get(ticker)
                team = self.determine_team(ticker, resonance_score)
                
                # 如果队伍是观察队但该标的有持仓，强制设为1队（因为已在持仓中）
                if team == "观察队":
                    team = "1队"
                    logger.info(f"持仓标的{ticker}共振评分低于60，但因已有持仓强制设为1队")
                
                new_item = {
                    "ticker": ticker,
                    "name": name,
                    "team": team,
                    "added_date": current_date,
                    "added_by": "sync_watch_list",
                    "status": "active",
                    "priority": "high",
                    "reason": "持仓同步" if resonance_score is None else f"共振评分: {resonance_score}",
                    "monitoring_required": True,
                    "last_synced": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00"),
                    "sync_status": "auto_sync"
                }
                
                watch_list_data["watch_list"].append(new_item)
                existing_tickers.add(ticker)
                updates_made = True
                logger.info(f"新增监控标的: {ticker} ({name}) -> {team}")
        
        if updates_made:
            watch_list_data["status"]["total_tickers"] = len(watch_list_data["watch_list"])
            watch_list_data["status"]["active_tickers"] = len([item for item in watch_list_data["watch_list"] if item.get("status") == "active"])
            watch_list_data["status"]["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")
            watch_list_data["status"]["update_method"] = "auto_sync"
            watch_list_data["status"]["sync_mechanism"] = "implemented"
            logger.info(f"持仓同步完成，新增{updates_made}个标的")
        
        return watch_list_data
    
    def sync_from_resonance_scores(self, watch_list_data: Dict) -> Dict:
        """
        从共振评分同步高评分标的
        
        Args:
            watch_list_data: 监控列表数据
            
        Returns:
            更新后的监控列表数据
        """
        resonance_scores = self.get_resonance_scores()
        if not resonance_scores:
            logger.warning("无共振评分数据，跳过评分同步")
            return watch_list_data
        
        # 获取现有标的集合
        existing_tickers = {item["ticker"] for item in watch_list_data.get("watch_list", [])}
        
        updates_made = False
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        for ticker, score in resonance_scores.items():
            if ticker in existing_tickers:
                # 已存在，跳过
                continue
            
            # 只同步高分标的（≥60）
            if score >= 60:
                team = self.determine_team(ticker, score)
                if team == "观察队":
                    continue  # 跳过观察队
                
                new_item = {
                    "ticker": ticker,
                    "name": self._get_name_from_ticker(ticker),
                    "team": team,
                    "added_date": current_date,
                    "added_by": "sync_watch_list",
                    "status": "active",
                    "priority": "medium" if team == "2队" else "high",
                    "reason": f"共振评分: {score}",
                    "monitoring_required": True,
                    "last_synced": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00"),
                    "sync_status": "auto_sync"
                }
                
                watch_list_data["watch_list"].append(new_item)
                existing_tickers.add(ticker)
                updates_made = True
                logger.info(f"新增高分监控标的: {ticker} (评分: {score}) -> {team}")
        
        if updates_made:
            watch_list_data["status"]["total_tickers"] = len(watch_list_data["watch_list"])
            watch_list_data["status"]["active_tickers"] = len([item for item in watch_list_data["watch_list"] if item.get("status") == "active"])
            watch_list_data["status"]["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")
            watch_list_data["status"]["update_method"] = "auto_sync"
            logger.info(f"共振评分同步完成，新增{updates_made}个高分标的")
        
        return watch_list_data
    
    def _get_name_from_ticker(self, ticker: str) -> str:
        """根据股票代码获取名称（简化版）"""
        # 这里可以扩展为从本地数据库或API获取名称
        # 暂时返回代码本身
        name_map = {
            "000681": "视觉中国",
            "600633": "浙数文化",
            "000938": "紫光股份",
            "518880": "黄金ETF",
            "510500": "中证500ETF",
            "510300": "沪深300ETF"
        }
        return name_map.get(ticker, ticker)
    
    def run_sync(self, sync_mode: str = "all") -> bool:
        """
        执行同步
        
        Args:
            sync_mode: 同步模式 ("positions", "resonance", "all")
            
        Returns:
            是否成功
        """
        try:
            logger.info(f"开始执行监控列表同步，模式: {sync_mode}")
            
            # 加载现有监控列表
            watch_list_data = self.load_watch_list()
            
            # 执行同步
            if sync_mode in ["positions", "all"]:
                watch_list_data = self.sync_from_positions(watch_list_data)
            
            if sync_mode in ["resonance", "all"]:
                watch_list_data = self.sync_from_resonance_scores(watch_list_data)
            
            # 保存更新后的监控列表
            self.save_watch_list(watch_list_data)
            
            logger.info("监控列表同步完成")
            return True
            
        except Exception as e:
            logger.error(f"同步失败: {e}", exc_info=True)
            return False
    
    def save_watch_list(self, data: Dict) -> None:
        """保存监控列表"""
        try:
            # 确保config目录存在
            config_dir = os.path.dirname(self.watch_list_path)
            os.makedirs(config_dir, exist_ok=True)
            
            with open(self.watch_list_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"监控列表已保存: {self.watch_list_path}")
            
        except Exception as e:
            logger.error(f"保存监控列表失败: {e}")
            raise


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="演武场监控列表同步钩子")
    parser.add_argument("--mode", choices=["positions", "resonance", "all"], default="all",
                       help="同步模式: positions=仅持仓, resonance=仅共振评分, all=全部")
    parser.add_argument("--dry-run", action="store_true", help="干运行，不保存更改")
    
    args = parser.parse_args()
    
    try:
        syncer = WatchListSyncer()
        
        if args.dry_run:
            logger.info("干运行模式，仅检查不保存")
            # 加载数据但不保存
            watch_list_data = syncer.load_watch_list()
            print(f"当前监控列表标的数: {len(watch_list_data.get('watch_list', []))}")
            
            positions = syncer.load_virtual_fund_positions()
            print(f"当前持仓标的数: {len(positions)}")
            
            resonance_scores = syncer.get_resonance_scores()
            print(f"当前共振评分标的数: {len(resonance_scores)}")
            print("干运行完成")
            return 0
        
        success = syncer.run_sync(args.mode)
        return 0 if success else 1
        
    except Exception as e:
        logger.error(f"同步失败: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())