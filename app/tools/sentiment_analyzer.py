import logging

from langchain_core.messages import SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from openai import APIConnectionError, APITimeoutError, RateLimitError
from pydantic import ValidationError

from app.config import settings
from app.prompts import SENTIMENT_PROMPT
from app.schemas import SentimentResults

logger = logging.getLogger(__name__)


def make_analyze_sentiment_tool(llm: ChatOpenAI):
    """Factory that creates an analyze_sentiment tool bound to the given LLM instance."""

    structured_llm = llm.with_structured_output(SentimentResults).with_retry(
        retry_if_exception_type=(
            RateLimitError,
            APIConnectionError,
            APITimeoutError,
            ValidationError,
        ),
        wait_exponential_jitter=True,
        stop_after_attempt=settings.max_retries,
    )

    @tool
    def analyze_sentiment(scraped_data: str) -> str:
        """
        Analyze customer sentiment for ALL scraped hockey equipment products in a single call.
        Must be called AFTER scrape_product_pages — pass its FULL output directly as scraped_data.
        Returns structured sentiment data for every product, including overall score,
        aspect breakdown (durability, performance, value_for_money, comfort, fit),
        sentiment distribution, and recurring praise and complaint themes.

        Args:
            scraped_data: The full raw markdown output returned by scrape_product_pages
                (all products).

        Returns:
            JSON object with a "results" array containing one sentiment analysis per product.
        """
        logger.info("[TOOL] analyze_sentiment called")

        try:
            messages = [
                SystemMessage(content=SENTIMENT_PROMPT),
                {"role": "user", "content": f"Analyze these products:\n\n{scraped_data}"},
            ]
            result = structured_llm.invoke(messages)
            if result is None:
                logger.error(
                    "[TOOL] structured_llm returned None — model produced an unparseable response"
                )
                return (
                    "[TOOL ERROR] Sentiment analysis returned no structured result. "
                    "No data was retrieved. Do not infer or guess product information."
                )
            logger.info(
                "[TOOL] Successfully analyzed sentiment for %d product(s)", len(result.results)
            )
            return result.model_dump_json()

        except Exception as e:
            logger.error("[TOOL] Failed to analyze sentiment: %s", e)
            return (
                f"[TOOL ERROR] Failed to analyze sentiment: {e}. "
                f"No data was retrieved. Do not infer or guess product information."
            )

    return analyze_sentiment


analyze_sentiment = make_analyze_sentiment_tool(
    ChatOpenAI(
        base_url=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key,
        model=settings.model_name,
    )
)
