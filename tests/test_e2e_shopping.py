from core.ebay_actions import EbayActions


def test_search_add_assert(page, scenario):
    actions = EbayActions(page)
    actions.login()
    urls = actions.search_items_by_name_under_price(
        scenario["query"], scenario["maxPrice"], scenario["limit"]
    )
    added = actions.add_items_to_cart(urls)
    assert added == len(urls), (
        f"Added {added}/{len(urls)} items — partial success masks threshold check"
    )
    actions.assert_cart_total_not_exceeds(scenario["budgetPerItem"], len(urls))
    assert isinstance(urls, list)
    assert len(urls) <= scenario["limit"]
