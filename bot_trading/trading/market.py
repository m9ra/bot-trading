import time
from threading import Thread
from typing import List

from bot_trading.core.data.parsing import parse_pair, make_pair
from bot_trading.trading.connector_base import ConnectorBase
from bot_trading.trading.currency_history import CurrencyHistory
from bot_trading.trading.fund import Fund
from bot_trading.trading.peek_connector import PeekConnector


class Market(object):
    def __init__(self, target_currency: str, currency_pairs: List[str], connector: ConnectorBase):
        self._target_currency = target_currency
        self._currencies = set()
        self._currency_pairs = set()
        self._connector = connector

        for pair in currency_pairs:
            self._currency_pairs.add(pair)
            self._currencies.update(parse_pair(pair))

    @property
    def currencies(self):
        return list(self._currencies)

    @property
    def non_target_currencies(self):
        result = self.currencies
        result.remove(self.target_currency)
        return result

    @property
    def direct_currency_pairs(self):
        return self._currency_pairs

    @property
    def target_currency(self):
        return self._target_currency

    @property
    def current_time(self):
        return self._connector.current_time

    @property
    def present(self):
        # todo this should be optimized
        return self.get_history(0)

    def has_currency(self, currency):
        return currency in self._currencies

    def get_history(self, seconds_back: float) -> CurrencyHistory:
        if seconds_back < 0 and isinstance(self._connector, PeekConnector):
            raise AssertionError("Can request only history (not future) for PeekConnector")

        history = CurrencyHistory(self, self._connector)
        history.set_time(self.current_time - seconds_back)

        return history

    def validate_currencies(self, *currencies):
        for currency in currencies:
            if isinstance(currency, Fund):
                currency = currency.currency

            if not self.has_currency(currency):
                raise ValueError(f"Currency {currency} is not a tradable currency.")

    def get_transfer_path(self, source_currency, target_currency) -> List[str]:
        """
        Gets path of all currencies that has to be traded to issue transfer between source and target currencies
        NOTE: Not all currency pairs can be traded directly.
        """
        self.validate_currencies(source_currency, target_currency)
        if source_currency == target_currency:
            return [source_currency]

        pair = make_pair(source_currency, target_currency)
        pair_reversed = make_pair(target_currency, source_currency)

        if pair in self.direct_currency_pairs or pair_reversed in self.direct_currency_pairs:
            return [source_currency, target_currency]

        return [source_currency, self.target_currency, target_currency]

    def get_value(self, amount, currency):
        return self.get_history(0).get_value(Fund(amount, currency))

    def subscribe(self, subscriber):
        self._connector.subscribe(subscriber)

    def run(self):
        self._connector.run()

    def run_async(self):
        Thread(target=self.run, daemon=True).start()
        while not self.present.is_available:
            time.sleep(0.1)
