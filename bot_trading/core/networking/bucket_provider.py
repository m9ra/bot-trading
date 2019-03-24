from threading import RLock
from typing import List, Callable, Dict

from bot_trading.core.data.storage_writer import StorageWriter
from bot_trading.core.data.trade_entry import TradeEntry
from bot_trading.core.networking.bucket_cache import BucketCache


class BucketProvider(object):
    @classmethod
    def get_bucket_id(cls, entry_index: int):
        return int(entry_index / StorageWriter.bucket_entry_count), int(entry_index % StorageWriter.bucket_entry_count)

    @property
    def peek_entry_count(self):
        return self._current_peek_entry_index

    def __init__(self, pair: str, entry_count: int, async_bucket_requester: Callable[[str, int], None]):
        self._requester = async_bucket_requester
        self._pair = pair

        self._L_entry_index = RLock()
        self._L_buckets = RLock()
        self._buckets: Dict[int, BucketCache] = {}
        self._current_peek_entry_index = entry_count

    def read(self, entry_index):
        bucket, bucket_offset = self._get_bucket(entry_index)

        can_request_bucket = entry_index < self._current_peek_entry_index
        return bucket.read(bucket_offset, can_request_bucket)

    def write(self, first_entry_index, entries: List[TradeEntry]):
        current_index = first_entry_index
        for entry in entries:
            self._write(current_index, entry)
            current_index += 1

    def close(self):
        for bucket in self._buckets.values():
            bucket.close()

    def _write(self, entry_index, entry: TradeEntry):
        with self._L_entry_index:
            self._current_peek_entry_index = max(self._current_peek_entry_index, entry_index)

        bucket, offset = self._get_bucket(entry_index)
        bucket.write(offset, entry)

    def _get_bucket(self, entry_index):
        bucket_id, bucket_offset = BucketProvider.get_bucket_id(entry_index)
        bucket = self._buckets.get(bucket_id, None)
        if bucket is None:
            with self._L_buckets:
                bucket = self._buckets.get(bucket_id, None)
                if bucket is None:
                    bucket = BucketCache(self._pair, bucket_id, self._requester)
                    self._buckets[bucket_id] = bucket

        return bucket, bucket_offset
