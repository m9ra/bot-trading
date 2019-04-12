from bot_trading.bots.predictors.predictor_base import PredictorBase
from bot_trading.trading.price_snapshot import PriceSnapshot
import numpy as np


class OraculumPredictor(PredictorBase):
    def _calculate_future_unit_values(self, present: PriceSnapshot):
        future = present.get_snapshot(seconds_back=-self.prediction_lookahead_seconds)

        noise = 0.000
        result = {}
        for currency in present.non_target_currencies:
            result[currency] = future.get_unit_value(currency) * np.random.uniform(1.0 - noise, 1.0 + noise)

        return result
