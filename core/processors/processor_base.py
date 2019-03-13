from core.data.trade_entry import TradeEntry


class ProcessorBase(object):
    def accept(self, entry: TradeEntry):
        if entry.is_reset:
            self.reset(entry.is_buy)
        else:
            self.write(entry.is_buy, entry.price, entry.volume, entry.timestamp)

    def write(self, is_buy: bool, price: float, volume: float, timestamp: float):
        raise NotImplementedError("must be overridden")

    def reset(self, is_buy: bool):
        raise NotImplementedError("must be overridden")

    def flush(self):
        # there is nothing to process by default
        pass
