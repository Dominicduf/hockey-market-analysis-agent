from app.tools.list_products import list_products


def test_filter_by_single_category():
    result = list_products.invoke({"categories": ["Hockey Sticks"]})
    assert "bauer_supreme_stick" in result
    assert "warrior_covert_stick" in result
    assert "ccm_tacks_skates" not in result
    assert "bauer_reakt_helmet" not in result


def test_filter_is_case_insensitive():
    lower = list_products.invoke({"categories": ["hockey sticks"]})
    upper = list_products.invoke({"categories": ["Hockey Sticks"]})
    assert lower == upper


def test_multiple_categories_returns_products_from_all():
    result = list_products.invoke({"categories": ["Hockey Sticks", "Shin Pads"]})
    assert "bauer_supreme_stick" in result
    assert "warrior_covert_stick" in result
    assert "bauer_vapor_shin_pads" in result
    assert "ccm_tacks_skates" not in result


def test_empty_categories_returns_all_products():
    result = list_products.invoke({"categories": []})
    for pid in [
        "bauer_supreme_stick",
        "warrior_covert_stick",
        "ccm_tacks_skates",
        "bauer_reakt_helmet",
        "ccm_ht_gloves",
        "bauer_vapor_shin_pads",
    ]:
        assert pid in result


def test_unknown_category_returns_tool_error():
    result = list_products.invoke({"categories": ["Footballs"]})
    assert "[TOOL ERROR]" in result
    assert "Footballs" in result
