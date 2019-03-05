from typing import List

from data.parsing import make_pair, parse_pair, reverse_pair
from data.storage_reader import StorageReader
from data.trade_entry import TradeEntry
from trading.connector_base import ConnectorBase
from trading.pricebook_view import PricebookView
from trading.pricebook_view_provider import PricebookViewProvider


class LocalStorageConnector(ConnectorBase):
    def __init__(self, storage_readers):
        self._readers: List[StorageReader] = list(storage_readers)
        self._current_time = 0

        self._view_providers = {}
        for reader in storage_readers:
            provider = PricebookViewProvider(reader)
            self._view_providers[reader.pair] = provider
            self._view_providers[reverse_pair(reader.pair)] = provider

    @property
    def current_time(self):
        return self._current_time

    def next_entry(self) -> TradeEntry:
        best_reader = None
        best_timestamp = None
        for reader in self._readers:
            entry = reader.get_peek_entry()
            if entry is None:
                continue

            if best_timestamp is None or best_timestamp > entry.timestamp:
                best_timestamp = entry.timestamp
                best_reader = reader

        if best_reader is None:
            raise StopIteration()

        entry = best_reader.get_peek_entry()
        best_reader.shift_to_next_entry()

        self._current_time = max(self._current_time, entry.timestamp)
        return entry

    def get_pricebook(self, source_currency, target_currency, timestamp) -> PricebookView:
        pair = make_pair(source_currency, target_currency)
        pricebook_provider = self._view_providers.get(pair)

        if pricebook_provider is None:
            raise ValueError(f"Pair {pair} was not found.")

        return pricebook_provider.get_pricebook_view(timestamp)

    def is_synchronized(self, pair, timestamp):
        pricebook = self.get_pricebook(*parse_pair(pair), timestamp)
        return pricebook.is_synchronized
