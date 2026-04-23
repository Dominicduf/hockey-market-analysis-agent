import logging
from typing import Literal

from langchain_core.messages import AIMessage, SystemMessage, trim_messages
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import MessagesState
from langgraph.prebuilt import ToolNode, tools_condition

from app.config import settings
from app.prompts import GUARDRAIL_PROMPT, SYSTEM_PROMPT
from app.tools.list_products import list_products
from app.tools.report_generator import generate_report
from app.tools.sentiment_analyzer import analyze_sentiment
from app.tools.web_scraper import scrape_product_pages

tools = [list_products, scrape_product_pages, analyze_sentiment, generate_report]

REFUSAL_MESSAGE = (
    "I'm a hockey equipment market analyst and I can only help with queries related "
    "to hockey equipment, pricing, market trends, or customer sentiment. "
    "I'm not able to help with that request."
)


class AgentState(MessagesState):
    is_safe: bool


def build_agent():
    llm = ChatOpenAI(
        base_url=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key,
        model=settings.model_name,
    )
    llm_with_tools = llm.bind_tools(tools)

    logger = logging.getLogger(__name__)

    def guardrail(state: AgentState):
        user_message = state["messages"][-1].content
        logger.info("[GUARDRAIL] Classifying input: '%s'", user_message[:80])
        response = llm.invoke(
            [
                SystemMessage(content=GUARDRAIL_PROMPT),
                {"role": "user", "content": user_message},
            ]
        )
        is_safe = response.content.strip().upper() == "SAFE"
        logger.info("[GUARDRAIL] Classification result: %s", "SAFE" if is_safe else "UNSAFE")

        if not is_safe:
            return {
                "is_safe": False,
                "messages": [AIMessage(content=REFUSAL_MESSAGE)],
            }

        return {"is_safe": True}

    def route_after_guardrail(state: AgentState) -> Literal["call_llm", "__end__"]:
        if state["is_safe"]:
            return "call_llm"
        return END

    def has_called_tool(messages: list, tool_name: str) -> bool:
        return any(
            tc["name"] == tool_name
            for m in messages
            if hasattr(m, "tool_calls")
            for tc in m.tool_calls
        )

    def call_llm(state: AgentState):
        logger.info("[AGENT] Calling LLM...")
        trimmed = trim_messages(
            state["messages"],
            max_tokens=settings.max_context_tokens,
            strategy="last",
            token_counter=lambda msgs: sum(len(str(m.content)) // 4 for m in msgs),
            allow_partial=False,
        )
        if len(trimmed) < len(state["messages"]):
            logger.warning(
                "[AGENT] Context trimmed: %d → %d messages",
                len(state["messages"]),
                len(trimmed),
            )
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + trimmed

        analysis_done = has_called_tool(state["messages"], "generate_report")
        llm_to_use = (
            llm_with_tools if analysis_done else llm_with_tools.bind(tool_choice="required")
        )

        response = llm_to_use.invoke(messages)
        if response.tool_calls:
            for tc in response.tool_calls:
                logger.info("[AGENT] Tool call: %s | Args: %s", tc["name"], tc["args"])
        else:
            logger.info("[AGENT] Final response:\n%s", response.content)
        return {"messages": [response]}

    graph = StateGraph(AgentState)
    graph.add_node("guardrail", guardrail)
    graph.add_node("call_llm", call_llm)
    graph.add_node("tools", ToolNode(tools))
    graph.add_edge(START, "guardrail")
    graph.add_conditional_edges("guardrail", route_after_guardrail)
    graph.add_conditional_edges("call_llm", tools_condition)
    graph.add_edge("tools", "call_llm")

    return graph.compile()


agent = build_agent()
