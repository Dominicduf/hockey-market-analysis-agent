import logging
from typing import Literal

from langchain_core.messages import AIMessage, SystemMessage, trim_messages
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from openai import APIConnectionError, APITimeoutError, RateLimitError

from app.agent_utils import (
    count_completed_tool_calls,
    get_scraped_product_count,
    has_called_tool,
    select_llm_for_state,
)
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


RETRY_EXCEPTIONS = (RateLimitError, APIConnectionError, APITimeoutError)


def build_agent(llm_base: ChatOpenAI | None = None):
    if llm_base is None:
        llm_base = ChatOpenAI(
            base_url=settings.openrouter_base_url,
            api_key=settings.openrouter_api_key,
            model=settings.model_name,
        )
    llm = llm_base.with_retry(
        retry_if_exception_type=RETRY_EXCEPTIONS,
        wait_exponential_jitter=True,
        stop_after_attempt=settings.max_retries,
    )
    llm_with_tools = llm_base.bind_tools(tools).with_retry(
        retry_if_exception_type=RETRY_EXCEPTIONS,
        wait_exponential_jitter=True,
        stop_after_attempt=settings.max_retries,
    )
    llm_force_report = llm_base.bind_tools([generate_report], tool_choice="required").with_retry(
        retry_if_exception_type=RETRY_EXCEPTIONS,
        wait_exponential_jitter=True,
        stop_after_attempt=settings.max_retries,
    )
    llm_force_any_tool = llm_base.bind_tools(tools, tool_choice="required").with_retry(
        retry_if_exception_type=RETRY_EXCEPTIONS,
        wait_exponential_jitter=True,
        stop_after_attempt=settings.max_retries,
    )

    logger = logging.getLogger(__name__)

    # Guardrail to make sure the LLM is not prompt injected
    # or answers random question
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

    def call_llm(state: AgentState):
        logger.info("[AGENT] Calling LLM...")
        # TODO : Find a better way to handle the context
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

        sentiments_done = count_completed_tool_calls(state["messages"], "analyze_sentiment")
        products_to_analyze = get_scraped_product_count(state["messages"])
        has_report = has_called_tool(state["messages"], "generate_report")

        logger.debug(
            "[AGENT] sentiments_done=%d / products_to_analyze=%d | has_report=%s",
            sentiments_done,
            products_to_analyze,
            has_report,
        )

        llm_to_use = select_llm_for_state(
            state["messages"], llm_with_tools, llm_force_report, llm_force_any_tool
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
