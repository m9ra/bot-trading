import operator

from bot_trading.bots.bot_base import BotBase
from bot_trading.trading.portfolio_controller import PortfolioController
from bot_trading.trading.utils import calculate_value_deltas, filter_currencies


class ComplexBaselineBot(BotBase):
    def __init__(self):
        super().__init__()

        # BOTS TUNABLE PARAMETERS

        # how often the bot will be called for portfolio update
        self.update_interval = 10.0  # [seconds]
        # how long history for delta value will be considered
        self.delta_history_seconds = 60
        # how big chunks will be traded (aproximate value)
        self.trade_chunk = 50  # [target currency]

        # EMERGENCY SELL OUTS
        # They are used when a fund with the configured gain decreased in value
        # If emergency is triggered, the detected funds are sold to target currency

        # how much gain non-target funds need to be allowed for next transfers
        self.min_repeat_trade_gain = 1.01  # [ratio]
        # min gain for fund to be applicable for emergency sell outs
        self.min_emergency_gain = 1.005  # [ratio]
        # largest delta that is not triggering emergency
        self.emergency_threshold_delta = -0.01  # [delta]

    def update_portfolio(self, portfolio: PortfolioController):

        history = portfolio.get_history(seconds_back=self.delta_history_seconds)
        present = portfolio.present

        if not history.is_available:
            # the requested history is not available (probably too far to the past?)
            return

        deltas = calculate_value_deltas(present, history)

        if self.try_request_emergency_transfers(portfolio, deltas):
            return  # don't trade anything more

        best_currency, best_delta = max(deltas.items(), key=operator.itemgetter(1))
        profitable_currency_delta = filter_currencies(deltas, portfolio, gain=self.min_repeat_trade_gain)
        if not profitable_currency_delta:
            # no profitable fund is available
            return

        # get worst currency that we have and have some gain already
        worst_currency, worst_delta = min(profitable_currency_delta.items(), key=operator.itemgetter(1))
        if worst_currency == best_currency:
            return  # no trade here

        source_fund = portfolio.get_fund_with(worst_currency, gain_greater_than=self.min_repeat_trade_gain)
        if source_fund.currency == portfolio.target_currency:
            source_fund = source_fund.soft_cap_to(self.trade_chunk)

        self._last_conversion_time = present.timestamp
        portfolio.request_transfer(source_fund, best_currency)

    def try_request_emergency_transfers(self, portfolio, deltas):
        has_emergency_transfer = False
        for fund in portfolio.get_funds_with(gain_greater_than=self.min_emergency_gain):
            if fund.currency == portfolio.target_currency:
                # target currency is not interesting for emergency
                continue

            if deltas.get(fund.currency) > self.emergency_threshold_delta:
                # no need for emergency
                continue

            # in case, something we have is going down transfer it to target_currency
            print(f"Emergency transfer for {fund}")
            portfolio.request_transfer(fund, portfolio.target_currency)
            has_emergency_transfer = True

        return has_emergency_transfer
