import time
import random
import os
from DrissionPage import ChromiumOptions, ChromiumPage

class BrowserManager:
    """
    底层浏览器实例管理模块。
    基于 CDP (Chrome DevTools Protocol) 协议封装，负责初始化隔离环境的无壳浏览器容器，
    支持状态持久化、自动化行为抗风控映射及页面拦截预警机制。
    """
    def __init__(self):
        """
        初始化 BrowserManager 实例。
        自动探测并拉起独立线程的 Chromium 进程池。
        """
        self.page = self._auto_launch()

    def _auto_launch(self) -> ChromiumPage:
        """
        构造并初始化 ChromiumOptions，挂载独立的用户数据与会话存储池。
        
        Returns:
            ChromiumPage: 初始化的浏览器控制句柄。
        """
        co = ChromiumOptions()
        co.set_local_port(9222)
        co.set_user_data_path(os.path.join(os.path.expanduser("~"), ".agent_chrome_profile"))
        return ChromiumPage(addr_or_opts=co)

    def human_like_sleep(self, min_seconds: float = 2.5, max_seconds: float = 5.8):
        """
        执行随机延时阻断机制，规避时序特征检测。
        
        Args:
            min_seconds (float): 最小延时周期秒数。
            max_seconds (float): 最大延时周期秒数。
        """
        time.sleep(random.uniform(min_seconds, max_seconds))

    def human_like_scroll(self, scroll_steps: int = 3, pixel_per_step: int = 400):
        """
        执行模拟滚动行为向量，模拟真实客户端渲染交互。
        
        Args:
            scroll_steps (int): 页面滚动矢量步数。
            pixel_per_step (int): 每步滚动像素跨度。
        """
        for _ in range(scroll_steps):
            self.page.scroll.down(pixel_per_step)
            self.human_like_sleep(0.5, 1.5)

    def check_for_captcha(self, html_content: str) -> bool:
        """
        风险阻断规则匹配校验。扫描当前 HTML 根流中的高危封控关键字。
        
        Args:
            html_content (str): 页面的原始文档字符串。
            
        Returns:
            bool: 存在风控预警则触发 True，否则为 False。
        """
        real_danger_keywords = ["请完成安全验证", "访问过于频繁", "安全拦截", "滑动滑块完成验证"]
        for keyword in real_danger_keywords:
            if keyword in html_content:
                return True
        return False
