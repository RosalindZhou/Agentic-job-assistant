import os
from dotenv import load_dotenv

load_dotenv()

class LLMManager:
    """
    提供全局高可用 LLM 引擎池，统一接管 Planner 和 Evaluator：
    使用带有重试与穿透的三级降级策略 (Cascade Fallbacks)：
    1. 首选：DeepSeek-V3 (Silicon AI)
    2. 备用：Llama (Groq)
    3. 兜底：Gemini-2.0-Flash (Google)
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LLMManager, cls).__new__(cls)
            
            silicon_key = os.getenv("SILICON_API_KEY")
            groq_key    = os.getenv("GROQ_API_KEY")
            gemini_key  = os.getenv("GEMINI_API_KEY")

            models = []
            
            # 【Tier 1】核心主力：DeepSeek-V3 (超强性能，高并发额度)
            if silicon_key:
                from langchain_openai import ChatOpenAI
                models.append(ChatOpenAI(
                    model="deepseek-ai/DeepSeek-V3",  # 根据你给的示例，使用稳定支持工具调用的 V3
                    temperature=0.1,
                    api_key=silicon_key,
                    base_url="https://api.siliconflow.com/v1",
                    max_tokens=4096  # 强制大幅增加输出极限，防止长 JSON 列表被物理截断产生语法错误
                ))

            # 【Tier 2】光速备胎：Groq Llama 3.3 70B (大模型能力，防第一层故障)
            if groq_key:
                from langchain_groq import ChatGroq
                models.append(ChatGroq(
                    model="llama-3.3-70b-versatile",
                    temperature=0.1,
                    api_key=groq_key
                ))

            # 【Tier 3】终极兜底：Gemini 2.0 Flash (海量 Token 上下文防御异常)
            if gemini_key:
                from langchain_google_genai import ChatGoogleGenerativeAI
                models.append(ChatGoogleGenerativeAI(
                    model="gemini-2.0-flash",
                    google_api_key=gemini_key,
                    temperature=0.1
                ))

            if not models:
                raise ValueError("Initialization Error: 没有找到任何 API Key。请在 .env 中配置 SILICON_API_KEY / GROQ_API_KEY / GEMINI_API_KEY")

            # 装配高可用 Fallback 链
            primary_model = models[0]
            if len(models) > 1:
                cls._instance.model = primary_model.with_fallbacks(models[1:])
            else:
                cls._instance.model = primary_model

        return cls._instance

    def get_evaluator(self):
        """返回高可用联合引擎，确保长文本提取绝不宕机"""
        return self._instance.model

    def get_planner(self):
        """返回高可用联合引擎，确保 Agent 路由随时护航"""
        return self._instance.model
