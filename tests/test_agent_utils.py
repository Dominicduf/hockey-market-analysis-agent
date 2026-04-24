from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, ToolMessage

from app.agent_utils import (
    count_completed_tool_calls,
    get_scraped_product_count,
    has_called_tool,
    select_llm_for_state,
)

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _tool_call_msg(tool_name: str, args: dict, call_id: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": tool_name, "args": args, "id": call_id, "type": "tool_call"}],
    )


def _tool_result_msg(tool_name: str, call_id: str) -> ToolMessage:
    return ToolMessage(content="result", name=tool_name, tool_call_id=call_id)


def _mock_llm(name: str) -> MagicMock:
    return MagicMock(name=name)


# ─── count_completed_tool_calls ───────────────────────────────────────────────


def test_count_zero_when_no_tool_messages():
    assert count_completed_tool_calls([AIMessage(content="hello")], "analyze_sentiment") == 0


def test_count_only_matching_tool_name():
    messages = [
        _tool_result_msg("analyze_sentiment", "c1"),
        _tool_result_msg("analyze_sentiment", "c2"),
        _tool_result_msg("generate_report", "c3"),
    ]
    assert count_completed_tool_calls(messages, "analyze_sentiment") == 2
    assert count_completed_tool_calls(messages, "generate_report") == 1


def test_count_returns_zero_for_unknown_tool():
    messages = [_tool_result_msg("analyze_sentiment", "c1")]
    assert count_completed_tool_calls(messages, "unknown_tool") == 0


# ─── get_scraped_product_count ────────────────────────────────────────────────


def test_scraped_count_zero_when_no_scrape_call():
    assert get_scraped_product_count([AIMessage(content="hello")]) == 0


def test_scraped_count_returns_correct_number():
    messages = [_tool_call_msg("scrape_product_pages", {"product_ids": ["a", "b", "c"]}, "c1")]
    assert get_scraped_product_count(messages) == 3


def test_scraped_count_uses_most_recent_call():
    messages = [
        _tool_call_msg("scrape_product_pages", {"product_ids": ["a", "b"]}, "c1"),
        _tool_call_msg("scrape_product_pages", {"product_ids": ["c"]}, "c2"),
    ]
    assert get_scraped_product_count(messages) == 1


# ─── has_called_tool ──────────────────────────────────────────────────────────


def test_has_called_tool_false_when_not_called():
    assert has_called_tool([AIMessage(content="hello")], "generate_report") is False


def test_has_called_tool_true_when_called():
    messages = [_tool_call_msg("generate_report", {}, "c1")]
    assert has_called_tool(messages, "generate_report") is True


def test_has_called_tool_does_not_confuse_tool_names():
    messages = [_tool_call_msg("analyze_sentiment", {"scraped_data": "..."}, "c1")]
    assert has_called_tool(messages, "generate_report") is False


# ─── select_llm_for_state ─────────────────────────────────────────────────────


def test_select_returns_force_any_tool_at_pipeline_start():
    llm_with_tools = _mock_llm("llm_with_tools")
    llm_force_report = _mock_llm("llm_force_report")
    llm_force_any_tool = _mock_llm("llm_force_any_tool")

    result = select_llm_for_state(
        [AIMessage(content="start")], llm_with_tools, llm_force_report, llm_force_any_tool
    )
    assert result is llm_force_any_tool


def test_select_returns_force_any_tool_before_sentiment_called():
    # analyze_sentiment processes all products in one batch call, so the only
    # "not done" state is: products scraped but analyze_sentiment not yet called.
    llm_with_tools = _mock_llm("llm_with_tools")
    llm_force_report = _mock_llm("llm_force_report")
    llm_force_any_tool = _mock_llm("llm_force_any_tool")
    messages = [
        _tool_call_msg("scrape_product_pages", {"product_ids": ["a", "b"]}, "c1"),
        # analyze_sentiment not yet called
    ]

    result = select_llm_for_state(messages, llm_with_tools, llm_force_report, llm_force_any_tool)
    assert result is llm_force_any_tool


def test_select_returns_force_report_when_all_sentiments_done():
    llm_with_tools = _mock_llm("llm_with_tools")
    llm_force_report = _mock_llm("llm_force_report")
    llm_force_any_tool = _mock_llm("llm_force_any_tool")
    messages = [
        _tool_call_msg("scrape_product_pages", {"product_ids": ["a", "b"]}, "c1"),
        _tool_result_msg("analyze_sentiment", "c2"),
        _tool_result_msg("analyze_sentiment", "c3"),  # 2 of 2 done
    ]

    result = select_llm_for_state(messages, llm_with_tools, llm_force_report, llm_force_any_tool)
    assert result is llm_force_report


def test_select_returns_llm_with_tools_after_report_generated():
    llm_with_tools = _mock_llm("llm_with_tools")
    llm_force_report = _mock_llm("llm_force_report")
    llm_force_any_tool = _mock_llm("llm_force_any_tool")
    messages = [_tool_call_msg("generate_report", {"sentiment_results": ["..."]}, "c1")]

    result = select_llm_for_state(messages, llm_with_tools, llm_force_report, llm_force_any_tool)
    assert result is llm_with_tools
