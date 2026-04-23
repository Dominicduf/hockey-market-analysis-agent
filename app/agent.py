import logging
from typing import Literal

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import MessagesState
from langgraph.prebuilt import ToolNode, tools_condition

from app.config import settings
from app.prompts import GUARDRAIL_PROMPT, SYSTEM_PROMPT
from app.tools.web_scraper import scrape_product_page

tools = [scrape_product_page]

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
        response = llm.invoke([
            SystemMessage(content=GUARDRAIL_PROMPT),
            {"role": "user", "content": user_message},
        ])
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

    def call_llm(state: AgentState):
        logger.info("[AGENT] Calling LLM...")
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]

        has_tool_results = any(isinstance(m, ToolMessage) for m in state["messages"])
        llm_to_use = llm_with_tools if has_tool_results else llm_with_tools.bind(tool_choice="required")

        response = llm_to_use.invoke(messages)
        if response.tool_calls:
            tool_names = [tc["name"] for tc in response.tool_calls]
            logger.info("[AGENT] LLM requested tools: %s", tool_names)
        else:
            logger.info("[AGENT] LLM generated final response")
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
