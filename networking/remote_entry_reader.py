from threading import Lock
from typing import Callable, List

from data.entry_reader_base import EntryReaderBase
from data.storage_writer import StorageWriter
from data.trade_entry import TradeEntry


class RemoteEntryReader(EntryReaderBase):
    def __init__(self, pair: str, entry_count: int, observer: 'RemoteObserver'):
        super().__init__(pair)

        self._observer = observer

        self._L_cache = Lock()
        self._cached_buckets = {}
        self._full_buckets = set()
        self._entry_count = entry_count
        self._subscribers = []

    def get_entry(self, entry_index: int):
        bucket_id, offset = self._get_bucket_id(entry_index)
        bucket = self._get_bucket(bucket_id, need_full=True)

        if bucket is None or len(bucket) < offset:
            # index is not available yet
            return None

        return bucket[offset]

    def get_entry_count(self):
        raise NotImplementedError()

    def find_pricebook_start(self, start_time: float):
        return self._observer.find_pricebook_start(self.pair, start_time)

    def subscribe(self, feed_handler: Callable[[int, List[TradeEntry]], None]):
        self._subscribers.append(feed_handler)

    def _get_bucket(self, bucket_index, need_full=False):
        if (bucket_index not in self._cached_buckets) or \
                (need_full and bucket_index not in self._full_buckets):
            bucket = self._observer.get_bucket(self.pair, bucket_index)
            self._receive_bucket(bucket_index, bucket)
            self._full_buckets.add(bucket_index)

        with self._L_cache:
            return self._cached_buckets[bucket_index]

    def _get_bucket_id(self, entry_index: int):
        bucket_size: int = StorageWriter.bucket_entry_count
        return int(entry_index / bucket_size), entry_index % bucket_size

    def _receive_entries(self, start_entry_index, entries: List[TradeEntry]):
        entry_index = start_entry_index
        for entry in entries:
            bucket_index = int(entry_index / StorageWriter.bucket_entry_count)

            self._set_bucket_entry(bucket_index, entry_index, entry)
            entry_index += 1

        for subscriber in self._subscribers:
            subscriber(start_entry_index, entries)

    def _receive_bucket(self, bucket_start_index, bucket: List[TradeEntry]):
        entry_index = bucket_start_index * StorageWriter.bucket_entry_count
        for entry in bucket:
            self._set_bucket_entry(bucket_start_index, entry_index, entry)
            entry_index += 1

    def _set_bucket_entry(self, bucket_index, entry_index, entry):
        with self._L_cache:
            entry_offset = entry_index % StorageWriter.bucket_entry_count
            if bucket_index not in self._cached_buckets:
                self._cached_buckets[bucket_index] = [None] * StorageWriter.bucket_entry_count

            self._cached_buckets[bucket_index][entry_offset] = entry
            self._entry_count = max(self._entry_count, entry_index)
