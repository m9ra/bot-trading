import random

from bots.bot_base import BotBase
from trading.portfolio_controller import PortfolioController


class RandomBot(BotBase):
    def update_portfolio(self, portfolio: PortfolioController):
        history = portfolio.get_history(seconds_back=60)
        present = portfolio.get_history(seconds_back=0)

        if not present.is_available:
            present = portfolio.get_history(seconds_back=0)
            present.is_available
            raise AssertionError("wtf")

        if not history.is_available:
            # the requested history is not available (probably too long to the past?)
            return

        best_delta = None
        best_currency = None
        for currency in portfolio.currencies:
            price_delta = present.get_unit_value(currency) - history.get_unit_value(currency)
            if best_delta is None or price_delta > best_delta:
                best_delta = price_delta
                best_currency = currency

        funds = portfolio.profitable_funds
        if not funds:
            return  # there is no profitable fund that could be used now

        source_fund = random.choice(funds)
        if source_fund.currency != best_currency:
            #if source_fund.currency == portfolio.target_currency:
            #    source_fund = source_fund / 10  # dont trade everything at once

            portfolio.request_conversion(source_fund, best_currency)
