from collections import defaultdict
from copy import deepcopy
from typing import Optional

from bot_trading.core.configuration import DUST_LEVEL
from bot_trading.core.exceptions import PortfolioUpdateException
from bot_trading.trading.fund import Fund


class FastPortfolio(object):
    def __init__(self, samples, initial_amount: float, target_currency: str):
        self._samples = samples
        self._prices = samples["data"]
        self._current_tick: Optional[int] = None
        self._tick_duration = samples["meta"]["period_in_seconds"]
        self._start_time = samples["meta"]["end_timestamp"] - samples["meta"]["length_in_hours"] * 3600

        self._positions = defaultdict(FastPosition)
        self._positions[target_currency].set(initial_amount)
        self.target_currency = target_currency
        self._non_target_currencies = list(self._prices.keys())
        self._currencies = self._non_target_currencies + [self.target_currency]

    def get_copy(self):
        copy = FastPortfolio(self._samples, 0, self.target_currency)
        copy.set_tick(self._current_tick)
        copy._positions = deepcopy(self._positions)

        return copy

    def set_tick(self, tick: int):
        self._current_tick = tick

    @property
    def present(self):
        return FastSnapshot(self, self._current_tick)

    @property
    def currencies(self):
        return list(self._currencies)

    @property
    def non_target_currencies(self):
        return list(self._non_target_currencies)

    @property
    def funds(self):
        result = []
        for currency, position in self._positions.items():
            result.append(Fund(position.amount, currency))

        return result

    @property
    def total_value(self):
        value = 0.0
        for currency, position in self._positions.items():
            currency_value = self._sell_to_target(position.amount, currency, self._current_tick)
            value += currency_value

        return value

    def get_history(self, seconds_back):
        return FastSnapshot(self, self._current_tick - int(seconds_back / self._tick_duration))

    def get_fund_with(self, currency, gain_greater_than: float = 0.0, force_include_target=True) -> Optional[Fund]:
        position = self._positions[currency]
        if position.amount <= DUST_LEVEL:
            return None

        if force_include_target and currency == self.target_currency:
            return Fund(position.amount, currency)

        current_value = self._sell_to_target(position.amount, currency, self._current_tick)
        if current_value < position.initial_value * gain_greater_than:
            return None

        return Fund(position.amount, currency)

    def request_transfer(self, fund, currency):
        value = self._sell_to_target(fund.amount, fund.currency, self._current_tick)

        if fund.amount > self._positions[fund.currency].amount:
            raise PortfolioUpdateException(f"Requested {fund} but only have {self._positions[fund.currency].amount}")

        self._positions[fund.currency].amount -= fund.amount
        if self._positions[fund.currency].amount <= DUST_LEVEL:
            del self._positions[fund.currency]
        else:
            self._positions[fund.currency].initial_value -= value

        converted = self.present.after_conversion(fund, currency)
        converted_amount = converted.amount
        if converted.currency == self.target_currency:
            value = converted_amount  # reset value for target currency

        self._positions[converted.currency].amount += converted_amount
        self._positions[converted.currency].initial_value += value

        rev_converted = self.present.after_conversion(converted, fund.currency)
        print(f"\t {fund} -> {converted} | {rev_converted}")

    def _sell_to_target(self, amount, currency, current_tick):
        if currency == self.target_currency:
            return amount

        price = self._prices[currency][current_tick][0]
        return amount * price

    def _buy_for_target(self, amount, currency, current_tick):
        price = self._prices[currency][current_tick][1]
        return amount / price


class FastSnapshot(object):
    def __init__(self, fast_portfolio, current_tick):
        if current_tick < 0:
            raise TickNotAvailableException(-current_tick)

        self._fast_portfolio = fast_portfolio
        self._current_tick = current_tick

    @property
    def timestamp(self):
        return self._fast_portfolio._tick_duration * self._current_tick + self._fast_portfolio._start_time

    @property
    def target_currency(self):
        return self._fast_portfolio.target_currency

    @property
    def non_target_currencies(self):
        return self._fast_portfolio.non_target_currencies

    def get_snapshot(self, seconds_back: float):
        ticks_back = int(seconds_back / self._fast_portfolio._tick_duration)
        return FastSnapshot(self._fast_portfolio, self._current_tick - ticks_back)

    def get_unit_value(self, currency):
        return self._fast_portfolio._prices[currency][self._current_tick][0]

    def get_unit_bid_ask_samples(self, currency, sampling_period):
        tick_duration = self._fast_portfolio._tick_duration
        sampling_step = int(sampling_period / tick_duration)
        sampling_error = sampling_period % tick_duration

        if abs(sampling_error) > 1e-5:
            raise AssertionError(f"Non-consistent sampling period {tick_duration} vs {sampling_period}")

        result = []

        i = self._current_tick
        while i <= self._fast_portfolio._current_tick:
            bid_ask = self._fast_portfolio._prices[currency][i]
            result.append(bid_ask)

            i += sampling_step

        return result

    def get_value(self, fund):
        return Fund(self._fast_portfolio._sell_to_target(fund.amount, fund.currency, self._current_tick),
                    self.target_currency)

    def after_conversion(self, fund, target_currency):
        if fund.currency == target_currency:
            return fund

        if fund.currency == self._fast_portfolio.target_currency:
            converted_amount = self._fast_portfolio._buy_for_target(fund.amount, target_currency, self._current_tick)
        else:
            converted_amount = self._fast_portfolio._sell_to_target(fund.amount, fund.currency, self._current_tick)
            if target_currency != self._fast_portfolio.target_currency:
                # complex transfers will be always done via target currency
                converted_amount = self._fast_portfolio._buy_for_target(converted_amount, target_currency,
                                                                        self._current_tick)

        return Fund(converted_amount, target_currency)


class TickNotAvailableException(Exception):
    def __init__(self, tick):
        super().__init__(f"Tick {tick} is not available")
        self.missing_tick = tick


class FastPosition(object):
    def __init__(self):
        self.amount = 0
        self.initial_value = 0

    def set(self, amount):
        self.amount = amount
        self.initial_value = amount

    def __repr__(self):
        return f"{self.amount}"
