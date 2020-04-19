from consts import elements
from items.items_priorities import get_item_to_search_according_to_prices
from search_filters.filter_setter import FilterSetter
from ea_account_info.ea_account_actions import update_ea_account_coin_balance_db


def update_search_item_if_coin_balance_changed(fab, best_item_to_search, items):
    new_coin_balance = int(fab.element_actions.get_element(elements.COIN_BALANCE).text.replace(',', ''))
    if new_coin_balance != fab.ea_account.coin_balance:
        update_ea_account_coin_balance_db(fab.ea_account.email, fab.element_actions)
        best_item_to_search = get_item_to_search_according_to_prices(items)
        if best_item_to_search is not None:
            FilterSetter(fab.element_actions, best_item_to_search).set_search_filteres()
    return best_item_to_search
