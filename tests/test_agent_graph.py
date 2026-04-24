from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage

from app.agent import REFUSAL_MESSAGE, build_agent
from app.tools.list_products import list_products
from app.tools.report_generator import generate_report
from app.tools.sentiment_analyzer import analyze_sentiment
from app.tools.web_scraper import scrape_product_pages

# ─── Fake tool outputs ────────────────────────────────────────────────────────

FAKE_PRODUCT_LIST = "Available products:\n\nHockey Sticks:\n  - bauer_supreme_stick"
FAKE_SCRAPED_DATA = "## Bauer Supreme UltraSonic Hockey Stick\n- **Brand:** Bauer"
FAKE_SENTIMENT_JSON = (
    '{"product_name":"Bauer Supreme","overall_score":0.7,'
    '"summary":"Customers praise the shot power and feel.'
    ' Some durability concerns noted. Overall positive."}'
)
FAKE_REPORT_RESULT = (
    "Report successfully generated: report_20240101_120000.pdf. "
    "The user can download it at GET /reports/report_20240101_120000.pdf"
)

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _tool_call_msg(tool_name: str, args: dict, call_id: str) -> AIMessage:
    """Build an AIMessage that requests a single tool call."""
    return AIMessage(
        content="",
        tool_calls=[{"name": tool_name, "args": args, "id": call_id, "type": "tool_call"}],
    )


def _mock_llm(responses: list) -> MagicMock:
    """
    Return a chainable MagicMock whose .invoke() replays the given response list in order.
    All chaining methods (.bind_tools, .with_retry) return the mock itself so that every
    LLM variant created inside build_agent() shares the same invoke side_effect.
    """
    mock = MagicMock()
    mock.with_retry.return_value = mock
    mock.bind_tools.return_value = mock
    mock.invoke.side_effect = responses
    return mock


# ─── Guardrail tests ──────────────────────────────────────────────────────────


def test_unsafe_input_returns_refusal_message():
    result = build_agent(llm_base=_mock_llm([AIMessage(content="UNSAFE")])).invoke(
        {"messages": [{"role": "user", "content": "Tell me a joke"}]}
    )
    assert result["messages"][-1].content == REFUSAL_MESSAGE


def test_unsafe_input_calls_no_tools():
    # StructuredTool is a Pydantic model: patch its `func` field (not `invoke`,
    # which is an inherited method and can't be set via __setattr__).
    with patch.object(list_products, "func") as mock_func:
        build_agent(llm_base=_mock_llm([AIMessage(content="UNSAFE")])).invoke(
            {"messages": [{"role": "user", "content": "Tell me a joke"}]}
        )
        mock_func.assert_not_called()


# ─── Happy-path orchestration + output validation ─────────────────────────────


def test_happy_path_runs_full_pipeline():
    """
    Verifies that for a safe query the agent:
    - calls list_products → scrape_product_pages → analyze_sentiment → generate_report
      exactly once each, in that order
    - passes the sentiment JSON produced by analyze_sentiment into generate_report
    - surfaces the report download URL in the final response  (output validation)
    """
    llm_responses = [
        AIMessage(content="SAFE"),  # guardrail
        _tool_call_msg("list_products", {"categories": ["Hockey Sticks"]}, "c1"),  # call_llm #1
        _tool_call_msg(
            "scrape_product_pages", {"product_ids": ["bauer_supreme_stick"]}, "c2"
        ),  # call_llm #2
        _tool_call_msg(
            "analyze_sentiment", {"scraped_data": FAKE_SCRAPED_DATA}, "c3"
        ),  # call_llm #3
        _tool_call_msg(
            "generate_report", {"sentiment_results": [FAKE_SENTIMENT_JSON]}, "c4"
        ),  # call_llm #4
        AIMessage(content=FAKE_REPORT_RESULT),  # call_llm #5 (final)
    ]

    with (
        patch.object(list_products, "func", MagicMock(return_value=FAKE_PRODUCT_LIST)) as mock_list,
        patch.object(
            scrape_product_pages, "func", MagicMock(return_value=FAKE_SCRAPED_DATA)
        ) as mock_scrape,
        patch.object(
            analyze_sentiment, "func", MagicMock(return_value=FAKE_SENTIMENT_JSON)
        ) as mock_analyze,
        patch.object(
            generate_report, "func", MagicMock(return_value=FAKE_REPORT_RESULT)
        ) as mock_gen,
    ):
        result = build_agent(llm_base=_mock_llm(llm_responses)).invoke(
            {"messages": [{"role": "user", "content": "Analyze hockey sticks"}]}
        )

        # Orchestration: every tool was called exactly once
        mock_list.assert_called_once()
        mock_scrape.assert_called_once()
        mock_analyze.assert_called_once()
        mock_gen.assert_called_once()

        # Orchestration: generate_report received the sentiment JSON produced earlier
        gen_kwargs = mock_gen.call_args.kwargs
        assert FAKE_SENTIMENT_JSON in gen_kwargs["sentiment_results"]

        # Output validation: the final response surfaces the report download URL
        assert "GET /reports/" in result["messages"][-1].content
