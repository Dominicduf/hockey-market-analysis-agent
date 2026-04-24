import logging
from pathlib import Path

from bs4 import BeautifulSoup
from langchain_core.tools import tool

from app.catalog import AVAILABLE_PRODUCTS

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "products"


def parse_product_page(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    name = soup.select_one(".product-name").get_text(strip=True)
    brand = soup.select_one(".product-brand").get_text(strip=True)
    category = soup.select_one(".product-category").get_text(strip=True)
    price = soup.select_one(".price-current").get_text(strip=True)
    original_price = soup.select_one(".price-original")
    rating = soup.select_one(".rating-score").get_text(strip=True)
    review_count = soup.select_one(".review-count").get_text(strip=True)

    reviews = []
    for review in soup.select(".review"):
        rating_el = review.select_one(".review-rating")
        author_el = review.select_one(".review-author")
        date_el = review.select_one(".review-date")
        text_el = review.select_one(".review-text")
        if text_el:
            line = f'- "{text_el.get_text(strip=True)}"'
            if author_el:
                line += f" — {author_el.get_text(strip=True)}"
            if rating_el:
                line += f" {rating_el.get_text(strip=True)}★"
            if date_el:
                line += f" ({date_el.get_text(strip=True)})"
            reviews.append(line)

    md = f"## {name}\n"
    md += f"- **Brand:** {brand}\n"
    md += f"- **Category:** {category}\n"
    md += f"- **Price:** {price}"
    if original_price:
        md += f" ~~{original_price.get_text(strip=True)}~~"
    md += f"\n- **Rating:** {rating}/5 {review_count}\n"

    if reviews:
        md += "\n### Customer Reviews\n"
        md += "\n".join(reviews)

    return md


@tool
def scrape_product_pages(product_ids: list[str]) -> str:
    """
    Scrape one or more hockey equipment product pages in a single call.
    Always use list_products first to get valid product IDs.
    Pass all relevant product IDs at once to minimize tool calls.

    Args:
        product_ids: List of product identifiers to scrape.

    Returns:
        Markdown formatted product data for each product, separated by dividers.
    """
    logger.info(
        "[TOOL] scrape_product_pages called with %d product(s): %s", len(product_ids), product_ids
    )

    results = []
    for product_id in product_ids:
        if product_id not in AVAILABLE_PRODUCTS:
            logger.warning("[TOOL] Unknown product_id='%s'", product_id)
            results.append(
                f"[TOOL ERROR] Unknown product ID '{product_id}'. "
                f"No data was retrieved. Do not infer or guess product information."
            )
            continue

        file_path = DATA_DIR / AVAILABLE_PRODUCTS[product_id]
        try:
            html = file_path.read_text(encoding="utf-8")
            results.append(parse_product_page(html))
            logger.info("[TOOL] Successfully scraped '%s'", product_id)
        except Exception as e:
            logger.error("[TOOL] Failed to scrape '%s': %s", product_id, e)
            results.append(
                f"[TOOL ERROR] Failed to retrieve data for '{product_id}': {e}. "
                f"No data was retrieved. Do not infer or guess product information."
            )

    return "\n\n---\n\n".join(results)
