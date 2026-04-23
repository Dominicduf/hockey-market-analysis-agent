import logging
from pathlib import Path

from bs4 import BeautifulSoup
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "mock_data" / "products"

AVAILABLE_PRODUCTS = {
    "bauer_supreme_stick": "bauer_supreme_stick.html",
    "warrior_covert_stick": "warrior_covert_stick.html",
    "ccm_tacks_skates": "ccm_tacks_skates.html",
    "bauer_reakt_helmet": "bauer_reakt_helmet.html",
    "ccm_ht_gloves": "ccm_ht_gloves.html",
    "bauer_vapor_shin_pads": "bauer_vapor_shin_pads.html",
}


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
        text_el = review.select_one(".review-text")
        if text_el:
            line = f'- "{text_el.get_text(strip=True)}"'
            if author_el:
                line += f" — {author_el.get_text(strip=True)}"
            if rating_el:
                line += f" {rating_el.get_text(strip=True)}★"
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
def scrape_product_page(product_id: str) -> str:
    """
    Scrape a hockey equipment product page and return structured product information
    including name, brand, category, price, rating, and customer reviews.

    Available product IDs:
    - bauer_supreme_stick
    - warrior_covert_stick
    - ccm_tacks_skates
    - bauer_reakt_helmet
    - ccm_ht_gloves
    - bauer_vapor_shin_pads

    Args:
        product_id: The product identifier to scrape.

    Returns:
        Markdown formatted product data.
    """
    logger.info("[TOOL] web_scraper called with product_id='%s'", product_id)

    if product_id not in AVAILABLE_PRODUCTS:
        available = ", ".join(AVAILABLE_PRODUCTS.keys())
        logger.warning("[TOOL] Unknown product_id='%s'", product_id)
        return f"Unknown product ID '{product_id}'. Available products: {available}"

    file_path = DATA_DIR / AVAILABLE_PRODUCTS[product_id]

    try:
        html = file_path.read_text(encoding="utf-8")
        result = parse_product_page(html)
        logger.info("[TOOL] Successfully scraped '%s'", product_id)
        return result
    except Exception as e:
        logger.error("[TOOL] Failed to scrape '%s': %s", product_id, e)
        return f"Error reading product page for '{product_id}': {e}"
