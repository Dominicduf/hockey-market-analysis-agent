from app.tools.web_scraper import scrape_product_pages


def test_known_product_returns_markdown_with_key_fields():
    result = scrape_product_pages.invoke({"product_ids": ["bauer_supreme_stick"]})
    assert "Bauer Supreme UltraSonic Hockey Stick" in result
    assert "$289.99" in result
    assert "4.6" in result
    assert "### Customer Reviews" in result


def test_multiple_products_are_separated_by_divider():
    result = scrape_product_pages.invoke(
        {"product_ids": ["bauer_supreme_stick", "bauer_vapor_shin_pads"]}
    )
    assert "Bauer Supreme UltraSonic Hockey Stick" in result
    assert "Bauer Vapor 3X Hockey Shin Pads" in result
    assert "---" in result


def test_unknown_product_id_returns_tool_error():
    result = scrape_product_pages.invoke({"product_ids": ["totally_fake_product"]})
    assert "[TOOL ERROR]" in result
    assert "totally_fake_product" in result


def test_mixed_valid_and_invalid_ids_handles_both():
    result = scrape_product_pages.invoke({"product_ids": ["bauer_supreme_stick", "fake_product"]})
    assert "Bauer Supreme UltraSonic Hockey Stick" in result
    assert "[TOOL ERROR]" in result
    assert "fake_product" in result
