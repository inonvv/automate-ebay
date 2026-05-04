from core.ebay_actions import EbayActions


def test_search_add_assert(page, scenario, validator):
    actions = EbayActions(page, validator)
    actions.login()
    urls = actions.search_items_by_name_under_price(
        scenario["query"], scenario["maxPrice"], scenario["limit"]
    )
    actions.add_items_to_cart(urls)
    actions.assert_cart_total_not_exceeds(
        scenario["budgetPerItem"], len(urls), scenario["currency"]
    )
    assert isinstance(urls, list)
    assert len(urls) <= scenario["limit"]
