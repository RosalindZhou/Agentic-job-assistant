from typing import TypedDict, List, Annotated, Set
import operator
from langchain_core.messages import AnyMessage

def add_messages(left: list, right: list):
    """LangGraph message reducer"""
    return left + right

def merge_jobs(left: list, right: list):
    """
    自定义岗位合并逻辑：
    1. 依据 title + company 进行去重。
    2. 如果新岗位包含详情页信息（非“待深挖”），则覆盖旧的列表页粗略信息。
    """
    job_map = {f"{j.get('title')}-{j.get('company')}": j for j in left}
    for j in right:
        fingerprint = f"{j.get('title')}-{j.get('company')}"
        if fingerprint in job_map:
            # 只有当新数据看起来比旧数据“更详尽”时才覆盖
            old_req = str(job_map[fingerprint].get("requirements", ""))
            new_req = str(j.get("requirements", ""))
            if "待深挖" in old_req and "待深挖" not in new_req:
                job_map[fingerprint] = j
        else:
            job_map[fingerprint] = j
    return list(job_map.values())

class AgentState(TypedDict):
    """
    全局状态定义 (LangGraph State) - ReAct Autonomous Agent 增强版
    """
    # 核心记忆链 (Reasoning + Tool Use)
    messages: Annotated[List[AnyMessage], add_messages]

    # 当前动作上下文
    query: str
    current_site: str
    page_num: int

    # 临时传递载体
    scraped_raw_data: str

    # 数据聚合区 (通过 merge_jobs 实现智能去重与更新)
    job_list: Annotated[List[dict], merge_jobs]
    seen_keys: Set[str]              # 防重判定池 (覆盖更新)

    # 记忆与反思区
    search_history: Annotated[List[str], operator.add]
    failed_queries: Annotated[List[str], operator.add]
    reflection_summary: str          # Reflection 节点的最新反思结论 (覆盖更新)

    # 知识与限制
    negative_knowledge_base: List[str]
    total_iterations: int            # 累加循环次数
    error_count_consecutive: int     # 连续异常次数
