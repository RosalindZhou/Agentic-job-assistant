"""
节点: Reflection (反思节点) 🧠
在每轮 Evaluate 之后触发，让 LLM 分析当前搜索策略的有效性，
输出自我修正建议写入 state["reflection_summary"]，
供下一轮 Agent 规划时参考。

面试核心说辞：
  "我加了一个 Reflection 模块，Agent 会在每次提取结果后，
   自动检测策略是否失效，并生成改进建议——类似 ReAct 的 Observation + Critic 融合。"
"""
import json
from langchain_core.messages import HumanMessage
from llm_manager import LLMManager
from state import AgentState
from prompts import REFLECTION_PROMPT
import logger


class ReflectionNode:
    def __init__(self):
        self.llm = LLMManager().get_planner()

    def run(self, state: AgentState) -> dict:
        job_count    = len(state.get("job_list", []))
        history      = state.get("search_history", [])
        failed       = state.get("failed_queries", [])
        iterations   = state.get("total_iterations", 0)
        error_count  = state.get("error_count_consecutive", 0)

        # Reflection 不单独 print 开始，结果由 critic_result 打印

        prompt = REFLECTION_PROMPT.format(
            job_count=job_count,
            iterations=iterations,
            history="\n".join(f"  - {h}" for h in history[-8:]) if history else "  (暂无)",
            failed=", ".join(failed[-5:]) if failed else "无",
            error_count=error_count,
        )

        try:
            bound_llm = self.llm.bind(response_format={"type": "json_object"})
            response  = bound_llm.invoke([HumanMessage(content=prompt)])
            raw       = response.content.strip()

            start  = raw.find("{")
            end    = raw.rfind("}") + 1
            result = json.loads(raw[start:end])

            diagnosis   = result.get("diagnosis", "无法诊断")
            suggestion  = result.get("suggestion", "维持现有策略")
            next_query  = result.get("next_query_hint", "")
            confidence  = result.get("strategy_confidence", 0.5)

            summary = (
                f"[第{iterations}轮反思] "
                f"诊断: {diagnosis} | "
                f"建议: {suggestion} | "
                f"推荐新词: {next_query} | "
                f"策略信心: {confidence:.0%}"
            )
            logger.critic_result(confidence, next_query, diagnosis)
            return {"reflection_summary": summary}

        except Exception as e:
            logger.warn(f"Reflection 评审失败: {e}")
            return {"reflection_summary": ""}
