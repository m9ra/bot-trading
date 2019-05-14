from typing import List

from bot_trading.core.configuration import BOOK_DEPTH, DUST_LEVEL
from bot_trading.core.data.trade_entry import TradeEntry
from bot_trading.core.processors.processor_base import ProcessorBase


class PricebookProcessor(ProcessorBase):
    def __init__(self, pair):
        self._pair = pair
        self._sell_container = None
        self._buy_container = None
        self._current_time = 0.0
        self._is_ready = False

        self._buffer: List[TradeEntry] = []

    @property
    def is_ready(self):
        return self._sell_container is not None and self._buy_container is not None

    @property
    def is_book_available(self):
        return self._buy_container and self._sell_container

    @property
    def current_time(self):
        return self._current_time

    @property
    def buy_levels(self):
        return self._get_levels(self._buy_container, True)

    @property
    def sell_levels(self):
        return list(reversed(self._get_levels(self._sell_container, False)))

    @property
    def spread(self):
        bid_ask = self.bid_ask
        return max(0.0, bid_ask[1] - bid_ask[0])

    @property
    def bid_ask(self):
        max_b = max(self._buy_container)
        min_b = min(self._sell_container)

        return [max_b, min_b]

    @property
    def current_depth(self):
        return min(len(self._buy_container), len(self._sell_container))

    def accept(self, entry):
        self._buffer.append(entry)

        if entry.is_flush_entry:
            self.flush()

    def reset(self, is_buy):
        self._buy_container = {}
        self._sell_container = {}

    def write(self, is_buy, price, amount, timestamp):
        self._current_time = max(self._current_time, timestamp)
        if is_buy:
            container = self._buy_container
        else:
            container = self._sell_container

        if amount <= DUST_LEVEL:
            if price in container:
                del container[price]
        else:
            container[price] = (amount, timestamp)

        if len(container) > BOOK_DEPTH:
            if is_buy:
                last_key = min(container.keys())
            else:
                last_key = max(container.keys())

            del container[last_key]

    def flush(self):
        for entry in self._buffer:
            super().accept(entry)

        self._buffer = []

    def inject(self, buy_container, sell_container, buffer):
        self._buy_container = buy_container
        self._sell_container = sell_container
        self._buffer = buffer

    def get_dump(self):
        return self._buy_container, self._sell_container, self._buffer

    def _get_levels(self, container, increasing_accumulation):
        borders = sorted(container.items(), key=lambda i: i[0], reverse=increasing_accumulation)

        acc = 0.0
        for i in range(len(borders)):
            border_value = borders[i][1][0]
            acc += border_value
            new_border = list(borders[i])
            new_border[1] = acc
            borders[i] = tuple(new_border + [border_value])

        return borders

    def dump_to_entries(self) -> List[TradeEntry]:
        result = []
        result.extend(self._dump_container(self._buy_container, is_buy=True, is_index_entry=True))
        result.extend(self._dump_container(self._sell_container, is_buy=False, is_index_entry=False))

        if result:
            result[-1].is_flush_entry = True

        return result

    def _dump_container(self, container, is_buy, is_index_entry):
        if is_index_entry:
            # one of the buy/sell service entries will be used as top level index
            yield TradeEntry.create_entry(self._pair, is_buy, 0.0, 0.0, self._current_time, is_reset=True,
                                          is_flush=False)

        if container is None:
            return

        for price, (volume, timestamp) in container.items():
            yield TradeEntry.create_entry(self._pair, is_buy, price, volume, timestamp, is_reset=False, is_flush=False)

    def print_pricebook(self):
        sell_levels = self.sell_levels
        buy_levels = self.buy_levels
        print(f"PRICEBOOK {self._pair}")
        print("SELLS")
        for sell in sell_levels:
            print(f"\t {sell}")

        print("BUYS")
        for buy in buy_levels:
            print(f"\t {buy}")
