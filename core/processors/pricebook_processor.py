from configuration import BOOK_DEPTH
from core.processors.processor_base import ProcessorBase


class PricebookProcessor(ProcessorBase):
    def __init__(self, pair):
        self._pair = pair
        self._sell_container = None
        self._buy_container = None

        self._w_sell_container = {}
        self._w_buy_container = {}

        self._depth = BOOK_DEPTH

    @property
    def is_ready(self):
        return self._buy_container is not None and self._sell_container is not None

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

    def reset(self, is_buy):
        if is_buy:
            self._w_buy_container = {}
        else:
            self._w_sell_container = {}

    def write(self, is_buy, price, amount, timestamp):
        container = self._w_buy_container if is_buy else self._w_sell_container
        if amount == 0.0:
            if price in container:
                del container[price]
        else:
            container[price] = amount

        if len(container) > self._depth:
            new_container = dict(sorted(container.items(), key=lambda i: i[0], reverse=is_buy)[0:self._depth])
            container.clear()
            container.update(new_container)

        if is_buy:
            if self._w_buy_container is self._buy_container:
                return

            if len(self._w_buy_container) >= self._depth:
                self._buy_container = self._w_buy_container

        else:
            if self._w_sell_container is self._sell_container:
                return

            if len(self._w_sell_container) >= self._depth:
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
            border_value = borders[i][1]
            acc += border_value
            new_border = list(borders[i])
            new_border[1] = acc
            borders[i] = tuple(new_border)

        return borders
