"""
节点 Tool: Evaluator
处理 Scraper 抓取的缓存内容。集成去重、解释性理由(Explainable AI)。
"""
import json
from llm_manager import LLMManager
from state import AgentState
from langchain_core.messages import HumanMessage, ToolMessage
from prompts import EVALUATOR_PROMPT
import logger

class EvaluatorNode:
    def __init__(self):
        self.llm = LLMManager().get_evaluator()

    def run(self, state: AgentState) -> dict:
        last_message = state.get("messages", [])[-1]
        tool_call = next((tc for tc in getattr(last_message, 'tool_calls', []) if tc["name"] == "evaluate_jobs"), None)
        
        if not tool_call:
            return {"messages": [ToolMessage(content="Error: No evaluate_jobs tool call found", tool_call_id="unknown")]}

        tool_call_id = tool_call["id"]
        markdown = state.get("scraped_raw_data", "")
        negative_kb = state.get("negative_knowledge_base", [])
        seen_keys = state.get("seen_keys", set())
        query = state.get("query", "")
        site = state.get("current_site", "")

        if not markdown or len(markdown) < 100:
            msg = f"Evaluate failed: markdown text too short (<100 chars). It seems the previous scrape captured no jobs."
            return {
                "messages": [ToolMessage(content=msg, tool_call_id=tool_call_id)],
                "search_history": [f"{site} - {query} - 0 jobs"],
                "failed_queries": [query] if query not in state.get("failed_queries", []) else []
            }

        # 调用大模型执行核心评估
        # 调用大模型执行核心评估（log 由 logger.evaluated 在完成后打印）
        prompt = EVALUATOR_PROMPT.format(
            negative_kb="、".join(negative_kb),
            current_site=site,
            markdown_content=markdown[:35000] # 恢复大上下文长度，因为已跑通 DeepSeek
        )

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            raw = response.content.strip()
            
            # 改进的 JSON 提取：寻找最外层的 {}
            start = raw.find("{")
            end = raw.rfind("}") + 1
            
            candidates = []
            if start != -1 and end > start:
                json_str = raw[start:end]
                candidates = self._extract_candidates(json_str)

            if not candidates:
                # 记录原始数据以便人工排查
                with open("evaluator_error_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"\n\n--- FAIL at {datetime.now()} ---\n{raw}\n")
                
                logger.error("JSON 提取为空或格式错误。原始响应已存至 evaluator_error_debug.log")
                
                # 关键：即使失败也要记入 history，防止 Agent 陷入死循环
                search_entry = f"{site} - {query} - FAILED(JSON)"
                return {
                    "messages": [ToolMessage(content="Failed to parse job list. Please try a different query.", tool_call_id=tool_call_id)],
                    "search_history": [search_entry],
                    "failed_queries": [query]
                }

            new_jobs_to_add = []
            new_count = 0
            
            for job in candidates:
                title = str(job.get("title", "")).strip()
                company = str(job.get("company", "")).strip()
                fingerprint = f"{title}-{company}"
                
                if fingerprint not in seen_keys:
                    seen_keys.add(fingerprint)
                    new_count += 1
                new_jobs_to_add.append(job)

            total_in_db = len(state.get('job_list', [])) + new_count
            logger.evaluated(new_count, len(candidates) - new_count, total_in_db)

            observation = f"Processed {len(candidates)} jobs, {new_count} brand new."
            search_entry = f"{site} - {query} - {new_count} new"
            return {
                "messages": [ToolMessage(content=observation, tool_call_id=tool_call_id)],
                "job_list": new_jobs_to_add,
                "seen_keys": seen_keys,
                "search_history": [search_entry]
            }

        except Exception as e:
            logger.error(f"评估节点系统崩溃: {e}")
            return {
                "messages": [ToolMessage(content=f"Evaluator system error: {str(e)}", tool_call_id=tool_call_id)],
                "search_history": [f"{site} - {query} - ERROR"]
            }

    def _extract_candidates(self, json_str: str) -> list:
        """强化版 JSON 提取逻辑，支持正则补齐"""
        import re
        try:
            result = json.loads(json_str)
            return result.get("job_list", [])
        except json.JSONDecodeError:
            # 正则抠取每一个 {} 对象
            chunks = re.findall(r'\{(?:[^{}]|(?R))*\}', json_str, re.DOTALL)
            results = []
            for chunk in chunks:
                try:
                    results.append(json.loads(chunk))
                except: continue
            return results

from datetime import datetime
