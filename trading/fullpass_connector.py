from collections import defaultdict
from typing import List

from data.entry_reader_base import EntryReaderBase
from data.trade_entry import TradeEntry
from trading.connector_base import ConnectorBase


class FullpassConnector(ConnectorBase):
    def __init__(self, entry_readers: List[EntryReaderBase]):
        super().__init__(entry_readers)

        self._reader_peeks = defaultdict(int)
        self._reader_limits = {}
        for reader in entry_readers:
            self._reader_limits[reader] = reader.get_entry_count()

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
