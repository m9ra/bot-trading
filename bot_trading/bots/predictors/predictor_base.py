from typing import Dict

from bot_trading.trading.fund import Fund
from bot_trading.trading.price_snapshot import PriceSnapshot


class PredictorBase(object):
    def __init__(self):
        self.target_currency: str = None  # which currency expresses value
        self.prediction_lookahead_seconds: float = None  # how far into future predictor has to look

        self._actual_unit_values: Dict[str, float] = None

    def _run_training(self, snapshot: PriceSnapshot):
        pass

    def _calculate_future_unit_values(self, present: PriceSnapshot) -> Dict[str, float]:
        raise NotImplementedError("must be overridden")

    def train(self, snapshot: PriceSnapshot, prediction_lookahead_seconds: float):
        """
        Train predictor on given snapshot.
        The predictor is supposed to start answer requests that are prediction_lookahead_seconds in the future
        """
        self.target_currency = snapshot.target_currency
        self.prediction_lookahead_seconds = prediction_lookahead_seconds

        self._run_training(snapshot)

    def recalculate_to(self, present: PriceSnapshot):
        """
        Recalculates predictions according to given snapshot of prices.
        """

        future_values = self._calculate_future_unit_values(present)
        self._actual_unit_values = dict(future_values)

    def get_value(self, fund):
        if fund.currency == self.target_currency:
            return fund  # value of target currency can't change because value is relative to target currency

        if self.target_currency is None:
            raise AssertionError("target_currency is not initialized")

        predicted_value = self._actual_unit_values[fund.currency] * fund.amount
        return Fund(predicted_value, self.target_currency)
