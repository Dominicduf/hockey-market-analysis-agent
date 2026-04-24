PRODUCT_CATALOG: dict[str, dict[str, str]] = {
    "bauer_supreme_stick": {"file": "bauer_supreme_stick.html", "category": "Hockey Sticks"},
    "warrior_covert_stick": {"file": "warrior_covert_stick.html", "category": "Hockey Sticks"},
    "ccm_tacks_skates": {"file": "ccm_tacks_skates.html", "category": "Ice Skates"},
    "bauer_reakt_helmet": {"file": "bauer_reakt_helmet.html", "category": "Helmets"},
    "ccm_ht_gloves": {"file": "ccm_ht_gloves.html", "category": "Hockey Gloves"},
    "bauer_vapor_shin_pads": {"file": "bauer_vapor_shin_pads.html", "category": "Shin Pads"},
}

AVAILABLE_PRODUCTS = {pid: info["file"] for pid, info in PRODUCT_CATALOG.items()}
