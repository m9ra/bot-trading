from core.processors.pricebook_processor import PricebookProcessor
from data.parsing import parse_pair
from data.trade_entry import TradeEntry
from trading.fund import Fund
from trading.pricebook_view_state import PricebookViewState


class PricebookView(object):
    def __init__(self, state: PricebookViewState, update_reader, end_index):
        self._reader = update_reader
        self.source_currency, self.target_currency = parse_pair(self._reader.pair)

        self._end = end_index
        self._current_index = state.current_index
        self._current_time = state.current_time

        if self._current_index > end_index:
            raise ValueError("Current index can't be greater than the end.")

        self._processor = PricebookProcessor(self._reader.pair)
        state.inject_to(self._processor)

    @property
    def sell_levels(self):
        return list(self._processor.sell_levels)

    @property
    def buy_levels(self):
        return list(self._processor.buy_levels)

    @property
    def is_synchronized(self):
        return self._processor.is_ready

    def fast_forward_to(self, timestamp):
        while self._current_index < self._end:
            entry = self._reader.get_entry(self._current_index)
            if entry.timestamp > timestamp:
                break

            self._process_entry(entry)

    def forward_to_next_change(self):
        if self._current_index + 1 >= self._end:
            raise StopIteration()

        self._current_index += 1

    def after_conversion(self, fund: Fund):
        is_reversed = self.target_currency == fund.currency
        is_valid = is_reversed or self.source_currency == fund.currency

        if not is_valid:
            raise ValueError(f"Can't process sell of {fund} on pair {self._reader.pair}")

        # todo consider levels
        # todo consider fees
        if is_reversed:
            price_per_source_unit = self.sell_levels[0][0]
            return Fund(fund.amount / price_per_source_unit, self.source_currency)
        else:
            price_per_source_unit = self.buy_levels[0][0]
            return Fund(fund.amount * price_per_source_unit, self.target_currency)

    def _process_entry(self, entry: TradeEntry):
        self._processor.accept(entry)
        self._current_index += 1
        self._current_time = max(self._current_time, entry.timestamp)

    def _dump_state(self):
        state = PricebookViewState(self._current_index, self._current_time)
        state.load_from(self._processor)

        return state
