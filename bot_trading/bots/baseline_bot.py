import operator

from bot_trading.bots.bot_base import BotBase
from bot_trading.trading.portfolio_controller import PortfolioController
from bot_trading.trading.utils import calculate_price_deltas, filter_currencies


class BaselineBot(BotBase):
    def __init__(self):
        super().__init__()
        self._last_conversion_time = None

    def update_portfolio(self, portfolio: PortfolioController):
        history = portfolio.get_history(seconds_back=60)
        present = portfolio.get_history(seconds_back=0)
        min_trade_back_gain = 1.01  # don't trade currencies that did not reached the gain yet

        if not history.is_available:
            # the requested history is not available (probably too far to the past?)
            return

        for fund in portfolio.get_funds_with(gain_greater_than=1.05, force_include_target=False):
            # in case something is making profit, cash it back
            print(f"Cash back {fund}")
            print(portfolio._current_portfolio_state)
            portfolio.request_conversion(fund, portfolio.target_currency)
            return

        deltas = calculate_price_deltas(present, history)
        best_currency, best_delta = max(deltas.items(), key=operator.itemgetter(1))

        profitable_currency_delta = filter_currencies(deltas, portfolio, gain=min_trade_back_gain)
        if not profitable_currency_delta:
            # no profitable fund is available
            return

        # get worst currency that we have and have some gain already
        worst_currency, worst_delta = min(profitable_currency_delta.items(), key=operator.itemgetter(1))
        if worst_currency == best_currency:
            return  # no trade here

        source_fund = portfolio.get_fund_with(worst_currency, gain_greater_than=min_trade_back_gain)
        if source_fund.currency == portfolio.target_currency:
            source_fund = source_fund.soft_cap_to(50)

        self._last_conversion_time = present.timestamp
        portfolio.request_conversion(source_fund, best_currency)
