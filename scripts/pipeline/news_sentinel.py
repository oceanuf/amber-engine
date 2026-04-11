#!/usr/bin/env python3
"""
新闻哨兵 (News Sentinel) - 宏观感知自动化模块
版本: 1.0.0
描述: 从多个新闻源获取财经新闻，实现SOP第一阶段的宏观感知自动化。
功能:
  1. 从Tushare API获取新闻（主要源）
  2. 从RSS源获取新闻（备用源）
  3. 频率控制与请求限制
  4. 结构化JSON存储
  5. 降级机制与错误处理
  6. 新闻去重与时间过滤
"""

import os
import sys
import json
import time
import datetime
import hashlib
import requests
import feedparser  # RSS解析库
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 配置文件路径
SECRETS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                           "_PRIVATE_DATA", "secrets.json")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                         "database", "news")
CACHE_DIR = os.path.join(OUTPUT_DIR, "cache")

# 确保目录存在
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# 新闻源配置
@dataclass
class NewsSource:
    """新闻源配置"""
    name: str
    type: str  # "tushare", "rss", "api"
    url: str
    weight: float  # 置信度权重
    enabled: bool
    rate_limit_seconds: int  # 请求频率限制

# 新闻源列表
NEWS_SOURCES = [
    NewsSource(
        name="Tushare VIP新闻",
        type="tushare",
        url="https://api.tushare.pro/v1/news/vip",
        weight=0.8,
        enabled=True,
        rate_limit_seconds=5  # Tushare API频率限制
    ),
    NewsSource(
        name="财联社RSS",
        type="rss",
        url="http://www.cls.cn/rss",  # 示例URL，需要验证
        weight=0.7,
        enabled=False,  # 暂时禁用，需要验证URL
        rate_limit_seconds=10
    ),
    NewsSource(
        name="东方财富RSS",
        type="rss",
        url="http://finance.eastmoney.com/rss",  # 示例URL，需要验证
        weight=0.6,
        enabled=False,  # 暂时禁用，需要验证URL
        rate_limit_seconds=10
    ),
    NewsSource(
        name="华尔街见闻RSS",
        type="rss",
        url="https://wallstreetcn.com/rss",  # 示例URL，需要验证
        weight=0.7,
        enabled=False,  # 暂时禁用，需要验证URL
        rate_limit_seconds=10
    ),
    NewsSource(
        name="新浪财经RSS",
        type="rss",
        url="http://finance.sina.com.cn/rss",  # 示例URL
        weight=0.5,
        enabled=True,
        rate_limit_seconds=15
    ),
]

# 关键词矩阵（用于信号过滤）
KEYWORDS_MATRIX = {
    "货币政策": ["降准", "降息", "MLF", "LPR", "逆回购", "货币政策", "央行"],
    "财政政策": ["财政政策", "减税", "增税", "赤字", "国债", "地方债"],
    "经济数据": ["GDP", "CPI", "PPI", "PMI", "出口", "进口", "贸易顺差", "失业率"],
    "产业政策": ["AI", "人工智能", "新能源", "半导体", "芯片", "集成电路", "5G"],
    "地缘政治": ["中美", "中欧", "贸易战", "制裁", "关税", "地缘风险", "冲突"],
    "监管政策": ["监管", "整顿", "规范", "指导意见", "新规"],
    "市场情绪": ["牛市", "熊市", "反弹", "回调", "震荡", "波动"],
}

@dataclass
class NewsItem:
    """新闻条目数据结构"""
    id: str  # 唯一ID (MD5哈希)
    title: str
    content: str
    source: str
    url: Optional[str]
    pub_time: str
    keywords: List[str]
    confidence_score: float
    category: str
    has_macro_impact: bool
    macro_pulse_tags: List[str]
    processed_time: str
    
    def to_dict(self) -> Dict:
        return asdict(self)

class NewsSentinel:
    """新闻哨兵主类"""
    
    def __init__(self, tushare_token: Optional[str] = None):
        """初始化新闻哨兵"""
        self.tushare_token = tushare_token or self._load_tushare_token()
        self.news_sources = NEWS_SOURCES
        self.last_request_time = {}  # 记录各源最后请求时间
        self.cache = {}
        
        # 加载缓存
        self._load_cache()
        
        logger.info(f"新闻哨兵初始化完成，启用 {sum(1 for s in self.news_sources if s.enabled)}/{len(self.news_sources)} 个新闻源")
    
    def _load_tushare_token(self) -> Optional[str]:
        """加载Tushare Token"""
        try:
            if os.path.exists(SECRETS_FILE):
                with open(SECRETS_FILE, 'r', encoding='utf-8') as f:
                    secrets = json.load(f)
                    token = secrets.get("TUSHARE_TOKEN")
                    if token and token != "your_tushare_token_here":
                        logger.info("✅ 从secrets.json加载Tushare Token")
                        return token
            
            # 尝试环境变量
            token = os.getenv("TUSHARE_TOKEN")
            if token:
                logger.info("✅ 从环境变量加载Tushare Token")
                return token
            
            logger.warning("⚠️  未找到Tushare Token，Tushare新闻源将不可用")
            return None
        except Exception as e:
            logger.error(f"❌ 加载Tushare Token失败: {e}")
            return None
    
    def _load_cache(self):
        """加载缓存数据"""
        cache_file = os.path.join(CACHE_DIR, "news_cache.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
                logger.info(f"✅ 加载缓存数据，包含 {len(self.cache)} 条记录")
            except Exception as e:
                logger.error(f"❌ 加载缓存失败: {e}")
                self.cache = {}
        else:
            self.cache = {}
    
    def _save_cache(self):
        """保存缓存数据"""
        cache_file = os.path.join(CACHE_DIR, "news_cache.json")
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            logger.debug(f"✅ 缓存数据已保存到 {cache_file}")
        except Exception as e:
            logger.error(f"❌ 保存缓存失败: {e}")
    
    def _can_make_request(self, source: NewsSource) -> bool:
        """检查是否可以发送请求（频率控制）"""
        source_key = f"{source.name}_{source.type}"
        current_time = time.time()
        
        if source_key not in self.last_request_time:
            return True
        
        elapsed = current_time - self.last_request_time[source_key]
        return elapsed >= source.rate_limit_seconds
    
    def _update_request_time(self, source: NewsSource):
        """更新最后请求时间"""
        source_key = f"{source.name}_{source.type}"
        self.last_request_time[source_key] = time.time()
    
    def _generate_news_id(self, title: str, pub_time: str, source: str) -> str:
        """生成新闻唯一ID"""
        content = f"{title}_{pub_time}_{source}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def fetch_from_tushare(self, source: NewsSource, limit: int = 20) -> List[Dict]:
        """从Tushare获取新闻"""
        if not self.tushare_token:
            logger.warning("Tushare Token未设置，跳过Tushare新闻获取")
            return []
        
        if not self._can_make_request(source):
            logger.warning(f"频率限制: {source.name}，跳过本次请求")
            return []
        
        logger.info(f"📰 从Tushare获取新闻 (限制: {limit})")
        
        api_data = {
            "api_name": "news/vip",
            "token": self.tushare_token,
            "params": {
                "src": "sina",  # 新闻来源，可以是sina, 163等
                "start_date": (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y%m%d"),
                "end_date": datetime.datetime.now().strftime("%Y%m%d"),
                "limit": limit
            },
            "fields": "title,content,pub_time,src,tags,related_stocks"
        }
        
        try:
            response = requests.post(source.url, json=api_data, timeout=10)
            self._update_request_time(source)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    news_items = result.get("data", [])
                    logger.info(f"✅ 从Tushare获取到 {len(news_items)} 条新闻")
                    return news_items
                else:
                    logger.error(f"❌ Tushare API错误: {result.get('msg')}")
                    return []
            else:
                logger.error(f"❌ HTTP错误: {response.status_code}")
                return []
        except requests.exceptions.Timeout:
            logger.error("❌ Tushare请求超时")
            return []
        except Exception as e:
            logger.error(f"❌ Tushare请求异常: {e}")
            return []
    
    def fetch_from_rss(self, source: NewsSource, limit: int = 10) -> List[Dict]:
        """从RSS源获取新闻"""
        if not self._can_make_request(source):
            logger.warning(f"频率限制: {source.name}，跳过本次请求")
            return []
        
        logger.info(f"📰 从RSS源获取新闻: {source.name}")
        
        try:
            # 解析RSS
            feed = feedparser.parse(source.url)
            self._update_request_time(source)
            
            if feed.bozo and feed.bozo_exception:
                logger.warning(f"⚠️  RSS解析警告: {feed.bozo_exception}")
            
            news_items = []
            for entry in feed.entries[:limit]:
                # 提取新闻信息
                title = entry.get('title', '')
                content = entry.get('summary', '') or entry.get('description', '')
                link = entry.get('link', '')
                
                # 处理发布时间
                pub_time = ''
                if hasattr(entry, 'published'):
                    pub_time = entry.published
                elif hasattr(entry, 'updated'):
                    pub_time = entry.updated
                
                news_items.append({
                    'title': title,
                    'content': content,
                    'url': link,
                    'pub_time': pub_time,
                    'source': source.name,
                    'tags': []
                })
            
            logger.info(f"✅ 从 {source.name} 获取到 {len(news_items)} 条新闻")
            return news_items
        except Exception as e:
            logger.error(f"❌ RSS源 {source.name} 请求失败: {e}")
            return []
    
    def fetch_news(self, limit_per_source: int = 10) -> List[Dict]:
        """从所有启用的新闻源获取新闻"""
        all_news = []
        
        for source in self.news_sources:
            if not source.enabled:
                continue
            
            logger.info(f"🔍 从 {source.name} 获取新闻...")
            
            if source.type == "tushare":
                news_items = self.fetch_from_tushare(source, limit_per_source)
            elif source.type == "rss":
                news_items = self.fetch_from_rss(source, limit_per_source)
            else:
                logger.warning(f"⚠️  未知的新闻源类型: {source.type}")
                continue
            
            all_news.extend(news_items)
            
            # 避免请求过快
            time.sleep(1)
        
        logger.info(f"📊 总计获取到 {len(all_news)} 条新闻")
        return all_news
    
    def analyze_news(self, raw_news: List[Dict]) -> List[NewsItem]:
        """分析新闻，提取关键词和置信度"""
        processed_news = []
        
        for news in raw_news:
            # 提取基本信息
            title = news.get('title', '')
            content = news.get('content', '')
            source = news.get('source', '未知')
            url = news.get('url', '')
            pub_time = news.get('pub_time', '')
            
            # 生成唯一ID
            news_id = self._generate_news_id(title, pub_time, source)
            
            # 检查是否已处理过（去重）
            if news_id in self.cache:
                logger.debug(f"新闻已处理过，跳过: {title[:50]}...")
                continue
            
            # 提取关键词
            full_text = f"{title} {content}"
            keywords = self._extract_keywords(full_text)
            
            # 计算置信度得分
            confidence_score = self._calculate_confidence_score(news, keywords)
            
            # 判断是否有宏观影响
            has_macro_impact = self._has_macro_impact(keywords, confidence_score)
            
            # 提取宏观脉冲标签
            macro_pulse_tags = self._extract_macro_tags(keywords)
            
            # 确定类别
            category = self._determine_category(keywords)
            
            # 创建新闻对象
            news_item = NewsItem(
                id=news_id,
                title=title,
                content=content,
                source=source,
                url=url,
                pub_time=pub_time,
                keywords=keywords,
                confidence_score=confidence_score,
                category=category,
                has_macro_impact=has_macro_impact,
                macro_pulse_tags=macro_pulse_tags,
                processed_time=datetime.datetime.now().isoformat()
            )
            
            processed_news.append(news_item)
            
            # 更新缓存
            self.cache[news_id] = {
                'title': title,
                'source': source,
                'pub_time': pub_time,
                'processed_time': datetime.datetime.now().isoformat()
            }
        
        # 保存缓存
        self._save_cache()
        
        return processed_news
    
    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        keywords = []
        text_lower = text.lower()
        
        for category, keyword_list in KEYWORDS_MATRIX.items():
            for keyword in keyword_list:
                keyword_lower = keyword.lower()
                if keyword_lower in text_lower:
                    keywords.append(keyword)
        
        # 去重
        return list(set(keywords))
    
    def _calculate_confidence_score(self, news: Dict, keywords: List[str]) -> float:
        """计算置信度得分"""
        base_score = 0.0
        
        # 1. 新闻源权重
        source_name = news.get('source', '')
        source_weight = 0.5  # 默认权重
        
        for source in self.news_sources:
            if source.name == source_name:
                source_weight = source.weight
                break
        
        base_score += source_weight * 0.3
        
        # 2. 关键词命中权重
        keyword_score = min(len(keywords) * 0.1, 0.4)
        base_score += keyword_score
        
        # 3. 内容完整性权重
        title = news.get('title', '')
        content = news.get('content', '')
        
        if title and content:
            if len(content) > 100:
                base_score += 0.2
            elif len(content) > 50:
                base_score += 0.1
        
        # 确保得分在0-1之间
        return min(max(base_score, 0.0), 1.0)
    
    def _has_macro_impact(self, keywords: List[str], confidence_score: float) -> bool:
        """判断是否有宏观影响"""
        # 有关键词且置信度较高
        if len(keywords) > 0 and confidence_score >= 0.5:
            return True
        
        return False
    
    def _extract_macro_tags(self, keywords: List[str]) -> List[str]:
        """提取宏观脉冲标签"""
        tags = []
        
        # 根据关键词确定标签
        macro_categories = {
            "货币政策": ["降准", "降息", "MLF", "LPR", "逆回购"],
            "财政政策": ["财政政策", "减税", "增税", "赤字", "国债"],
            "经济数据": ["GDP", "CPI", "PPI", "PMI", "出口", "进口"],
            "产业政策": ["AI", "人工智能", "新能源", "半导体", "芯片"],
            "地缘政治": ["中美", "中欧", "贸易战", "制裁", "关税"],
        }
        
        for category, cat_keywords in macro_categories.items():
            if any(kw in keywords for kw in cat_keywords):
                tags.append(category)
        
        return tags
    
    def _determine_category(self, keywords: List[str]) -> str:
        """确定新闻类别"""
        if not keywords:
            return "其他"
        
        # 统计关键词类别
        category_count = defaultdict(int)
        
        for category, keyword_list in KEYWORDS_MATRIX.items():
            for keyword in keywords:
                if keyword in keyword_list:
                    category_count[category] += 1
        
        if category_count:
            # 返回出现最多的类别
            return max(category_count.items(), key=lambda x: x[1])[0]
        
        return "其他"
    
    def save_news(self, news_items: List[NewsItem], filename: Optional[str] = None):
        """保存新闻数据"""
        if not filename:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"news_{timestamp}.json"
        
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        # 转换为字典
        news_dicts = [item.to_dict() for item in news_items]
        
        # 添加元数据
        output_data = {
            "metadata": {
                "generated_by": "NewsSentinel",
                "version": "1.0.0",
                "generation_time": datetime.datetime.now().isoformat(),
                "total_news": len(news_items),
                "sources_used": [s.name for s in self.news_sources if s.enabled],
                "macro_impact_news": sum(1 for item in news_items if item.has_macro_impact)
            },
            "news": news_dicts
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 新闻数据已保存到 {filepath}")
            
            # 同时保存今日最新文件
            today_file = os.path.join(OUTPUT_DIR, "news_today.json")
            with open(today_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            return filepath
        except Exception as e:
            logger.error(f"❌ 保存新闻数据失败: {e}")
            return None
    
    def run(self, limit_per_source: int = 10) -> Tuple[List[NewsItem], str]:
        """运行新闻哨兵"""
        logger.info("🚀 启动新闻哨兵...")
        
        # 获取新闻
        raw_news = self.fetch_news(limit_per_source)
        
        if not raw_news:
            logger.warning("⚠️  未获取到任何新闻")
            return [], ""
        
        # 分析新闻
        processed_news = self.analyze_news(raw_news)
        
        if not processed_news:
            logger.warning("⚠️  未处理到有效新闻")
            return [], ""
        
        # 保存新闻
        filepath = self.save_news(processed_news)
        
        # 生成摘要报告
        macro_news = [item for item in processed_news if item.has_macro_impact]
        logger.info(f"📊 处理完成: 总计 {len(processed_news)} 条新闻，其中 {len(macro_news)} 条有宏观影响")
        
        return processed_news, filepath or ""

def main():
    """主函数"""
    print("=" * 60)
    print("📰 新闻哨兵 - 宏观感知自动化模块")
    print("=" * 60)
    
    try:
        # 初始化哨兵
        sentinel = NewsSentinel()
        
        # 运行新闻采集
        news_items, output_file = sentinel.run(limit_per_source=15)
        
        if news_items:
            print(f"\n✅ 新闻采集完成!")
            print(f"   总计新闻: {len(news_items)} 条")
            
            macro_news = [item for item in news_items if item.has_macro_impact]
            print(f"   宏观影响新闻: {len(macro_news)} 条")
            
            if macro_news:
                print(f"\n📈 宏观影响新闻摘要:")
                for i, item in enumerate(macro_news[:5], 1):
                    print(f"   {i}. [{item.category}] {item.title[:60]}...")
                    print(f"      关键词: {', '.join(item.keywords[:3])}")
                    print(f"      置信度: {item.confidence_score:.2f}")
            
            print(f"\n📁 输出文件: {output_file}")
        else:
            print("\n⚠️  未获取到有效新闻")
        
        print("\n" + "=" * 60)
        print("🎉 新闻哨兵执行完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 新闻哨兵执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()