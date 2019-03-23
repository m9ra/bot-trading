from collections import defaultdict
from typing import List

from bot_trading.core.data.entry_reader_base import EntryReaderBase
from bot_trading.core.data.parsing import parse_pair
from bot_trading.core.data.trade_entry import TradeEntry
from bot_trading.core.runtime.connector_base import ConnectorBase


class FullpassConnector(ConnectorBase):
    def __init__(self, entry_readers: List[EntryReaderBase]):
        super().__init__(entry_readers)

        self._reader_peeks = defaultdict(int)
        self._reader_limits = {}
        for reader in entry_readers:
            self._reader_limits[reader] = reader.get_entry_count()

    def set_run_start(self, timestamp):
        for reader in self._readers:
            self._reader_peeks[reader] = reader.find_pricebook_start(timestamp)

    def get_start_timestamp(self):
        timestamp = float("inf")
        for reader in self._readers:
            timestamp = min(timestamp, reader.get_entry(self._reader_peeks[reader]).timestamp)

        return timestamp

    def set_run_end(self, end_timestamp):
        for reader in self._readers:
            pricebook = self.get_pricebook(*parse_pair(reader.pair), end_timestamp)
            self._reader_limits[reader] = pricebook._current_index

    def blocking_get_next_entry(self) -> TradeEntry:
        best_reader = None
        best_timestamp = None
        for reader in self._readers:
            if self._reader_peeks[reader] >= self._reader_limits[reader]:
                continue

            entry = reader.get_entry(self._reader_peeks[reader])

            if best_timestamp is None or best_timestamp > entry.timestamp:
                best_timestamp = entry.timestamp
                best_reader = reader

        if best_reader is None:
            raise StopIteration()

        entry = best_reader.get_entry(self._reader_peeks[best_reader])
        self._reader_peeks[best_reader] += 1

        return entry
