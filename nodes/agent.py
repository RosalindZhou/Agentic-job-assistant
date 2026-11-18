from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from llm_manager import LLMManager
from state import AgentState
from prompts import AGENT_SYSTEM_PROMPT
import logger

MAX_ITERATIONS = 100

class AgentNode:
    def __init__(self):
        self.llm = LLMManager().get_planner()

    def run(self, state: AgentState) -> dict:
        job_count  = len(state.get("job_list", []))
        iterations = state.get("total_iterations", 0)
        history    = state.get("search_history", [])
        failed     = state.get("failed_queries", [])
        negative_kb = state.get("negative_knowledge_base", [])

        if iterations >= MAX_ITERATIONS:
            logger.max_iter_reached(MAX_ITERATIONS)
            return {"messages": []}

        logger.round_header(iterations + 1, job_count)

        prompt = AGENT_SYSTEM_PROMPT.format(
            job_count=job_count,
            iterations=iterations,
            max_iterations=MAX_ITERATIONS,
            history=" | ".join(history[-5:]) if history else "无",
            failed=", ".join(failed[-5:]) if failed else "无",
            negative_kb=", ".join(negative_kb[:10]),
            reflection=state.get("reflection_summary", "（首轮，尚无反思记录）")
        )

        tools_schema = [
            {
                "type": "function",
                "function": {
                    "name": "scrape_job_page",
                    "description": "访问搜索列表页。用于初步发现岗位 URL。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "搜索关键词"},
                            "site": {"type": "string", "enum": ["实习僧", "智联招聘", "猎聘"]},
                            "page_num": {"type": "integer"}
                        },
                        "required": ["query", "site", "page_num"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "scrape_job_details",
                    "description": "进入具体岗位的详情页。当你通过 evaluate_jobs 拿到列表后，必须调用此工具深入抓取 JD 以获得完整的技术要求和真实的 URL。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "岗位的详情链接"}
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "evaluate_jobs",
                    "description": "解析当前抓取到的 HTML/Markdown。无论是列表页还是详情页，抓完都要 evaluate。",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]

        llm_with_tools = self.llm.bind(tools=tools_schema, tool_choice="required")
        messages_to_send = [SystemMessage(content=prompt)]
        for msg in state.get("messages", [])[-6:]:
            messages_to_send.append(msg)

        try:
            response = llm_with_tools.invoke(messages_to_send)
            tool_calls = getattr(response, 'tool_calls', [])

            if tool_calls:
                t = tool_calls[0]
                if t['name'] == 'scrape_job_page':
                    args = t['args']
                    logger.searching(args.get('site', '?'), args.get('query', '?'), args.get('page_num', '?'))
                elif t['name'] == 'scrape_job_details':
                    args = t['args']
                    logger.detail_scraping(args.get('url', '?'))
                
                if len(tool_calls) > 1:
                    logger.warn(f"检测到模型试图单次执行 {len(tool_calls)} 个动作，已强制限制为单步执行")
                    # 关键修改：为了满足 Gemini 严格的消息轮次检查，必须物理截断多余的 tool_calls
                    response.tool_calls = [tool_calls[0]]
                    if "tool_calls" in response.additional_kwargs:
                        response.additional_kwargs["tool_calls"] = [response.additional_kwargs["tool_calls"][0]]
                
                return {
                    "messages": [response],
                    "total_iterations": iterations + 1
                }
            else:
                # Agent 没有调用工具 —— 可能误判停止，强制记录并继续
                logger.warn(f"Agent 未返回工具调用，将在下一轮重试（内容: {response.content[:60]}…）")
                
                # 关键修改：在无工具调用的 AIMessage 后立即补充一条 HumanMessage，防止 Gemini 报错 (连续两个 AIMessage)
                return {
                    "messages": [
                        response, 
                        HumanMessage(content="系统警告：你没有调用任何工具。请务必使用 `scrape_job_page` 或 `evaluate_jobs` 继续任务，直到收集满50个岗位。不要仅仅说任务完成。")
                    ],
                    "total_iterations": iterations + 1
                }

        except Exception as e:
            logger.error(f"Agent 推理失败: {e}")
            return {"messages": []}
