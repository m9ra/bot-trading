from typing import Dict

from bot_trading.core.data.trade_entry import TradeEntry
from bot_trading.core.processors.pricebook_processor import PricebookProcessor
from bot_trading.core.processors.processor_base import ProcessorBase


class VerificationProcessor(ProcessorBase):
    def __init__(self, pair):
        self._p1 = PricebookProcessor(pair)
        self._p2 = PricebookProcessor(pair)
        self._entries = []
        self._network_log = []
        self._last_entry = None
        self._is_invalid = False
        self._is_invalid_candidate = False
        self._invalidation_before = 0

    def log_network_data(self, data_obj):
        self._check_validity()

        self._network_log.append(data_obj)

        if self._is_invalid:
            print(data_obj)

    def accept(self, entry: TradeEntry):
        self._entries.append(entry)
        while len(self._entries) > 100:
            self._entries.pop(0)

        self._p1.accept(entry)
        if self._last_entry:
            self._p2.accept(self._last_entry)

        self._last_entry = entry

        if self._invalidation_before > 100:
            self._is_invalid = False
            self._invalidation_before = 0
            raise NotImplementedError("stop please")

        if self._is_invalid:
            self._invalidation_before += 1
            print(entry)

        if not self._p1.is_ready:
            return

        sells = self._p1.sell_levels
        buys = self._p1.buy_levels

        if not buys or not sells:
            return

        self._is_invalid_candidate = sells[-1][0] < buys[0][0]

    def _check_validity(self):
        if self._is_invalid_candidate and not self._is_invalid:
            self._is_invalid = True

            print("NETWORK LOG")
            for data_obj in self._network_log:
                print(data_obj)

            print("ENTRIES")
            for entry in self._entries:
                print(entry)

            print("OLD")
            self._p2.print_pricebook()
            print("INVALID")
            self._p1.print_pricebook()

            self._entries.clear()
            self._network_log.clear()

    def write(self, is_buy: bool, price: float, volume: float, timestamp: float):
        self.accept(TradeEntry.create_entry(self._p1._pair, is_buy, price, volume, timestamp, False, False))

    def reset(self, is_buy: bool):
        self.accept(TradeEntry.create_entry(self._p1._pair, is_buy, 0.0, 0.0, 0.0, True, False))
