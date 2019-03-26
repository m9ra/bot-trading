import random

from bot_trading.bots.bot_base import BotBase
from bot_trading.bots.predictors.predictor_base import PredictorBase
from bot_trading.trading.portfolio_controller import PortfolioController
from bot_trading.trading.utils import future_value


class PredictorBot(BotBase):
    def __init__(self, predictor: PredictorBase, prediction_lookahead=10):
        super().__init__()

        self.update_interval = prediction_lookahead
        self._predictor = predictor

    def initialize(self, portfolio: PortfolioController):
        self._predictor.train(portfolio.present, self.update_interval)

    def update_portfolio(self, portfolio: PortfolioController):
        present = portfolio.present
        self._predictor.recalculate_to(present)
        # todo retraining from time to time could be here (e.g. based on last training time)

        for fund in portfolio.funds:
            best_currency = max(portfolio.currencies,
                                key=lambda currency: future_value(fund, currency, present, self._predictor))

            if best_currency != fund.currency:
                if fund.currency == portfolio.target_currency:
                    fund = fund.soft_cap_to(100)

                else:
                    profitable_fund = portfolio.get_fund_with(fund.currency, gain_greater_than=1.0005)
                    if not profitable_fund:
                        if random.uniform(0.0, 1.0) < 0.95:
                            continue  # don't make the trade yet (we are loosing anyway)

                portfolio.request_transfer(fund, best_currency)
