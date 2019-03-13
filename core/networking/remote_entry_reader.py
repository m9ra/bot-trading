from typing import Callable, List

from core.data.entry_reader_base import EntryReaderBase
from core.data.storage_writer import StorageWriter
from core.data.trade_entry import TradeEntry
from core.networking.bucket_provider import BucketProvider


class RemoteEntryReader(EntryReaderBase):
    def __init__(self, pair: str, entry_count: int, observer: 'RemoteObserver'):
        super().__init__(pair)

        self._observer = observer
        self._subscribers = []
        self._bucket_provider = BucketProvider(pair, entry_count, observer.async_get_bucket)

    def get_entry(self, entry_index: int):
        return self._bucket_provider.read(entry_index)

    def get_entry_count(self):
        return self._bucket_provider.peek_entry_count

    def find_pricebook_start(self, start_time: float):
        return self._observer.find_pricebook_start(self.pair, start_time)

    def subscribe(self, feed_handler: Callable[[int, List[TradeEntry]], None]):
        self._subscribers.append(feed_handler)

    def _receive_peek_entries(self, first_entry_index, entries: List[TradeEntry]):
        self._bucket_provider.write(first_entry_index, entries)

        for subscriber in self._subscribers:
            subscriber(first_entry_index, entries)

    def _receive_bucket(self, bucket_index, bucket: List[TradeEntry]):
        self._bucket_provider.write(bucket_index * StorageWriter.bucket_entry_count, bucket)
