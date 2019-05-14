from bot_trading.core.exceptions import TradeEntryNotAvailableException
from bot_trading.core.data.parsing import parse_pair
from bot_trading.core.data.pricebook_processor_state import PricebookProcessorState
from bot_trading.core.data.trade_entry import TradeEntry
from bot_trading.core.processors.pricebook_processor import PricebookProcessor
from bot_trading.trading.fund import Fund


class PricebookView(object):
    def __init__(self, state: PricebookProcessorState, reader):
        self._reader = reader
        self.source_currency, self.target_currency = parse_pair(self._reader.pair)

        self._current_index = state.current_index
        self._current_time = state.current_time

        self._processor = PricebookProcessor(self._reader.pair)
        state.inject_to(self._processor)

    @property
    def pair(self):
        return self._reader.pair

    @property
    def sell_levels(self):
        return list(self._processor.sell_levels)

    @property
    def buy_levels(self):
        return list(self._processor.buy_levels)

    @property
    def spread(self):
        return self._processor.spread

    @property
    def bid_ask(self):
        return self._processor.bid_ask

    @property
    def is_synchronized(self):
        return self._processor.is_ready

    def fast_forward_to(self, timestamp):
        while True:
            entry = self._reader.get_entry(self._current_index)
            if entry is None:
                if self.is_synchronized:
                    self._reader.get_entry(self._current_index)
                    # it is OK to end up before the timestamp - it means that no change till the timestamp arrived
                    return False  # desired time was not reached

                raise TradeEntryNotAvailableException(self.pair, timestamp, self._current_index)

            if entry.timestamp > timestamp:
                if self._processor.is_book_available:
                    return True

            self._process_entry(entry)

    def forward_to_next_change(self):
        entry = self._reader.get_entry(self._current_index)
        self._process_entry(entry)

    def get_entry(self, entry_index: int):
        return self._reader.get_entry(entry_index)

    def after_conversion(self, fund: Fund):
        is_reversed = self.target_currency == fund.currency
        is_valid = is_reversed or self.source_currency == fund.currency

        if not is_valid:
            raise ValueError(f"Can't process sell of {fund} on pair {self._reader.pair}")

        # todo consider levels
        # todo consider fees
        bid, ask = self.bid_ask
        if is_reversed:
            price_per_source_unit = ask
            return Fund(fund.amount / price_per_source_unit, self.source_currency)
        else:
            price_per_source_unit = bid
            return Fund(fund.amount * price_per_source_unit, self.target_currency)

    def to_convert(self, fund: Fund):
        is_reversed = self.target_currency == fund.currency
        is_valid = is_reversed or self.source_currency == fund.currency

        if not is_valid:
            raise ValueError(f"Can't process sell of {fund} on pair {self._reader.pair}")

        # todo consider levels
        # todo consider fees
        bid, ask = self.bid_ask
        if is_reversed:
            price_per_source_unit = bid
            return Fund(fund.amount / price_per_source_unit, self.source_currency)
        else:
            price_per_source_unit = ask
            return Fund(fund.amount * price_per_source_unit, self.target_currency)

    def _process_entry(self, entry: TradeEntry):
        self._processor.accept(entry)
        self._current_index += 1
        self._current_time = max(self._current_time, entry.timestamp)

    def _dump_state(self):
        state = PricebookProcessorState(self._current_index, self._current_time)
        state.load_from(self._processor)

        return state
