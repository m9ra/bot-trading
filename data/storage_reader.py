import os
from io import SEEK_SET, SEEK_END
from math import floor
from typing import Tuple, Optional, List

from data.storage_index import StorageIndex
from data.storage_writer import StorageWriter
from data.trade_entry import TradeEntry


class StorageReader(object):
    def __init__(self, pair):
        self.pair = pair
        self._peek_entry_index = 0
        self._files = {}

        self._current_last_index = 0

    def get_peek_entry(self) -> TradeEntry:
        return self._parse_entry(self._peek_entry_index)

    def get_entry(self, index):
        return self._parse_entry(index)

    def shift_to_next_entry(self):
        self._peek_entry_index += 1

    def get_peek_index(self) -> int:
        return self._peek_entry_index

    def update_index(self, index: StorageIndex):
        max_block_entry_count = 1000
        entry_count = self.get_entry_count()
        next_entry_index = index.last_entry_index + 1
        while next_entry_index < entry_count:
            block_entry_count = min(max_block_entry_count, entry_count - next_entry_index)

            entry_block = self._read_block(next_entry_index, block_entry_count)
            index.accept_block(entry_block)
            next_entry_index += block_entry_count

    def get_date_range(self) -> Optional[Tuple[float, float]]:
        entry_count = self.get_entry_count()
        if entry_count == 0:
            return None

        first_entry = self._parse_entry(0)
        last_entry = self._parse_entry(entry_count - 1)
        return (first_entry.timestamp, last_entry.timestamp)

    def get_entry_count(self):
        file = self._get_last_file()
        return self._get_file_entry_count(file)

    def get_bucket_count(self):
        return int(self.get_entry_count() / StorageWriter.bucket_entry_count)

    def validate_date_sequence(self):
        last_timestamp = 0
        for i in range(self.get_entry_count()):
            timestamp = self._parse_entry(i).timestamp
            if timestamp < last_timestamp:
                for j in range(max(0, i - 20), min(self.get_entry_count(), i + 20)):
                    if j == i:
                        print("==>", end="")
                    print(self._parse_entry(j))
                raise AssertionError(f"sequence is not consistent at {i} for {last_timestamp} vs {timestamp}")

            last_timestamp = timestamp

    def find_book_entries(self, start: float, end: float, book_size: int):
        entry_count = self.get_entry_count()
        if entry_count <= 0:
            return None

        _, date_end = self.get_date_range()
        if start > date_end:
            # search is out of the interval
            return []

        current_position = self.find_pricebook_start(start, book_size)

        # collect the window
        result = []
        while True:
            entry = self._parse_entry(current_position)
            if entry.timestamp <= end:
                result.append(entry)
            else:
                break

            current_position += 1
            if current_position >= entry_count:
                break

        return result

    def find_pricebook_start(self, start, book_size):
        current_position = 0
        interval_start = 0
        interval_end = self.get_bucket_count()
        # find the nearest lower index (binary search on buckets)
        while interval_end - interval_start > 1:
            current_bucket = int((interval_end + interval_start) / 2)
            current_position = current_bucket * StorageWriter.bucket_entry_count
            current_entry = self.get_entry(current_position)
            timestamp = current_entry.timestamp

            if timestamp > start:
                interval_end = current_bucket
            else:
                interval_start = current_bucket

        return interval_start * StorageWriter.bucket_entry_count

    def _parse_entry(self, entry_index) -> TradeEntry:
        file, in_file_entry_index = self._get_file(entry_index)
        if file is None:
            raise ValueError(f"Invalid index {entry_index}")

        chunk_size = TradeEntry.chunk_size
        file.seek(in_file_entry_index * chunk_size, SEEK_SET)
        chunk = file.read(chunk_size)

        if len(chunk) != chunk_size:
            raise AssertionError(f"Incorrect chunk returned: {chunk}")

        return TradeEntry(self.pair, chunk)

    def _get_file(self, entry_index):
        file_index, in_file_index = StorageWriter.get_file_index(entry_index)
        file = self._get_file_by_index(file_index)

        return file, in_file_index

    def _get_file_by_index(self, file_index):
        if file_index not in self._files:
            path = StorageWriter.get_storage_path(self.pair, file_index)
            if not os.path.exists(path):
                return None

            self._files[file_index] = open(path, "rb")
            self._current_last_index = max(self._current_last_index, file_index)

        return self._files[file_index]

    def _get_last_file(self):
        if self._current_last_index in self._files:
            entry_count = self._get_file_entry_count(self._files[self._current_last_index])

            if entry_count < StorageWriter.file_entry_count:
                # then known last file is not filled yet -> its really the last file
                return self._get_file_by_index(self._current_last_index)

        # otherwise search for the really last file
        i = 0
        while True:
            path = StorageWriter.get_storage_path(self.pair, i)
            if not os.path.exists(path):
                break

            i += 1

        return self._get_file_by_index(i - 1)

    def _get_file_entry_count(self, file):
        file.seek(0, SEEK_END)
        length = file.tell()
        return int(floor(length / TradeEntry.chunk_size))

    def _parse_entry_block(self, index, entry_count) -> List[TradeEntry]:
        raise NotImplementedError("Block reading over multiple files ")
        self._seek_entry(index)

        block_size = StorageWriter.entry_size * entry_count
        block_chunk = self._file.read(block_size)
        if (len(block_chunk) != block_size):
            raise AssertionError(
                f"Incorrect block chunk returned, requested len {block_size} but got {len(block_chunk)}")

        for start in range(0, block_size, StorageWriter.entry_size):
            chunk = block_chunk[start:start + StorageWriter.entry_size]
            yield TradeEntry(self.pair, chunk)
