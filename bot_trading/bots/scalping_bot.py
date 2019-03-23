from typing import Dict

from bot_trading.bots.bot_base import BotBase
from bot_trading.trading.fund import Fund
from bot_trading.trading.portfolio_controller import PortfolioController


class ScalpingBot(BotBase):
    def initialize(self, portfolio: PortfolioController):
        self.update_interval = 10

        self._last_stair_levels: Dict[str, float] = {}
        for currency in portfolio.non_target_currencies:
            self._last_stair_levels[currency] = portfolio.present.get_unit_cost(currency)

    def update_portfolio(self, portfolio: PortfolioController):
        single_buy_value = 10  # how much will be sent for every buy
        required_gain_threshold = 1.001  # how much the bought currency must gain in value to be sold
        stair_height = (required_gain_threshold - 1.0) * 2

        present = portfolio.present
        for currency in portfolio.non_target_currencies:
            # run scalping algorithm on every currency that can be bought by target currency

            current_level = present.get_unit_cost(currency)
            last_level = self._last_stair_levels[currency]

            # detect whether price stepped down/up the stair
            diff = current_level / last_level
            if diff < 1 - stair_height:
                # we stepped down the whole stair
                # we expect the price to go high after some time - lets buy
                if not portfolio.can_sell(single_buy_value, portfolio.target_currency):
                    continue  # we don't have enough to buy

                self._last_stair_levels[currency] = current_level  # update last level
                portfolio.request_transfer(Fund(single_buy_value, portfolio.target_currency), currency)

            elif not portfolio.get_funds(currency):
                # no pending funds - move upstairs freely
                self._last_stair_levels[currency] = max(last_level, current_level)

        # scalp all the profitable funds we collected
        for fund in portfolio.get_funds_with(gain_greater_than=required_gain_threshold):
            if fund.currency == portfolio.target_currency:
                continue  # target fund can't be converted to target again :)

            portfolio.request_transfer(fund, portfolio.target_currency)
            self._last_stair_levels[fund.currency] = present.get_unit_cost(fund.currency)
