#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代理管理器 - 对抗性网络设计模块
文档编号: AE-NET-001-V1.0
依据: [2614-044号]首席架构师战略构想
功能: 解决高频爬虫防御，建立伪装者协议
"""

import random
import time
import requests
from typing import List, Dict, Optional
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProxyManager:
    """代理管理器 - 对抗目标服务器防御机制"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        """
        初始化代理管理器
        
        Args:
            max_retries: 最大重试次数
            base_delay: 基础延迟时间(秒)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        
        # 用户代理池 - 伪装成不同浏览器
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
        ]
        
        # 请求头模板
        self.headers_template = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        # 代理服务器列表 (示例配置，实际使用时需要配置真实代理)
        self.proxy_pool = [
            None,  # 直连
            # 实际部署时应配置真实代理服务器
            # {'http': 'http://proxy1:8080', 'https': 'https://proxy1:8080'},
            # {'http': 'http://proxy2:8080', 'https': 'https://proxy2:8080'},
        ]
        
        logger.info(f"代理管理器初始化完成，用户代理池: {len(self.user_agents)}个，代理池: {len(self.proxy_pool)}个")
    
    def get_random_headers(self) -> Dict[str, str]:
        """生成随机请求头 - 伪装者协议核心"""
        headers = self.headers_template.copy()
        headers['User-Agent'] = random.choice(self.user_agents)
        
        # 随机添加一些额外的头部信息
        extra_headers = {
            'DNT': random.choice(['1', '0']),
            'Sec-Fetch-Dest': random.choice(['document', 'empty']),
            'Sec-Fetch-Mode': random.choice(['navigate', 'cors']),
            'Sec-Fetch-Site': random.choice(['none', 'same-origin', 'cross-site']),
        }
        
        # 随机选择1-2个额外头部
        for _ in range(random.randint(1, 2)):
            key, value = random.choice(list(extra_headers.items()))
            headers[key] = value
        
        return headers
    
    def get_random_proxy(self) -> Optional[Dict[str, str]]:
        """随机选择代理服务器"""
        return random.choice(self.proxy_pool)
    
    def calculate_delay(self, attempt: int) -> float:
        """
        计算延迟时间 - 指数退避算法
        
        Args:
            attempt: 当前尝试次数
            
        Returns:
            延迟时间(秒)
        """
        # 指数退避: base_delay * (2^attempt) + 随机抖动
        delay = self.base_delay * (2 ** attempt) + random.uniform(0, 0.5)
        
        # 添加人类行为随机延迟: 1-3秒
        human_delay = random.uniform(1, 3)
        
        return delay + human_delay
    
    def make_request_with_retry(self, url: str, method: str = 'GET', **kwargs) -> Optional[requests.Response]:
        """
        带重试机制的请求方法
        
        Args:
            url: 请求URL
            method: HTTP方法
            **kwargs: 其他requests参数
            
        Returns:
            Response对象或None
        """
        for attempt in range(self.max_retries):
            try:
                # 生成随机配置
                headers = self.get_random_headers()
                proxy = self.get_random_proxy()
                delay = self.calculate_delay(attempt)
                
                logger.info(f"尝试 {attempt+1}/{self.max_retries}: URL={url}, 延迟={delay:.2f}s, 代理={proxy is not None}")
                
                # 应用延迟
                time.sleep(delay)
                
                # 准备请求参数
                request_kwargs = kwargs.copy()
                request_kwargs['headers'] = headers
                if proxy:
                    request_kwargs['proxies'] = proxy
                
                # 设置超时
                if 'timeout' not in request_kwargs:
                    request_kwargs['timeout'] = (10, 30)  # 连接超时10s，读取超时30s
                
                # 执行请求
                if method.upper() == 'GET':
                    response = requests.get(url, **request_kwargs)
                elif method.upper() == 'POST':
                    response = requests.post(url, **request_kwargs)
                else:
                    raise ValueError(f"不支持的HTTP方法: {method}")
                
                # 检查响应状态
                response.raise_for_status()
                
                logger.info(f"请求成功: 状态码={response.status_code}, 内容长度={len(response.content)}")
                return response
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"请求失败 (尝试 {attempt+1}/{self.max_retries}): {type(e).__name__}: {e}")
                
                # 如果是最后一次尝试，记录错误
                if attempt == self.max_retries - 1:
                    logger.error(f"所有重试均失败: {url}")
                    return None
        
        return None
    
    def test_connectivity(self, test_url: str = "https://www.baidu.com") -> bool:
        """
        测试网络连通性
        
        Args:
            test_url: 测试URL
            
        Returns:
            是否连通
        """
        logger.info(f"测试网络连通性: {test_url}")
        
        response = self.make_request_with_retry(test_url)
        if response and response.status_code == 200:
            logger.info("网络连通性测试通过")
            return True
        else:
            logger.error("网络连通性测试失败")
            return False


class AntiBlockSkill:
    """反封禁技能 - 通用对抗性逻辑"""
    
    def __init__(self):
        self.proxy_manager = ProxyManager()
        self.request_history = []  # 请求历史记录
        
    def execute_with_protection(self, func, *args, **kwargs):
        """
        保护执行函数 - 添加对抗性逻辑
        
        Args:
            func: 要执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            函数执行结果
        """
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                # 执行前随机延迟
                delay = random.uniform(0.5, 2.0)
                time.sleep(delay)
                
                result = func(*args, **kwargs)
                
                # 记录成功请求
                self.record_request(success=True)
                return result
                
            except Exception as e:
                logger.warning(f"执行失败 (尝试 {attempt+1}/{max_attempts}): {type(e).__name__}: {e}")
                
                # 记录失败请求
                self.record_request(success=False, error=str(e))
                
                # 如果是最后一次尝试，重新抛出异常
                if attempt == max_attempts - 1:
                    raise
        
        return None
    
    def record_request(self, success: bool, error: str = None):
        """记录请求历史"""
        record = {
            'timestamp': time.time(),
            'success': success,
            'error': error
        }
        self.request_history.append(record)
        
        # 保持历史记录长度
        if len(self.request_history) > 100:
            self.request_history = self.request_history[-100:]
    
    def get_success_rate(self) -> float:
        """计算成功率"""
        if not self.request_history:
            return 0.0
        
        successful = sum(1 for r in self.request_history if r['success'])
        return successful / len(self.request_history)


# 全局实例
proxy_manager = ProxyManager()
anti_block = AntiBlockSkill()


if __name__ == "__main__":
    # 测试代码
    print("=== 代理管理器测试 ===")
    
    # 测试连通性
    if proxy_manager.test_connectivity():
        print("✅ 网络连通性测试通过")
    else:
        print("❌ 网络连通性测试失败")
    
    # 测试请求
    test_url = "https://httpbin.org/get"
    response = proxy_manager.make_request_with_retry(test_url)
    
    if response:
        print(f"✅ 测试请求成功: 状态码 {response.status_code}")
        print(f"   用户代理: {response.request.headers.get('User-Agent')}")
    else:
        print("❌ 测试请求失败")