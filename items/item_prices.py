import time

from selenium.webdriver.common.keys import Keys

from consts import elements
from consts.app import MAX_CARD_ON_PAGE, NUMBER_OF_SEARCHS_BEFORE_BINARY_SEARCH
from consts.elements import START_ITEM_PRICE_ON_PAGE, END_ITEM_PRICE_ON_PAGE
from consts.prices.prices_consts import MIN_ITEM_PRICE, MAX_PRICE, MIN_PRICE
from enums.actions_for_execution import ElementCallback
from utils.prices import calc_new_max_price, get_scale_from_dict


def search_item_RT_price_on_market(fab, item_price_limit):
    found_item_from_regular_search, item_price = _check_item_price_regular_search(fab, item_price_limit)
    if found_item_from_regular_search:
        return item_price
    is_found_price, item_price = _check_if_got_results_in_current_price_webapp(fab, item_price)
    if is_found_price:
        find_item_from_binary_search, min_price = _check_item_price_binary_search(fab, item_price)
        return min_price
    else:
        return MAX_PRICE
    # todo: emit if the card was not found, maybe emit the found price..


def _check_item_price_regular_search(fab, item_price):
    searchs = NUMBER_OF_SEARCHS_BEFORE_BINARY_SEARCH
    found_correct_price = False
    for search in range(searchs):
        if int(str(item_price).replace(',', '')) == MIN_PRICE:
            return True, MIN_PRICE
        fab.element_actions.execute_element_action(elements.SEARCH_ITEM_BTN, ElementCallback.CLICK)
        fab.element_actions.wait_for_page_to_load_without_element_timeout(fab)
        no_results_banner = fab.element_actions.get_element(elements.NO_RESULTS_FOUND)
        # check if the item is less than the approximate price or not
        if no_results_banner and found_correct_price:
            fab.element_actions.execute_element_action(elements.NAVIGATE_BACK, ElementCallback.CLICK)
            return True, int(str(item_price).replace(',', ''))
        if no_results_banner:
            fab.element_actions.execute_element_action(elements.NAVIGATE_BACK, ElementCallback.CLICK)
            fab.element_actions.execute_element_action(elements.INCREASE_MAX_PRICE_BTN, ElementCallback.CLICK)
            item_price = fab.element_actions.get_element(elements.MAX_BIN_PRICE_INPUT).get_attribute("value")
        if not no_results_banner:
            is_last_element_exist = fab.element_actions.check_if_last_element_exist()
            if not is_last_element_exist:
                return get_item_min_price_on_webapp_page(fab.element_actions)

            fab.element_actions.execute_element_action(elements.NAVIGATE_BACK, ElementCallback.CLICK)
            fab.element_actions.wait_until_visible(elements.MAX_BIN_PRICE_INPUT)
            item_price = fab.element_actions.get_element(elements.MAX_BIN_PRICE_INPUT).get_attribute("value")
            found_correct_price = True
            fab.element_actions.execute_element_action(elements.DECREASE_MAX_PRICE_BTN, ElementCallback.CLICK)
    return False, item_price


def _change_max_bin_price(element_actions, new_price):
    element_actions.execute_element_action(elements.NAVIGATE_BACK, ElementCallback.CLICK)
    element_actions.execute_element_action(elements.MAX_BIN_PRICE_INPUT, ElementCallback.CLICK)
    element_actions.execute_element_action(elements.MAX_BIN_PRICE_INPUT, ElementCallback.SEND_KEYS, Keys.CONTROL, "a")
    time.sleep(0.5)
    element_actions.execute_element_action(elements.MAX_BIN_PRICE_INPUT, ElementCallback.SEND_KEYS, str(new_price))
    time.sleep(0.5)
    element_actions.execute_element_action(elements.SEARCH_PRICE_HEADER, ElementCallback.CLICK)
    return int(element_actions.get_element(elements.MAX_BIN_PRICE_INPUT).get_attribute("value").replace(',', ''))


def _check_if_got_results_in_current_price_webapp(fab, item_price):
    item_price = int(item_price.replace(",", ""))
    fab.element_actions.execute_element_action(elements.SEARCH_ITEM_BTN, ElementCallback.CLICK)
    fab.element_actions.wait_for_page_to_load_without_element_timeout(fab)
    no_results_banner = fab.element_actions.get_element(elements.NO_RESULTS_FOUND)
    while no_results_banner:
        item_price = item_price * 2
        item_price = _change_max_bin_price(fab.element_actions, item_price)
        fab.element_actions.execute_element_action(elements.SEARCH_ITEM_BTN, ElementCallback.CLICK)
        fab.element_actions.wait_for_page_to_load_without_element_timeout(fab)
        no_results_banner = fab.element_actions.get_element(elements.NO_RESULTS_FOUND)
        if no_results_banner and item_price >= MAX_PRICE:
            fab.element_actions.execute_element_action(elements.NAVIGATE_BACK, ElementCallback.CLICK)
            return False, MAX_PRICE
    return True, item_price


def get_item_min_price_on_webapp_page(element_actions):
    min_prices_on_page = []
    for i in range(1, MAX_CARD_ON_PAGE + 1):
        if element_actions.get_element("{}{}{}".format(START_ITEM_PRICE_ON_PAGE, i, END_ITEM_PRICE_ON_PAGE)) is not None:
            min_prices_on_page.append(
                int(element_actions.get_element("{}{}{}".format(START_ITEM_PRICE_ON_PAGE, i, END_ITEM_PRICE_ON_PAGE)).text.replace(",", "")))
        else:
            break
    element_actions.execute_element_action(elements.NAVIGATE_BACK, ElementCallback.CLICK)
    return True, min(min_prices_on_page)


def _check_item_price_binary_search(fab, item_price):
    down_limit = MIN_ITEM_PRICE
    up_limit = item_price
    item_new_max_price = calc_new_max_price(down_limit, up_limit, 0)
    search_scales = get_scale_from_dict(up_limit, down_limit)
    item_price_after_webapp_transfer = _change_max_bin_price(fab.element_actions, item_new_max_price)
    fab.element_actions.execute_element_action(elements.SEARCH_ITEM_BTN, ElementCallback.CLICK)
    while up_limit - down_limit not in search_scales:
        fab.element_actions.wait_for_page_to_load_without_element_timeout(fab)
        is_no_results_banner = fab.element_actions.get_element(elements.NO_RESULTS_FOUND)
        if is_no_results_banner:
            down_limit = item_price_after_webapp_transfer
            item_new_max_price = calc_new_max_price(down_limit, up_limit, 1)
            item_price_after_webapp_transfer = _change_max_bin_price(fab.element_actions, item_new_max_price)

            search_scales = get_scale_from_dict(down_limit, up_limit)
        else:
            is_last_element_exist = fab.element_actions.check_if_last_element_exist()
            if not is_last_element_exist:
                return get_item_min_price_on_webapp_page(fab.element_actions)
            up_limit = item_price_after_webapp_transfer
            item_new_max_price = calc_new_max_price(down_limit, up_limit, 0)
            item_price_after_webapp_transfer = _change_max_bin_price(fab.element_actions, item_new_max_price)

            search_scales = get_scale_from_dict(down_limit, up_limit)

        fab.element_actions.execute_element_action(elements.SEARCH_ITEM_BTN, ElementCallback.CLICK)
    fab.element_actions.execute_element_action(elements.NAVIGATE_BACK, ElementCallback.CLICK)
    return True, up_limit
