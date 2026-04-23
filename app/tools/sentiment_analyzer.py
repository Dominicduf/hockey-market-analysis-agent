import logging

from langchain_core.messages import SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from openai import APIConnectionError, APITimeoutError, RateLimitError
from pydantic import ValidationError

from app.config import settings
from app.prompts import SENTIMENT_PROMPT
from app.schemas import SentimentResult

logger = logging.getLogger(__name__)

_llm = ChatOpenAI(
    base_url=settings.openrouter_base_url,
    api_key=settings.openrouter_api_key,
    model=settings.model_name,
)

llm = _llm.with_retry(
    retry_if_exception_type=(RateLimitError, APIConnectionError, APITimeoutError),
    wait_exponential_jitter=True,
    stop_after_attempt=settings.max_retries,
)


@tool
def analyze_sentiment(scraped_data: str) -> str:
    """
    Analyze customer sentiment from already-scraped hockey equipment product data.
    Must be called AFTER scrape_product_page — pass its output directly as scraped_data.
    Returns structured sentiment data including overall score, aspect breakdown
    (durability, performance, value_for_money, comfort, fit), sentiment distribution,
    and recurring praise and complaint themes.

    Args:
        scraped_data: The raw markdown output returned by scrape_product_page.

    Returns:
        JSON formatted sentiment analysis.
    """
    logger.info("[TOOL] analyze_sentiment called")

    try:
        messages = [
            SystemMessage(content=SENTIMENT_PROMPT),
            {"role": "user", "content": f"Analyze this product:\n\n{scraped_data}"},
        ]
        structured_llm = llm.with_structured_output(SentimentResult)

        result = None
        for attempt in range(2):
            try:
                result = structured_llm.invoke(messages)
                break
            except ValidationError as e:
                if attempt == 1:
                    raise
                logger.warning(
                    "[TOOL] Structured output invalid on attempt %d, retrying: %s", attempt + 1, e
                )

        logger.info("[TOOL] Successfully analyzed sentiment for '%s'", result.product_name)
        return result.model_dump_json()

    except Exception as e:
        logger.error("[TOOL] Failed to analyze sentiment: %s", e)
        return (
            f"[TOOL ERROR] Failed to analyze sentiment: {e}. "
            f"No data was retrieved. Do not infer or guess product information."
        )
