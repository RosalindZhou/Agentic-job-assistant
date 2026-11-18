"""
Agentic AI 求职助手 - LangGraph 主入口
图结构 (ReAct Pattern): Agent <---> Tools (Scraper / Evaluator)
"""
import threading
import webbrowser
import warnings
from PIL import Image
warnings.simplefilter("ignore", Image.DecompressionBombWarning)
Image.MAX_IMAGE_PIXELS = None # 解除像素上限限制

import http.server
import socketserver
import json
import pandas as pd
from datetime import datetime

from langgraph.graph import StateGraph, END
from state import AgentState
from nodes.agent import AgentNode
from nodes.scraper import ScraperNode
from nodes.evaluator import EvaluatorNode
from nodes.reflection import ReflectionNode
import logger

def export_data(job_list):
    if not job_list:
        print("[Export] [WARN] 列表为空，跳过导出。")
        return
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    csv_path = f"AI_Engineer_Jobs_{timestamp}.csv"
    df = pd.DataFrame(job_list)
    
    # 按照最终需要存在的解释性字段导出
    cols = ["title", "company", "location", "salary", "tech_tags", "requirements", "is_ai_job", "confidence", "reason", "source", "job_url"]
    existing_cols = [c for c in cols if c in df.columns]
    df = df[existing_cols]
    
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    
    try:
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(job_list, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Export] [ERROR] JSON 导出失败: {e}")

    print(f"\n[Export] 原始数据已导出至: {csv_path}")
    print(f"[Export] 看板数据已更新: data.json")

def launch_dashboard_auto(port=8000):
    def run_server():
        Handler = http.server.SimpleHTTPRequestHandler
        socketserver.TCPServer.allow_reuse_address = True
        try:
            with socketserver.TCPServer(("", port), Handler) as httpd:
                httpd.serve_forever()
        except Exception:
            pass

    daemon_thread = threading.Thread(target=run_server, daemon=True)
    daemon_thread.start()

    url = f"http://localhost:{port}/web/index.html"
    print(f"\n[Web] 任务已载入完成，正在自动打开看板: {url}")
    webbrowser.open(url)

def route_agent_action(state: AgentState) -> str:
    """自动判断是调用工具，还是结束。"""
    iteration = state.get("total_iterations", 0)
    if iteration >= 100:
        logger.route_stop(f"已达最大迭代轮次 (100 轮)")
        return END

    if len(state.get("job_list", [])) >= 50:
        logger.route_stop("已完成目标 50 个岗位")
        return END

    messages = state.get("messages", [])
    if not messages:
        return END

    last_message = messages[-1]
    tool_calls = getattr(last_message, "tool_calls", [])

    if not tool_calls:
        # Agent 没有调用工具 —— 可能因为内容里回了"任务完成"
        # 强制回到 agent 再次思考，直到满足 job_count >= 50
        logger.warn("任务未达标，模型未返回动作，已强制重试")
        return "agent"

    if len(tool_calls) > 1:
        logger.warn(f"决策路由：模型规划过载 ({len(tool_calls)} 步)，已修剪为单步执行")

    tool_name = tool_calls[0]["name"]
    if tool_name in ["scrape_job_page", "scrape_job_details"]:
        return "scraper_tool"
    elif tool_name == "evaluate_jobs":
        return "evaluator_tool"
    else:
        return END

def build_graph():
    agent      = AgentNode()
    scraper    = ScraperNode()
    evaluator  = EvaluatorNode()
    reflection = ReflectionNode()

    graph = StateGraph(AgentState)

    graph.add_node("agent",           agent.run)
    graph.add_node("scraper_tool",    scraper.run)
    graph.add_node("evaluator_tool",  evaluator.run)
    graph.add_node("reflection",      reflection.run)   # 反思节点

    # Scraper 完成 → 回 Agent（Agent 随后决定是否 evaluate）
    graph.add_edge("scraper_tool",   "agent")
    # Evaluator 完成 → Reflection → Agent（完整的 ReAct + Critic 闭环）
    graph.add_edge("evaluator_tool", "reflection")
    graph.add_edge("reflection",     "agent")

    # Agent 执行完后，根据自身内部决策，条件跳转
    graph.add_conditional_edges(
        "agent",
        route_agent_action,
        {
            "scraper_tool":   "scraper_tool",
            "evaluator_tool": "evaluator_tool",
            "agent":          "agent",
            END: END
        }
    )

    graph.set_entry_point("agent")
    return graph.compile()

def main():
    logger.section("AI 求职助手  |  自动收集 AI 算法岗位")

    initial_state: AgentState = {
        "messages": [],
        "query": "AI 算法 实习",
        "current_site": "实习僧",
        "scraped_raw_data": "",
        "job_list": [],
        "seen_keys": set(),
        "negative_knowledge_base": [
            "CRUD", "产品设计", "仅调用API", "纯接口", "测试工程师",
            "前端", "运营", "市场", "销售", "客服", "行政", "前台",
            "文员", "出纳", "财务", "会计", "保险", "理财", "催收",
            "管培生", "储备干部", "审核",
            "Java开发", "C++开发", "电气", "航电", "机械", "土木",
            "建筑", "结构设计", "飞机", "汽车", "电子硬件", "硬件工程师",
            "嵌入式", "网络工程师", "ERP", "SAP", "运维",
            "课程销售", "引流", "地推", "BD", "供应链"
        ],
        "search_history": [],
        "failed_queries": [],
        "reflection_summary": "",
        "total_iterations": 0,
        "error_count_consecutive": 0,
        "page_num": 1
    }

    app = build_graph()

    print("\n[Main] Agent 引擎已启动，正在执行完全闭环扫描...\n")
    final_state = app.invoke(initial_state)

    job_list = final_state.get('job_list', [])
    logger.done(len(job_list))
    
    export_data(job_list)
    launch_dashboard_auto(port=8000)

    import time
    time.sleep(2)
    print("\n[OK] 看板服务运行中... 按 Ctrl+C 可退出。")
    try:
        while True: time.sleep(100)
    except KeyboardInterrupt:
        print("\n[Exit] 用户终止，程序退出。")

if __name__ == "__main__":
    main()
