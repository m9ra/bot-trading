import os
import pickle
import random
import struct
import time
import traceback
from os import SEEK_SET
from queue import Queue
from threading import Thread
from typing import Dict, Tuple, List, Callable
from bot_trading.configuration import LOCAL_DISK_CACHE_SIZE
from bot_trading.core.data.storage_writer import StorageWriter
from bot_trading.core.data.trade_entry import TradeEntry


class DiskCache(object):
    @classmethod
    def get_cache_path(cls):
        return "./bucket_cache.bin"

    def __init__(self, cache_size: int):
        self._cache: Dict[str, CacheEntry] = {}
        self._id_to_cache_entry: Dict[int, CacheEntry] = {}
        self._disk_queue = Queue()
        self._allowed_cache_entry_count = int(cache_size / CacheEntry.chunk_size)
        self._available_cache_entry_ids = set(range(self._allowed_cache_entry_count))
        self._has_change_update = False

        print("LOADING DISK CACHE...")
        try:
            with open(DiskCache.get_cache_path(), "rb") as f:
                while True:  # reading cache entry behind the file size will raise an exception
                    entry = self._read_next_cache_entry(f)
                    if entry is None:
                        # entry is corrupted
                        continue

                    if entry.key in self._cache:
                        continue  # when running multiple processes, some entries can be written multiple times in the cache file

                    self._put(entry)
                    if entry.cache_entry_id in self._available_cache_entry_ids:
                        self._available_cache_entry_ids.remove(entry.cache_entry_id)

        except:
            print("\t complete")

        Thread(target=self._journal_writer, daemon=True).start()

    def get_bucket(self, pair: str, bucket_index: int):
        key = CacheEntry.get_key(pair, bucket_index)
        entry = self._cache.get(key)

        if entry is None:
            return None

        return entry.payload

    def set_bucket(self, pair: str, bucket_index: int, payload: bytes):
        if len(payload) != StorageWriter.bucket_entry_count * TradeEntry.chunk_size:
            return  # bucket is not complete

        cache_entry_id = self._allocate_cache_entry_id()
        entry = CacheEntry.from_raw(cache_entry_id, pair, bucket_index, payload)
        self._cache[entry.key] = entry
        self._disk_queue.put(entry)  # request disk write

    def _put(self, entry):
        self._cache[entry.key] = entry
        self._id_to_cache_entry[entry.cache_entry_id] = entry

    def _allocate_cache_entry_id(self) -> int:
        if self._available_cache_entry_ids:
            try:
                return self._available_cache_entry_ids.pop()
            except:
                # set is empty - it won't get here for the second time
                return self._allocate_cache_entry_id()
        else:
            id = random.randint(0, self._allowed_cache_entry_count)
            entry = self._id_to_cache_entry.pop(id, None)
            if entry:
                self._cache.pop(entry.key, None)

            return id

    def _journal_writer(self):
        cache_path = DiskCache.get_cache_path()
        while True:
            entry: CacheEntry = self._disk_queue.get()
            chunk = entry.to_chunk()

            while True:
                try:
                    # try to write the data (it may fail because of concurrent write attempts)
                    with open(cache_path, "r+b") as f:
                        f.seek(entry.entry_offset, SEEK_SET)
                        f.write(chunk)
                except FileNotFoundError:
                    with (open(cache_path, "c")) as f:
                        f.close()
                        time.sleep(5.0)
                        continue
                except:
                    traceback.print_exc()
                    time.sleep(5.0)
                    continue  # try again

                break  # entry was successfully written

    def _read_next_cache_entry(self, f):
        entry_offset = f.tell()
        chunk = f.read(CacheEntry.chunk_size)
        if len(chunk) != CacheEntry.chunk_size:
            raise StopIteration("end of file")

        return CacheEntry.from_chunk(entry_offset, chunk)


class CacheEntry(object):
    # 16B*ascii + 8B bucket index + 8B checksum + entry payload
    chunk_size = 16 + 8 + 8 + StorageWriter.bucket_entry_count * TradeEntry.chunk_size

    @property
    def entry_offset(self):
        return CacheEntry.chunk_size * self.cache_entry_id

    @property
    def key(self):
        return CacheEntry.get_key(self.pair, self.bucket_index)

    def __init__(self, cache_entry_id: int, pair: str, bucket_index: int, payload: bytes):
        self.cache_entry_id = cache_entry_id
        self.pair = pair
        self.bucket_index = bucket_index
        self.payload = payload

    @classmethod
    def get_key(cls, pair: str, bucket_index: int):
        return f"{pair}{bucket_index}"

    @classmethod
    def from_raw(cls, cache_entry_id: int, pair: str, bucket: int, payload: bytes):
        entry = CacheEntry(cache_entry_id, pair, bucket, payload)
        return entry

    @classmethod
    def from_chunk(cls, entry_offset, chunk: bytes):
        entry_id = int(entry_offset / CacheEntry.chunk_size)
        pair = chunk[:16].decode('ascii').strip()
        bucket_index, checksum = struct.unpack("qq", chunk[16:32])
        payload = chunk[32:]

        real_checksum = CacheEntry.get_checksum(pair, bucket_index, payload)
        if real_checksum != checksum:
            return None

        return CacheEntry(entry_id, pair, bucket_index, payload)

    def to_chunk(self) -> bytes:
        result = []
        pair_data = self.pair.ljust(16, ' ')
        if len(pair_data) != 16:
            raise AssertionError("Incorrect pair data serialization")

        checksum = CacheEntry.get_checksum(self.pair, self.bucket_index, self.payload)

        result.extend(pair_data.encode('ascii'))
        result.extend(CacheEntry.get_longlong_bytes(self.bucket_index))
        result.extend(CacheEntry.get_longlong_bytes(checksum))
        result.extend(self.payload)

        if len(result) != CacheEntry.chunk_size:
            raise AssertionError("Invalid cache entry serialization")

        return bytes(result)

    @classmethod
    def get_longlong_bytes(cls, number: int):
        result = struct.pack('q', number)
        if len(result) != 8:
            raise AssertionError("Invalid number serialization")

        return result

    @classmethod
    def get_checksum(cls, pair, bucket_index, payload):
        return 11 + sum(pair.encode('ascii')) + sum(CacheEntry.get_longlong_bytes(bucket_index)) + sum(payload)
