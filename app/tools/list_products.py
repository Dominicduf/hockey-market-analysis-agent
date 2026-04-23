import logging
from collections import defaultdict

from langchain_core.tools import tool

from app.tools.web_scraper import PRODUCT_CATALOG

logger = logging.getLogger(__name__)


@tool
def list_products(categories: list[str] = []) -> str:
    """
    List available hockey equipment products in the catalog.
    Always call this tool first to discover which product IDs exist
    before calling scrape_product_pages or analyze_sentiment.
    Pass all desired categories at once to minimize tool calls.

    Available categories: Hockey Sticks, Ice Skates, Helmets, Hockey Gloves, Shin Pads

    Args:
        categories: Optional list of category filters (case-insensitive, partial match allowed).
                    If empty, returns all products grouped by category.

    Returns:
        Markdown list of matching product IDs grouped by category.
    """
    logger.info("[TOOL] list_products called with categories=%s", categories or "all")

    grouped: dict[str, list[str]] = defaultdict(list)
    for product_id, info in PRODUCT_CATALOG.items():
        if not categories or any(cat.lower() in info["category"].lower() for cat in categories):
            grouped[info["category"]].append(product_id)

    if not grouped:
        return (
            f"[TOOL ERROR] No products found for categories {categories}. "
            f"Available categories: Hockey Sticks, Ice Skates, Helmets, Hockey Gloves, Shin Pads."
        )

    lines = ["Available products:\n"]
    for cat, product_ids in grouped.items():
        lines.append(f"{cat}:")
        for pid in product_ids:
            lines.append(f"  - {pid}")
        lines.append("")

    result = "\n".join(lines).strip()
    logger.info("[TOOL] list_products returned %d product(s)", sum(len(v) for v in grouped.values()))
    return result
