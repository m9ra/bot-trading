import pickle
from copy import deepcopy
from typing import Dict, Set

from bot_trading.bots.bot_base import BotBase
from bot_trading.trading.portfolio_controller import PortfolioController
import numpy as np


class PrecalculatedStrategyBot(BotBase):
    def __init__(self, samples):
        super().__init__()

        self._samples = samples
        self._meta = self._samples["meta"]
        self._data = self._samples["data"]
        self._data_size = len(list(self._samples["data"].values())[0])
        self._sampling_period = self._meta["period_in_seconds"]
        self._start_time = self._meta["end_timestamp"] - self._meta["length_in_hours"] * 3600

        self._trade_per_hour_rate = 2.0
        self._trade_count = int(self._meta["length_in_hours"] * self._trade_per_hour_rate)

        self._parameters = []
        self._currencies = list(sorted(self._data.keys()))

        self._buy_strategy: Dict[Set[int]] = {}
        self._sell_strategy: Dict[Set[int]] = {}

    def calculate_strategy(self):
        for currency in self._currencies:
            print(f"strategy calculation for {currency}")
            b, s = self._calculate_strategy(currency)
            self._buy_strategy[currency] = set(b)
            self._sell_strategy[currency] = set(s)

    def _calculate_strategy(self, currency):
        c_data = self._data[currency]

        b = set()
        s = set()

        lookahead_seconds = 300
        lookahead = int(lookahead_seconds / self._sampling_period)
        last_index = len(c_data) - lookahead

        for i in range(last_index):
            if self._has_sell_indicator(i, c_data, lookahead):
                s.add(i)

        for i in range(last_index):
            if self._has_buy_indicator(i, s, c_data, lookahead):
                b.add(i)

        return b, s

    def _has_sell_indicator(self, i, c_data, lookahead):
        v_i = c_data[i]
        for k in range(lookahead):
            j = i + k
            v_j = c_data[j]

            spread_ratio = (v_j[1] - v_j[0]) / v_i[0]
            sell_ratio = v_j[0] / v_i[0]

            if 1.0 - spread_ratio > sell_ratio:
                return True

        return False

    def _has_buy_indicator(self, i, s, c_data, lookahead):
        v_i = c_data[i]
        for k in range(lookahead):
            j = i + k
            if j in s:
                return False  # sell is close, don't buy

            v_j = c_data[j]

            spread_ratio = (v_j[1] - v_j[0]) / v_i[1]
            buy_ratio = v_j[1] / v_i[1]

            if 1.0 + spread_ratio * 2 < buy_ratio:
                return True

    def _known_sell(self, i, sells, lookahead):
        for j in range(lookahead):
            if i + j in sells:
                return True

        return False

    def update_portfolio(self, portfolio: PortfolioController):
        current_time = portfolio.present.timestamp
        current_index = int((current_time - self._start_time) / self._sampling_period)

        # simulate imprecise detection
        interval_ticks = int(self.update_interval / self._sampling_period)
        current_index += np.random.random_integers(-interval_ticks, +interval_ticks)

        for fund in portfolio.funds:
            if fund.currency != portfolio.target_currency:
                if current_index in self._sell_strategy[fund.currency]:
                    portfolio.request_transfer(fund, portfolio.target_currency)
                continue

            for currency in self._currencies:
                if current_index in self._buy_strategy[currency]:
                    if portfolio.get_fund_with(currency):
                        continue

                    portfolio.request_transfer(fund.soft_cap_to(200), currency)
                    break

    def eva_initialization(self, snapshot):
        parameters = []
        for _ in self._currencies:
            parameters.append(np.zeros(self._trade_count * 2))

        self.set_parameters(parameters)

    def set_parameters(self, parameters):
        for currency, parameter in zip(self._currencies, parameters):
            self._buy_strategy[currency] = b = set()
            self._sell_strategy[currency] = s = set()
            if len(parameter) != self._trade_count * 2:
                raise AssertionError(f"Invalid parameter size {parameter.shape}")

            for i, p in enumerate(parameter):
                position = int(abs(p) * self._data_size)
                if i % 2 == 0:
                    b.add(position)
                else:
                    s.add(position)

        self._parameters = parameters

    def get_parameters(self):
        return self._parameters

    def plot(self):
        import matplotlib.pyplot as plt

        for currency in self._currencies:
            xs = range(len(self._data[currency]))

            ys = [ba[0] for ba in self._data[currency]]
            markers_on = list(filter(lambda x: x < len(self._data[currency]), (self._buy_strategy[currency])))
            plt.plot(xs, ys, '-gD', markevery=markers_on)
            plt.show()

            ys = [ba[1] for ba in self._data[currency]]
            markers_on = list(filter(lambda x: x < len(self._data[currency]), (self._sell_strategy[currency])))
            plt.plot(xs, ys, '-gD', markevery=markers_on)
            plt.show()

    def export_strategy(self, file):
        strategy = self.get_strategy_copy()

        data = pickle.dumps(strategy)
        with open(file, "wb") as f:
            f.write(data)

    def import_strategy(self, file):
        with open(file, "rb") as f:
            strategy = pickle.load(f)

            self._sell_strategy = strategy["sells"]
            self._buy_strategy = strategy["buys"]

    def get_strategy_copy(self):
        return {
            "sells": deepcopy(self._sell_strategy),
            "buys": deepcopy(self._buy_strategy)
        }

    def add_noise(self):
        for currency in self._sell_strategy:
            for i in range(1500):
                self._sell_strategy[currency].add(np.random.random_integers(0, self._data_size))
                self._buy_strategy[currency].add(np.random.random_integers(0, self._data_size))

                self._sell_strategy[currency].discard(np.random.random_integers(0, self._data_size))
                self._buy_strategy[currency].discard(np.random.random_integers(0, self._data_size))
