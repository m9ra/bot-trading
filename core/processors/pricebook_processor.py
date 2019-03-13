from typing import List

from configuration import BOOK_DEPTH
from core.processors.processor_base import ProcessorBase
from core.data.trade_entry import TradeEntry


class PricebookProcessor(ProcessorBase):
    def __init__(self, pair):
        self._pair = pair
        self._sell_container = None
        self._buy_container = None

        self._w_sell_container = {}
        self._w_buy_container = {}

        self._current_time = 0.0
        self._is_service_mode_active = False
        self._is_in_service_entry_area = False

    @property
    def is_ready(self):
        return self._buy_container is not None and self._sell_container is not None

    @property
    def is_in_service_entry_area(self):
        return self._is_in_service_entry_area

    @property
    def buy_levels(self):
        levels = self._get_levels(self._buy_container, True)
        return levels

    @property
    def sell_levels(self):
        levels = self._get_levels(self._sell_container, False)
        return reversed(levels)

    @property
    def current_depth(self):
        return min(len(self._buy_container), len(self._sell_container))

    def accept(self, entry):
        self._is_service_mode_active = entry.is_service_entry
        self._is_in_service_entry_area = entry.is_service_entry
        super().accept(entry)

    def reset(self, is_buy):
        self._write_container(is_buy, {})

    def write(self, is_buy, price, amount, timestamp):
        self._current_time = max(self._current_time, timestamp)

        if self._is_service_mode_active:
            # in service mode, direct writes are performed
            container = self._choose_container(is_buy, self._buy_container, self._sell_container)
        else:
            container = self._choose_container(is_buy, self._w_buy_container, self._w_sell_container)

        if amount == 0.0:
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

        if self._is_service_mode_active:
            # in service mode, the buy/sells are updated directly
            return

        if is_buy:

            if self._w_buy_container is self._buy_container:
                return

            if len(self._w_buy_container) >= BOOK_DEPTH:
                self._buy_container = self._w_buy_container

        else:
            if self._w_sell_container is self._sell_container:
                return

            if len(self._w_sell_container) >= BOOK_DEPTH:
                self._sell_container = self._w_sell_container

    def flush(self):
        print(" ")
        print("SELLS")
        for level in self.sell_levels:
            print(level)
        print()

    def inject(self, buy_container, sell_container, w_buy_container, w_sell_container):
        self._buy_container = buy_container
        self._sell_container = sell_container
        self._w_buy_container = w_buy_container
        self._w_sell_container = w_sell_container

    def get_dump(self):
        return self._buy_container, self._sell_container, self._w_buy_container, self._w_sell_container

    def _get_levels(self, container, increasing_accumulation):
        borders = sorted(container.items(), key=lambda i: i[0], reverse=increasing_accumulation)

        acc = 0.0
        for i in range(len(borders)):
            border_value = borders[i][1][0]
            acc += border_value
            new_border = list(borders[i])
            new_border[1] = acc
            borders[i] = tuple(new_border)

        return borders

    def dump_to_entries(self) -> List[TradeEntry]:
        result = []
        result.extend(self._dump_container(self._buy_container, is_buy=True, is_service=True))
        result.extend(self._dump_container(self._sell_container, is_buy=False, is_service=True))

        if self._buy_container is not self._w_buy_container:
            result.extend(self._dump_container(self._w_buy_container, is_buy=True, is_service=False))

        if self._sell_container is not self._w_sell_container:
            result.extend(self._dump_container(self._w_sell_container, is_buy=False, is_service=False))

        return result

    def _dump_container(self, container, is_buy, is_service):
        if is_service:
            # one of the buy/sell service entries will be used as top level index
            yield TradeEntry.create_entry(self._pair, is_buy, 0.0, 0.0, self._current_time, is_reset=True,
                                          is_service=True)

        if container is None:
            return

        for price, (volume, timestamp) in container.items():
            yield TradeEntry.create_entry(self._pair, is_buy, price, volume, timestamp, is_reset=False,
                                          is_service=is_service)

    def _write_container(self, is_buy, value):
        if is_buy:
            self._w_buy_container = value
        else:
            self._w_sell_container = value

        if self._is_service_mode_active:
            if is_buy:
                self._buy_container = value
            else:
                self._sell_container = value

    def _choose_container(self, is_first, c1, c2):
        return c1 if is_first else c2
