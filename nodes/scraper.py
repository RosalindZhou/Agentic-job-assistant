"""
节点 Tool: Scraper
Agent 调用的原生工具链：根据 Agent 的 tool_calls 执行网页检索，拉取并将其提取。
"""
import time
import re
import os
import random
from markdownify import markdownify as md
from browser_manager import BrowserManager
from state import AgentState
from langchain_core.messages import ToolMessage
import logger

SITE_URLS = {
    "智联招聘": "https://sou.zhaopin.com/?jl=538&kw={query}&p={page}",
    "猎聘": "https://www.liepin.com/zhaopin/?key={query}&curPage={page}",
    "实习僧": "https://www.shixiseng.com/interns?keyword={query}&page={page}",
}

VALID_SITES = ["实习僧", "智联招聘", "猎聘"]
# 容错映射：模型常见幻觉词 -> 最接近的合法平台
SITE_FUZZY_MAP = {
    "实习": "实习僧",
    "实事": "实习僧",
    "实习生": "实习僧",
    "僧": "实习僧",
    "智联": "智联招聘",
    "猎": "猎聘",
}

def _snap_site(site: str) -> str:
    """将任意幻觉 site 名称纠正为合法平台，保证系统不崩溃。"""
    if site in VALID_SITES:
        return site
    # 模糊匹配
    for keyword, valid in SITE_FUZZY_MAP.items():
        if keyword in site:
            logger.guard_corrected(site, valid)
            return valid
    # 兜底：轮转
    fallback = random.choice(VALID_SITES)
    logger.guard_corrected(site, fallback)
    return fallback

FONT_ENCRYPTED_SITES = {"实习僧"}

class ScraperNode:
    def __init__(self):
        self.browser = BrowserManager()
        self.ocr_engine = None

    def _get_ocr(self):
        if self.ocr_engine is None:
            try:
                from rapidocr_onnxruntime import RapidOCR
                self.ocr_engine = RapidOCR()
            except ImportError:
                pass
        return self.ocr_engine

    def _ocr_screenshot(self) -> str:
        ocr = self._get_ocr()
        if ocr is None: return ""
        screenshot_path = os.path.abspath("temp_screenshot.png")
        try:
            self.browser.page.get_screenshot(path=screenshot_path, full_page=True)
            result, _ = ocr(screenshot_path)
            if result:
                return "\n".join([line[1] for line in result])
        except:
             pass
        finally:
            if os.path.exists(screenshot_path): os.remove(screenshot_path)
        return ""

    def _clean_html_to_markdown(self, html: str) -> str:
        # 移除干扰标签
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
        html = re.sub(r'<svg[^>]*>.*?</svg>', '', html, flags=re.DOTALL)
        # 转换为 Markdown，保留链接以便后续进入详情页
        markdown = md(html, heading_style="ATX", strip=['img'])
        return re.sub(r'\n{3,}', '\n\n', markdown).strip()

    def run(self, state: AgentState) -> dict:
        last_message = state.get("messages", [])[-1]
        tcs = getattr(last_message, 'tool_calls', [])
        tool_call = next((tc for tc in tcs if tc["name"] in ["scrape_job_page", "scrape_job_details"]), None)
        
        if not tool_call:
            return {"messages": [ToolMessage(content="Error: No valid scraper tool_call found", tool_call_id="unknown")]}

        if tool_call["name"] == "scrape_job_page":
            return self._scrape_list_page(state, tool_call)
        else:
            return self._scrape_details_page(state, tool_call)

    def _scrape_list_page(self, state: AgentState, tool_call: dict) -> dict:
        args = tool_call["args"]
        query = args.get("query", "AI")
        site = _snap_site(args.get("site", "实习僧"))
        page = args.get("page_num", 1)
        tool_call_id = tool_call["id"]

        url = SITE_URLS[site].format(query=query, page=page)
        print(f"[SCRAPE]  LIST {site} | \"{query}\" | p.{page} ...")

        try:
            self.browser.page.get(url)
            self.browser.page.wait.load_start()
            self.browser.human_like_sleep(3.0, 5.0)

            page_html = self.browser.page.html
            if self.browser.check_for_captcha(page_html):
                logger.captcha_warn(site)
                return {
                     "messages": [ToolMessage(content=f"Scraping failed: CAPTCHA block on {site}.", tool_call_id=tool_call_id)],
                     "error_count_consecutive": state.get("error_count_consecutive", 0) + 1
                }

            markdown_result = self._clean_html_to_markdown(page_html)

            if site in FONT_ENCRYPTED_SITES:
                ocr_text = self._ocr_screenshot()
                if ocr_text:
                    markdown_result += f"\n\n--- OCR渲染文本 ---\n{ocr_text}"
            
            logger.fetched(len(markdown_result), ocr=(site in FONT_ENCRYPTED_SITES))
            
            return {
                "messages": [ToolMessage(
                    content=f"Successfully scraped list from {site}. Please call `evaluate_jobs` to extract job summaries and detail URLs.", 
                    tool_call_id=tool_call_id
                )],
                "scraped_raw_data": markdown_result,
                "current_site": site,
                "query": query,
                "page_num": int(page),
                "error_count_consecutive": 0
            }
        except Exception as e:
            logger.error(f"列表抓取失败: {e}")
            return {
                 "messages": [ToolMessage(content=f"Scraping failed: {str(e)}", tool_call_id=tool_call_id)],
                 "error_count_consecutive": state.get("error_count_consecutive", 0) + 1
            }

    def _scrape_details_page(self, state: AgentState, tool_call: dict) -> dict:
        args = tool_call["args"]
        url = args.get("url")
        tool_call_id = tool_call["id"]

        if not url:
            return {"messages": [ToolMessage(content="Error: No URL provided for detail scraping", tool_call_id=tool_call_id)]}

        # 简单的相对路径修复逻辑
        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("/"):
            # 根据当前 site 补全（如果 state 中有 site）
            site = state.get("current_site", "实习僧")
            base = "https://www.shixiseng.com"
            if site == "智联招聘": base = "https://www.zhaopin.com"
            elif site == "猎聘": base = "https://www.liepin.com"
            url = base + url

        print(f"[SCRAPE]  DETAIL -> {url} ...")

        try:
            self.browser.page.get(url)
            self.browser.page.wait.load_start()
            self.browser.human_like_sleep(2.0, 4.0)

            page_html = self.browser.page.html
            markdown_result = self._clean_html_to_markdown(page_html)
            
            # 详情页也可能需要 OCR（尤其是实习僧的薪资）
            site = state.get("current_site", "实习僧")
            if site in FONT_ENCRYPTED_SITES:
                ocr_text = self._ocr_screenshot()
                if ocr_text:
                    markdown_result += f"\n\n--- OCR渲染文本 ---\n{ocr_text}"

            return {
                "messages": [ToolMessage(
                    content=f"Successfully scraped JOB DETAILS from {url}. Please call `evaluate_jobs` now to extract the FULL information.", 
                    tool_call_id=tool_call_id
                )],
                "scraped_raw_data": markdown_result,
                "error_count_consecutive": 0
            }
        except Exception as e:
            logger.error(f"详情抓取失败: {e}")
            return {
                 "messages": [ToolMessage(content=f"Detail scraping failed: {str(e)}", tool_call_id=tool_call_id)],
                 "error_count_consecutive": state.get("error_count_consecutive", 0) + 1
            }
