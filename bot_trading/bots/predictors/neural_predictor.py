import os

import tflearn
from typing import List

from bot_trading.bots.predictors.predictor_base import PredictorBase
from bot_trading.trading.price_snapshot import PriceSnapshot
import numpy as np
import tensorflow as tf

"""
This is a sketch of neural predictor 
- it can be run and it gives some predictions
- the coding need some more polishing 
"""


class NeuralPredictor(PredictorBase):
    def __init__(self, name):
        super(NeuralPredictor, self).__init__()
        self.model_name = f"trained_models/{name}"
        self.training_data_length = 30000.0  # seconds into history that will be used for generating training data
        self.window_steps = 100  # how large window will be fed as the input
        self.sample_period = 0.1  # how long apart the window samples will be
        self.model_strength = 1.0  # inhibits strength of model predictions by keeping them close to current values
        self.target_factor = 1000.0  # is used for scaling output - this gives better loss readings
        self.lookahead = 10
        self._model = None
        self.currencies: List[str] = None

    def _run_training(self, snapshot: PriceSnapshot):
        # train model on pair window -> target (where target is the value after the predicted period)

        self.currencies = list(sorted(snapshot.non_target_currencies))
        self._model = self._get_model(snapshot)

    def _get_model(self, snapshot):
        load_model = self.model_name and os.path.exists(self.model_name + ".index")

        currencies_len = len(self.currencies)

        # Network building
        net = tflearn.input_data(shape=[None, 2 * self.window_steps * currencies_len])
        net = gaussian_noise_layer(net, 0.001)

        net = tflearn.fully_connected(net, 300, activation='sigmoid')
        net = tflearn.batch_normalization(net)
        net = tf.expand_dims(net, axis=-1)
        net = tflearn.conv_1d(net, 64, 5)
        net = tflearn.fully_connected(net, 50, activation='sigmoid')
        net = tflearn.batch_normalization(net)
        net = tflearn.fully_connected(net, 30, activation='sigmoid')
        net = tflearn.batch_normalization(net)
        net = tflearn.fully_connected(net, currencies_len, activation='linear')
        net = tflearn.regression(net, optimizer='adam', loss='mean_square', learning_rate=0.0005)

        # Training
        model = tflearn.DNN(net, tensorboard_verbose=0)

        if load_model:
            model.load(self.model_name)
            return model

        if snapshot is None:
            return model  # training is skipped

        print("TRAINING MODEL")

        training_start_snapshot = snapshot.get_snapshot(seconds_back=self.training_data_length)

        c_samples = []
        c_targets = []
        for currency in self.currencies:
            samples = training_start_snapshot.get_unit_bid_ask_samples(currency, sampling_period=self.sample_period)
            c_sample = []
            c_target = []

            lookahead = int(self.lookahead / self.sample_period)
            for i in range(self.window_steps, len(samples) - lookahead, self.window_steps // 3):
                target = samples[i + lookahead][0] # direct target
                # target = np.sign(np.max([s[0] for s in samples[i:i + lookahead]]) - samples[i][0]) * samples[i][
                #    0] * 0.01 + samples[i][0]
                #target = np.max([s[0] for s in samples[i:i + lookahead]])
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

        xs = [x[0]] * 100
        ys = self._model.predict(xs)
        y = np.median(ys, axis=0)

        prediction = []
        for i in range(len(y)):
            raw_y = y[i]
            sample = c_sample[i]
            sample_mean = np.mean(sample)
            prediction.append((raw_y / self.target_factor) * sample_mean + sample_mean)

            # print(f"PREDICTION raw: {raw_y}, denorm: {prediction[-1]}")

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

            # print(f"diff {currency}: {model_value - current_value}")
            result[currency] = final_prediction

        return result

    def eva_initialization(self, snapshot: PriceSnapshot, prediction_lookahead_seconds: float):
        self.target_currency = snapshot.target_currency
        self.prediction_lookahead_seconds = prediction_lookahead_seconds
        self.currencies = list(sorted(snapshot.non_target_currencies))
        self._model = self._get_model(snapshot)
        self._assigners = None

    def get_parameters(self):
        if not self._model:
            self._model = self._get_model(None)

        result = []
        for variable in self._model.get_train_vars():
            result.append(self._model.get_weights(variable))
        return result

    def set_parameters(self, parameters):
        if not self._assigners:
            self._assigners = []
            for var in self._model.get_train_vars():
                placeholder = tf.placeholder(var.dtype, shape=var.shape)
                self._assigners.append((placeholder, tf.assign(var, placeholder)))

        for assigner, parameter in zip(self._assigners, parameters):
            self._model.session.run(assigner[1], feed_dict={assigner[0]: parameter})


def gaussian_noise_layer(input_layer, std):
    noise = tf.random_normal(shape=tf.shape(input_layer), mean=0.0, stddev=std, dtype=tf.float32)
    return input_layer + noise
