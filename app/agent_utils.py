from langchain_core.messages import ToolMessage


def count_completed_tool_calls(messages: list, tool_name: str) -> int:
    """Count completed ToolMessage results for a given tool name."""
    return sum(1 for m in messages if isinstance(m, ToolMessage) and m.name == tool_name)


def get_scraped_product_count(messages: list) -> int:
    """Return the number of product_ids from the most recent scrape_product_pages call."""
    for m in reversed(messages):
        if hasattr(m, "tool_calls"):
            for tc in m.tool_calls:
                if tc["name"] == "scrape_product_pages":
                    return len(tc["args"].get("product_ids", []))
    return 0


def has_called_tool(messages: list, tool_name: str) -> bool:
    """Return True if any AIMessage in the history has requested a call to tool_name."""
    return any(
        tc["name"] == tool_name for m in messages if hasattr(m, "tool_calls") for tc in m.tool_calls
    )


def select_llm_for_state(messages: list, llm_with_tools, llm_force_report, llm_force_any_tool):
    """
    Return the appropriate LLM configuration based on the current pipeline state.

    - After generate_report has been called → llm_with_tools (free tool choice, agent wraps up)
    - After all sentiments are done         → llm_force_report (only generate_report available)
    - Otherwise                             → llm_force_any_tool (all tools available, required)
    """
    if has_called_tool(messages, "generate_report"):
        return llm_with_tools

    sentiments_done = count_completed_tool_calls(messages, "analyze_sentiment")
    products_to_analyze = get_scraped_product_count(messages)
    all_sentiment_done = products_to_analyze > 0 and sentiments_done >= 1

    if all_sentiment_done:
        return llm_force_report

    return llm_force_any_tool
