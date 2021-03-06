import json
import time
from operator import attrgetter
from typing import List

import requests

from consts import CONTENT_URL, GUID, CONFIG_JSON_SUFFIX, YEAR, MAX_PRICE
from consts import GAME_URL, REQUEST_TIMEOUT, MAX_CARD_ON_PAGE
from models.successful_bid import SuccessfulBid
from models.web_app_auction import WebAppAuction
from src.web_app.live_logins import authenticated_accounts
from src.web_app.auction_helpers import get_auction_data, get_successfull_trade_data
from src.web_app.price_evaluator import get_futbin_price, get_sell_price
from utils.exceptions import TimeoutError, UnknownError, ExpiredSession, Conflict, TooManyRequests, Captcha, PermissionDenied, MarketLocked, TemporaryBanned, \
    NoTradeExistingError, NoBudgetLeft, FutError


class WebAppActions:
    def __init__(self, ea_account):
        self.login_instance = authenticated_accounts.get(ea_account)
        self.host = self.login_instance.fut_host
        self.request_session = requests.Session()
        self.request_session.headers['X-UT-SID'] = self.login_instance.sid
        self.pin = self.login_instance.pin
        self.request_count = 0
        self.credits = 0
        self.duplicates = 0

    def _web_app_request(self, method, url, data=None, params=None):
        self.request_count += 1
        data = data or {}
        params = params or {}
        url = f'https://{self.host}/{GAME_URL}/{url}'
        self.request_session.options(url, params=params)

        res = None
        try:
            if method.upper() == 'GET':
                res = self.request_session.get(url, data=data, params=params, timeout=REQUEST_TIMEOUT)
            elif method.upper() == 'POST':
                res = self.request_session.post(url, data=data, params=params, timeout=REQUEST_TIMEOUT)
            elif method.upper() == 'PUT':
                res = self.request_session.put(url, data=data, params=params, timeout=REQUEST_TIMEOUT)
            elif method.upper() == 'DELETE':
                res = self.request_session.delete(url, data=data, params=params, timeout=REQUEST_TIMEOUT)
            if res is None:
                raise UnknownError()

        except requests.exceptions.Timeout:
            raise TimeoutError()
        operation_status_switcher = {
            401: ExpiredSession,
            409: Conflict,
            429: TooManyRequests,
            458: Captcha,
            461: PermissionDenied,
            460: PermissionDenied,
            494: MarketLocked,
            512: TemporaryBanned,
            521: TemporaryBanned,
            478: NoTradeExistingError
        }
        if not res.ok:
            exception = operation_status_switcher.get(res.status_code)
            if exception:
                raise exception
            raise UnknownError()

        if res.text == '':
            res = {}
        else:
            res = res.json()
        # update coin balance
        if 'credits' in res and res['credits']:
            self.credits = res['credits']
        if 'duplicateItemIdList' in res:
            self.duplicates = [i['itemId'] for i in res['duplicateItemIdList']]
        return res

    def make_settings_request(self):
        self._web_app_request('GET', 'settings')

    def make_remote_config_request(self):
        self.request_session.get(f"{CONTENT_URL}/{GUID}/{YEAR}/{CONFIG_JSON_SUFFIX}")

    def send_item_to_trade_pile(self, item_ids, pile="trade"):
        data = {"itemData": [{'id': i, 'pile': pile} for i in item_ids]}

        res = self._web_app_request('PUT', 'item', data=json.dumps(data))
        if res.get('itemData'):
            if res['itemData'][0]['success']:
                """ emit here from socket io that the item was sent """
                print("item was sent to transfer list")
            else:
                print(f"failed to list item, reason: {res['itemData'][0]['reason']}")
        else:
            raise FutError(reason="listing went wrong, log into the webapp and chek the issue. come back later.")

    def enter_first_transfer_market_search(self):
        self._web_app_request('GET', 'watchlist')
        self.pin.send_hub_transfers_pin_event()
        self.pin.send_transfer_search_pin_event()

    def send_back_to_new_search_pin_event(self):
        self.pin.send_transfer_search_pin_event()

    def search_items(self, item_type='player', level=None, category=None, masked_def_id=None, defenition_id=None,
                     min_price=None, max_price=None, min_bin=None, max_bin=None,
                     league=None, club=None, position=None, zone=None, nationality=None,
                     rare=False, play_style=None, start=0):

        self.pin.send_transfer_search_pin_event()

        params = {
            'start': start,
            'num': 21,
            'type': item_type
        }

        if level: params['lev'] = level
        if category: params['cat'] = category
        if masked_def_id: params['maskedDefId'] = masked_def_id
        if defenition_id: params['definitionId'] = defenition_id
        if min_price: params['micr'] = min_price
        if max_price: params['macr'] = max_price
        if min_bin: params['minb'] = min_bin
        if max_bin: params['maxb'] = max_bin
        if league: params['leag'] = league
        if club: params['team'] = club
        if position: params['pos'] = position
        if zone: params['zone'] = zone
        if nationality: params['nat'] = nationality
        if rare: params['rare'] = 'SP'
        if play_style: params['playStyle'] = play_style

        res = self._web_app_request('GET', 'transfermarket', params=params)

        search_results = [get_auction_data(i) for i in res.get('auctionInfo')]

        if search_results:
            self.pin.send_got_search_results_pin_event()
        else:
            self.pin.send_no_results_pin_event()
        return search_results

    """ try to snipe - this function does not check, trade state and is not responsible for deciding the max bin price - it just snipes!"""

    def snipe_items(self, auctions: List[WebAppAuction]):
        # if somehow there are more than one result snipe all the deals from min to max bin!
        successful_bids: List[SuccessfulBid] = []
        for min_auction in auctions:
            trade_id = min_auction.trade_id
            coins_to_bid = min_auction.buy_now_price
            if coins_to_bid > self.credits:
                raise NoBudgetLeft()
            data = {'bid': coins_to_bid}
            try:
                res = self._web_app_request('PUT', f'trade/{trade_id}/bid', data=json.dumps(data))
                acquired_item_data = res.get('auctionInfo')[0].get('itemData')
                successful_bid = get_successfull_trade_data(acquired_item_data)
                print(
                    f'== SUCEESS {successful_bid.timestamp} == '
                    f'{successful_bid.rating} '
                    f'{successful_bid.revision} '
                    f'{successful_bid.player_name} '
                    f'was bought for {coins_to_bid} coins')
                successful_bids.append(successful_bid)

            except (Conflict, PermissionDenied, NoTradeExistingError) as e:
                time.sleep(3)
                print(f'{e.reason}')

            except TemporaryBanned as e:
                print(f'{e.reason}')
                time.sleep(5)

            except TooManyRequests as e:
                print(f'{e.reason}')
                raise e

            except ExpiredSession as e:
                print(f'{e.reason}')
                raise e

            except NoBudgetLeft as e:
                raise e
        return successful_bids

    def get_item_min_price(self, def_id):
        futbin_price = get_futbin_price(def_id, self.login_instance.platform)
        min_price = MAX_PRICE
        page = 0
        while True:
            results = self.search_items(masked_def_id=def_id, max_bin=futbin_price, start=MAX_CARD_ON_PAGE * page)
            if not results:
                break
            curr_page_min = min(results, key=attrgetter('buy_now_price')).buy_now_price
            min_price = min(min_price, curr_page_min)
            if len(results) < MAX_CARD_ON_PAGE: break
            page += 1
            self.send_back_to_new_search_pin_event()
        # todo: think about "fraiers"
        return min_price

    def list_item(self, item_id, def_id, duration=3600):
        try:
            # check rt price
            market_price = self.get_item_min_price(def_id)
            start_price, buy_now = get_sell_price(market_price)

            data = {'buyNowPrice': buy_now, 'duration': duration, 'startingBid': start_price, 'itemData': {'id': item_id}}
            self._web_app_request('POST', 'auctionhouse', data=json.dumps(data))
            self._web_app_request('GET', 'tradepile')
        except FutError as e:
            time.sleep(1)

    def list_all_items_in_tradepile(self):
        # items can be bought at the middle of the search thus this is needed to be in while all items are listed
        listed_count = 0
        while True:
            self.pin.send_transfer_list_pin_evnet()
            # tradeId = 0 if the item was not listed and if it was not bought coinsProcessed does not exist
            not_sold = [trade for trade in self._web_app_request('GET', 'tradepile').get('auctionInfo')
                        if (trade.get('tradeId') == 0 or (trade.get('expires') == -1 and not trade.get('coinsProcessed')))]
            if len(not_sold) == 0: break
            for item in not_sold:
                item_id = item.get('itemData').get('id')
                resource_id = item.get('itemData').get('resourceId')
                self.list_item(item_id, resource_id)
                listed_count += 1
                print(f"listed {listed_count}")
                # wait a bit to avoid exceptions
                if listed_count == 5:
                    time.sleep(1)
        # check if clear is needed
        self.pin.send_transfer_list_pin_evnet()
        sold = [trade for trade in self._web_app_request('GET', 'tradepile').get('auctionInfo') if trade.get('coinsProcessed')]
        # clear if there are sold items
        if len(sold) != 0:
            self._web_app_request('DELETE', 'trade/sold')

    def logout(self):
        self.request_session.delete(f'https://{self.host}/ut/auth', timeout=REQUEST_TIMEOUT)
