import random

from bots.bot_base import BotBase
from trading.portfolio_controller import PortfolioController


class RandomBot(BotBase):
    def update_portfolio(self, portfolio: PortfolioController):
        history = portfolio.get_history2(seconds_back=60)
        present = portfolio.get_history2(seconds_back=0)

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

        source_fund = random.choice(portfolio.funds)
        if source_fund.currency != best_currency:
            portfolio.request_conversion(source_fund / 2, best_currency)
            pass
