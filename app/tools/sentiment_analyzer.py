import logging

from langchain_core.messages import SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from app.config import settings
from app.schemas import SentimentResult
from app.prompts import SENTIMENT_PROMPT

logger = logging.getLogger(__name__)

llm = ChatOpenAI(
    base_url=settings.openrouter_base_url,
    api_key=settings.openrouter_api_key,
    model=settings.model_name,
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
        structured_llm = llm.with_structured_output(SentimentResult)
        result: SentimentResult = structured_llm.invoke([
            SystemMessage(content=SENTIMENT_PROMPT),
            {"role": "user", "content": f"Analyze this product:\n\n{scraped_data}"},
        ])

        logger.info("[TOOL] Successfully analyzed sentiment for '%s'", result.product_name)
        return result.model_dump_json()

    except Exception as e:
        logger.error("[TOOL] Failed to analyze sentiment: %s", e)
        return (
            f"[TOOL ERROR] Failed to analyze sentiment: {e}. "
            f"No data was retrieved. Do not infer or guess product information."
        )
