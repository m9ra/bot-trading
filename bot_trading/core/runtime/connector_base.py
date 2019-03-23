from typing import List

from bot_trading.core.data.entry_reader_base import EntryReaderBase
from bot_trading.core.data.parsing import reverse_pair, make_pair
from bot_trading.core.data.trade_entry import TradeEntry
from bot_trading.trading.pricebook_view import PricebookView
from bot_trading.core.runtime.pricebook_view_provider import PricebookViewProvider


class ConnectorBase(object):
    def blocking_get_next_entry(self) -> TradeEntry:
        raise NotImplementedError("must be overridden")

    @property
    def current_time(self):
        return self._current_time

    def __init__(self, entry_readers: List[EntryReaderBase]):
        self._readers: List[EntryReaderBase] = list(entry_readers)
        self._subscribers = []
        self._current_time = 0.0

        self._view_providers = {}
        for reader in self._readers:
            provider = PricebookViewProvider(reader)

            self._view_providers[reader.pair] = provider
            self._view_providers[reverse_pair(reader.pair)] = provider

    def get_pricebook(self, source_currency, target_currency, timestamp) -> PricebookView:
        pair = make_pair(source_currency, target_currency)
        pricebook_provider = self._view_providers.get(pair)

        if pricebook_provider is None:
            raise ValueError(f"Pair {pair} was not found.")

        return pricebook_provider.get_pricebook_view(timestamp)

    def subscribe(self, subscriber):
        self._subscribers.append(subscriber)

    def _read_entries(self):
        while True:
            yield self.blocking_get_next_entry()

    def run(self):
        for entry in self._read_entries():
            self._current_time = max(self._current_time, entry.timestamp)

            for subscriber in self._subscribers:
                subscriber.receive(entry)
