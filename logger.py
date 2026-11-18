"""
统一日志模块 - 用户友好的中文进度式输出
"""
import sys

TARGET = 50  # 目标岗位数

def _bar(current: int, total: int = TARGET, width: int = 12) -> str:
    filled = int(width * min(current, total) / total)
    return "█" * filled + "░" * (width - filled)

def section(title: str):
    """程序启动标题栏"""
    print(f"\n{'═' * 54}")
    print(f"  {title}")
    print(f"{'═' * 54}")

def round_header(iteration: int, collected: int):
    """每轮开始"""
    print(f"\n  ── 第 {iteration} 轮   已收集 {collected} / {TARGET} ──")

def searching(site: str, query: str, page: int):
    """搜索动作"""
    print(f"  搜索   {site}  \"{query}\"  第 {page} 页")

def detail_scraping(url: str):
    """进入详情页动作"""
    short_url = url[:45] + "..." if len(url) > 48 else url
    print(f"  详情   访问 -> {short_url}")

def fetched(chars: int, ocr: bool = False):
    """页面抓取结果"""
    ocr_note = "  (+OCR 解密薪资)" if ocr else ""
    print(f"  获取   {chars:,} 字{ocr_note}")

def evaluated(added: int, dupes: int, total: int):
    """岗位提取结果"""
    bar = _bar(total)
    if added > 0:
        print(f"  提取   +{added} 个岗位  去重 {dupes}  [{bar}] {total} / {TARGET}")
    else:
        print(f"  提取   无新增  (重复或非 AI 方向，将更换策略)")

def critic_result(confidence: float, hint: str, diagnosis: str):
    """Reflection 评审结论"""
    pct = int(confidence * 100)
    short = diagnosis[:30] + ("…" if len(diagnosis) > 30 else "")
    print(f"  评审   {pct}% 信心  {short}  推荐: {hint}")

def captcha_warn(site: str):
    print(f"  警告   {site} 触发风控，跳过本页")

def guard_corrected(bad: str, good: str):
    print(f"  纠正   平台名 '{bad}' → '{good}'")

def warn(msg: str):
    print(f"  警告   {msg}")

def error(msg: str):
    print(f"  错误   {msg}", file=sys.stderr)

def done(total: int):
    bar = _bar(total)
    print(f"\n{'─' * 54}")
    print(f"  完成   共收集 {total} 个 AI 算法岗位   [{bar}] {total} / {TARGET}")
    print(f"{'─' * 54}")

def max_iter_reached(n: int):
    print(f"  停止   已达最大迭代轮次 ({n} 轮)")

def route_stop(reason: str):
    print(f"  停止   {reason}")
