from bot_trading.bots.predictors.predictor_base import PredictorBase
from bot_trading.trading.price_snapshot import PriceSnapshot
from sklearn.linear_model import LinearRegression
import numpy as np


class LinearPredictor(PredictorBase):
    def __init__(self, delta_scale: float):
        """
        :param delta_scale: Influences how much the difference between past and present influences predicted values
        """
        super().__init__()

        self._delta_scale = delta_scale*20
        self._prediction_distance = 1.1
        self._strength = 1.0

    def _run_training(self, snapshot: PriceSnapshot):
        self._lookahead = self.prediction_lookahead_seconds

    def _calculate_future_unit_values(self, present: PriceSnapshot):
        # we will look same time to the past as we need to predict to the future
        past = present.get_snapshot(seconds_back=self._lookahead)

        lm = LinearRegression()

        currencies = sorted(present.non_target_currencies)
        all_samples = []
        for currency in currencies:
            # calculate predictions for all relevant currencies
            samples = past.get_unit_value_samples(currency, 0.1)
            all_samples.append(samples)

        ys = list(map(list, zip(*all_samples)))
        xs = np.reshape(list((range(len(ys)))), [-1, 1])
        lm.fit(xs, np.reshape(ys, [-1, len(currencies)]))
        model_values, = lm.predict([[len(ys) * self._prediction_distance]])

        result = {}
        for currency, model_value in zip(currencies, model_values):
            current_value = present.get_unit_value(currency)

            predicted_value = model_value * self._strength + current_value * (1.0 - self._strength)

            # print(f"Currency: {predicted_value} {currency}")
            result[currency] = predicted_value  # store the prediction for further use

        return result

    def eva_initialization(self, snapshot, update_interval):
        self._lookahead = update_interval * 2
        self.target_currency = snapshot.target_currency

    def get_parameters(self):
        return [np.array([self._lookahead, self._prediction_distance, self._strength])]

    def set_parameters(self, parameters):
        self._lookahead, self._prediction_distance, self._strength = parameters[0]
        self._lookahead = max(10.0, min(100.0, self._lookahead))
        self._prediction_distance = max(0.1, min(100, self._prediction_distance))
        self._strength = max(-1.0, min(1.0, self._strength))
