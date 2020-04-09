from consts.app import EA_TAX, PROFIT_MULTIPLIER
from consts.prices import DECREASE_SALE_PRICE_PERCENTAGE


class Player:
    def __init__(self, id='', name='', rating='', revision='', nation='', position='', club='', player_image='', club_image='', nation_image=''):
        self.id = id
        self.name = name
        self.rating = rating
        self.revision = revision
        self.position = position
        self.club = club
        self.profit = 0
        self.market_price = 0
        self.nation = nation
        self.player_image = player_image
        self.club_image = club_image
        self.nation_image = nation_image

    def set_market_price(self, market_price):
        self.market_price = market_price

    def get_max_buy_price(self):
        return self.market_price * EA_TAX - self.market_price * PROFIT_MULTIPLIER

    def get_sell_price(self):
        return self.market_price - (self.market_price * DECREASE_SALE_PRICE_PERCENTAGE)

    def calculate_profit(self, user_coin_balance):
        # if the user costs more than the user can afford then no profit can be made
        if self.get_max_buy_price() > user_coin_balance:
            self.profit = 0
        else:
            self.profit = self.market_price - self.get_sell_price()

    def player_json(self):
        return {
            'id': self.id,
            'name': self.name,
            'rating': self.rating,
            'revision': self.revision,
            'nation': self.nation,
            'position': self.position,
            'club': self.club,
            'player_image':self.player_image,
            'club_image': self.club_image,
            'nation_image': self.nation_image
        }