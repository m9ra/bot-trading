import random

from tflearn.callbacks import Callback

from bot_trading.bots.bot_base import BotBase
import numpy as np
import tflearn

from bot_trading.core.configuration import DUST_LEVEL
from bot_trading.trading.portfolio_controller import PortfolioController


class NeuralStrategyBot(BotBase):
    def __init__(self):
        super().__init__()

        self.verbose = False

    def save(self, file):
        self._model.save(file)
        np.save(file + ".normalizer", self._normalizer)

    def load(self, file, currencies, sampling_period):
        self.currencies = list(sorted(currencies))
        self.sampling_period = sampling_period

        self._model, self._normalizer = self.create_model()
        self._model.load(file)
        self._normalizer = np.load(file + ".normalizer.npy")

    def create_model(self):

        ## version 6
        # self.window_size = 200
        # self.step = [i * 20 for i in range(self.window_size)]

        # version 4
        self.window_size = 100
        self.step = [i + int(i * (1.07 ** i) / 50) for i in range(self.window_size)]

        # self.step = [i * 1 for i in range(self.window_size)]

        self.step_boundary = max(self.step)

        currencies_len = len(self.currencies)

        net = tflearn.input_data(shape=[None, self.window_size, 2 * currencies_len])
        # net = tflearn.reshape(net, (-1, self.window_size * 2 * currencies_len))
        # net = tflearn.lstm(net, 128)
        # net = tflearn.conv_1d(net, 1000, 5)
        # net = tflearn.max_pool_1d(net,5)
        # net = tflearn.conv_1d(net, 500, 5)

        net = tflearn.fully_connected(net, 5000, activation='sigmoid')
        net = tflearn.batch_normalization(net)
        net = tflearn.dropout(net, keep_prob=0.8)
        net = tflearn.fully_connected(net, 500, activation='sigmoid')
        net = tflearn.batch_normalization(net)
        net = tflearn.fully_connected(net, 100, activation='sigmoid')
        net = tflearn.batch_normalization(net)
        net = tflearn.fully_connected(net, 50, activation='sigmoid')
        net = tflearn.batch_normalization(net)
        net = tflearn.fully_connected(net, currencies_len, activation='tanh', bias=True)
        # net = tflearn.batch_normalization(net)
        net = tflearn.regression(net, optimizer='rmsprop', loss='mean_square', learning_rate=0.00001)

        # Training
        model = tflearn.DNN(net, tensorboard_verbose=0)

        normalizer = np.zeros(shape=(currencies_len, 2))

        return model, normalizer

    def update_portfolio(self, portfolio: PortfolioController):
        windows = []
        for i in range(1):
            window = self.get_formatted_window(portfolio.present.get_snapshot(seconds_back=i))
            windows.append(window)

        debug_output = []

        predictions = self._model.predict(windows)
        prediction = np.mean(predictions, axis=0)
        variance = np.var(predictions, axis=0)

        for i, currency in enumerate(self.currencies):
            opening_count = self._normalizer[0][i]
            closing_count = self._normalizer[1][i]
            total_count = opening_count + closing_count

            opening_limit = opening_count / total_count
            closing_limit = closing_count / total_count
            limit_factor = 1.0

            currency_signal = prediction[i]
            signal_variance = variance[i]
            fund = portfolio.get_fund_with(currency)
            profitable_fund = portfolio.get_fund_with(currency, gain_greater_than=1.001)

            open_threshold = opening_limit * limit_factor + signal_variance
            close_threshold = -closing_limit * limit_factor * 1.0
            open_threshold = min(0.9, open_threshold)
            close_threshold = min(0.9, close_threshold)
            if profitable_fund:
                close_threshold *= 0.3

            debug_output.append(f"{close_threshold:.3f} < {currency_signal:.3f} < {open_threshold:.3f} {currency}")

            if currency_signal < close_threshold and fund:
                portfolio.request_transfer(fund, portfolio.target_currency)
            elif currency_signal > open_threshold and not fund:
                budget = portfolio.get_fund_with(portfolio.target_currency)
                if not budget or budget.amount < DUST_LEVEL:
                    continue

                portfolio.request_transfer(budget.soft_cap_to(200.0), currency)

        if self.verbose:
            print(" | ".join(debug_output))

    def get_formatted_window(self, snapshot):
        window = np.empty(shape=(self.window_size, len(self.currencies) * 2))

        history = snapshot.get_snapshot(seconds_back=self.sampling_period * self.step_boundary)

        for currency_index, currency in enumerate(self.currencies):
            samples = history.get_unit_bid_ask_samples(currency, sampling_period=self.sampling_period)
            window_currency_index = currency_index * 2
            for i in range(self.window_size):
                bid_ask = samples[self.step[i]]
                window[i, window_currency_index] = bid_ask[0]
                window[i, window_currency_index + 1] = bid_ask[1]

        normalized_window = (window - window[0]) / window[0]
        return normalized_window

    def get_formatted_data(self, data, indexes, strategy):
        xs = []
        ys = []

        for index in indexes:
            window = np.empty(shape=(self.window_size, len(self.currencies) * 2))
            target = np.empty(shape=(len(self.currencies)))
            for currency_index, currency in enumerate(self.currencies):
                target[currency_index] = self.get_target(index, currency, strategy)

                window_currency_index = currency_index * 2
                for i in range(self.window_size):
                    bid_ask = data[currency][index - self.step_boundary + self.step[i]]
                    window[i, window_currency_index] = bid_ask[0]
                    window[i, window_currency_index + 1] = bid_ask[1]

            normalized_window = (window - window[0]) / window[0]
            xs.append(normalized_window)
            ys.append(target)

        return xs, ys

    def get_target(self, index, currency, strategy):
        if index in strategy["sells"][currency]:
            return -1.0

        if index in strategy["buys"][currency]:
            return 1.0

        return 0.0

    def fit(self, samples, strategy, file_path, validator=None):
        data = samples["data"]
        self.currencies = list(sorted(data))
        self.sampling_period = samples["meta"]["period_in_seconds"]

        self._model, self._normalizer = self.create_model()

        validation_sample_count = 1500
        training_sample_count = 150000

        # todo last samples do not have valid strategy (it did not have enought lookahead)

        data_length = len(next(iter(data.values())))

        data_point_indexes = list(sorted(random.sample(range(self.step_boundary, data_length),
                                                       training_sample_count + validation_sample_count)))
        validation_indexes = data_point_indexes[:validation_sample_count]
        training_indexes = data_point_indexes[validation_sample_count:]

        print("Data generation")
        t_xs, t_ys = self.get_formatted_data(data, training_indexes, strategy)
        v_xs, v_ys = self.get_formatted_data(data, validation_indexes, strategy)

        callbacks = []
        if file_path:
            callbacks.append(SaveCallback(self, file_path, validator))

        self._normalizer = np.array([np.sum(np.clip(t_ys, 0, 1), axis=0), np.sum(np.clip(t_ys, -1, 0), axis=0) * -1])
        self._model.fit(t_xs, t_ys, validation_set=(v_xs, v_ys), n_epoch=100, shuffle=True, callbacks=callbacks)


class SaveCallback(Callback):
    def __init__(self, bot, file_path, validator):
        super().__init__()
        self._bot = bot
        self._validator = validator
        self._file_path = file_path
        self._saved_val_loss = float("inf")

    def on_epoch_end(self, training_state):
        value = training_state.val_loss
        if self._validator:
            value = self._validator()

        if value < self._saved_val_loss:
            self._bot.save(self._file_path)
            self._saved_val_loss = value
            print(f"Model saved with value: {self._saved_val_loss}. Validation loss: {training_state.val_loss}.")
