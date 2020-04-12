from consts import elements
from items.item_data import calculate_items_profit
from search_filters.filtered_search import FilteredSearch
from user_info.user_actions import update_coin_balance


def get_next_item_to_search(user_coin_balance, requested_items):
    requested_items = list(calculate_items_profit(user_coin_balance, requested_items))
    sorted_by_profit = sorted(requested_items, key=lambda item: item.profit, reverse=True)
    most_profitable_item = sorted_by_profit[0]
    # if all the players are above the budget
    if most_profitable_item.profit == 0:
        return None
    else:
        return sorted_by_profit[0]


def update_search_item_if_coin_balance_changed(fab, item_to_search, requested_items):
    new_coin_balance = int(fab.element_actions.get_element(elements.COIN_BALANCE).text.replace(',', ''))
    if new_coin_balance != fab.user.coin_balance:
        update_coin_balance(fab.user.email, fab.element_actions)
        item_to_search = get_next_item_to_search(fab.user.coin_balance, requested_items)
        if item_to_search is not None:
            FilteredSearch(fab.element_actions,item_to_search).set_custom_search_filteres()
    return item_to_search
