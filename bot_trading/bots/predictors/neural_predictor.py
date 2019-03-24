import tflearn

from bot_trading.bots.predictors.predictor_base import PredictorBase
from bot_trading.trading.price_snapshot import PriceSnapshot
import numpy as np

"""
This is a sketch of neural predictor 
- it can be run and it gives some predictions
- the coding need some more polishing 
"""


class NeuralPredictor(PredictorBase):
    def _run_training(self, snapshot: PriceSnapshot):
        training_data_length = 10000.0  # seconds into history that will be used for generating training data
        self.window_steps = 100  # how large window will be fed as the input
        self.sample_period = 5.0  # how long apart the window samples will be
        self.model_strength = 0.9  # inhibits strength of model predictions by keeping them close to current values
        self.target_factor = 1000  # is used for scaling output - this gives better loss readings

        training_start_snapshot = snapshot.get_snapshot(seconds_back=training_data_length)

        inputs = []
        targets = []
        for currency in training_start_snapshot.non_target_currencies:
            # collect history windows for all currencies
            cis, cts = self._get_normalized_windows(currency, training_start_snapshot)
            inputs.extend(cis)
            targets.extend(cts)

        # train model on pair window -> target (where target is the value after the predicted period)
        self._model = self._train_model(inputs, targets)

    def _get_prediction(self, samples):
        window, _ = self._normalize_data(samples)  # normalize in the same way as training data
        x = np.reshape(window, [-1, self.window_steps])
        y = self._model.predict(x)[0][0]

        denormalized_y = self._denormalize_target(samples, y)
        print(f"PREDICTION raw: {y}, denorm: {denormalized_y}")

        return denormalized_y

    def _train_model(self, input_windows, targets):

        train_x = np.reshape(input_windows, [-1, self.window_steps])
        train_y = np.reshape(targets, [-1, 1])

        # Network building
        net = tflearn.input_data(shape=[None, self.window_steps])
        # net = tflearn.lstm(net, n_units=32, return_seq=False)
        net = tflearn.fully_connected(net, 30, activation='sigmoid')
        net = tflearn.batch_normalization(net)
        net = tflearn.fully_connected(net, 10, activation='sigmoid')
        net = tflearn.fully_connected(net, 1, activation='linear')
        net = tflearn.regression(net, optimizer='adam', loss='mean_square', learning_rate=0.0001)

        # Training
        model = tflearn.DNN(net, tensorboard_verbose=0)
        model.fit(train_x, train_y, n_epoch=32, validation_set=0.1, batch_size=128, shuffle=True)

        return model

    def _calculate_future_unit_values(self, present: PriceSnapshot):
        history = present.get_snapshot(seconds_back=self.window_steps * self.sample_period)

        result = {}
        for currency in present.non_target_currencies:
            # get input data for the network - sample single window
            samples = history.get_unit_value_samples(currency, self.sample_period)
            model_value = self._get_prediction(samples)
            current_value = present.get_unit_value(currency)
            final_prediction = (1.0 - self.model_strength) * current_value + self.model_strength * model_value
            if model_value < current_value:
                final_prediction = model_value # don't underestimate low trends

            result[currency] = final_prediction  # store the prediction for further use

        return result

    def _denormalize_target(self, window, normalized_target):
        mean = np.mean(window)
        return normalized_target / self.target_factor * mean + mean

    def _normalize_data(self, window, target=None):
        result = np.array(window)
        mean = np.mean(window)

        if target is None:
            normalized_target = None
        else:
            normalized_target = (target - mean) / mean * self.target_factor

        return list((result - mean) / mean * self.target_factor), normalized_target

    def _get_normalized_windows(self, currency, training_snapshot: PriceSnapshot):
        value_samples = training_snapshot.get_unit_value_samples(currency, self.sample_period)
        input_windows = []
        targets = []

        lookahead = int(self.prediction_lookahead_seconds / self.sample_period)

        for i in range(self.window_steps, len(value_samples) - lookahead):
            target = value_samples[i + lookahead]
            window = (value_samples[i - self.window_steps:i])
            normalized_window, normalized_target = self._normalize_data(window, target)

            input_windows.append(normalized_window)
            targets.append(normalized_target)

        return input_windows, targets
