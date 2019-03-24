from bot_trading.bots.predictors.predictor_base import PredictorBase
from bot_trading.trading.price_snapshot import PriceSnapshot


class LinearPredictor(PredictorBase):
    def __init__(self, delta_scale: float):
        """
        :param delta_scale: Influences how much the difference between past and present influences predicted values
        """
        super().__init__()

        self._delta_scale = delta_scale

    def _run_training(self, snapshot: PriceSnapshot):
        pass  # no training is used in the linear predictor

    def _calculate_future_unit_values(self, present: PriceSnapshot):
        # we will look same time to the past as we need to predict to the future
        past = present.get_snapshot(seconds_back=self.prediction_lookahead_seconds)

        result = {}
        for currency in present.non_target_currencies:
            # calculate predictions for all relevant currencies
            current_value = present.get_unit_value(currency)
            past_value = past.get_unit_value(currency)
            delta = current_value - past_value

            # use linear interpolation for predictions
            predicted_value = current_value + delta * self._delta_scale

            result[currency] = predicted_value  # store the prediction for further use

        return result
