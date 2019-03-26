import os

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
        self.training_data_length = 200000.0  # seconds into history that will be used for generating training data
        self.window_steps = 100  # how large window will be fed as the input
        self.sample_period = 5.0  # how long apart the window samples will be
        self.model_strength = 0.2  # inhibits strength of model predictions by keeping them close to current values
        self.target_factor = 1000.0  # is used for scaling output - this gives better loss readings
        self.model_name = "trained_models/model_10s4"

        self.currencies = list(sorted(snapshot.non_target_currencies))

        # train model on pair window -> target (where target is the value after the predicted period)
        self._model = self._get_model(snapshot)

    def _get_model(self, snapshot):
        currencies_len = len(self.currencies)

        # Network building
        net = tflearn.input_data(shape=[None, 2 * self.window_steps * currencies_len])

        net = tflearn.fully_connected(net, 200, activation='sigmoid')
        net = tflearn.batch_normalization(net)
        net = tflearn.fully_connected(net, 50, activation='sigmoid')
        net = tflearn.batch_normalization(net)
        net = tflearn.fully_connected(net, 10, activation='sigmoid')
        net = tflearn.batch_normalization(net)
        net = tflearn.fully_connected(net, currencies_len, activation='linear')
        net = tflearn.regression(net, optimizer='adam', loss='mean_square', learning_rate=0.002)

        # Training
        model = tflearn.DNN(net, tensorboard_verbose=0)

        if self.model_name and os.path.exists(self.model_name + ".index"):
            model.load(self.model_name)
            return model

        print("TRAINING MODEL")

        training_start_snapshot = snapshot.get_snapshot(seconds_back=self.training_data_length)

        c_samples = []
        c_targets = []
        for currency in self.currencies:
            samples = training_start_snapshot.get_unit_bid_ask_samples(currency, sampling_period=self.sample_period)
            c_sample = []
            c_target = []

            lookahead = int(self.prediction_lookahead_seconds / self.sample_period) * 6
            for i in range(self.window_steps, len(samples) - lookahead, self.window_steps // 3):
                # target = samples[i + lookahead][0] # direct target
                target = max(s[0] for s in samples[i:i + lookahead])
                sample = samples[i - self.window_steps:i]
                c_sample.append(sample)
                c_target.append(target)

            c_samples.append(c_sample)
            c_targets.append(c_target)

        train_x = self._get_inputs(c_samples)
        train_y = self._get_targets(c_samples, c_targets)

        train_x, train_y = tflearn.data_utils.shuffle(train_x, train_y)

        model.fit(train_x, train_y, n_epoch=200, validation_set=0.1, batch_size=128, shuffle=True)
        if self.model_name:
            model.save(self.model_name)

        return model

    def _get_prediction(self, c_sample):
        x = self._get_inputs([c_sample])
        y = self._model.predict(x)[0]

        prediction = []
        for i in range(len(y)):
            raw_y = y[i]
            sample = c_sample[i]
            sample_mean = np.mean(sample)
            prediction.append((raw_y / self.target_factor) * sample_mean + sample_mean)

            print(f"PREDICTION raw: {raw_y}, denorm: {prediction[-1]}")

        return prediction

    def _get_targets(self, c_samples, c_targets):
        currencies_len = len(self.currencies)

        normalized_all = []
        for c_sample, c_target in zip(c_samples, c_targets):
            normalized = []
            normalized_all.append(normalized)
            for sample, target in zip(c_sample, c_target):
                sample_mean = np.mean(sample)
                norm = (target - sample_mean) / sample_mean * self.target_factor
                normalized.append(norm)

        y = np.reshape(np.swapaxes(normalized_all, 0, 1), [-1, currencies_len])
        return y

    def _get_inputs(self, c_samples):
        currencies_len = len(self.currencies)

        normalized_all = []
        for c_sample in c_samples:
            normalized = []
            normalized_all.append(normalized)
            for sample in c_sample:
                sample_mean = np.mean(sample)
                norm = (sample - sample_mean) / sample_mean
                normalized.append(norm)

        x = np.reshape(np.swapaxes(normalized_all, 0, 1), [-1, 2 * self.window_steps * currencies_len])
        return x

    def _calculate_future_unit_values(self, present: PriceSnapshot):
        history = present.get_snapshot(seconds_back=self.window_steps * self.sample_period)
        c_input = []
        for currency in self.currencies:
            samples = history.get_unit_bid_ask_samples(currency, sampling_period=self.sample_period)
            samples = samples[-self.window_steps:]
            c_input.append(samples)

        predictions = self._get_prediction(c_input)

        result = {}
        for i, currency in enumerate(self.currencies):
            model_value = predictions[i]
            current_value = present.get_unit_value(currency)
            final_prediction = (1.0 - self.model_strength) * current_value + self.model_strength * model_value
            # if model_value < current_value:
            #    final_prediction = model_value  # don't underestimate low trends

            print(f"diff {currency}: {model_value - current_value}")
            result[currency] = final_prediction

        return result
