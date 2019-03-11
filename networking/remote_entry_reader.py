from typing import Callable, List

from data.entry_reader_base import EntryReaderBase
from data.storage_writer import StorageWriter
from data.trade_entry import TradeEntry


class RemoteEntryReader(EntryReaderBase):
    def __init__(self, pair: str, entry_count: int, observer: 'RemoteObserver'):
        super().__init__(pair)

        self._observer = observer

        self._cached_buckets = {}
        self._entry_count = entry_count
        self._subscribers = []

    def get_entry(self, entry_index: int):
        bucket_id, offset = self._get_bucket_id(entry_index)
        bucket = self._get_bucket(bucket_id)

        if bucket is None or len(bucket) < offset:
            # index is not available yet
            return None

        return bucket[offset]

    def get_entry_count(self):
        raise NotImplementedError()

    def subscribe(self, feed_handler: Callable[[int, List[TradeEntry]], None]):
        self._subscribers.append(feed_handler)

    def _get_bucket(self, bucket_id):
        if bucket_id not in self._cached_buckets:
            self._cached_buckets[bucket_id] = self._observer.get_bucket(self.pair, bucket_id)

        return self._cached_buckets[bucket_id]

    def _get_bucket_id(self, entry_index: int):
        bucket_size: int = StorageWriter.bucket_entry_count
        return int(entry_index / bucket_size), entry_index % bucket_size

    def _receive_entries(self, start_entry_index, entries: List[TradeEntry]):
        for subscriber in self._subscribers:
            subscriber(start_entry_index, entries)
