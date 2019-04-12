import random

from bot_trading.bots.bot_base import BotBase
from bot_trading.bots.predictors.predictor_base import PredictorBase
from bot_trading.trading.fund import Fund
from bot_trading.trading.portfolio_controller import PortfolioController
from bot_trading.trading.price_snapshot import PriceSnapshot
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

        if self._predictor._actual_unit_values:
            for currency in portfolio.non_target_currencies:
                fund = Fund(1.0, currency)
                predicted_value = self._predictor.get_value(fund).amount
                real_value = present.get_value(fund).amount

                print(f"E: {1 - (predicted_value / real_value):.4f} {currency}")

        self._predictor.recalculate_to(present)
        # todo retraining from time to time could be here (e.g. based on last training time)

        for fund in portfolio.funds:
            # profitable_fund = portfolio.get_fund_with(fund.currency, gain_greater_than=1.0005)
            # if not profitable_fund:
            #    if random.uniform(0.0, 1.0) < 0.9:
            #        continue  # don't make the trade yet (we are loosing anyway)

            best_currency = max(portfolio.currencies,
                                key=lambda currency: future_value(fund, currency, present, self._predictor))

            if best_currency == fund.currency:
                continue

            # predicted_value = future_value(fund, best_currency, present, self._predictor)
            # if fund.currency == portfolio.target_currency and fund.amount * 1.001 > predicted_value.amount:
            #    continue  # the gain is too small

            if fund.currency == portfolio.target_currency:
                fund = fund.soft_cap_to(200)

            if best_currency != portfolio.target_currency:
                if portfolio.get_fund_with(best_currency):
                    continue  # buy everything once at most

            portfolio.request_transfer(fund, best_currency)

    def get_parameters(self):
        return self._predictor.get_parameters()

    def set_parameters(self, parameters):
        return self._predictor.set_parameters(parameters)

    def eva_initialization(self, snapshot: PriceSnapshot):
        self._predictor.eva_initialization(snapshot, self.update_interval)
